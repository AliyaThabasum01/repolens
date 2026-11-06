
import json
import re


SECURITY_SECTIONS = {
    "reporting vulnerabilities": [
        "reporting a vulnerability",
        "reporting vulnerabilities",
        "report a vulnerability",
        "reporting security issues"
    ],
    "supported versions": [
        "supported versions",
        "version support"
    ],
    "response process": [
        "response process",
        "response timeline",
        "what to expect",
        "security response"
    ],
    "contact information": [
        "contact",
        "security contact",
        "email"
    ]
}


def analyze_security_policy(files):
    report = {
        "policy_found": False,
        "policy_path": None,
        "word_count": 0,
        "sections_found": [],
        "sections_missing": [],
        "email_addresses_found": 0,
        "recommendations": []
    }

    policy = None

    for file in files:
        path = file.get("path", "").replace("\\", "/")

        if path.lower() == "security.md":
            policy = file
            break

    if policy is None:
        report["sections_missing"] = list(SECURITY_SECTIONS)
        report["recommendations"].append(
            "Create a SECURITY.md file."
        )
        return report

    report["policy_found"] = True
    report["policy_path"] = policy.get("path")

    content = policy.get("content", "")
    content_lower = content.lower()

    report["word_count"] = len(content.split())

    report["email_addresses_found"] = len(
        re.findall(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
            content
        )
    )

    for section, keywords in SECURITY_SECTIONS.items():
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

    if report["word_count"] < 80:
        report["recommendations"].append(
            "Add more detailed security policy instructions."
        )

    for section in report["sections_missing"]:
        report["recommendations"].append(
            f"Consider adding a {section} section."
        )

    if report["email_addresses_found"] == 0:
        report["recommendations"].append(
            "Provide a secure way to contact the maintainers."
        )

    if not report["recommendations"]:
        report["recommendations"].append(
            "All checked policy sections are present."
        )

    return report


def print_report(report):
    print("\n===== SECURITY POLICY REPORT =====")

    if report["policy_found"]:
        print("Policy found:", report["policy_path"])
    else:
        print("SECURITY.md: Not found")

    print("Word count:", report["word_count"])
    print("Email addresses found:", report["email_addresses_found"])

    print("\nSections Found:")
    for section in report["sections_found"]:
        print("-", section)

    print("\nSections Missing:")
    for section in report["sections_missing"]:
        print("-", section)

    print("\nRecommendations:")
    for recommendation in report["recommendations"]:
        print("-", recommendation)


def export_report(report, filename="security_policy_report.json"):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    print("\nReport exported to", filename)


if __name__ == "__main__":
    sample_files = [
        {
            "path": "SECURITY.md",
            "content": """
# Security Policy

## Supported Versions
We support the latest version.

## Reporting a Vulnerability
Email security@example.com to report an issue.

## Response Process
Our team will review the report.

## Contact Information
Contact security@example.com for help.
"""
        }
    ]

    result = analyze_security_policy(sample_files)
    print_report(result)
    export_report(result)
