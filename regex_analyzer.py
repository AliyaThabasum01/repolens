
import ast
import json
import re
from pathlib import Path


REGEX_FUNCTIONS = {
    "compile",
    "search",
    "match",
    "fullmatch",
    "findall",
    "finditer",
    "sub",
    "subn",
    "split"
}


def get_full_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        return get_full_name(node.value) + "." + node.attr

    return ""


def extract_pattern(node):
    if not node.args:
        return None

    pattern = node.args[0]

    if isinstance(pattern, ast.Constant):
        if isinstance(pattern.value, str):
            return pattern.value

    return None


def analyze_pattern(pattern, raw_string, line, file_path):
    findings = []

    def add(severity, issue):
        findings.append({
            "file": str(file_path),
            "line": line,
            "severity": severity,
            "pattern": pattern,
            "issue": issue
        })

    try:
        re.compile(pattern)

    except re.error as error:
        add(
            "HIGH",
            f"Invalid regular expression: {error}"
        )
        return findings

    # Detect nested quantifiers that may cause excessive backtracking.
    nested_patterns = [
        r"\([^)]*[+*][^)]*\)[+*{]",
        r"\([^)]*[+*][^)]*\)[+*?]"
    ]

    if any(re.search(rule, pattern) for rule in nested_patterns):
        add(
            "HIGH",
            "Possible nested quantifiers detected. "
            "Review for catastrophic backtracking."
        )

    # Flag wildcard combinations for manual review.
    if ".*" in pattern or ".+" in pattern:
        add(
            "LOW",
            "Greedy wildcard detected. "
            "Review whether a more specific pattern is possible."
        )

    # Check whether the source used a raw string.
    if not raw_string and "\\" in pattern:
        add(
            "MEDIUM",
            "Regex contains backslashes but may not use a raw string. "
            "Consider r'pattern'."
        )

    # Flag repeated broad quantifier combinations.
    if re.search(r"(\.\*|\.\+).*(\.\*|\.\+)", pattern):
        add(
            "MEDIUM",
            "Multiple greedy wildcard expressions detected. "
            "Review matching efficiency."
        )

    return findings


class RegexVisitor(ast.NodeVisitor):

    def __init__(self, file_path):
        self.file_path = file_path
        self.findings = []

    def visit_Call(self, node):
        function_name = get_full_name(node.func)

        if (
            function_name.startswith("re.")
            and function_name.split(".")[-1] in REGEX_FUNCTIONS
        ):
            pattern = extract_pattern(node)

            if pattern is not None:
                raw_string = False

                if node.args:
                    raw_string = isinstance(
                        node.args[0],
                        ast.Constant
                    ) and isinstance(
                        node.args[0].value,
                        str
                    )

                # Python AST does not preserve raw-string prefixes.
                # This flag is refined using the source line below.
                self.findings.extend(
                    analyze_pattern(
                        pattern,
                        raw_string,
                        node.lineno,
                        self.file_path
                    )
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
            "pattern": "",
            "issue": f"Unable to analyze file: {error}"
        }]

    visitor = RegexVisitor(file_path)
    visitor.visit(tree)

    # AST does not retain raw-string notation.
    # Remove the raw-string warning to avoid false positives.
    visitor.findings = [
        item for item in visitor.findings
        if "raw string" not in item["issue"]
    ]

    return visitor.findings


def analyze_directory(directory):
    root = Path(directory)

    if not root.exists() or not root.is_dir():
        raise ValueError("Please provide a valid directory.")

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

        print("\n===== REGEX ANALYSIS REPORT =====")
        print(json.dumps(report, indent=4))

        with open(
            "regex_analysis_report.json",
            "w",
            encoding="utf-8"
        ) as output:
            json.dump(report, output, indent=4)

        print("\nReport saved successfully!")

    except ValueError as error:
        print("Error:", error)
