
import ast
import json
import re


def extract_environment_variables(content):
    variables = set()

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return variables

    for node in ast.walk(tree):

        # os.getenv("API_KEY")
        if isinstance(node, ast.Call):
            function = node.func

            if (
                isinstance(function, ast.Attribute)
                and function.attr == "getenv"
                and isinstance(function.value, ast.Name)
                and function.value.id == "os"
            ):
                if node.args and isinstance(
                    node.args[0], ast.Constant
                ):
                    if isinstance(node.args[0].value, str):
                        variables.add(node.args[0].value)

            # os.environ.get("API_KEY")
            if (
                isinstance(function, ast.Attribute)
                and function.attr == "get"
                and isinstance(function.value, ast.Attribute)
                and function.value.attr == "environ"
                and isinstance(function.value.value, ast.Name)
                and function.value.value.id == "os"
            ):
                if node.args and isinstance(
                    node.args[0], ast.Constant
                ):
                    if isinstance(node.args[0].value, str):
                        variables.add(node.args[0].value)

        # os.environ["API_KEY"]
        if isinstance(node, ast.Subscript):
            value = node.value

            if (
                isinstance(value, ast.Attribute)
                and value.attr == "environ"
                and isinstance(value.value, ast.Name)
                and value.value.id == "os"
                and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)
            ):
                variables.add(node.slice.value)

    return variables


def parse_env_example(content):
    variables = []
    pattern = re.compile(
        r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*="
    )

    for line in content.splitlines():
        match = pattern.match(line)

        if match:
            variables.append(match.group(1))

    return variables


def analyze_environment(files):
    used_variables = set()
    documented_variables = []
    python_files = []

    for file in files:
        path = file.get("path", "")
        content = file.get("content", "")

        if path.endswith(".py"):
            python_files.append(path)
            used_variables.update(
                extract_environment_variables(content)
            )

        if path.endswith(".env.example"):
            documented_variables.extend(
                parse_env_example(content)
            )

    documented_set = set(documented_variables)

    missing = sorted(
        used_variables - documented_set
    )

    unused = sorted(
        documented_set - used_variables
    )

    duplicates = sorted({
        name for name in documented_variables
        if documented_variables.count(name) > 1
    })

    return {
        "total_used_variables": len(used_variables),
        "total_documented_variables": len(documented_set),
        "missing_from_example": missing,
        "unused_in_example": unused,
        "duplicate_declarations": duplicates,
        "used_variables": sorted(used_variables),
        "documented_variables": sorted(documented_set),
        "python_files_scanned": len(python_files)
    }


def export_report(report, filename="env_report.json"):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)


if __name__ == "__main__":
    sample_files = [
        {
            "path": "app.py",
            "content": '''
import os

API_KEY = os.getenv("API_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")
SECRET_TOKEN = os.environ["SECRET_TOKEN"]
'''
        },
        {
            "path": ".env.example",
            "content": '''
API_KEY=
DATABASE_URL=
OLD_VARIABLE=
API_KEY=
'''
        }
    ]

    report = analyze_environment(sample_files)

    print(json.dumps(report, indent=4))
    export_report(report)
