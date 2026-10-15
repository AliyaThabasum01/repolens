
"""
RepoLens - Repository Configuration Checker
Checks essential configuration files in a repository.
"""

from pathlib import PurePosixPath


CONFIG_FILES = {
    "README.md": "Project documentation",
    ".gitignore": "Files Git should ignore",
    "LICENSE": "Project license",
    "requirements.txt": "Python dependencies",
    "pyproject.toml": "Modern Python project configuration",
    "setup.py": "Python package setup",
    "Dockerfile": "Docker container configuration",
    "docker-compose.yml": "Multi-container Docker configuration",
    "docker-compose.yaml": "Multi-container Docker configuration",
    ".env.example": "Example environment variables",
    ".env.sample": "Example environment variables",
    ".github/workflows": "GitHub Actions automation",
    "tests": "Automated tests directory",
    "CONTRIBUTING.md": "Contribution guidelines",
    "CHANGELOG.md": "Project change history",
}

ALTERNATIVES = {
    "requirements.txt": ["pyproject.toml", "Pipfile"],
    "pyproject.toml": ["requirements.txt", "Pipfile"],
    "docker-compose.yml": ["docker-compose.yaml"],
    ".env.example": [".env.sample"],
}


def normalize_paths(files):
    """Normalize repository file paths."""
    if not files:
        return set()

    paths = set()

    for item in files:
        if isinstance(item, str):
            path = item
        elif isinstance(item, dict):
            path = item.get("path", "")
        else:
            continue

        if path:
            paths.add(str(PurePosixPath(path)).lstrip("./"))

    return paths


def path_exists(paths, target):
    """Check whether a file or directory exists."""
    target = target.rstrip("/")

    return any(
        path == target or path.startswith(target + "/")
        for path in paths
    )


def check_repository_config(files):
    """
    Analyze repository configuration.

    Args:
        files: List of file paths or dictionaries containing 'path'.

    Returns:
        Dictionary containing score, findings and recommendations.
    """
    paths = normalize_paths(files)

    if not paths:
        return {
            "score": 0,
            "status": "No files found",
            "checked_files": 0,
            "present": [],
            "missing": [],
            "recommendations": [
                "Check that the repository file list was fetched correctly."
            ],
        }

    present = []
    missing = []
    skipped = []

    for filename, purpose in CONFIG_FILES.items():
        alternatives = ALTERNATIVES.get(filename, [])

        if path_exists(paths, filename):
            present.append({
                "file": filename,
                "purpose": purpose,
            })
        elif any(path_exists(paths, alt) for alt in alternatives):
            skipped.append({
                "file": filename,
                "reason": "Equivalent configuration file found",
            })
        else:
            missing.append({
                "file": filename,
                "purpose": purpose,
            })

    # Score core configuration separately from optional files.
    core_files = [
        "README.md",
        ".gitignore",
        "LICENSE",
    ]

    core_present = sum(
        path_exists(paths, filename)
        for filename in core_files
    )

    score = round((core_present / len(core_files)) * 100)

    if score == 100:
        status = "Core configuration complete"
    elif score >= 67:
        status = "Mostly configured"
    elif score >= 34:
        status = "Needs improvement"
    else:
        status = "Configuration needs attention"

    recommendations = []

    if not path_exists(paths, "README.md"):
        recommendations.append(
            "Add a README.md describing the project, setup and usage."
        )

    if not path_exists(paths, ".gitignore"):
        recommendations.append(
            "Add a .gitignore to avoid committing generated or local files."
        )

    if not path_exists(paths, "LICENSE"):
        recommendations.append(
            "Consider adding a license that matches your intended usage."
        )

    has_python_dependencies = any(
        path_exists(paths, filename)
        for filename in [
            "requirements.txt",
            "pyproject.toml",
            "Pipfile",
        ]
    )

    if any(
        path.endswith(".py") for path in paths
    ) and not has_python_dependencies:
        recommendations.append(
            "If the Python project uses external packages, document "
            "them in requirements.txt, pyproject.toml or Pipfile."
        )

    if not path_exists(paths, "tests"):
        recommendations.append(
            "Consider adding automated tests to improve reliability."
        )

    if not path_exists(paths, ".github/workflows"):
        recommendations.append(
            "Consider GitHub Actions for automated testing and checks."
        )

    if not recommendations:
        recommendations.append(
            "No core configuration recommendations at this time."
        )

    return {
        "score": score,
        "status": status,
        "checked_files": len(CONFIG_FILES),
        "present": present,
        "missing": missing,
        "equivalent_files": skipped,
        "recommendations": recommendations,
    }


def print_report(result):
    """Print a readable configuration report."""
    print("\n" + "=" * 45)
    print("       REPOLENS CONFIGURATION REPORT")
    print("=" * 45)

    print(f"Configuration score: {result['score']}%")
    print(f"Status: {result['status']}")
    print(f"Checks performed: {result['checked_files']}")

    print("\nPRESENT FILES")
    for item in result.get("present", []):
        print(f"  [OK] {item['file']} - {item['purpose']}")

    print("\nMISSING FILES")
    for item in result.get("missing", []):
        print(f"  [!] {item['file']} - {item['purpose']}")

    print("\nRECOMMENDATIONS")
    for recommendation in result.get("recommendations", []):
        print(f"  - {recommendation}")

    print("=" * 45)


if __name__ == "__main__":
    # Example repository structure for testing.
    sample_files = [
        {"path": "README.md"},
        {"path": ".gitignore"},
        {"path": "app.py"},
        {"path": "requirements.txt"},
        {"path": "tests/test_app.py"},
    ]

    report = check_repository_config(sample_files)
    print_report(report)
