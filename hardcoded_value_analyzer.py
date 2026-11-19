
import ast
import json
from collections import defaultdict


class HardcodedValueAnalyzer(ast.NodeVisitor):

    def __init__(self, filename):
        self.filename = filename
        self.issues = []
        self.values = defaultdict(list)

    def add_issue(self, node, severity, message, suggestion):
        self.issues.append({
            "file": self.filename,
            "line": node.lineno,
            "severity": severity,
            "issue": message,
            "suggestion": suggestion
        })

    def visit_Constant(self, node):
        if isinstance(node.value, str):
            value = node.value.strip()

            if value:
                self.values[value].append(node.lineno)

                if (
                    "localhost" in value.lower()
                    or "127.0.0.1" in value
                ):
                    self.add_issue(
                        node,
                        "Medium",
                        "Hardcoded localhost address",
                        "Move environment-specific addresses into configuration."
                    )

                elif value.startswith("http://"):
                    self.add_issue(
                        node,
                        "Medium",
                        "Hardcoded HTTP URL",
                        "Use HTTPS where supported or configure the URL externally."
                    )

                elif (
                    len(value) > 2
                    and (
                        value.startswith("/home/")
                        or value.startswith("/Users/")
                        or (
                            len(value) > 2
                            and value[1:3] == ":\\"
                        )
                    )
                ):
                    self.add_issue(
                        node,
                        "Medium",
                        "Potential hardcoded machine-specific file path",
                        "Use pathlib or configurable project paths."
                    )

        elif isinstance(node.value, (int, float)):
            if not isinstance(node.value, bool):
                self.values[str(node.value)].append(node.lineno)

        self.generic_visit(node)

    def analyze_repeated_values(self):
        for value, lines in self.values.items():
            if len(lines) >= 3:
                self.issues.append({
                    "file": self.filename,
                    "line": lines[0],
                    "severity": "Low",
                    "issue": (
                        f"Repeated literal '{value}' appears "
                        f"{len(lines)} times"
                    ),
                    "suggestion": (
                        "Consider defining a named constant "
                        "if this value represents shared configuration."
                    )
                })


def analyze_hardcoded_values(files):
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

        analyzer = HardcodedValueAnalyzer(path)
        analyzer.visit(tree)
        analyzer.analyze_repeated_values()

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


def export_report(
    report,
    filename="hardcoded_value_report.json"
):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)


if __name__ == "__main__":

    sample_files = [
        {
            "path": "app.py",
            "content": '''
API_URL = "http://localhost:8000"
BACKUP_URL = "http://localhost:8000"
DATA_PATH = "C:\\\\Users\\\\Developer\\\\data"

PORT = 8080
RETRY_LIMIT = 8080
TIMEOUT = 8080

print("Application started")
'''
        }
    ]

    report = analyze_hardcoded_values(sample_files)

    print(json.dumps(report, indent=4))
    export_report(report)
