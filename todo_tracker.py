
"""
RepoLens TODO/FIXME Tracker
---------------------------
Finds unfinished tasks and notes in repository files.

Supported markers:
TODO, FIXME, XXX, HACK, BUG, NOTE

No external packages required.
"""

import re
import json
from collections import Counter, defaultdict
from datetime import datetime


MARKER_PATTERN = re.compile(
    r"\b(TODO|FIXME|XXX|HACK|BUG|NOTE)\b\s*:?\s*(.*)",
    re.IGNORECASE,
)

PRIORITY = {
    "FIXME": "High",
    "BUG": "High",
    "XXX": "Medium",
    "HACK": "Medium",
    "TODO": "Medium",
    "NOTE": "Low",
}

SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx",
    ".java", ".c", ".cpp", ".h", ".hpp",
    ".cs", ".go", ".rs", ".php", ".rb",
    ".swift", ".kt", ".kts", ".dart",
    ".html", ".css", ".scss", ".sql",
    ".sh", ".yaml", ".yml", ".toml",
    ".md", ".txt",
}


def get_extension(path):
    """Return a lowercase file extension."""
    filename = path.rsplit("/", 1)[-1]

    if "." not in filename:
        return ""

    return "." + filename.rsplit(".", 1)[-1].lower()


def normalize_files(files):
    """
    Accept a list of dictionaries containing 'path' and 'content'.
    Also supports 'name' instead of 'path'.

    Example:
    [
        {"path": "app.py", "content": "TODO: add validation"}
    ]
    """
    normalized = []

    for item in files:
        if not isinstance(item, dict):
            continue

        path = str(item.get("path") or item.get("name") or "")
        content = item.get("content", "")

        if not path or not isinstance(content, str):
            continue

        if get_extension(path) not in SUPPORTED_EXTENSIONS:
            continue

        normalized.append({
            "path": path,
            "content": content,
        })

    return normalized


def scan_file(path, content):
    """Find TODO-style markers in one file."""
    findings = []

    for line_number, line in enumerate(content.splitlines(), start=1):
        match = MARKER_PATTERN.search(line)

        if not match:
            continue

        marker = match.group(1).upper()
        message = match.group(2).strip()

        findings.append({
            "file": path,
            "line": line_number,
            "marker": marker,
            "priority": PRIORITY.get(marker, "Low"),
            "message": message or "(No description provided)",
            "snippet": line.strip()[:200],
        })

    return findings


def analyze_todos(files):
    """Analyze files and return a structured report."""
    normalized_files = normalize_files(files)
    findings = []

    for file_info in normalized_files:
        findings.extend(
            scan_file(
                file_info["path"],
                file_info["content"],
            )
        )

    findings.sort(
        key=lambda item: (
            {"High": 0, "Medium": 1, "Low": 2}.get(
                item["priority"], 3
            ),
            item["file"].lower(),
            item["line"],
        )
    )

    marker_counts = Counter(
        item["marker"] for item in findings
    )

    priority_counts = Counter(
        item["priority"] for item in findings
    )

    file_counts = defaultdict(int)

    for item in findings:
        file_counts[item["file"]] += 1

    return {
        "generated_at": datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
        "files_scanned": len(normalized_files),
        "total_findings": len(findings),
        "priority_summary": {
            "High": priority_counts.get("High", 0),
            "Medium": priority_counts.get("Medium", 0),
            "Low": priority_counts.get("Low", 0),
        },
        "marker_summary": dict(sorted(marker_counts.items())),
        "files_with_findings": dict(
            sorted(
                file_counts.items(),
                key=lambda item: (-item[1], item[0].lower()),
            )
        ),
        "findings": findings,
        "limitations": [
            "Scans file text only; it does not understand code context.",
            "May match marker words in strings or documentation.",
            "Only scans the supplied file contents and supported extensions.",
        ],
    }


def print_report(report):
    """Display a readable summary in the terminal."""
    print("=" * 60)
    print("          REPOLENS TODO / FIXME TRACKER")
    print("=" * 60)

    print(f"Files scanned: {report['files_scanned']}")
    print(f"Total findings: {report['total_findings']}")

    print("\nPriority Summary")
    for priority, count in report["priority_summary"].items():
        print(f"  {priority}: {count}")

    if not report["findings"]:
        print("\nNo TODO-style markers found.")
        return

    print("\nFindings")
    print("-" * 60)

    for item in report["findings"]:
        print(
            f"[{item['priority']}] {item['marker']} "
            f"| {item['file']}:{item['line']}"
        )
        print(f"  {item['message']}")

    print("\nFiles with the most findings")
    for path, count in list(
        report["files_with_findings"].items()
    )[:10]:
        print(f"  {path}: {count}")


if __name__ == "__main__":
    # Example data to test the tracker.
    sample_files = [
        {
            "path": "app.py",
            "content": (
                "def login():\n"
                "    # TODO: validate user input\n"
                "    # FIXME: handle invalid credentials\n"
                "    pass\n"
            ),
        },
        {
            "path": "utils.js",
            "content": (
                "// HACK: temporary workaround\n"
                "// NOTE: review this function later\n"
            ),
        },
        {
            "path": "README.md",
            "content": (
                "# Project\n"
                "<!-- TODO: add installation instructions -->\n"
            ),
        },
    ]

    result = analyze_todos(sample_files)
    print_report(result)

    # Save a sample report as JSON.
    with open("todo_report.json", "w", encoding="utf-8") as file:
        json.dump(result, file, indent=2, ensure_ascii=False)

    print("\nJSON report saved to todo_report.json")
