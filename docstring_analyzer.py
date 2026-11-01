
import ast
import json


def analyze_docstrings(files):
    results = {
        "total_modules": 0,
        "documented_modules": 0,
        "total_classes": 0,
        "documented_classes": 0,
        "total_functions": 0,
        "documented_functions": 0,
        "missing_docstrings": [],
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
            results["syntax_errors"].append({
                "file": path,
                "line": error.lineno,
                "message": error.msg
            })
            continue

        results["total_modules"] += 1

        if ast.get_docstring(tree):
            results["documented_modules"] += 1
        else:
            results["missing_docstrings"].append({
                "file": path,
                "type": "Module",
                "name": path,
                "line": 1
            })

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                results["total_classes"] += 1

                if ast.get_docstring(node):
                    results["documented_classes"] += 1
                else:
                    results["missing_docstrings"].append({
                        "file": path,
                        "type": "Class",
                        "name": node.name,
                        "line": node.lineno
                    })

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                results["total_functions"] += 1

                if ast.get_docstring(node):
                    results["documented_functions"] += 1
                else:
                    results["missing_docstrings"].append({
                        "file": path,
                        "type": "Function",
                        "name": node.name,
                        "line": node.lineno
                    })

    total = (
        results["total_modules"]
        + results["total_classes"]
        + results["total_functions"]
    )

    documented = (
        results["documented_modules"]
        + results["documented_classes"]
        + results["documented_functions"]
    )

    results["coverage_percentage"] = (
        round((documented / total) * 100, 2)
        if total else 0
    )

    return results


def print_report(results):
    print("\n===== DOCSTRING COVERAGE REPORT =====")

    print(f"Modules: {results['documented_modules']}/"
          f"{results['total_modules']} documented")

    print(f"Classes: {results['documented_classes']}/"
          f"{results['total_classes']} documented")

    print(f"Functions: {results['documented_functions']}/"
          f"{results['total_functions']} documented")

    print(f"\nDocumentation Coverage: "
          f"{results['coverage_percentage']}%")

    print("\nMissing Docstrings:")

    if not results["missing_docstrings"]:
        print("All checked items have docstrings!")
    else:
        for item in results["missing_docstrings"]:
            print(
                f"- {item['type']}: {item['name']} "
                f"({item['file']}:{item['line']})"
            )

    print(f"\nSyntax Errors: {len(results['syntax_errors'])}")

    for error in results["syntax_errors"]:
        print(
            f"- {error['file']}:{error['line']} "
            f"{error['message']}"
        )


def export_report(results, filename="docstring_report.json"):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=4)

    print(f"\nReport saved to {filename}")


if __name__ == "__main__":
    sample_files = [
        {
            "path": "example.py",
            "content": '''
"""Example project module."""

def greet():
    """Display a greeting."""
    print("Hello!")

def calculate():
    return 10

class Student:
    """Represents a student."""

    def study(self):
        pass
'''
        }
    ]

    report = analyze_docstrings(sample_files)
    print_report(report)
    export_report(report)
