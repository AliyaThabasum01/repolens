
import ast
import json
from pathlib import Path


class ExceptionAnalyzer(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.issues = []

    def add_issue(self, line, severity, issue, suggestion):
        self.issues.append({
            "file": self.filename,
            "line": line,
            "severity": severity,
            "issue": issue,
            "suggestion": suggestion
        })

    def visit_ExceptHandler(self, node):
        exception_name = " ".join(
            ast.unparse(node.type).split()
        ) if node.type else "bare except"

        if node.type is None:
            self.add_issue(
                node.lineno,
                "High",
                "Bare except block detected",
                "Catch specific exception types."
            )

        elif exception_name in ("Exception", "BaseException"):
            self.add_issue(
                node.lineno,
                "Medium",
                f"Broad exception caught: {exception_name}",
                "Catch only the exceptions your code expects."
            )

        if not node.body:
            self.add_issue(
                node.lineno,
                "High",
                "Empty exception handler",
                "Handle the error or re-raise it."
            )

        elif all(
            isinstance(statement, ast.Pass)
            for statement in node.body
        ):
            self.add_issue(
                node.lineno,
                "High",
                "Exception silently ignored using pass",
                "Log the error or handle it properly."
            )

        elif all(
            isinstance(statement, ast.Expr)
            and isinstance(statement.value, ast.Constant)
            and isinstance(statement.value.value, str)
            for statement in node.body
        ):
            self.add_issue(
                node.lineno,
                "Medium",
                "Exception handler contains only a docstring",
                "Add actual error-handling logic."
            )

        self.generic_visit(node)


def analyze_exception_handling(files):
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
                "suggestion": "Fix the syntax before analyzing."
            })
            continue

        analyzer = ExceptionAnalyzer(path)
        analyzer.visit(tree)
        results.extend(analyzer.issues)

    return {
        "total_issues": len(results),
        "high": sum(
            item["severity"] == "High" for item in results
        ),
        "medium": sum(
            item["severity"] == "Medium" for item in results
        ),
        "issues": results
    }


def export_report(report, filename="exception_report.json"):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)


if __name__ == "__main__":
    sample_files = [
        {
            "path": "sample.py",
            "content": '''
try:
    value = 10 / 0
except:
    pass

try:
    print("Hello")
except Exception:
    print("Something went wrong")
'''
        }
    ]

    report = analyze_exception_handling(sample_files)

    print(json.dumps(report, indent=4))
    export_report(report)
