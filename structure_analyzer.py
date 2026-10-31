
"""
RepoLens Repository Structure Analyzer
---------------------------------------
Analyzes repository organization and folder structure.

Features:
- Counts files and folders
- Detects root-level files
- Identifies common project directories
- Finds deeply nested files
- Detects empty-looking folders from supplied paths
- Provides organization recommendations
- Exports results as JSON

Uses Python's standard library only.
"""

import json
from collections import Counter
from datetime import datetime
from pathlib import PurePosixPath


IMPORTANT_DIRECTORIES = {
    "src": "Main source code",
    "tests": "Automated tests",
    "test": "Automated tests",
    "docs": "Project documentation",
    "documentation": "Project documentation",
    "assets": "Images and other assets",
    "public": "Public static files",
    "config": "Configuration files",
    "scripts": "Utility scripts",
    ".github": "GitHub workflows and templates",
}

IMPORTANT_FILES = {
    "README.md": "Project introduction",
    "LICENSE": "Project license",
    ".gitignore": "Ignored files configuration",
    "requirements.txt": "Python dependencies",
    "pyproject.toml": "Python project configuration",
    "package.json": "Node.js project configuration",
    "dockerfile": "Container configuration",
    "docker-compose.yml": "Container orchestration",
    "docker-compose.yaml": "Container orchestration",
}


def normalize_path(path):
    """Normalize a repository path safely."""

    path = str(path).replace("\\", "/").strip()
    path = path.lstrip("./")

    if not path or path.startswith("/"):
        return None

    parts = PurePosixPath(path).parts

    if ".." in parts:
        return None

    return "/".join(parts)


def analyze_structure(files):
    """
    Analyze repository paths.

    Expected input:
    [
        {"path": "src/app.py"},
        {"path": "tests/test_app.py"},
        {"path": "README.md"}
    ]

    Both file and directory paths are accepted.
    """

    file_paths = set()
    directory_paths = set()
    invalid_paths = []

    for item in files:
        if not isinstance(item, dict):
            continue

        raw_path = item.get("path")

        if not isinstance(raw_path, str):
            continue

        is_directory = raw_path.endswith("/")
        normalized = normalize_path(raw_path)

        if not normalized:
            invalid_paths.append(raw_path)
            continue

        if is_directory:
            directory_paths.add(normalized)
            continue

        file_paths.add(normalized)

        # Add all parent directories.
        parts = normalized.split("/")

        for index in range(1, len(parts)):
            directory_paths.add("/".join(parts[:index]))

    # Identify files and directories at repository root.
    root_files = [
        path for path in sorted(file_paths)
        if "/" not in path
    ]

    root_directories = [
        path for path in sorted(directory_paths)
        if "/" not in path
    ]

    # Count files in each top-level directory.
    top_level_counts = Counter()

    for path in file_paths:
        parts = path.split("/")

        if len(parts) > 1:
            top_level_counts[parts[0]] += 1

    # Identify deeply nested files.
    deeply_nested = []

    for path in sorted(file_paths):
        depth = len(path.split("/")) - 1

        if depth >= 4:
            deeply_nested.append({
                "path": path,
                "depth": depth,
            })

    # Find folders explicitly supplied without any known files.
    folders_with_files = set()

    for path in file_paths:
        parts = path.split("/")

        for index in range(1, len(parts)):
            folders_with_files.add("/".join(parts[:index]))

    empty_directories = sorted(
        directory
        for directory in directory_paths
        if directory not in folders_with_files
    )

    # Check important project directories.
    existing_directory_names = {
        path.split("/")[-1].lower()
        for path in directory_paths
    }

    directory_status = {}

    for directory, description in IMPORTANT_DIRECTORIES.items():
        directory_status[directory] = {
            "description": description,
            "present": directory.lower() in existing_directory_names,
        }

    # Check important root-level files.
    root_file_names = {
        path.lower() for path in root_files
    }

    file_status = {}

    for filename, description in IMPORTANT_FILES.items():
        file_status[filename] = {
            "description": description,
            "present": filename.lower() in root_file_names,
        }

    recommendations = []

    if not root_files and not root_directories:
        recommendations.append(
            "No valid repository paths were supplied."
        )

    if not any(
        directory_status[name]["present"]
        for name in ["src"]
    ):
        recommendations.append(
            "Consider organizing application code inside a src/ directory."
        )

    if not any(
        directory_status[name]["present"]
        for name in ["tests", "test"]
    ):
        recommendations.append(
            "Consider adding a tests/ directory for automated tests."
        )

    if not file_status["README.md"]["present"]:
        recommendations.append(
            "Add a README.md file explaining the project."
        )

    if not file_status[".gitignore"]["present"]:
        recommendations.append(
            "Add a .gitignore file to exclude unnecessary files."
        )

    if deeply_nested:
        recommendations.append(
            "Review deeply nested files to see whether the folder "
            "structure can be simplified."
        )

    if invalid_paths:
        recommendations.append(
            "Review invalid or unsafe repository paths."
        )

    return {
        "generated_at": datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
        "total_files": len(file_paths),
        "total_directories": len(directory_paths),
        "root_file_count": len(root_files),
        "root_directory_count": len(root_directories),
        "root_files": root_files,
        "root_directories": root_directories,
        "top_level_file_distribution": dict(
            sorted(top_level_counts.items())
        ),
        "deeply_nested_files": deeply_nested,
        "empty_directories": empty_directories,
        "important_directories": directory_status,
        "important_files": file_status,
        "invalid_paths": invalid_paths,
        "recommendations": recommendations,
        "limitations": [
            "Analysis is based on supplied paths, not actual file contents.",
            "Empty directories can only be identified when explicitly supplied.",
            "Missing folders are suggestions, not necessarily project defects.",
            "A repository may use a valid structure without the suggested directories.",
        ],
    }


