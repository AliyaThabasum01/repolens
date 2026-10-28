
"""
RepoLens Changelog & Release Analyzer
-------------------------------------
Checks changelog text for:
- Version headings
- Release dates
- Missing release sections
- Duplicate version headings
- Unreleased sections
- Basic release-note quality

Uses Python's standard library only.
"""

import re
import json
from collections import Counter
from datetime import datetime


VERSION_PATTERN = re.compile(
    r"^\s*#{1,6}\s+"
    r"(?:\[\s*)?"
    r"(?:v(?:ersion\s*)?)?"
    r"(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?)"
    r"(?:\s*\])?"
    r"(?:\s*[-–—(]\s*(.*?)\s*\)?)?\s*$",
    re.IGNORECASE,
)

UNRELEASED_PATTERN = re.compile(
    r"^\s*#{1,6}\s+.*\b(unreleased|upcoming|next release)\b",
    re.IGNORECASE,
)

DATE_PATTERN = re.compile(
    r"\b("
    r"\d{4}-\d{2}-\d{2}"
    r"|\d{4}/\d{2}/\d{2}"
    r"|\d{2}-\d{2}-\d{4}"
    r"|\d{2}/\d{2}/\d{4}"
    r")\b"
)

SECTION_PATTERN = re.compile(
    r"^\s*#{2,6}\s+(.+?)\s*$"
)

EXPECTED_SECTIONS = {
    "added": ["added", "new", "features"],
    "changed": ["changed", "changes", "updated", "updates"],
    "fixed": ["fixed", "fixes", "bug fixes"],
    "removed": ["removed", "deprecated"],
    "security": ["security", "security fixes"],
}


def parse_version_heading(line):
    """Return parsed version information for a heading."""
    match = VERSION_PATTERN.match(line)

    if not match:
        return None

    return {
        "version": match.group(1),
        "extra": (match.group(2) or "").strip(),
    }


def validate_date(date_text):
    """Validate supported date formats."""
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
    ]

    for date_format in formats:
        try:
            parsed = datetime.strptime(date_text, date_format)
            return parsed.date().isoformat()
        except ValueError:
            continue

    return None


