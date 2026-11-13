
import ast
import json


class AsyncAnalyzer(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.issues = []
        self.async_depth = 0

    def add_issue(self, node, severity, issue, suggestion):
        self.issues.append({
            "file": self.filename,
            "line": node.lineno,
            "severity": severity,
            "issue": issue,
            "suggestion": suggestion
        })

    def visit_AsyncFunctionDef(self, node):
        has_await = any(
            isinstance(child, ast.Await)
            for child in ast.walk(node)
        )

        if not has_await:
            self.add_issue(
                node,
                "Medium",
                f"Async function '{node.name}' has no await",
                "Check whether this function needs to be asynchronous."
            )

        self.async_depth += 1

        for statement in node.body:
            self.visit(statement)

        self.async_depth -= 1

    def visit_Call(self, node):
        if self.async_depth > 0:
            function = node.func

            if (
                isinstance(function, ast.Attribute)
                and isinstance(function.value, ast.Name)
                and function.value.id == "time"
                and function.attr == "sleep"
            ):
                self.add_issue(
                    node,
                    "High",
                    "Blocking time.sleep() inside async function",
                    "Use await asyncio.sleep() instead."
                )

            if (
                isinstance(function, ast.Attribute)
                and isinstance(function.value, ast.Name)
                and function.value.id == "requests"
                and function.attr in (
                    "get", "post", "put",
                    "delete", "patch", "request"
                )
            ):
                self.add_issue(
                    node,
                    "High",
                    f"Blocking requests.{function.attr}() inside async function",
                    "Consider an asynchronous HTTP client such as httpx."
                )

        self.generic_visit(node)


def analyze_async_code(files):
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

        analyzer = AsyncAnalyzer(path)
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
        "issues": results
    }


def export_report(report, filename="async_report.json"):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)


if __name__ == "__main__":
    sample_files = [
        {
            "path": "app.py",
            "content": '''
import time
import requests

async def fetch_data():
    time.sleep(5)
    response = requests.get("https://example.com")
    return response.text

async def greet():
    print("Hello")
'''
        }
    ]

    report = analyze_async_code(sample_files)

    print(json.dumps(report, indent=4))
    export_report(report)
