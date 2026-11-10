
import ast
import configparser
import json
import re


def analyze_metadata(files):
    report = {
        "metadata_files_found": [],
        "project_name": None,
        "version": None,
        "description": None,
        "authors": [],
        "python_requirement": None,
        "classifiers": [],
        "missing_fields": [],
        "warnings": []
    }

    for file in files:
        path = file.get("path", "").replace("\\", "/")
        content = file.get("content", "")
        filename = path.split("/")[-1].lower()

        if filename not in (
            "pyproject.toml", "setup.cfg", "setup.py"
        ):
            continue

        report["metadata_files_found"].append(path)

        if filename == "pyproject.toml":
            try:
                import tomllib
                data = tomllib.loads(content)

                project = data.get("project", {})

                report["project_name"] = (
                    report["project_name"]
                    or project.get("name")
                )

                report["version"] = (
                    report["version"]
                    or project.get("version")
                )

                report["description"] = (
                    report["description"]
                    or project.get("description")
                )

                report["authors"].extend(
                    item.get("name", "")
                    for item in project.get("authors", [])
                    if item.get("name")
                )

                report["python_requirement"] = (
                    report["python_requirement"]
                    or project.get("requires-python")
                )

                report["classifiers"].extend(
                    project.get("classifiers", [])
                )

            except Exception as error:
                report["warnings"].append({
                    "file": path,
                    "message": f"Could not parse TOML: {error}"
                })

        elif filename == "setup.cfg":
            parser = configparser.ConfigParser()

            try:
                parser.read_string(content)

                if parser.has_section("metadata"):
                    metadata = parser["metadata"]

                    report["project_name"] = (
                        report["project_name"]
                        or metadata.get("name")
                    )

                    report["version"] = (
                        report["version"]
                        or metadata.get("version")
                    )

                    report["description"] = (
                        report["description"]
                        or metadata.get("description")
                    )

                if parser.has_section("options"):
                    report["python_requirement"] = (
                        report["python_requirement"]
                        or parser["options"].get("python_requires")
                    )

            except configparser.Error as error:
                report["warnings"].append({
                    "file": path,
                    "message": str(error)
                })

        elif filename == "setup.py":
            try:
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if not isinstance(node, ast.Call):
                        continue

                    function = node.func

                    if not (
                        isinstance(function, ast.Name)
                        and function.id == "setup"
                    ):
                        continue

                    for keyword in node.keywords:
                        if keyword.arg not in (
                            "name", "version", "description",
                            "python_requires"
                        ):
                            continue

                        try:
                            value = ast.literal_eval(keyword.value)
                        except (ValueError, TypeError):
                            continue

                        if keyword.arg == "name":
                            report["project_name"] = (
                                report["project_name"] or value
                            )

                        elif keyword.arg == "version":
                            report["version"] = (
                                report["version"] or value
                            )

                        elif keyword.arg == "description":
                            report["description"] = (
                                report["description"] or value
                            )

                        elif keyword.arg == "python_requires":
                            report["python_requirement"] = (
                                report["python_requirement"] or value
                            )

            except SyntaxError as error:
                report["warnings"].append({
                    "file": path,
                    "message": f"Python syntax error: {error.msg}"
                })

    required_fields = [
        "project_name",
        "version",
        "description"
    ]

    for field in required_fields:
        if not report[field]:
            report["missing_fields"].append(field)

    if not report["metadata_files_found"]:
        report["warnings"].append(
            "No supported Python metadata file was found."
        )

    if report["missing_fields"]:
        report["warnings"].append(
            "Some important project metadata fields are missing."
        )

    report["authors"] = list(dict.fromkeys(report["authors"]))
    report["classifiers"] = list(dict.fromkeys(report["classifiers"]))

    return report


def print_report(report):
    print("\n===== REPOSITORY METADATA REPORT =====")

    print("Metadata files:", report["metadata_files_found"])
    print("Project name:", report["project_name"] or "Missing")
    print("Version:", report["version"] or "Missing")
    print("Description:", report["description"] or "Missing")
    print("Authors:", report["authors"] or "Not specified")
    print(
        "Python requirement:",
        report["python_requirement"] or "Not specified"
    )

    print("\nClassifiers:")

    for item in report["classifiers"]:
        print("-", item)

    print("\nMissing Fields:")

    for item in report["missing_fields"]:
        print("-", item)

    print("\nWarnings:")

    for item in report["warnings"]:
        print("-", item["message"])


def export_report(report, filename="metadata_report.json"):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    print("\nReport exported to", filename)


if __name__ == "__main__":
    sample_files = [
        {
            "path": "pyproject.toml",
            "content": '''
[project]
name = "repolens"
version = "1.0.0"
description = "A GitHub repository analyzer"
requires-python = ">=3.10"

authors = [
    {name = "Developer"}
]

classifiers = [
    "Programming Language :: Python :: 3"
]
'''
        }
    ]

    result = analyze_metadata(sample_files)
    print_report(result)
    export_report(result)