def analyze_changelog(content, filename="CHANGELOG.md"):
    """Analyze changelog Markdown and return a report."""

    if not isinstance(content, str):
        raise TypeError("Changelog content must be a string.")

    lines = content.splitlines()
    findings = []
    releases = []
    current_release = None
    section_counts = Counter()

    def add_finding(severity, message, line=None):
        findings.append({
            "severity": severity,
            "message": message,
            "line": line,
        })

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()

        if not stripped:
            continue

        if UNRELEASED_PATTERN.match(stripped):
            releases.append({
                "version": "Unreleased",
                "heading": stripped.lstrip("#").strip(),
                "line": line_number,
                "date": None,
                "sections": [],
                "entry_count": 0,
                "unreleased": True,
            })
            current_release = releases[-1]
            continue

        parsed_version = parse_version_heading(stripped)

        if parsed_version:
            current_release = {
                "version": parsed_version["version"],
                "heading": stripped.lstrip("#").strip(),
                "line": line_number,
                "date": None,
                "sections": [],
                "entry_count": 0,
                "unreleased": False,
            }
            releases.append(current_release)
            continue

        if current_release is not None:
            date_match = DATE_PATTERN.search(stripped)

            if date_match and current_release["date"] is None:
                normalized_date = validate_date(date_match.group(1))

                if normalized_date:
                    current_release["date"] = normalized_date
                else:
                    add_finding(
                        "Warning",
                        f"Invalid date '{date_match.group(1)}'.",
                        line_number,
                    )

            section_match = SECTION_PATTERN.match(stripped)

            if section_match:
                section_name = section_match.group(1).strip()
                current_release["sections"].append(section_name)
                section_counts[section_name.lower()] += 1

            # Count ordinary Markdown list entries.
            if re.match(r"^\s*[-*+]\s+\S+", line):
                current_release["entry_count"] += 1

    if not releases:
        add_finding(
            "High",
            "No version headings found. Add headings such as "
            "'## 1.0.0 - 2026-10-28'.",
        )

    # Detect duplicate version headings.
    version_counts = Counter(
        release["version"].lower()
        for release in releases
        if not release["unreleased"]
    )

    for release in releases:
        if release["unreleased"]:
            continue

        if version_counts[release["version"].lower()] > 1:
            add_finding(
                "High",
                f"Duplicate version heading: {release['version']}.",
                release["line"],
            )
            version_counts[release["version"].lower()] = 1

    # Inspect each release entry.
    for release in releases:
        if release["unreleased"]:
            continue

        if release["entry_count"] == 0:
            add_finding(
                "Medium",
                f"Version {release['version']} has no list entries.",
                release["line"],
            )

        if release["date"] is None:
            add_finding(
                "Low",
                f"No recognizable release date for "
                f"version {release['version']}.",
                release["line"],
            )

        if not release["sections"]:
            add_finding(
                "Low",
                f"Version {release['version']} has no subsections. "
                "Consider organizing changes under Added, Changed, "
                "Fixed, or Security.",
                release["line"],
            )

    # Check whether standard change categories appear anywhere.
    all_sections = list(section_counts.keys())

    missing_categories = []

    for category, aliases in EXPECTED_SECTIONS.items():
        if not any(
            alias in section_name
            for section_name in all_sections
            for alias in aliases
        ):
            missing_categories.append(category)

    if missing_categories:
        add_finding(
            "Info",
            "Consider documenting these categories when relevant: "
            + ", ".join(missing_categories) + ".",
        )

    unreleased_count = sum(
        1 for release in releases if release["unreleased"]
    )

    if unreleased_count > 1:
        add_finding(
            "Medium",
            "Multiple Unreleased/upcoming sections were found. "
            "Check whether these should be combined.",
        )

    findings.sort(
        key=lambda item: (
            {"High": 0, "Medium": 1, "Low": 2, "Info": 3}.get(
                item["severity"], 4
            ),
            item["line"] or 0,
        )
    )

    return {
        "filename": filename,
        "analyzed_at": datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
        "total_lines": len(lines),
        "total_releases": len(releases),
        "unreleased_sections": unreleased_count,
        "severity_summary": {
            severity: sum(
                1 for finding in findings
                if finding["severity"] == severity
            )
            for severity in ["High", "Medium", "Low", "Info"]
        },
        "releases": releases,
        "findings": findings,
        "limitations": [
            "This is a static Markdown analyzer, not a full changelog standard validator.",
            "Dates are recognized only in supported formats.",
            "Missing categories are suggestions, not necessarily errors.",
        ],
    }


def print_report(report):
    """Print the changelog analysis."""

    print("=" * 60)
    print("         REPOLENS CHANGELOG ANALYZER")
    print("=" * 60)
    print(f"File: {report['filename']}")
    print(f"Lines: {report['total_lines']}")
    print(f"Release sections: {report['total_releases']}")
    print(f"Unreleased sections: {report['unreleased_sections']}")

    print("\nRelease History")
    if not report["releases"]:
        print("  No release headings detected.")

    for release in report["releases"]:
        date = release["date"] or "No date"
        print(
            f"  {release['version']} | {date} | "
            f"{release['entry_count']} entries"
        )

    print("\nFinding Summary")
    for severity, count in report["severity_summary"].items():
        print(f"  {severity}: {count}")

    print("\nRecommendations")
    if not report["findings"]:
        print("  No issues detected.")

    for finding in report["findings"]:
        location = (
            f"Line {finding['line']}"
            if finding["line"] is not None
            else "General"
        )
        print(f"  [{finding['severity']}] {location}: {finding['message']}")


if __name__ == "__main__":
    sample_changelog = """
# Changelog

## Unreleased
- Improve dashboard performance

## 1.1.0 - 2026-10-28
### Added
- Added repository comparison
- Added JSON export

### Fixed
- Fixed README preview rendering

## 1.0.0 - 2026-10-20
### Added
- Initial RepoLens release
"""

    report = analyze_changelog(sample_changelog)
    print_report(report)

    with open(
        "changelog_report.json",
        "w",
        encoding="utf-8",
    ) as output_file:
        json.dump(report, output_file, indent=2)

    print("\nJSON report saved to changelog_report.json")
