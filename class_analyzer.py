
import ast
import json
from collections import defaultdict


def get_base_name(base):
    if isinstance(base, ast.Name):
        return base.id

    if isinstance(base, ast.Attribute):
        return base.attr

    return None


class ClassAnalyzer(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.classes = []
        self.issues = []

    def add_issue(self, node, severity, issue, suggestion):
        self.issues.append({
            "file": self.filename,
            "line": node.lineno,
            "severity": severity,
            "issue": issue,
            "suggestion": suggestion
        })

    def visit_ClassDef(self, node):
        bases = [
            get_base_name(base)
            for base in node.bases
        ]

        bases = [base for base in bases if base]

        self.classes.append({
            "name": node.name,
            "line": node.lineno,
            "bases": bases
        })

        if len(bases) > 2:
            self.add_issue(
                node,
                "Medium",
                f"Class '{node.name}' has {len(bases)} parent classes",
                "Review whether multiple inheritance is necessary."
            )

        self.generic_visit(node)

    def analyze(self):
        class_names = defaultdict(list)

        for item in self.classes:
            class_names[item["name"]].append(item)

        # Detect duplicate class names
        for name, definitions in class_names.items():
            if len(definitions) > 1:
                for item in definitions:
                    self.issues.append({
                        "file": self.filename,
                        "line": item["line"],
                        "severity": "Medium",
                        "issue": f"Duplicate class name: {name}",
                        "suggestion": "Use unique class names."
                    })

        # Build inheritance graph
        graph = {}

        for item in self.classes:
            graph[item["name"]] = [
                base for base in item["bases"]
                if base in class_names
            ]

        # Detect inheritance cycles
        visited = set()
        active = set()
        reported_cycles = set()

        def detect_cycle(name):
            if name in active:
                if name not in reported_cycles:
                    reported_cycles.add(name)

                    item = class_names[name][0]

                    self.issues.append({
                        "file": self.filename,
                        "line": item["line"],
                        "severity": "High",
                        "issue": (
                            f"Circular inheritance detected involving "
                            f"'{name}'"
                        ),
                        "suggestion": (
                            "Review the inheritance hierarchy "
                            "and remove circular dependencies."
                        )
                    })
                return

            if name in visited:
                return

            active.add(name)

            for parent in graph.get(name, []):
                detect_cycle(parent)

            active.remove(name)
            visited.add(name)

        for name in graph:
            detect_cycle(name)

        # Calculate inheritance depth
        def get_depth(name, path=None):
            if path is None:
                path = set()

            if name in path:
                return 0

            path = path | {name}

            parents = [
                parent for parent in graph.get(name, [])
                if parent not in path
            ]

            if not parents:
                return 0

            return 1 + max(
                get_depth(parent, path)
                for parent in parents
            )

        for item in self.classes:
            depth = get_depth(item["name"])

            if depth > 4:
                self.issues.append({
                    "file": self.filename,
                    "line": item["line"],
                    "severity": "Medium",
                    "issue": (
                        f"Deep inheritance detected in "
                        f"'{item['name']}': depth {depth}"
                    ),
                    "suggestion": (
                        "Consider composition or a simpler "
                        "class hierarchy."
                    )
                })

        return {
            "total_classes": len(self.classes),
            "total_issues": len(self.issues),
            "classes": self.classes,
            "issues": self.issues
        }


def analyze_classes(files):
    results = []
    total_classes = 0

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

        analyzer = ClassAnalyzer(path)
        analyzer.visit(tree)

        report = analyzer.analyze()
        total_classes += report["total_classes"]
        results.extend(report["issues"])

    return {
        "total_classes": total_classes,
        "total_issues": len(results),
        "high": sum(
            issue["severity"] == "High"
            for issue in results
        ),
        "medium": sum(
            issue["severity"] == "Medium"
            for issue in results
        ),
        "issues": results
    }


def export_report(report, filename="class_report.json"):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)


if __name__ == "__main__":
    sample_files = [
        {
            "path": "app.py",
            "content": '''
class A:
    pass

class B(A):
    pass

class C(B):
    pass

class D(C):
    pass

class E(D):
    pass

class F(E):
    pass
'''
        }
    ]

    report = analyze_classes(sample_files)

    print(json.dumps(report, indent=4))
    export_report(report)
