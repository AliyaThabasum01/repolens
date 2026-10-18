
"""
RepoLens - Python Test Analyzer
Analyzes Python test files without third-party dependencies.
"""

import ast
from pathlib import PurePosixPath


TEST_DIRECTORIES = {"test", "tests"}
TEST_PREFIXES = ("test_",)
TEST_SUFFIXES = ("_test.py",)


def is_python_file(path):
    return PurePosixPath(path).suffix.lower() == ".py"


def is_test_file(path):
    """Identify common Python test-file naming conventions."""
    file_path = PurePosixPath(path)
    filename = file_path.name.lower()

    return (
        filename.startswith(TEST_PREFIXES)
        or filename.endswith(TEST_SUFFIXES)
        or any(
            part.lower() in TEST_DIRECTORIES
            for part in file_path.parts[:-1]
        )
    )


def analyze_test_file(path, source):
    """Inspect one Python test file."""
    report = {
        "file": path,
        "status": "ok",
        "test_functions": [],
        "test_classes": [],
        "issues": [],
        "line_count": len(source.splitlines()),
    }

    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        report["status"] = "syntax_error"
        report["issues"].append(
            f"Syntax error on line {error.lineno}: {error.msg}"
        )
        return report

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test_"):
                report["test_functions"].append({
                    "name": node.name,
                    "line": node.lineno,
                })

        elif isinstance(node, ast.ClassDef):
            if node.name.startswith("Test"):
                report["test_classes"].append({
                    "name": node.name,
                    "line": node.lineno,
                })

    if not report["test_functions"] and not report["test_classes"]:
        report["issues"].append(
            "No conventional test functions or test classes found."
        )

    if report["line_count"] > 500:
        report["issues"].append(
            "Large test file: consider splitting it into smaller modules."
        )

    return report


def analyze_repository_tests(file_contents):
    """
    Analyze repository files.

    file_contents format:
        {"tests/test_app.py": "def test_example(): ..."}
    """
    if not isinstance(file_contents, dict):
        raise TypeError("file_contents must be a dictionary.")

    test_files = []
    python_files = 0

    for path, source in file_contents.items():
        if not isinstance(path, str) or not isinstance(source, str):
            continue

        if not is_python_file(path):
            continue

        python_files += 1

        if is_test_file(path):
            test_files.append(analyze_test_file(path, source))

    total_tests = sum(
        len(item["test_functions"]) for item in test_files
    )

    total_classes = sum(
        len(item["test_classes"]) for item in test_files
    )

    syntax_errors = sum(
        item["status"] == "syntax_error" for item in test_files
    )

    recommendations = []

    if not test_files:
        recommendations.append(
            "Create a tests/ directory and add files such as test_app.py."
        )

    if total_tests == 0 and test_files:
        recommendations.append(
            "Add functions named test_something() so common Python "
            "test tools can discover them."
        )

    if syntax_errors:
        recommendations.append(
            "Fix syntax errors in test files before running the test suite."
        )

    if not recommendations:
        recommendations.append(
            "Test files were found. Run your test runner to verify "
            "that the tests actually pass."
        )

    return {
        "python_files_scanned": python_files,
        "test_files_found": len(test_files),
        "test_functions_found": total_tests,
        "test_classes_found": total_classes,
        "syntax_errors": syntax_errors,
        "test_files": test_files,
        "recommendations": recommendations,
    }


def print_report(report):
    """Print the test analysis report."""
    print("\n" + "=" * 48)
    print("        REPOLENS TEST ANALYSIS")
    print("=" * 48)

    print(f"Python files scanned: {report['python_files_scanned']}")
    print(f"Test files found: {report['test_files_found']}")
    print(f"Test functions found: {report['test_functions_found']}")
    print(f"Test classes found: {report['test_classes_found']}")
    print(f"Files with syntax errors: {report['syntax_errors']}")

    for item in report["test_files"]:
        print(f"\nFile: {item['file']}")

        if item["status"] == "syntax_error":
            print("  STATUS: Syntax error")
        else:
            print("  STATUS: Parsed successfully")

        for test in item["test_functions"]:
            print(f"  Test function: {test['name']} (line {test['line']})")

        for test_class in item["test_classes"]:
            print(f"  Test class: {test_class['name']} (line {test_class['line']})")

        for issue in item["issues"]:
            print(f"  Finding: {issue}")

    print("\nRecommendations:")
    for recommendation in report["recommendations"]:
        print(f"  - {recommendation}")

    print("\nNote: Finding a test does not prove it passes.")
    print("=" * 48)


if __name__ == "__main__":
    sample_files = {
        "app.py": "def greet(name):\n    return 'Hello ' + name\n",
        "tests/test_app.py": (
            "def test_greet():\n"
            "    assert 1 + 1 == 2\n\n"
            "class TestExample:\n"
            "    def test_example(self):\n"
            "        assert True\n"
        ),
    }

    result = analyze_repository_tests(sample_files)
    print_report(result)
