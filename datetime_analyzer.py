
import ast
import json
from pathlib import Path


RULES = {
    "utcnow": (
        "HIGH",
        "datetime.utcnow() is deprecated in Python 3.12. "
        "Prefer datetime.now(timezone.utc)."
    ),
    "today": (
        "LOW",
        "datetime.today() returns a naive datetime. "
        "Review timezone requirements."
    ),
    "strptime": (
        "INFO",
        "datetime.strptime() returns a naive datetime. "
        "Add timezone information if required."
    )
}


def get_call_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        return node.attr

    return ""


def get_full_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        return get_full_name(node.value) + "." + node.attr

    return ""


def analyze_file(file_path):
    findings = []

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

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        name = get_call_name(node.func)
        full_name = get_full_name(node.func)

        issue = None

        if name == "utcnow":
            issue = RULES["utcnow"]

        elif name == "today":
            issue = RULES["today"]

        elif name == "strptime":
            issue = RULES["strptime"]

        elif name == "now":
            if not any(
                keyword.arg == "tz"
                for keyword in node.keywords
            ):
                issue = (
                    "MEDIUM",
                    "datetime.now() has no explicit timezone. "
                    "Consider datetime.now(timezone.utc)."
                )

        elif name == "fromtimestamp":
            if not any(
                keyword.arg == "tz"
                for keyword in node.keywords
            ):
                issue = (
                    "MEDIUM",
                    "fromtimestamp() has no explicit timezone. "
                    "Consider supplying a timezone."
                )

        if issue:
            # Avoid flagging unrelated methods with the same name.
            if not any(
                term in full_name.lower()
                for term in ("datetime", "date")
            ):
                continue

            severity, message = issue

            findings.append({
                "file": str(file_path),
                "line": node.lineno,
                "severity": severity,
                "function": full_name,
                "issue": message
            })

    return findings


def analyze_directory(directory):
    root = Path(directory)

    if not root.exists() or not root.is_dir():
        raise ValueError("Invalid project directory.")

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

        print("\n===== DATETIME ANALYSIS REPORT =====")
        print(json.dumps(report, indent=4))

        with open(
            "datetime_analysis_report.json",
            "w",
            encoding="utf-8"
        ) as output:
            json.dump(report, output, indent=4)

        print("\nReport saved successfully!")

    except ValueError as error:
        print("Error:", error)
