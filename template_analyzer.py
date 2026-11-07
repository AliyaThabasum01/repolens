
import json
import re


TEMPLATE_KEYWORDS = {
    "bug_report": [
        "bug_report.md",
        "bug report",
        "bug_report"
    ],
    "feature_request": [
        "feature_request.md",
        "feature request",
        "feature_request"
    ],
    "pull_request": [
        "pull_request_template.md",
        "pull request template",
        "pull_request_template"
    ]
}


def analyze_templates(files):
    report = {
        "templates_found": [],
        "templates_missing": [],
        "template_details": [],
        "total_templates": 0,
        "recommendations": []
    }

    available_templates = {
        key: False for key in TEMPLATE_KEYWORDS
    }

    for file in files:
        path = file.get("path", "").replace("\\", "/")
        content = file.get("content", "")

        path_lower = path.lower()
        filename = path_lower.split("/")[-1]

        for template_type, keywords in TEMPLATE_KEYWORDS.items():

            matched = any(
                keyword in filename
                or keyword in path_lower
                for keyword in keywords
            )

            if matched and not available_templates[template_type]:
                available_templates[template_type] = True

                headings = re.findall(
                    r"^\s{0,3}#{1,6}\s+(.+)$",
                    content,
                    re.MULTILINE
                )

                checkboxes = len(
                    re.findall(r"\[\s*[xX ]?\s*\]", content)
                )

                details = {
                    "type": template_type,
                    "path": path,
                    "word_count": len(content.split()),
                    "headings": headings,
                    "checkboxes": checkboxes,
                    "empty": not content.strip()
                }

                report["template_details"].append(details)

    for template_type, found in available_templates.items():
        if found:
            report["templates_found"].append(template_type)
        else:
            report["templates_missing"].append(template_type)

    report["total_templates"] = len(report["templates_found"])

    for missing in report["templates_missing"]:
        report["recommendations"].append(
            f"Consider adding a {missing.replace('_', ' ')} template."
        )

    for template in report["template_details"]:
        if template["empty"]:
            report["recommendations"].append(
                f"{template['path']} is empty."
            )

        elif template["word_count"] < 10:
            report["recommendations"].append(
                f"{template['path']} may need more instructions."
            )

        if not template["headings"]:
            report["recommendations"].append(
                f"Add headings to {template['path']}."
            )

    if not report["recommendations"]:
        report["recommendations"].append(
            "All checked templates are present and have basic content."
        )

    return report


def print_report(report):
    print("\n===== GITHUB TEMPLATE ANALYZER =====")

    print("Templates found:", report["total_templates"])

    print("\nAvailable Templates:")

    for template in report["templates_found"]:
        print("-", template.replace("_", " ").title())

    print("\nMissing Templates:")

    for template in report["templates_missing"]:
        print("-", template.replace("_", " ").title())

    print("\nTemplate Details:")

    for template in report["template_details"]:
        print("\nFile:", template["path"])
        print("Words:", template["word_count"])
        print("Headings:", len(template["headings"]))
        print("Checkboxes:", template["checkboxes"])

    print("\nRecommendations:")

    for recommendation in report["recommendations"]:
        print("-", recommendation)


def export_report(report, filename="template_report.json"):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    print("\nReport exported to", filename)


if __name__ == "__main__":
    sample_files = [
        {
            "path": ".github/ISSUE_TEMPLATE/bug_report.md",
            "content": """
# Bug Report

## Description
Describe the problem.

## Steps to Reproduce
- Step 1
- Step 2

## Expected Behaviour
Explain what should happen.
"""
        },
        {
            "path": ".github/ISSUE_TEMPLATE/feature_request.md",
            "content": """
# Feature Request

## Problem
Describe the problem.

## Proposed Solution
Describe your idea.
"""
        },
        {
            "path": ".github/PULL_REQUEST_TEMPLATE.md",
            "content": """
# Pull Request

## Changes
Describe your changes.

## Checklist
- [ ] Tested changes
- [ ] Updated documentation
"""
        }
    ]

    result = analyze_templates(sample_files)
    print_report(result)
    export_report(result)
