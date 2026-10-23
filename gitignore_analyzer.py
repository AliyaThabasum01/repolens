
"""
RepoLens - .gitignore Analyzer
Checks common ignore rules and highlights possible risks.
Uses Python's standard library only.
"""

from pathlib import PurePosixPath
import fnmatch


RECOMMENDED_RULES = {
    ".env": "Environment files may contain secrets.",
    ".venv/": "Python virtual environments should not be committed.",
    "venv/": "Python virtual environments should not be committed.",
    "__pycache__/": "Python cache files are generated automatically.",
    "*.py[cod]": "Compiled Python files are generated artifacts.",
    "node_modules/": "JavaScript dependencies are usually installed separately.",
    ".DS_Store": "macOS metadata files are usually unnecessary in source control.",
    "dist/": "Build output should usually be generated when needed.",
    "build/": "Build output should usually be generated when needed.",
    ".pytest_cache/": "Pytest cache files are generated automatically.",
    ".coverage": "Coverage output is generated during testing.",
    ".idea/": "IDE-specific settings may be personal or machine-specific.",
    ".vscode/": "IDE settings may be personal or machine-specific.",
}

SENSITIVE_PATTERNS = {
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
}


def parse_gitignore(content):
    """Return active, non-comment .gitignore patterns."""
    patterns = []

    for line in content.splitlines():
        rule = line.strip()

        if not rule or rule.startswith("#"):
            continue

        # A leading ! means the pattern is re-included.
        patterns.append(rule)

    return patterns


def matches_rule(path, rule):
    """Approximate whether a gitignore rule matches a path."""
    if not rule:
        return False

    if rule.startswith("!"):
        return False

    rule = rule.lstrip("/")

    # Directory rules apply to the directory and its descendants.
    if rule.endswith("/"):
        directory = rule.rstrip("/")
        return path == directory or path.startswith(directory + "/")

    filename = PurePosixPath(path).name

    if "/" in rule:
        return fnmatch.fnmatch(path, rule) or path == rule

    return (
        fnmatch.fnmatch(filename, rule)
        or fnmatch.fnmatch(path, rule)
    )


def is_ignored(path, patterns):
    """
    Approximate ignore status based on supplied patterns.

    This is a lightweight check, not a complete implementation
    of Git's ignore precedence and parent-directory rules.
    """
    ignored = False

    for rule in patterns:
        if rule.startswith("!"):
            if matches_rule(path, rule[1:]):
                ignored = False
        elif matches_rule(path, rule):
            ignored = True

    return ignored


def analyze_gitignore(content, repository_files=None):
    """
    Analyze .gitignore contents.

    Args:
        content: Text from the repository's .gitignore file.
        repository_files: Optional list of repository paths.

    Returns:
        Dictionary containing missing rules and possible risks.
    """
    patterns = parse_gitignore(content)

    missing_rules = []

    for rule, reason in RECOMMENDED_RULES.items():
        if not any(
            not pattern.startswith("!")
            and (
                pattern == rule
                or pattern == rule.rstrip("/")
                or pattern == rule + "/"
            )
            for pattern in patterns
        ):
            missing_rules.append({
                "rule": rule,
                "reason": reason,
            })

    sensitive_files = []

    for path in repository_files or []:
        if not isinstance(path, str):
            continue

        filename = PurePosixPath(path).name

        looks_sensitive = any(
            fnmatch.fnmatch(filename, pattern)
            for pattern in SENSITIVE_PATTERNS
        )

        if looks_sensitive and not is_ignored(path, patterns):
            sensitive_files.append({
                "path": path,
                "warning": "Potentially sensitive file is not covered by the checked rules.",
            })

    total_rules = len(RECOMMENDED_RULES)
    covered = total_rules - len(missing_rules)
    score = round((covered / total_rules) * 100)

    if score >= 80:
        status = "Good baseline"
    elif score >= 50:
        status = "Needs improvement"
    else:
        status = "Important rules may be missing"

    recommendations = [
        f"Add '{item['rule']}' if it matches your project workflow."
        for item in missing_rules
    ]

    if sensitive_files:
        recommendations.append(
            "Review potentially sensitive files before committing. "
            "Do not rely on .gitignore alone to protect secrets."
        )

    if not recommendations:
        recommendations.append(
            "The checked baseline rules are present. Review project-specific needs."
        )

    return {
        "score": score,
        "status": status,
        "rules_checked": total_rules,
        "active_patterns": patterns,
        "missing_rules": missing_rules,
        "sensitive_files": sensitive_files,
        "recommendations": recommendations,
    }


def print_report(report):
    """Print the analyzer report."""
    print("\n" + "=" * 50)
    print("        REPOLENS GITIGNORE REPORT")
    print("=" * 50)

    print(f"Baseline score: {report['score']}%")
    print(f"Status: {report['status']}")
    print(f"Rules checked: {report['rules_checked']}")

    print("\nMISSING RECOMMENDED RULES")

    if not report["missing_rules"]:
        print("No missing baseline rules detected.")

    for item in report["missing_rules"]:
        print(f"  [!] {item['rule']}")
        print(f"      {item['reason']}")

    print("\nPOTENTIALLY SENSITIVE FILES")

    if not report["sensitive_files"]:
        print("No matching unignored sensitive filenames detected.")

    for item in report["sensitive_files"]:
        print(f"  [!] {item['path']}")
        print(f"      {item['warning']}")

    print("\nRECOMMENDATIONS")

    for recommendation in report["recommendations"]:
        print(f"  - {recommendation}")

    print("\nNote: This is an approximate static check.")
    print("=" * 50)


if __name__ == "__main__":
    sample_gitignore = """
# Python
__pycache__/
*.py[cod]
.venv/

# Environment
.env
"""

    sample_files = [
        ".env",
        "app.py",
        "src/credentials.json",
        "node_modules/package/index.js",
        "README.md",
    ]

    result = analyze_gitignore(sample_gitignore, sample_files)
    print_report(result)
