
import ast
import json
import re


class SQLAnalyzer(ast.NodeVisitor):

    SQL_PATTERN = re.compile(
        r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)\b",
        re.IGNORECASE
    )

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

    def contains_sql(self, node):
        if isinstance(node, ast.Constant):
            return (
                isinstance(node.value, str)
                and bool(self.SQL_PATTERN.search(node.value))
            )

        if isinstance(node, ast.JoinedStr):
            return any(
                self.contains_sql(value)
                for value in node.values
            )

        if isinstance(node, ast.BinOp):
            return (
                self.contains_sql(node.left)
                or self.contains_sql(node.right)
            )

        if isinstance(node, ast.Call):
            return self.contains_sql(node.func) or any(
                self.contains_sql(arg)
                for arg in node.args
            )

        return False

    def visit_Call(self, node):
        function = node.func

        is_execute = (
            isinstance(function, ast.Attribute)
            and function.attr in ("execute", "executemany")
        )

        if is_execute and node.args:
            query = node.args[0]

            if isinstance(query, ast.JoinedStr):
                self.add_issue(
                    node,
                    "High",
                    "SQL query uses an f-string",
                    "Use parameterized SQL queries instead of interpolating values."
                )

            elif (
                isinstance(query, ast.BinOp)
                and isinstance(query.op, ast.Add)
                and self.contains_sql(query)
            ):
                self.add_issue(
                    node,
                    "High",
                    "SQL query may use string concatenation",
                    "Use placeholders and pass values separately."
                )

            elif (
                isinstance(query, ast.Call)
                and isinstance(query.func, ast.Attribute)
                and query.func.attr == "format"
                and self.contains_sql(query.func.value)
            ):
                self.add_issue(
                    node,
                    "High",
                    "SQL query uses string format()",
                    "Use parameterized queries instead."
                )

            if self.contains_sql(query):
                query_text = None

                if isinstance(query, ast.Constant):
                    query_text = query.value

                elif isinstance(query, ast.JoinedStr):
                    query_text = "".join(
                        value.value
                        for value in query.values
                        if isinstance(value, ast.Constant)
                        and isinstance(value.value, str)
                    )

                if (
                    query_text
                    and re.search(
                        r"\bSELECT\s+\*",
                        query_text,
                        re.IGNORECASE
                    )
                ):
                    self.add_issue(
                        node,
                        "Low",
                        "SELECT * detected in SQL query",
                        "Select only the columns your application needs."
                    )

        self.generic_visit(node)


def analyze_sql(files):
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

        analyzer = SQLAnalyzer(path)
        analyzer.visit(tree)

        results.extend(analyzer.issues)

    return {
        "total_issues": len(results),
        "high": sum(
            item["severity"] == "High"
            for item in results
        ),
        "low": sum(
            item["severity"] == "Low"
            for item in results
        ),
        "issues": results
    }


def export_report(report, filename="sql_report.json"):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)


if __name__ == "__main__":

    sample_files = [
        {
            "path": "database.py",
            "content": '''
def find_user(user_id):
    cursor.execute(
        f"SELECT * FROM users WHERE id = {user_id}"
    )

def delete_user(user_id):
    query = "DELETE FROM users WHERE id = " + str(user_id)
    cursor.execute(query)

def get_products():
    cursor.execute("SELECT * FROM products")
'''
        }
    ]

    report = analyze_sql(sample_files)

    print(json.dumps(report, indent=4))
    export_report(report)
