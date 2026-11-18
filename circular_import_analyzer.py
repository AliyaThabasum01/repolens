
import ast
import json
from collections import defaultdict


def module_name(path):
    path = path.replace("\\", "/")

    if path.endswith(".py"):
        path = path[:-3]

    if path.endswith("/__init__"):
        path = path[:-9]

    return path.replace("/", ".")


def resolve_import(source, imported, level):
    if level == 0:
        return imported

    parts = source.split(".")
    package = parts[:-1]

    if level > len(package) + 1:
        return None

    base = package[:len(package) - level + 1]

    if imported:
        base.extend(imported.split("."))

    return ".".join(base)


def extract_imports(path, content):
    imports = set()

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return imports

    source = module_name(path)

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)

        elif isinstance(node, ast.ImportFrom):
            imported = node.module or ""

            resolved = resolve_import(
                source,
                imported,
                node.level
            )

            if resolved:
                imports.add(resolved)

    return imports


def analyze_circular_imports(files):
    project_modules = {
        module_name(file.get("path", ""))
        for file in files
        if file.get("path", "").endswith(".py")
    }

    graph = defaultdict(set)
    issues = []

    for file in files:
        path = file.get("path", "")

        if not path.endswith(".py"):
            continue

        source = module_name(path)
        content = file.get("content", "")

        imported_modules = extract_imports(path, content)

        for imported in imported_modules:

            target = imported

            while target and target not in project_modules:
                if "." not in target:
                    target = None
                    break

                target = target.rsplit(".", 1)[0]

            if not target:
                continue

            if source == target:
                issues.append({
                    "file": path,
                    "severity": "High",
                    "issue": "Self-import detected",
                    "suggestion": "Remove the import of the current module."
                })

            else:
                graph[source].add(target)

    # Detect cycles using depth-first search
    visited = set()
    active = []
    reported_cycles = set()

    def detect_cycles(module):
        if module in active:
            index = active.index(module)
            cycle = active[index:] + [module]

            # Normalize cycle to avoid reporting rotations twice
            members = cycle[:-1]
            rotations = [
                tuple(members[i:] + members[:i])
                for i in range(len(members))
            ]

            key = min(rotations)

            if key not in reported_cycles:
                reported_cycles.add(key)

                issues.append({
                    "file": module.replace(".", "/") + ".py",
                    "severity": "High",
                    "issue": "Circular import detected: " + " -> ".join(cycle),
                    "suggestion": "Move shared code into a separate module or restructure dependencies."
                })

            return

        if module in visited:
            return

        active.append(module)

        for dependency in sorted(graph[module]):
            detect_cycles(dependency)

        active.pop()
        visited.add(module)

    for module in sorted(graph):
        detect_cycles(module)

    return {
        "total_modules": len(project_modules),
        "total_import_relationships": sum(
            len(dependencies) for dependencies in graph.values()
        ),
        "total_issues": len(issues),
        "circular_imports": issues,
        "dependency_graph": {
            module: sorted(dependencies)
            for module, dependencies in sorted(graph.items())
        }
    }


def export_report(report, filename="circular_import_report.json"):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)


if __name__ == "__main__":
    sample_files = [
        {
            "path": "app.py",
            "content": "from services import helper"
        },
        {
            "path": "services.py",
            "content": "from app import start"
        },
        {
            "path": "utils.py",
            "content": "def calculate(): return 10"
        }
    ]

    report = analyze_circular_imports(sample_files)

    print(json.dumps(report, indent=4))
    export_report(report)
