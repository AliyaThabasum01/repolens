
import json
import re


REQUIRED_SECTIONS = {
    "installation": [
        "installation", "setup", "getting started"
    ],
    "development guidelines": [
        "development", "coding standards", "code style"
    ],
    "testing": [
        "testing", "tests", "run tests"
    ],
    "pull requests": [
        "pull request", "pull requests"
    ],
    "bug reports": [
        "bug report", "reporting bugs", "issues"
    ]
}


def analyze_contribution_guide(files):
    report = {
        "guide_found": False,
        "guide_path": None,
        "word_count": 0,
        "sections_found": [],
        "sections_missing": [],
        "links_found": 0,
        "recommendations": []
    }

    guide = None

    for file in files:
        path = file.get("path", "").replace("\\", "/")

        if path.lower() == "contributing.md":
            guide = file
            break

    if guide is None:
        report["recommendations"].append(
            "Create a CONTRIBUTING.md file."
        )
        report["sections_missing"] = list(REQUIRED_SECTIONS)
        return report

    report["guide_found"] = True
    report["guide_path"] = guide.get("path")

    content = guide.get("content", "")
    content_lower = content.lower()

    report["word_count"] = len(content.split())

    report["links_found"] = len(
        re.findall(r"\[[^\]]+\]\([^)]+\)", content)
    )

    for section, keywords in REQUIRED_SECTIONS.items():
        found = any(
            re.search(
                r"^\s{0,3}#{1,6}\s+.*"
                + re.escape(keyword),
                content_lower,
                re.MULTILINE
            )
            for keyword in keywords
        )

        if found:
            report["sections_found"].append(section)
        else:
            report["sections_missing"].append(section)

    if report["word_count"] < 100:
        report["recommendations"].append(
            "Add more detailed contributor instructions."
        )

    for section in report["sections_missing"]:
        report["recommendations"].append(
            f"Add a section about {section}."
        )

    if report["links_found"] == 0:
        report["recommendations"].append(
            "Consider adding useful documentation links."
        )

    if not report["recommendations"]:
        report["recommendations"].append(
            "The contribution guide covers all checked sections."
        )

    return report


def print_report(report):
    print("\n===== CONTRIBUTION GUIDE REPORT =====")

    if not report["guide_found"]:
        print("CONTRIBUTING.md: Not found")
    else:
        print("CONTRIBUTING.md:", report["guide_path"])
        print("Word count:", report["word_count"])
        print("Links found:", report["links_found"])

    print("\nSections Found:")

    for section in report["sections_found"]:
        print("-", section)

    print("\nSections Missing:")

    for section in report["sections_missing"]:
        print("-", section)

    print("\nRecommendations:")

    for recommendation in report["recommendations"]:
        print("-", recommendation)


def export_report(report, filename="contribution_report.json"):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    print("\nReport exported to", filename)


if __name__ == "__main__":
    sample_files = [
        {
            "path": "CONTRIBUTING.md",
            "content": """
# Contributing Guide

## Installation
Install the required dependencies.

## Development Guidelines
Follow the coding standards.

## Testing
Run tests before submitting changes.

## Pull Requests
Create a pull request for your changes.

## Bug Reports
Report bugs through GitHub issues.

[Documentation](https://example.com)
"""
        }
    ]

    result = analyze_contribution_guide(sample_files)
    print_report(result)
    export_report(result)
