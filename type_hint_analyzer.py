
import ast
import json


def analyze_type_hints(files):
    report = {
        "total_functions": 0,
        "fully_annotated": 0,
        "partially_annotated": 0,
        "unannotated": 0,
        "missing_return_hints": [],
        "missing_parameter_hints": [],
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

        for node in ast.walk(tree):
            if not isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                continue

            report["total_functions"] += 1

            missing_params = []

            all_args = (
                node.args.posonlyargs
                + node.args.args
                + node.args.kwonlyargs
            )

            if node.args.vararg:
                all_args.append(node.args.vararg)

            if node.args.kwarg:
                all_args.append(node.args.kwarg)

            for arg in all_args:
                if arg.arg == "self" or arg.arg == "cls":
                    continue

                if arg.annotation is None:
                    missing_params.append(arg.arg)

            missing_return = node.returns is None

            if missing_params:
                report["missing_parameter_hints"].append({
                    "file": path,
                    "function": node.name,
                    "line": node.lineno,
                    "parameters": missing_params
                })

            if missing_return:
                report["missing_return_hints"].append({
                    "file": path,
                    "function": node.name,
                    "line": node.lineno
                })

            if not missing_params and not missing_return:
                report["fully_annotated"] += 1
            elif missing_params and missing_return:
                report["unannotated"] += 1
            else:
                report["partially_annotated"] += 1

    total = report["total_functions"]

    report["coverage_percentage"] = (
        round(
            report["fully_annotated"] / total * 100, 2
        ) if total else 0
    )

    return report


def print_report(report):
    print("\n===== PYTHON TYPE HINT REPORT =====")

    print("Total functions:", report["total_functions"])
    print("Fully annotated:", report["fully_annotated"])
    print("Partially annotated:", report["partially_annotated"])
    print("Unannotated:", report["unannotated"])

    print(
        "\nComplete Type Hint Coverage:",
        str(report["coverage_percentage"]) + "%"
    )

    print("\nMissing Parameter Hints:")

    for item in report["missing_parameter_hints"]:
        print(
            f"- {item['function']} in {item['file']}: "
            f"{', '.join(item['parameters'])}"
        )

    print("\nMissing Return Hints:")

    for item in report["missing_return_hints"]:
        print(
            f"- {item['function']} in {item['file']}"
        )

    print("\nSyntax Errors:", len(report["syntax_errors"]))


def export_report(report, filename="type_hint_report.json"):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    print("\nReport exported to", filename)


if __name__ == "__main__":
    sample_files = [
        {
            "path": "example.py",
            "content": '''
def greet(name: str) -> str:
    return "Hello " + name

def add(a, b):
    return a + b

def welcome(name: str):
    print(name)
'''
        }
    ]

    result = analyze_type_hints(sample_files)
    print_report(result)
    export_report(result)
