
import ast
import json


DEPRECATED_APIS = {
    ("collections", "Callable"): (
        "High",
        "Use collections.abc.Callable instead."
    ),
    ("collections", "Iterable"): (
        "High",
        "Use collections.abc.Iterable instead."
    ),
    ("collections", "Mapping"): (
        "High",
        "Use collections.abc.Mapping instead."
    ),
    ("collections", "MutableMapping"): (
        "High",
        "Use collections.abc.MutableMapping instead."
    ),
    ("collections", "Sequence"): (
        "High",
        "Use collections.abc.Sequence instead."
    ),
    ("inspect", "getargspec"): (
        "Medium",
        "Use inspect.signature() instead."
    ),
    ("asyncio", "get_event_loop"): (
        "Medium",
        "Review modern asyncio event-loop management APIs."
    )
}


class DeprecatedAnalyzer(ast.NodeVisitor):

    def __init__(self, filename):
        self.filename = filename
        self.issues = []
        self.import_aliases = {}

    def add_issue(self, node, severity, message, suggestion):
        self.issues.append({
            "file": self.filename,
            "line": node.lineno,
            "severity": severity,
            "issue": message,
            "suggestion": suggestion
        })

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name == "collections":
                self.import_aliases[
                    alias.asname or "collections"
                ] = "collections"

            if alias.name == "inspect":
                self.import_aliases[
                    alias.asname or "inspect"
                ] = "inspect"

            if alias.name == "asyncio":
                self.import_aliases[
                    alias.asname or "asyncio"
                ] = "asyncio"

        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module or ""

        if module == "collections":
            for alias in node.names:
                key = (module, alias.name)

                if key in DEPRECATED_APIS:
                    severity, suggestion = DEPRECATED_APIS[key]

                    self.add_issue(
                        node,
                        severity,
                        f"Deprecated import: {module}.{alias.name}",
                        suggestion
                    )

        self.generic_visit(node)

    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name):
            module = self.import_aliases.get(node.value.id)

            if module:
                key = (module, node.attr)

                if key in DEPRECATED_APIS:
                    severity, suggestion = DEPRECATED_APIS[key]

                    self.add_issue(
                        node,
                        severity,
                        f"Potential deprecated API: {module}.{node.attr}",
                        suggestion
                    )

        self.generic_visit(node)


def analyze_deprecated_apis(files):
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

        analyzer = DeprecatedAnalyzer(path)
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


def export_report(report, filename="deprecated_report.json"):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)


if __name__ == "__main__":
    sample_files = [
        {
            "path": "app.py",
            "content": '''
import collections
import inspect

from collections import Iterable

items = collections.Callable
args = inspect.getargspec(print)
'''
        }
    ]

    report = analyze_deprecated_apis(sample_files)

    print(json.dumps(report, indent=4))
    export_report(report)
