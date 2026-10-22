
"""
RepoLens - Markdown Link Checker
Checks local links and image references in Markdown files.
Uses Python's standard library only.
"""

import re
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit


MARKDOWN_EXTENSIONS = {".md", ".markdown"}

LINK_PATTERN = re.compile(
    r"!?\[[^\]]*\]\((?:<([^>]+)>|([^\s)]+)(?:\s+[\"'][^)]*[\"'])?\s*)\)"
)

REFERENCE_PATTERN = re.compile(
    r"(?m)^\s{0,3}\[[^\]]+\]:\s*(?:<([^>]+)>|(\S+))"
)

AUTOMATIC_SKIP = {
    "http", "https", "mailto", "tel", "data", "ftp",
    "javascript",
}


def normalize_path(path):
    """Normalize a repository path."""
    return str(PurePosixPath(path))


def get_markdown_links(content):
    """Extract inline Markdown links and image references."""
    links = []

    for match in LINK_PATTERN.finditer(content):
        target = match.group(1) or match.group(2)

        if target:
            links.append({
                "target": target,
                "kind": "image" if match.group(0).startswith("!") else "link",
            })

    for match in REFERENCE_PATTERN.finditer(content):
        target = match.group(1) or match.group(2)

        if target:
            links.append({
                "target": target,
                "kind": "reference",
            })

    return links


def check_local_target(source_file, target, repository_files):
    """
    Check a local target against known repository paths.
    Returns None when the target is external or not checkable.
    """
    target = unquote(target.strip())

    if not target or target.startswith("#"):
        return None

    parsed = urlsplit(target)

    if parsed.scheme.lower() in AUTOMATIC_SKIP or parsed.netloc:
        return None

    # Strip query strings and fragments.
    target_path = parsed.path

    if not target_path:
        return None

    if target_path.startswith("/"):
        candidate = target_path.lstrip("/")
    else:
        candidate = str(
            PurePosixPath(source_file).parent / target_path
        )

    candidate = str(PurePosixPath(candidate))

    # Normalize relative path components without accessing the filesystem.
    parts = []
    for part in candidate.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            else:
                return False
        else:
            parts.append(part)

    candidate = "/".join(parts)

    if candidate in repository_files:
        return True

    # A link may point to a directory containing tracked files.
    if any(path.startswith(candidate.rstrip("/") + "/")
           for path in repository_files):
        return True

    # GitHub commonly resolves directory links to their README.
    readme_names = {"README.md", "README.markdown"}

    if any(
        path.startswith(candidate.rstrip("/") + "/")
        and PurePosixPath(path).name in readme_names
        for path in repository_files
    ):
        return True

    return False


def analyze_markdown_file(source_file, content, repository_files):
    """Analyze Markdown links in a single file."""
    findings = []

    for link in get_markdown_links(content):
        target = link["target"]

        valid = check_local_target(
            source_file,
            target,
            repository_files,
        )

        if valid is False:
            findings.append({
                "file": source_file,
                "target": target,
                "kind": link["kind"],
                "issue": "Local target not found",
            })

    return findings


def check_repository_links(file_contents):
    """
    Analyze Markdown files.

    Args:
        file_contents: Dictionary of {repository_path: file_text}.
                       Include all known repository paths as keys.

    Returns:
        Summary and broken local link findings.
    """
    if not isinstance(file_contents, dict):
        raise TypeError("file_contents must be a dictionary.")

    repository_files = {
        normalize_path(path)
        for path in file_contents
        if isinstance(path, str)
    }

    markdown_files = [
        (normalize_path(path), content)
        for path, content in file_contents.items()
        if isinstance(path, str)
        and isinstance(content, str)
        and PurePosixPath(path).suffix.lower() in MARKDOWN_EXTENSIONS
    ]

    findings = []

    for path, content in markdown_files:
        findings.extend(
            analyze_markdown_file(path, content, repository_files)
        )

    return {
        "markdown_files_scanned": len(markdown_files),
        "broken_links": sum(
            item["kind"] in {"link", "reference"}
            for item in findings
        ),
        "missing_images": sum(
            item["kind"] == "image"
            for item in findings
        ),
        "findings": findings,
        "recommendations": (
            [
                "Fix broken local links and verify image paths."
            ]
            if findings
            else [
                "No broken local targets were detected in the "
                "supported Markdown link formats."
            ]
        ),
    }


def print_report(report):
    """Print a readable link-checking report."""
    print("\n" + "=" * 48)
    print("        REPOLENS LINK CHECK REPORT")
    print("=" * 48)

    print(
        f"Markdown files scanned: "
        f"{report['markdown_files_scanned']}"
    )
    print(f"Broken links: {report['broken_links']}")
    print(f"Missing images: {report['missing_images']}")

    if not report["findings"]:
        print("\nNo broken local targets detected.")

    for finding in report["findings"]:
        print(f"\nIssue: {finding['issue']}")
        print(f"  File: {finding['file']}")
        print(f"  Target: {finding['target']}")
        print(f"  Type: {finding['kind']}")

    print("\nRecommendations:")
    for recommendation in report["recommendations"]:
        print(f"  - {recommendation}")

    print("\nNote: External URLs are not checked.")
    print("=" * 48)


if __name__ == "__main__":
    sample_files = {
        "README.md": """
# Demo Project

[Installation](docs/install.md)

![Project logo](images/logo.png)

[External website](https://example.com)
""",
        "docs/install.md": """
# Installation

Follow the setup instructions.
""",
        "app.py": """
print("Hello from RepoLens")
""",
    }

    report = check_repository_links(sample_files)
    print_report(report)
