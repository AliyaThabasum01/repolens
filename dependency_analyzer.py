
import json
import re
from pathlib import PurePosixPath


DEPENDENCY_FILES = {
    "requirements.txt": "Python",
    "pyproject.toml": "Python",
    "Pipfile": "Python",
    "package.json": "JavaScript / Node.js",
    "package-lock.json": "JavaScript / Node.js",
    "yarn.lock": "JavaScript / Node.js",
    "pnpm-lock.yaml": "JavaScript / Node.js",
    "pom.xml": "Java / Maven",
    "build.gradle": "Java / Gradle",
    "build.gradle.kts": "Kotlin / Gradle",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
    "Gemfile": "Ruby",
    "composer.json": "PHP",
    "pubspec.yaml": "Dart / Flutter",
}


def find_dependency_files(files):
    """Find dependency and package-manifest files in a repository."""
    found = []

    for item in files:
        if isinstance(item, str):
            path = item
        elif isinstance(item, dict):
            path = item.get("path", item.get("name", ""))
        else:
            continue

        filename = PurePosixPath(path).name

        if filename in DEPENDENCY_FILES:
            found.append({
                "path": path,
                "filename": filename,
                "ecosystem": DEPENDENCY_FILES[filename]
            })

    return found


def parse_requirements(content):
    """Extract package declarations from requirements.txt."""
    packages = []

    for line in content.splitlines():
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        if line.startswith(("-", "git+", "http://", "https://")):
            packages.append({
                "name": line,
                "version": "External or special requirement",
                "source": line
            })
            continue

        match = re.match(
            r"^([A-Za-z0-9_.-]+)\s*(.*)$",
            line
        )

        if not match:
            continue

        packages.append({
            "name": match.group(1),
            "version": match.group(2).strip() or "Unpinned",
            "source": line
        })

    return packages


def parse_package_json(content):
    """Extract dependencies from package.json."""
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return [], ["Invalid package.json format"]

    packages = []

    for section in (
        "dependencies",
        "devDependencies",
        "peerDependencies",
        "optionalDependencies"
    ):
        dependencies = data.get(section, {})

        if not isinstance(dependencies, dict):
            continue

        for name, version in dependencies.items():
            packages.append({
                "name": name,
                "version": str(version),
                "group": section
            })

    return packages, []


def parse_pyproject_toml(content):
    """Extract simple dependency declarations from pyproject.toml."""
    packages = []
    errors = []

    section = None

    for raw_line in content.splitlines():
        line = raw_line.strip()

        if line.startswith("[") and line.endswith("]"):
            section = line.lower()
            continue

        if section and (
            "dependencies" in section or
            "optional-dependencies" in section
        ):
            match = re.match(
                r'^["\']?([A-Za-z0-9_.-]+)["\']?\s*(.*)$',
                line
            )

            if match and "=" in line:
                name = match.group(1)
                version = match.group(2).split("#")[0].strip()
                packages.append({
                    "name": name,
                    "version": version or "Declared",
                    "group": section
                })

            elif line.startswith('"') or line.startswith("'"):
                requirement = line.strip(",").strip('"').strip("'")

                match = re.match(
                    r"^([A-Za-z0-9_.-]+)(.*)$",
                    requirement
                )

                if match:
                    packages.append({
                        "name": match.group(1),
                        "version": match.group(2).strip() or "Unpinned",
                        "group": section
                    })

    return packages, errors


def analyze_dependencies(file_contents):
    """
    Analyze dependency manifests.

    file_contents must be a dictionary:
    {repository_path: file_text}
    """
    results = []
    warnings = []
    seen = set()

    for path, content in file_contents.items():
        filename = PurePosixPath(path).name

        if filename not in DEPENDENCY_FILES:
            continue

        if not isinstance(content, str):
            continue

        if filename == "requirements.txt":
            packages = parse_requirements(content)
            errors = []

        elif filename == "package.json":
            packages, errors = parse_package_json(content)

        elif filename == "pyproject.toml":
            packages, errors = parse_pyproject_toml(content)

        else:
            packages = []
            errors = [
                f"{filename} was detected, but detailed parsing "
                "is not implemented for this file type."
            ]

        warnings.extend(errors)

        for package in packages:
            key = (
                package.get("name", "").lower(),
                path
            )

            if key in seen:
                continue

            seen.add(key)

            version = package.get("version", "")

            results.append({
                "name": package.get("name", "Unknown"),
                "version": version,
                "file": path,
                "ecosystem": DEPENDENCY_FILES[filename],
                "pinned": bool(
                    re.search(r"==|~=|>=|<=|@|^\^|^~", version)
                )
            })

    return {
        "dependency_files": find_dependency_files(
            [{"path": path} for path in file_contents]
        ),
        "dependencies": results,
        "dependency_count": len(results),
        "warnings": warnings
    }
