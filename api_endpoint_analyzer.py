
"""
RepoLens - API Endpoint Analyzer
Detects common Flask and FastAPI route declarations in Python files.
Uses Python's built-in AST module. No extra packages required.
"""

import ast
from pathlib import PurePosixPath


HTTP_METHODS = {
    "get", "post", "put", "patch",
    "delete", "options", "head",
}


def get_route_details(node):
    """Extract route path and HTTP methods from a decorator."""
    if not isinstance(node, ast.Call):
        return None

    function = node.func
    framework = None
    methods = []

    # @app.get("/users")
    # @router.post("/users")
    if isinstance(function, ast.Attribute):
        method_name = function.attr.lower()

        if method_name in HTTP_METHODS:
            methods = [method_name.upper()]
            framework = "Flask/FastAPI"

        # @app.route("/users", methods=["GET", "POST"])
        elif method_name == "route":
            framework = "Flask"
            methods = ["GET"]

            for keyword in node.keywords:
                if keyword.arg == "methods":
                    if isinstance(keyword.value, (ast.List, ast.Tuple)):
                        methods = [
                            item.value.upper()
                            for item in keyword.value.elts
                            if isinstance(item, ast.Constant)
                            and isinstance(item.value, str)
                        ]

    if not framework or not node.args:
        return None

    path_node = node.args[0]

    if not isinstance(path_node, ast.Constant):
        return None

    if not isinstance(path_node.value, str):
        return None

    if not methods:
        methods = ["UNKNOWN"]

    return {
        "path": path_node.value,
        "methods": methods,
        "framework": framework,
    }


def analyze_python_file(filename, source):
    """Detect API routes in one Python source file."""
    report = {
        "file": filename,
        "status": "ok",
        "endpoints": [],
        "issues": [],
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
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        for decorator in node.decorator_list:
            route = get_route_details(decorator)

            if route is None:
                continue

            report["endpoints"].append({
                **route,
                "function": node.name,
                "line": node.lineno,
            })

    return report


def analyze_api_endpoints(file_contents):
    """
    Analyze a dictionary of {file_path: source_code}.
    Only Python source files are inspected.
    """
    if not isinstance(file_contents, dict):
        raise TypeError("file_contents must be a dictionary.")

    reports = []

    for filename, source in file_contents.items():
        if not isinstance(filename, str):
            continue

        if PurePosixPath(filename).suffix.lower() != ".py":
            continue

        if not isinstance(source, str):
            continue

        reports.append(analyze_python_file(filename, source))

    endpoints = [
        endpoint
        for report in reports
        for endpoint in report["endpoints"]
    ]

    # Duplicate means the same HTTP method and path were declared
    # more than once. Dynamic paths are compared as written.
    route_groups = {}

    for endpoint in endpoints:
        for method in endpoint["methods"]:
            key = (method, endpoint["path"])
            route_groups.setdefault(key, []).append(endpoint)

    duplicates = [
        {
            "method": key[0],
            "path": key[1],
            "declarations": declarations,
        }
        for key, declarations in route_groups.items()
        if len(declarations) > 1
    ]

    syntax_errors = sum(
        report["status"] == "syntax_error"
        for report in reports
    )

    return {
        "python_files_scanned": len(reports),
        "files_with_syntax_errors": syntax_errors,
        "endpoint_count": len(endpoints),
        "unique_method_paths": len(route_groups),
        "duplicate_routes": duplicates,
        "endpoints": endpoints,
        "file_reports": reports,
    }


def print_report(report):
    """Print a readable endpoint analysis report."""
    print("\n" + "=" * 50)
    print("        REPOLENS API ENDPOINT REPORT")
    print("=" * 50)

    print(f"Python files scanned: {report['python_files_scanned']}")
    print(f"Detected endpoints: {report['endpoint_count']}")
    print(f"Unique method/path pairs: {report['unique_method_paths']}")
    print(
        "Files with syntax errors: "
        f"{report['files_with_syntax_errors']}"
    )

    print("\nDETECTED ENDPOINTS")

    if not report["endpoints"]:
        print("No supported route declarations found.")

    for endpoint in report["endpoints"]:
        methods = ", ".join(endpoint["methods"])
        print(f"\n  {methods} {endpoint['path']}")
        print(f"  Function: {endpoint['function']}")
        print(f"  File: {endpoint['file']}:{endpoint['line']}")
        print(f"  Framework pattern: {endpoint['framework']}")

    print("\nDUPLICATE ROUTES")

    if not report["duplicate_routes"]:
        print("No duplicate method/path declarations detected.")
    else:
        for duplicate in report["duplicate_routes"]:
            print(f"\n  {duplicate['method']} {duplicate['path']}")

            for declaration in duplicate["declarations"]:
                print(
                    f"    - {declaration['file']}:"
                    f"{declaration['line']} "
                    f"({declaration['function']})"
                )

    print("\nNote: This is static analysis, not a live API test.")
    print("=" * 50)


if __name__ == "__main__":
    sample_files = {
        "app.py": '''
from flask import Flask

app = Flask(__name__)

@app.route("/users", methods=["GET", "POST"])
def users():
    return "Users"

@app.get("/health")
def health():
    return "OK"
''',
        "routes.py": '''
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def check_health():
    return {"status": "ok"}
''',
    }

    result = analyze_api_endpoints(sample_files)
    print_report(result)
