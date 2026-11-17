
import ast
import json


class ErrorPatternAnalyzer(ast.NodeVisitor):

    def __init__(self, filename):
        self.filename = filename
        self.issues = []

    def add_issue(self, node, severity, message, suggestion):
        self.issues.append({
            "file": self.filename,
            "line": node.lineno,
            "severity": severity,
            "issue": message,
            "suggestion": suggestion
        })

    def visit_FunctionDef(self, node):
        self.check_mutable_defaults(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.check_mutable_defaults(node)
        self.generic_visit(node)

    def check_mutable_defaults(self, node):
        defaults = node.args.defaults + node.args.kw_defaults

        for default in defaults:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                self.add_issue(
                    node,
                    "High",
                    f"Mutable default argument in '{node.name}'",
                    "Use None as the default and create the object inside the function."
                )

    def visit_Compare(self, node):
        for operator in node.ops:
            if isinstance(operator, (ast.Is, ast.IsNot)):
                self.add_issue(
                    node,
                    "Medium",
                    "Identity comparison using 'is' or 'is not'",
                    "Use == or != when comparing values. Use identity checks for None or object identity."
                )

        # Detect direct float comparisons
        values = [node.left] + node.comparators

        for value in values:
            if (
                isinstance(value, ast.Call)
                and isinstance(value.func, ast.Name)
                and value.func.id == "float"
            ):
                self.add_issue(
                    node,
                    "Medium",
                    "Direct comparison involving float()",
                    "Consider math.isclose() for approximate floating-point comparisons."
                )
                break

        self.generic_visit(node)

    def visit_Assert(self, node):
        self.add_issue(
            node,
            "Low",
            "Assert statement used for validation",
            "Use explicit if statements and exceptions for essential runtime validation."
        )
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        if node.type is None:
            self.add_issue(
                node,
                "High",
                "Bare except block detected",
                "Catch specific exception types."
            )

        elif isinstance(node.type, ast.Name):
            if node.type.id == "BaseException":
                self.add_issue(
                    node,
                    "High",
                    "Catching BaseException",
                    "Catch Exception or a more specific exception when appropriate."
                )

        self.generic_visit(node)


def analyze_error_patterns(files):
    results = []

    for file in files:
        path = file.get("path", "")
        content = file.get("content", "")

        if not path.endswith(".py"):
            continue

        try:
            tree = ast.parse(content, filename=path)

        except SyntaxError as error:
            results.append({
                "file": path,
                "line": error.lineno,
                "severity": "Error",
                "issue": "Python syntax error",
                "suggestion": "Fix the syntax before analysis."
            })
            continue

        analyzer = ErrorPatternAnalyzer(path)
        analyzer.visit(tree)
        results.extend(analyzer.issues)

    return {
        "total_issues": len(results),
        "high": sum(
            item["severity"] == "High"
            for item in results
        ),
        "medium": sum(
            item["severity"] == "Medium"
            for item in results
        ),
        "low": sum(
            item["severity"] == "Low"
            for item in results
        ),
        "issues": results
    }


def export_report(report, filename="error_pattern_report.json"):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)


if __name__ == "__main__":
    sample_files = [
        {
            "path": "sample.py",
            "content": '''
def add_item(item, items=[]):
    items.append(item)
    return items

if 1000 is 1000:
    print("Same")

price = float("0.1")
assert price > 0

try:
    print("Processing")
except:
    pass
'''
        }
    ]

    report = analyze_error_patterns(sample_files)

    print(json.dumps(report, indent=4))
    export_report(report)
