
"""
RepoLens Python Import Analyzer
--------------------------------
Analyzes Python imports without executing the code.

Features:
- Lists imported modules
- Detects duplicate imports
- Flags wildcard imports
- Provides a basic unused-import heuristic
- Exports a JSON report

Uses Python's standard library only.
"""

import ast
import json
from collections import Counter, defaultdict
from datetime import datetime


def analyze_python_file(path, content):
    """Analyze imports in one Python file."""

    result = {
        "file": path,
        "imports": [],
        "findings": [],
        "error": None,
    }

    try:
        tree = ast.parse(content, filename=path)
    except SyntaxError as exc:
        result["error"] = (
            f"Syntax error at line {exc.lineno}: {exc.msg}"
        )
        result["findings"].append({
            "severity": "Warning",
            "line": exc.lineno,
            "message": "Could not analyze imports because the "
                       "file has a syntax error.",
        })
        return result

    import_records = []
    imported_names = defaultdict(list)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name
                bound_name = alias.asname or module.split(".")[0]

                record = {
                    "module": module,
                    "name": bound_name,
                    "line": node.lineno,
                    "kind": "import",
                    "wildcard": False,
                }
                import_records.append(record)
                imported_names[bound_name].append(record)

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""

            for alias in node.names:
                is_wildcard = alias.name == "*"
                bound_name = alias.asname or alias.name

                record = {
                    "module": (
                        f"{module}.{alias.name}"
                        if module else alias.name
                    ),
                    "name": bound_name,
                    "line": node.lineno,
                    "kind": "from_import",
                    "wildcard": is_wildcard,
                }
                import_records.append(record)

                if not is_wildcard:
                    imported_names[bound_name].append(record)

    result["imports"] = sorted(
        import_records,
        key=lambda item: (item["line"], item["module"]),
    )

    # Detect repeated import statements/names.
    import_counts = Counter(
        (item["kind"], item["module"], item["name"])
        for item in import_records
    )

    for item in result["imports"]:
        key = (item["kind"], item["module"], item["name"])

        if import_counts[key] > 1:
            result["findings"].append({
                "severity": "Info",
                "line": item["line"],
                "message": (
                    f"Repeated import detected: {item['module']}"
                ),
            })
            # Avoid reporting the same duplicate on every occurrence.
            import_counts[key] = 0

    # Flag wildcard imports.
    for item in result["imports"]:
        if item["wildcard"]:
            result["findings"].append({
                "severity": "Warning",
                "line": item["line"],
                "message": (
                    f"Wildcard import from '{item['module'].rsplit('.', 1)[0]}'. "
                    "Consider importing only the names you need."
                ),
            })

    # Gather identifiers used in the file.
    # This is a heuristic, not a full scope-aware analysis.
    used_names = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used_names.add(node.id)

        elif isinstance(node, ast.Attribute):
            # Attribute names may be relevant for imports such as
            # `import package.module`; their root Name is also visited.
            used_names.add(node.attr)

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            used_names.add(node.name)

        elif isinstance(node, ast.arg):
            used_names.add(node.arg)

    for name, records in imported_names.items():
        # Leading underscore imports are often intentional.
        if name.startswith("_"):
            continue

        # Avoid a false warning when a name appears in multiple imports.
        if name not in used_names:
            for record in records:
                result["findings"].append({
                    "severity": "Review",
                    "line": record["line"],
                    "message": (
                        f"Import '{name}' may be unused. "
                        "Verify manually before removing it."
                    ),
                })

    result["findings"].sort(
        key=lambda item: (
            item["line"] or 0,
            item["severity"],
            item["message"],
        )
    )

    return result


def analyze_imports(files):
    """
    Analyze a list of dictionaries.

    Expected input:
    [
        {"path": "app.py", "content": "import os\\n"}
    ]
    """

    file_results = []

    for item in files:
        if not isinstance(item, dict):
            continue

        path = item.get("path") or item.get("name")
        content = item.get("content")

        if not isinstance(path, str) or not path.endswith(".py"):
            continue

        if not isinstance(content, str):
            continue

        file_results.append(analyze_python_file(path, content))

    all_imports = [
        imported
        for file_result in file_results
        for imported in file_result["imports"]
    ]

    module_counts = Counter(
        item["module"] for item in all_imports
    )

    finding_counts = Counter(
        finding["severity"]
        for file_result in file_results
        for finding in file_result["findings"]
    )

    return {
        "generated_at": datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
        "files_scanned": len(file_results),
        "files_with_syntax_errors": sum(
            1 for item in file_results if item["error"]
        ),
        "total_imports": len(all_imports),
        "unique_imports": len(module_counts),
        "most_common_imports": [
            {"module": module, "count": count}
            for module, count in module_counts.most_common(10)
        ],
        "finding_summary": {
            "Warning": finding_counts.get("Warning", 0),
            "Review": finding_counts.get("Review", 0),
            "Info": finding_counts.get("Info", 0),
        },
        "files": file_results,
        "limitations": [
            "Unused-import detection is heuristic and may produce false positives.",
            "The analyzer does not execute code or install dependencies.",
            "Dynamic imports and complex Python scope behavior may not be detected.",
        ],
    }


def print_report(report):
    """Print a readable summary."""

    print("=" * 60)
    print("          REPOLENS PYTHON IMPORT ANALYZER")
    print("=" * 60)

    print(f"Files scanned: {report['files_scanned']}")
    print(f"Files with syntax errors: {report['files_with_syntax_errors']}")
    print(f"Total imports: {report['total_imports']}")
    print(f"Unique imported names/modules: {report['unique_imports']}")

    print("\nFinding Summary")
    for severity, count in report["finding_summary"].items():
        print(f"  {severity}: {count}")

    print("\nMost Common Imports")
    if report["most_common_imports"]:
        for item in report["most_common_imports"]:
            print(f"  {item['module']}: {item['count']}")
    else:
        print("  No imports found.")

    print("\nFile Details")
    for file_result in report["files"]:
        print(f"\n{file_result['file']}")

        if file_result["error"]:
            print(f"  ERROR: {file_result['error']}")

        if not file_result["findings"]:
            print("  No findings.")
            continue

        for finding in file_result["findings"]:
            line = finding["line"]
            location = f"Line {line}" if line else "File"
            print(
                f"  [{finding['severity']}] "
                f"{location}: {finding['message']}"
            )


if __name__ == "__main__":
    sample_files = [
        {
            "path": "app.py",
            "content": (
                "import os\n"
                "import json\n"
                "import os\n"
                "from math import *\n\n"
                "def main():\n"
                "    print(os.getcwd())\n"
            ),
        },
        {
            "path": "utils.py",
            "content": (
                "from pathlib import Path\n\n"
                "def get_name():\n"
                "    return 'RepoLens'\n"
            ),
        },
    ]

    report = analyze_imports(sample_files)
    print_report(report)

    with open(
        "python_import_report.json",
        "w",
        encoding="utf-8",
    ) as output_file:
        json.dump(report, output_file, indent=2)

    print("\nJSON report saved to python_import_report.json")
