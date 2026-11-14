
import ast
import json


class FunctionAnalyzer(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.issues = []
        self.function_names = set()
        self.duplicates = set()

    def add_issue(self, node, severity, issue, suggestion):
        self.issues.append({
            "file": self.filename,
            "line": node.lineno,
            "severity": severity,
            "issue": issue,
            "suggestion": suggestion
        })

    def visit_FunctionDef(self, node):
        self.check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.check_function(node)
        self.generic_visit(node)

    def check_function(self, node):
        name = node.name

        if name in self.function_names:
            self.duplicates.add(name)

            self.add_issue(
                node,
                "Medium",
                f"Duplicate function name: {name}",
                "Use unique and descriptive function names."
            )
        else:
            self.function_names.add(name)

        # Count function parameters
        arguments = (
            node.args.posonlyargs
            + node.args.args
            + node.args.kwonlyargs
        )

        if node.args.vararg:
            arguments.append(node.args.vararg)

        if node.args.kwarg:
            arguments.append(node.args.kwarg)

        if len(arguments) > 5:
            self.add_issue(
                node,
                "Medium",
                f"Function has {len(arguments)} parameters",
                "Consider grouping related parameters."
            )

        # Count function body lines
        start = node.lineno
        end = getattr(node, "end_lineno", start)
        line_count = end - start + 1

        if line_count > 50:
            self.add_issue(
                node,
                "High",
                f"Long function detected: {line_count} lines",
                "Break the function into smaller functions."
            )

        # Count return statements excluding nested functions
        returns = 0

        for child in ast.walk(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                if child is not node:
                    continue

            if isinstance(child, ast.Return):
                returns += 1

        if returns > 5:
            self.add_issue(
                node,
                "Low",
                f"Function has {returns} return statements",
                "Review whether the control flow can be simplified."
            )


def analyze_functions(files):
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

        analyzer = FunctionAnalyzer(path)
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


def export_report(report, filename="function_report.json"):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)


if __name__ == "__main__":
    sample_files = [
        {
            "path": "app.py",
            "content": '''
def calculate(a, b, c, d, e, f):
    result = a + b + c + d + e + f
    return result

def calculate_again():
    return 10

def calculate_again():
    return 20
'''
        }
    ]

    report = analyze_functions(sample_files)

    print(json.dumps(report, indent=4))
    export_report(report)
