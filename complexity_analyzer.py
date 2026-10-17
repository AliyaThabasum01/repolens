
"""
RepoLens - Code Complexity Analyzer
Provides lightweight Python source-code complexity checks.
Uses Python's built-in AST module; no extra packages required.
"""

import ast
import io
import tokenize
from pathlib import Path


def analyze_python_file(source, filename="unknown.py"):
    """Analyze functions and nesting in a Python source string."""
    result = {
        "filename": filename,
        "status": "success",
        "functions": [],
        "issues": [],
        "summary": {},
    }

    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        result["status"] = "syntax_error"
        result["issues"].append({
            "type": "Syntax Error",
            "line": error.lineno or 0,
            "message": error.msg,
        })
        return result

    # Count logical decision points in each function.
    decision_nodes = (
        ast.If, ast.For, ast.AsyncFor, ast.While,
        ast.ExceptHandler, ast.IfExp,
    )

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            decisions = sum(
                isinstance(child, decision_nodes)
                for child in ast.walk(node)
                if child is not node
            )

            complexity = decisions + 1
            end_line = getattr(node, "end_lineno", node.lineno)
            length = end_line - node.lineno + 1

            function = {
                "name": node.name,
                "start_line": node.lineno,
                "end_line": end_line,
                "length": length,
                "estimated_complexity": complexity,
            }
            result["functions"].append(function)

            if length > 50:
                result["issues"].append({
                    "type": "Long Function",
                    "line": node.lineno,
                    "message": (
                        f"Function '{node.name}' spans {length} lines."
                    ),
                })

            if complexity > 10:
                result["issues"].append({
                    "type": "High Complexity",
                    "line": node.lineno,
                    "message": (
                        f"Function '{node.name}' has an estimated "
                        f"complexity of {complexity}."
                    ),
                })

    # Measure indentation nesting using tokenized Python code.
    nesting = 0
    max_nesting = 0

    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)

        for token in tokens:
            if token.type == tokenize.INDENT:
                nesting += 1
                max_nesting = max(max_nesting, nesting)
            elif token.type == tokenize.DEDENT:
                nesting = max(0, nesting - 1)

    except (tokenize.TokenError, IndentationError):
        pass

    if max_nesting > 4:
        result["issues"].append({
            "type": "Deep Nesting",
            "line": 0,
            "message": (
                f"Maximum indentation nesting is {max_nesting} levels."
            ),
        })

    result["summary"] = {
        "function_count": len(result["functions"]),
        "long_functions": sum(
            item["type"] == "Long Function"
            for item in result["issues"]
        ),
        "high_complexity_functions": sum(
            item["type"] == "High Complexity"
            for item in result["issues"]
        ),
        "maximum_nesting": max_nesting,
        "issue_count": len(result["issues"]),
    }

    return result


def analyze_python_files(file_contents):
    """Analyze multiple Python files from a {path: source} dictionary."""
    reports = []

    for filename, source in file_contents.items():
        if Path(filename).suffix.lower() != ".py":
            continue

        if not isinstance(source, str):
            continue

        reports.append(analyze_python_file(source, filename))

    return {
        "files_scanned": len(reports),
        "total_functions": sum(
            report["summary"].get("function_count", 0)
            for report in reports
        ),
        "total_issues": sum(
            report["summary"].get("issue_count", len(report["issues"]))
            for report in reports
        ),
        "reports": reports,
    }


def print_report(report):
    """Print a readable report for multiple Python files."""
    print("\n" + "=" * 48)
    print("       REPOLENS COMPLEXITY REPORT")
    print("=" * 48)
    print(f"Python files scanned: {report['files_scanned']}")
    print(f"Functions found: {report['total_functions']}")
    print(f"Potential issues: {report['total_issues']}")

    for file_report in report["reports"]:
        print(f"\nFile: {file_report['filename']}")

        if file_report["status"] == "syntax_error":
            for issue in file_report["issues"]:
                print(
                    f"  Syntax error at line {issue['line']}: "
                    f"{issue['message']}"
                )
            continue

        if not file_report["functions"]:
            print("  No functions found.")

        for function in file_report["functions"]:
            print(
                f"  {function['name']}() | "
                f"Lines: {function['length']} | "
                f"Estimated complexity: "
                f"{function['estimated_complexity']}"
            )

        if file_report["issues"]:
            print("  Findings:")
            for issue in file_report["issues"]:
                line = (
                    f"Line {issue['line']}"
                    if issue["line"] else "File-level"
                )
                print(f"    [{issue['type']}] {line}: {issue['message']}")
        else:
            print("  No configured complexity warnings.")

    print("\nNote: These are heuristic warnings, not proof of defects.")
    print("=" * 48)


if __name__ == "__main__":
    sample_code = {
        "example.py": '''
def calculate_discount(price, is_member, has_coupon):
    if price > 100:
        if is_member:
            if has_coupon:
                return price * 0.7
            return price * 0.8
        return price * 0.9
    return price
'''
    }

    report = analyze_python_files(sample_code)
    print_report(report)
