
import json
import re


def analyze_markdown(files):
    report = {
        "files_analyzed": 0,
        "total_headings": 0,
        "duplicate_headings": [],
        "heading_issues": [],
        "long_sections": [],
        "empty_files": [],
        "file_details": []
    }

    for file in files:
        path = file.get("path", "")
        content = file.get("content", "")

        if not path.lower().endswith(".md"):
            continue

        report["files_analyzed"] += 1

        if not content.strip():
            report["empty_files"].append(path)
            continue

        headings = []
        heading_counts = {}
        previous_level = 0

        for line_number, line in enumerate(
            content.splitlines(), start=1
        ):
            match = re.match(
                r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$",
                line
            )

            if not match:
                continue

            level = len(match.group(1))
            title = match.group(2).strip()

            headings.append({
                "title": title,
                "level": level,
                "line": line_number
            })

            normalized = title.lower()

            heading_counts.setdefault(normalized, []).append(
                line_number
            )

            if previous_level and level > previous_level + 1:
                report["heading_issues"].append({
                    "file": path,
                    "line": line_number,
                    "issue": (
                        f"Heading level skipped: H{previous_level} "
                        f"to H{level}"
                    )
                })

            previous_level = level

        report["total_headings"] += len(headings)

        for title, lines in heading_counts.items():
            if len(lines) > 1:
                report["duplicate_headings"].append({
                    "file": path,
                    "heading": title,
                    "lines": lines
                })

        if not headings:
            report["heading_issues"].append({
                "file": path,
                "line": 1,
                "issue": "No Markdown headings found"
            })

        lines = content.splitlines()
        section_start = None
        section_title = None

        for index, line in enumerate(lines + ["# END"], start=1):
            match = re.match(
                r"^\s{0,3}#{1,6}\s+(.+)",
                line
            )

            if match:
                if section_start is not None:
                    word_count = len(
                        " ".join(
                            lines[section_start:index - 1]
                        ).split()
                    )

                    if word_count > 500:
                        report["long_sections"].append({
                            "file": path,
                            "section": section_title,
                            "word_count": word_count
                        })

                section_start = index
                section_title = (
                    match.group(1).strip()
                    if index <= len(lines)
                    else "Unknown"
                )

        report["file_details"].append({
            "file": path,
            "word_count": len(content.split()),
            "heading_count": len(headings)
        })

    report["total_issues"] = (
        len(report["duplicate_headings"])
        + len(report["heading_issues"])
        + len(report["long_sections"])
        + len(report["empty_files"])
    )

    return report


def print_report(report):
    print("\n===== MARKDOWN DOCUMENTATION REPORT =====")

    print("Files analyzed:", report["files_analyzed"])
    print("Total headings:", report["total_headings"])
    print("Total issues:", report["total_issues"])

    print("\nDuplicate Headings:")

    for item in report["duplicate_headings"]:
        print(
            f"- {item['file']}: {item['heading']} "
            f"(lines {item['lines']})"
        )

    print("\nHeading Issues:")

    for item in report["heading_issues"]:
        print(
            f"- {item['file']}:{item['line']} "
            f"{item['issue']}"
        )

    print("\nLong Sections:")

    for item in report["long_sections"]:
        print(
            f"- {item['file']}: {item['section']} "
            f"({item['word_count']} words)"
        )

    print("\nEmpty Markdown Files:")

    for path in report["empty_files"]:
        print("-", path)


def export_report(report, filename="markdown_report.json"):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    print("\nReport exported to", filename)


if __name__ == "__main__":
    sample_files = [
        {
            "path": "README.md",
            "content": """
# Project Overview

## Introduction
This is a sample project.

### Features
Some useful features.

## Installation
Install the dependencies.

## Installation
This duplicate heading is intentional for testing.

# Advanced Topics
""" 
        },
        {
            "path": "docs.md",
            "content": ""
        }
    ]

    result = analyze_markdown(sample_files)
    print_report(result)
    export_report(result)
