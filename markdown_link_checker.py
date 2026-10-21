
"""
RepoLens - Markdown Link Checker
Finds Markdown links and checks local repository references.
Uses Python's standard library only.
"""

import re
from pathlib import PurePosixPath
from urllib.parse import urlparse, unquote


MARKDOWN_EXTENSIONS = {".md", ".markdown"}

# Matches [link text](destination)
LINK_PATTERN = re.compile(
    r"(?<!!)\[([^\]]*)\]\(\s*(?:<([^>]+)>|([^\s)]+))"
    r"(?:\s+[\"'][^\"']*[\"'])?\s*\)"
)

# Matches reference-style definitions: [docs]: ./docs.md
REFERENCE_PATTERN = re.compile(
    r"(?m)^\s{0,3}\[([^\]]+)\]:\s*(\S+)"
)


def normalize_path(path):
    """Normalize a repository path."""
    return str(PurePosixPath(path))


def get_destination(match):
    """Return a destination from a Markdown link match."""
    return match.group(2) or match.group(3) or ""


def is_external_link(destination):
    """Identify links that point outside the repository."""
    parsed = urlparse(destination)
    return parsed.scheme.lower() in {
        "http", "https", "mailto", "tel", "ftp"
    } or destination.startswith("//")


def resolve_local_link(source_file, destination):
    """Resolve a relative link from its Markdown source file."""
    destination = unquote(destination.strip())

    if not destination:
        return None

    parsed = urlparse(destination)

    if parsed.scheme or destination.startswith("//"):
        return None

    if destination.startswith("#"):
        return {
            "path": normalize_path(source_file),
            "anchor": destination[1:],
        }

    target = parsed.path

    if not target:
        return {
            "path": normalize_path(source_file),
            "anchor": parsed.fragment,
        }

    source_parent = PurePosixPath(source_file).parent

    if target.startswith("/"):
        resolved = PurePosixPath(target.lstrip("/"))
    else:
        resolved = source_parent / target

    # Normalize "." and ".." without accessing the local filesystem.
    parts = []

    for part in resolved.parts:
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            else:
                return {
                    "path": target,
                    "anchor": parsed.fragment,
                    "outside_repository": True,
                }
        else:
            parts.append(part)

    return {
        "path": "/".join(parts),
        "anchor": parsed.fragment,
    }


