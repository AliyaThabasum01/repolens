
import ast
import json
from pathlib import Path


RULES = {
    "pickle": {
        "severity": "HIGH",
        "message": "Pickle deserialization can execute malicious code when input is untrusted."
    },
    "eval": {
        "severity": "HIGH",
        "message": "eval() executes dynamically supplied Python expressions."
    },
    "exec": {
        "severity": "HIGH",
        "message": "exec() executes dynamically supplied Python code."
    },
    "marshal": {
        "severity": "MEDIUM",
        "message": "marshal deserialization should only process trusted data."
    }
}


def get_call_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        return node.attr

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

        if name in RULES:
            rule = RULES[name]

            findings.append({
                "file": str(file_path),
                "line": node.lineno,
                "severity": rule["severity"],
                "issue": rule["message"]
            })

        elif name == "load":
            # Detect yaml.load() specifically.
            if (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "yaml"
            ):
                has_safe_loader = any(
                    keyword.arg == "Loader"
                    and isinstance(keyword.value, ast.Attribute)
                    and keyword.value.attr in {
                        "SafeLoader",
                        "CSafeLoader"
                    }
                    for keyword in node.keywords
                )

                if not has_safe_loader:
                    findings.append({
                        "file": str(file_path),
                        "line": node.lineno,
                        "severity": "HIGH",
                        "issue": (
                            "yaml.load() does not explicitly use "
                            "SafeLoader. Review YAML loading safety."
                        )
                    })

    return findings


def analyze_directory(directory):
    all_findings = []
    root = Path(directory)

    if not root.exists() or not root.is_dir():
        raise ValueError("Please provide a valid directory.")

    excluded = {
        ".git",
        ".venv",
        "venv",
        "__pycache__"
    }

    for path in root.rglob("*.py"):
        if any(part in excluded for part in path.parts):
            continue

        all_findings.extend(analyze_file(path))

    return all_findings


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

        print("\n===== SERIALIZATION SECURITY REPORT =====")
        print(json.dumps(report, indent=4))

        with open(
            "serialization_security_report.json",
            "w",
            encoding="utf-8"
        ) as output:
            json.dump(report, output, indent=4)

        print("\nReport saved successfully!")

    except ValueError as error:
        print(f"Error: {error}")
