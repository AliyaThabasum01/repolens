
import ast
import json
import re
from collections import Counter


# Common package names that differ from import names
PACKAGE_ALIASES = {
    "pillow": "PIL",
    "opencv-python": "cv2",
    "pyyaml": "yaml",
    "beautifulsoup4": "bs4",
    "scikit-learn": "sklearn",
    "python-dotenv": "dotenv",
    "pandas": "pandas",
    "numpy": "numpy",
    "requests": "requests",
    "streamlit": "streamlit",
}


def read_dependencies(content):
    dependencies = []

    for line in content.splitlines():
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        # Ignore common pip options and URLs
        if line.startswith(("-", "http://", "https://")):
            continue

        match = re.match(
            r"^([A-Za-z0-9_.-]+)",
            line
        )

        if match:
            dependencies.append(
                match.group(1).lower().replace("_", "-")
            )

    return dependencies


def extract_imports(content):
    imports = set()

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return imports

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])

    return imports


def analyze_dependency_usage(files, standard_library=None):
    declared = []
    imported = set()
    scanned_files = 0

    for file in files:
        path = file.get("path", "")
        content = file.get("content", "")

        if path.endswith(".py"):
            scanned_files += 1
            imported.update(extract_imports(content))

        if path.endswith("requirements.txt"):
            declared.extend(read_dependencies(content))

    declared_counts = Counter(declared)
    declared_set = set(declared)

    # Resolve package names to import names
    package_imports = {
        PACKAGE_ALIASES.get(package, package.replace("-", "_"))
        for package in declared_set
    }

    if standard_library is None:
        standard_library = set()

    standard_library = set(standard_library)

    used_packages = imported - standard_library

    unused = sorted(
        package for package in declared_set
        if PACKAGE_ALIASES.get(
            package, package.replace("-", "_")
        ) not in used_packages
    )

    missing = sorted(
        module for module in used_packages
        if module not in package_imports
    )

    duplicates = sorted(
        package for package, count in declared_counts.items()
        if count > 1
    )

    return {
        "python_files_scanned": scanned_files,
        "declared_dependencies": sorted(declared_set),
        "imported_modules": sorted(imported),
        "apparently_unused_dependencies": unused,
        "imports_without_matching_dependency": missing,
        "duplicate_declarations": duplicates,
        "total_declared": len(declared_set),
        "total_imported": len(imported)
    }


def export_report(report, filename="dependency_usage_report.json"):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)


if __name__ == "__main__":

    sample_files = [
        {
            "path": "app.py",
            "content": '''
import streamlit
import requests
import pandas
import json
import numpy
'''
        },
        {
            "path": "requirements.txt",
            "content": '''
streamlit
requests
numpy
flask
pandas
pandas
'''
        }
    ]

    # Example standard-library modules for this test
    stdlib = {
        "json",
        "os",
        "sys",
        "re",
        "ast",
        "math",
        "pathlib",
        "collections"
    }

    report = analyze_dependency_usage(
        sample_files,
        standard_library=stdlib
    )

    print(json.dumps(report, indent=4))
    export_report(report)
