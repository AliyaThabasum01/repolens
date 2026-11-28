
import ast
import json
from pathlib import Path


class ConfigurationAnalyzer(ast.NodeVisitor):

    def __init__(self, file_path):
        self.file_path = str(file_path)
        self.findings = []

    def add_finding(self, node, severity, issue):
        self.findings.append({
            "file": self.file_path,
            "line": node.lineno,
            "severity": severity,
            "issue": issue
        })

    def visit_Call(self, node):
        func = node.func

        # Detect yaml.load() without an explicit SafeLoader.
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "load"
            and isinstance(func.value, ast.Name)
            and func.value.id == "yaml"
        ):
            safe_loader = any(
                keyword.arg == "Loader"
                and isinstance(keyword.value, ast.Attribute)
                and keyword.value.attr in {
                    "SafeLoader",
                    "CSafeLoader"
                }
                for keyword in node.keywords
            )

            if not safe_loader:
                self.add_finding(
                    node,
                    "HIGH",
                    "yaml.load() does not explicitly use SafeLoader."
                )

        # Detect JSON loading for configuration review.
        if (
            isinstance(func, ast.Attribute)
            and func.attr in {"load", "loads"}
            and isinstance(func.value, ast.Name)
            and func.value.id == "json"
        ):
            self.add_finding(
                node,
                "INFO",
                "JSON data is being loaded. Review input validation."
            )

        # Detect direct environment variable access.
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "getenv"
            and isinstance(func.value, ast.Name)
            and func.value.id == "os"
        ):
            self.add_finding(
                node,
                "INFO",
                "Environment variable accessed. "
                "Check whether required variables have defaults."
            )

        self.generic_visit(node)

    def visit_Subscript(self, node):
        # Detect os.environ["VARIABLE"].
        if (
            isinstance(node.value, ast.Attribute)
            and node.value.attr == "environ"
            and isinstance(node.value.value, ast.Name)
            and node.value.value.id == "os"
        ):
            self.add_finding(
                node,
                "INFO",
                "Direct environment variable lookup detected. "
                "Ensure missing variables are handled."
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

    analyzer = ConfigurationAnalyzer(file_path)
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

        print("\n===== CONFIGURATION ANALYSIS REPORT =====")
        print(json.dumps(report, indent=4))

        with open(
            "configuration_analysis_report.json",
            "w",
            encoding="utf-8"
        ) as output:
            json.dump(report, output, indent=4)

        print("\nReport saved successfully!")

    except ValueError as error:
        print("Error:", error)