def check_markdown_links(file_contents):
    """
    Analyze Markdown links in a repository.

    Args:
        file_contents: Dictionary mapping repository paths to text.

    Returns:
        Summary, detected links, and potential issues.
    """
    if not isinstance(file_contents, dict):
        raise TypeError("file_contents must be a dictionary.")

    repo_paths = {
        normalize_path(path)
        for path in file_contents
        if isinstance(path, str)
    }

    markdown_files = {
        normalize_path(path): content
        for path, content in file_contents.items()
        if isinstance(path, str)
        and PurePosixPath(path).suffix.lower() in MARKDOWN_EXTENSIONS
        and isinstance(content, str)
    }

    links = []
    issues = []

    for source_file, content in markdown_files.items():
        # Ignore fenced code blocks to reduce false positives.
        cleaned_lines = []
        in_fence = False
        fence_marker = None

        for line in content.splitlines():
            stripped = line.lstrip()

            if stripped.startswith("```") or stripped.startswith("~~~"):
                marker = stripped[:3]

                if not in_fence:
                    in_fence = True
                    fence_marker = marker
                elif marker == fence_marker:
                    in_fence = False
                    fence_marker = None

                cleaned_lines.append("")
            elif in_fence:
                cleaned_lines.append("")
            else:
                cleaned_lines.append(line)

        cleaned_content = "\n".join(cleaned_lines)

        # Collect reference-style link definitions.
        references = {
            label.strip().lower(): destination
            for label, destination in REFERENCE_PATTERN.findall(
                cleaned_content
            )
        }

        matches = list(LINK_PATTERN.finditer(cleaned_content))

        # Also support simple reference uses such as [guide][docs].
        reference_use_pattern = re.compile(
            r"(?<!!)\[([^\]]+)\]\[([^\]]*)\]"
        )

        for match in matches:
            destination = get_destination(match).strip()

            if not destination:
                continue

            link = {
                "source": source_file,
                "text": match.group(1),
                "destination": destination,
                "line": cleaned_content[:match.start()].count("\n") + 1,
                "status": "unchecked",
            }

            if is_external_link(destination):
                link["status"] = "external_unverified"

            elif destination.startswith("#"):
                link["status"] = "anchor_unverified"

            else:
                resolved = resolve_local_link(
                    source_file, destination
                )

                if resolved.get("outside_repository"):
                    link["status"] = "outside_repository"

                elif resolved and resolved["path"] in repo_paths:
                    link["status"] = "exists"

                elif resolved and (
                    resolved["path"] + "/README.md" in repo_paths
                    or resolved["path"] + "/index.md" in repo_paths
                ):
                    link["status"] = "exists"

                else:
                    link["status"] = "missing"

            links.append(link)

            if link["status"] == "missing":
                issues.append({
                    "file": source_file,
                    "line": link["line"],
                    "destination": destination,
                    "message": "Local link target was not found.",
                })

            elif link["status"] == "outside_repository":
                issues.append({
                    "file": source_file,
                    "line": link["line"],
                    "destination": destination,
                    "message": "Link appears to resolve outside the repository.",
                })

        for match in reference_use_pattern.finditer(cleaned_content):
            label = match.group(2).strip().lower() or match.group(1).strip().lower()

            # Skip reference definitions themselves.
            line_start = cleaned_content.rfind("\n", 0, match.start()) + 1
            line_text = cleaned_content[line_start:match.start()].lstrip()

            if line_text.startswith("["):
                continue

            if label not in references:
                issues.append({
                    "file": source_file,
                    "line": cleaned_content[:match.start()].count("\n") + 1,
                    "destination": f"[{label}]",
                    "message": "Reference-style link definition was not found.",
                })

    counts = {
        "exists": sum(link["status"] == "exists" for link in links),
        "missing": sum(link["status"] == "missing" for link in links),
        "external_unverified": sum(
            link["status"] == "external_unverified" for link in links
        ),
        "anchor_unverified": sum(
            link["status"] == "anchor_unverified" for link in links
        ),
    }

    return {
        "markdown_files_scanned": len(markdown_files),
        "total_links_found": len(links),
        "counts": counts,
        "issues": issues,
        "links": links,
    }


def print_report(report):
    """Display a readable link-checking report."""
    print("\n" + "=" * 48)
    print("       REPOLENS MARKDOWN LINK REPORT")
    print("=" * 48)

    print(f"Markdown files scanned: {report['markdown_files_scanned']}")
    print(f"Links found: {report['total_links_found']}")

    for status, count in report["counts"].items():
        print(f"{status.replace('_', ' ').title()}: {count}")

    print("\nLINK DETAILS")

    for link in report["links"]:
        print(
            f"[{link['status']}] {link['source']}:"
            f"{link['line']} -> {link['destination']}"
        )

    print("\nPOTENTIAL ISSUES")

    if not report["issues"]:
        print("No missing local links detected.")
    else:
        for issue in report["issues"]:
            print(
                f"- {issue['file']}:{issue['line']} "
                f"{issue['destination']}: {issue['message']}"
            )

    print("\nNote: External URLs and anchors are not verified.")
    print("=" * 48)


if __name__ == "__main__":
    sample_files = {
        "README.md": """
# RepoLens

Read the [guide](docs/guide.md).
See the [missing page](docs/missing.md).
Visit [Python](https://www.python.org/).
""",
        "docs/guide.md": """
# User Guide

Welcome to RepoLens!
""",
    }

    result = check_markdown_links(sample_files)
    print_report(result)
