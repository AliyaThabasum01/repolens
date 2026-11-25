
import ast
import json
from pathlib import Path


class FileIOAnalyzer(ast.NodeVisitor):

    def __init__(self, file_path):
        self.file_path = str(file_path)
        self.findings = []
        self.with_open_calls = set()

    def add_finding(self, node, severity, message):
        self.findings.append({
            "file": self.file_path,
            "line": node.lineno,
            "severity": severity,
            "issue": message
        })

    def visit_With(self, node):
        for item in node.items:
            context = item.context_expr

            if (
                isinstance(context, ast.Call)
                and isinstance(context.func, ast.Name)
                and context.func.id == "open"
            ):
                self.with_open_calls.add(id(context))

        self.generic_visit(node)

    def visit_Call(self, node):
        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "open"
        ):
            mode = "r"

            for keyword in node.keywords:
                if keyword.arg == "mode":
                    if isinstance(keyword.value, ast.Constant):
                        mode = keyword.value.value

            if node.args:
                if (
                    isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)
                    and (
                        "/" in node.args[0].value
                        or "\\" in node.args[0].value
                    )
                ):
                    self.add_finding(
                        node,
                        "LOW",
                        "Hardcoded file path detected. "
                        "Consider using pathlib or configuration."
                    )

            if id(node) not in self.with_open_calls:
                self.add_finding(
                    node,
                    "MEDIUM",
                    "open() is not directly inside a with statement. "
                    "Review whether the file is properly closed."
                )

            is_binary = "b" in mode

            has_encoding = any(
                keyword.arg == "encoding"
                for keyword in node.keywords
            )

            if not is_binary and not has_encoding:
                self.add_finding(
                    node,
                    "LOW",
                    "Text file opened without explicit encoding."
                )

            if any(flag in mode for flag in ("w", "a", "x")):
                self.add_finding(
                    node,
                    "INFO",
                    f"File opened in '{mode}' mode. "
                    "Review whether overwriting or appending is intended."
                )

        self.generic_visit(node)


def analyze_file(file_path):
    try:
        source = Path(file_path).read_text(
            encoding="utf-8"
        )

        tree = ast.parse(source)

    except (OSError, UnicodeError, SyntaxError) as error:
        return [{
            "file": str(file_path),
            "line": 0,
            "severity": "ERROR",
            "issue": f"Unable to analyze file: {error}"
        }]

    analyzer = FileIOAnalyzer(file_path)
    analyzer.visit(tree)

    return analyzer.findings


def analyze_directory(directory):
    root = Path(directory)

    if not root.exists() or not root.is_dir():
        raise ValueError("Please enter a valid directory.")

    findings = []

    excluded = {
        ".git",
        ".venv",
        "venv",
        "__pycache__"
    }

    for path in root.rglob("*.py"):
        if any(part in excluded for part in path.parts):
            continue

        findings.extend(analyze_file(path))

    return findings


def generate_report(findings):
    return {
        "total_findings": len(findings),
        "high_risk": sum(
            item["severity"] == "HIGH"
            for item in findings
        ),
        "medium_risk": sum(
            item["severity"] == "MEDIUM"
            for item in findings
        ),
        "low_risk": sum(
            item["severity"] == "LOW"
            for item in findings
        ),
        "informational": sum(
            item["severity"] == "INFO"
            for item in findings
        ),
        "errors": sum(
            item["severity"] == "ERROR"
            for item in findings
        ),
        "findings": findings
    }


if __name__ == "__main__":
    folder = input(
        "Enter Python project folder path: "
    ).strip()

    try:
        findings = analyze_directory(folder)
        report = generate_report(findings)

        print("\n===== FILE I/O ANALYSIS REPORT =====")
        print(json.dumps(report, indent=4))

        with open(
            "file_io_analysis_report.json",
            "w",
            encoding="utf-8"
        ) as output:
            json.dump(report, output, indent=4)

        print("\nReport saved successfully!")

    except ValueError as error:
        print("Error:", error)
