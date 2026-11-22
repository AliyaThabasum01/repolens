
import ast
import json
from pathlib import Path


DANGEROUS_FUNCTIONS = {
    "system",
    "popen",
}

SUBPROCESS_FUNCTIONS = {
    "run",
    "call",
    "Popen",
    "check_call",
    "check_output",
}


def get_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        return node.attr

    return ""


def analyze_file(file_path):
    results = []

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
            "issue": f"Could not analyze file: {error}"
        }]

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        function_name = get_name(node.func)

        # Detect os.system() and os.popen()
        if function_name in DANGEROUS_FUNCTIONS:
            results.append({
                "file": str(file_path),
                "line": node.lineno,
                "severity": "HIGH",
                "issue": (
                    f"Use of {function_name}() detected. "
                    "Review command execution safety."
                )
            })

        # Detect subprocess functions
        if function_name in SUBPROCESS_FUNCTIONS:

            shell_enabled = any(
                keyword.arg == "shell"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is True
                for keyword in node.keywords
            )

            if shell_enabled:
                results.append({
                    "file": str(file_path),
                    "line": node.lineno,
                    "severity": "HIGH",
                    "issue": (
                        "subprocess called with shell=True. "
                        "This may allow command injection."
                    )
                })

            else:
                results.append({
                    "file": str(file_path),
                    "line": node.lineno,
                    "severity": "INFO",
                    "issue": (
                        f"subprocess.{function_name}() detected. "
                        "Review command arguments and input validation."
                    )
                })

    return results


def analyze_directory(directory):
    all_results = []

    for path in Path(directory).rglob("*.py"):
        if any(
            part in {".git", ".venv", "venv", "__pycache__"}
            for part in path.parts
        ):
            continue

        all_results.extend(analyze_file(path))

    return all_results


def generate_report(results):
    report = {
        "total_findings": len(results),
        "high_risk": sum(
            item["severity"] == "HIGH"
            for item in results
        ),
        "informational": sum(
            item["severity"] == "INFO"
            for item in results
        ),
        "findings": results
    }

    return report


if __name__ == "__main__":
    folder = input(
        "Enter Python project folder path: "
    ).strip()

    findings = analyze_directory(folder)
    report = generate_report(findings)

    print("\n===== SUBPROCESS SECURITY REPORT =====")
    print(json.dumps(report, indent=4))

    with open(
        "subprocess_security_report.json",
        "w",
        encoding="utf-8"
    ) as output:
        json.dump(report, output, indent=4)

    print("\nReport saved successfully!")
