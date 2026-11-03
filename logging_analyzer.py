
import ast
import json


SENSITIVE_WORDS = (
    "password", "passwd", "secret", "token",
    "api_key", "apikey", "access_key"
)


def analyze_logging(files):
    report = {
        "files_analyzed": 0,
        "print_statements": [],
        "logging_calls": [],
        "debug_calls": [],
        "sensitive_logging": [],
        "logging_configuration": [],
        "syntax_errors": []
    }

    for file in files:
        path = file.get("path", "")
        content = file.get("content", "")

        if not path.endswith(".py"):
            continue

        try:
            tree = ast.parse(content)
        except SyntaxError as error:
            report["syntax_errors"].append({
                "file": path,
                "line": error.lineno,
                "message": error.msg
            })
            continue

        report["files_analyzed"] += 1

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            line = getattr(node, "lineno", 0)

            if isinstance(node.func, ast.Name):
                function_name = node.func.id

                if function_name == "print":
                    report["print_statements"].append({
                        "file": path,
                        "line": line
                    })

            elif isinstance(node.func, ast.Attribute):
                method = node.func.attr

                if method == "basicConfig":
                    report["logging_configuration"].append({
                        "file": path,
                        "line": line
                    })

                if method in (
                    "debug", "info", "warning",
                    "error", "critical", "exception"
                ):
                    report["logging_calls"].append({
                        "file": path,
                        "line": line,
                        "level": method
                    })

                    if method == "debug":
                        report["debug_calls"].append({
                            "file": path,
                            "line": line
                        })

                    text = ast.get_source_segment(content, node)
                    text = (text or "").lower()

                    if any(word in text for word in SENSITIVE_WORDS):
                        report["sensitive_logging"].append({
                            "file": path,
                            "line": line,
                            "warning": "Possible sensitive data in log call"
                        })

    report["total_logging_calls"] = len(
        report["logging_calls"]
    )

    report["total_print_statements"] = len(
        report["print_statements"]
    )

    return report


def print_report(report):
    print("\n===== PYTHON LOGGING ANALYZER =====")

    print("Files analyzed:", report["files_analyzed"])

    print("Logging calls:", report["total_logging_calls"])

    print("Print statements:", report["total_print_statements"])

    print("Debug calls:", len(report["debug_calls"]))

    print(
        "Logging configurations:",
        len(report["logging_configuration"])
    )

    print(
        "Possible sensitive logging:",
        len(report["sensitive_logging"])
    )

    print("\nPrint Statements:")

    for item in report["print_statements"]:
        print(f"- {item['file']}:{item['line']}")

    print("\nDebug Logging:")

    for item in report["debug_calls"]:
        print(f"- {item['file']}:{item['line']}")

    print("\nPossible Sensitive Logging:")

    for item in report["sensitive_logging"]:
        print(
            f"- {item['file']}:{item['line']} "
            f"{item['warning']}"
        )

    print("\nSyntax Errors:", len(report["syntax_errors"]))


def export_report(report, filename="logging_report.json"):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    print("\nReport exported to", filename)


if __name__ == "__main__":
    sample_files = [
        {
            "path": "example.py",
            "content": '''
import logging

logging.basicConfig(level=logging.INFO)

def login(password):
    print("User login")
    logging.debug("Password received: " + password)
    logging.info("Login completed")
'''
        }
    ]

    result = analyze_logging(sample_files)
    print_report(result)
    export_report(result)