def print_report(report):
    """Print a readable repository structure report."""

    print("=" * 60)
    print("       REPOLENS REPOSITORY STRUCTURE ANALYZER")
    print("=" * 60)

    print(f"Total files: {report['total_files']}")
    print(f"Total directories: {report['total_directories']}")
    print(f"Root-level files: {report['root_file_count']}")
    print(f"Root-level directories: {report['root_directory_count']}")

    print("\nRoot Directories")

    for directory in report["root_directories"]:
        count = report["top_level_file_distribution"].get(
            directory, 0
        )
        print(f"  {directory}/ — {count} files")

    print("\nImportant Directory Checks")

    for name, details in report["important_directories"].items():
        status = "Present" if details["present"] else "Not found"
        print(f"  {name}: {status}")

    print("\nImportant File Checks")

    for name, details in report["important_files"].items():
        status = "Present" if details["present"] else "Not found"
        print(f"  {name}: {status}")

    print("\nDeeply Nested Files")

    if report["deeply_nested_files"]:
        for item in report["deeply_nested_files"]:
            print(f"  {item['path']} (depth: {item['depth']})")
    else:
        print("  None detected.")

    print("\nRecommendations")

    if report["recommendations"]:
        for recommendation in report["recommendations"]:
            print(f"  - {recommendation}")
    else:
        print("  No recommendations.")


if __name__ == "__main__":

    sample_files = [
        {"path": "README.md"},
        {"path": ".gitignore"},
        {"path": "requirements.txt"},
        {"path": "app.py"},
        {"path": "src/main.py"},
        {"path": "src/utils/helper.py"},
        {"path": "tests/test_main.py"},
        {"path": "docs/guide.md"},
        {"path": "assets/logo.png"},
        {"path": ".github/workflows/test.yml"},
        {"path": "src/modules/core/engine/runner.py"},
    ]

    report = analyze_structure(sample_files)

    print_report(report)

    with open(
        "structure_report.json",
        "w",
        encoding="utf-8",
    ) as output_file:
        json.dump(report, output_file, indent=2)

    print("\nJSON report saved to structure_report.json")
