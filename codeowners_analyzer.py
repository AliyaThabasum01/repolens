
import json
import re


CODEOWNERS_LOCATIONS = {
    "codeowners",
    ".github/codeowners",
    "docs/codeowners"
}


def analyze_codeowners(files):
    report = {
        "file_found": False,
        "file_path": None,
        "total_rules": 0,
        "valid_rules": [],
        "invalid_rules": [],
        "duplicate_patterns": [],
        "wildcard_rules": [],
        "recommendations": []
    }

    codeowners = None

    for file in files:
        path = file.get("path", "").replace("\\", "/").lower()

        if path in CODEOWNERS_LOCATIONS:
            codeowners = file
            break

    if codeowners is None:
        report["recommendations"].append(
            "Create a CODEOWNERS file in the repository."
        )
        return report

    report["file_found"] = True
    report["file_path"] = codeowners.get("path")

    content = codeowners.get("content", "")
    seen_patterns = set()

    for line_number, line in enumerate(content.splitlines(), 1):
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        parts = stripped.split()

        if len(parts) < 2:
            report["invalid_rules"].append({
                "line": line_number,
                "rule": stripped,
                "reason": "Missing owner"
            })
            continue

        pattern = parts[0]
        owners = parts[1:]

        invalid_owners = [
            owner for owner in owners
            if not (
                owner.startswith("@")
                or re.fullmatch(
                    r"[^@\s]+@[^@\s]+\.[^@\s]+",
                    owner
                )
            )
        ]

        if invalid_owners:
            report["invalid_rules"].append({
                "line": line_number,
                "rule": stripped,
                "reason": "Invalid owner format"
            })
            continue

        rule = {
            "line": line_number,
            "pattern": pattern,
            "owners": owners
        }

        report["total_rules"] += 1
        report["valid_rules"].append(rule)

        if pattern in seen_patterns:
            report["duplicate_patterns"].append({
                "line": line_number,
                "pattern": pattern
            })

        seen_patterns.add(pattern)

        if pattern == "*":
            report["wildcard_rules"].append(rule)

    if report["total_rules"] == 0:
        report["recommendations"].append(
            "Add at least one valid ownership rule."
        )

    if report["invalid_rules"]:
        report["recommendations"].append(
            "Fix invalid rules or rules with missing owners."
        )

    if report["duplicate_patterns"]:
        report["recommendations"].append(
            "Review repeated patterns and their rule order."
        )

    if not report["wildcard_rules"]:
        report["recommendations"].append(
            "Consider whether a default wildcard ownership rule is needed."
        )

    if not report["recommendations"]:
        report["recommendations"].append(
            "All basic CODEOWNERS checks passed."
        )

    return report


def print_report(report):
    print("\n===== CODEOWNERS ANALYZER =====")

    if not report["file_found"]:
        print("CODEOWNERS file: Not found")
    else:
        print("File:", report["file_path"])

    print("Valid rules:", report["total_rules"])

    print("\nValid Ownership Rules:")

    for rule in report["valid_rules"]:
        print(
            f"- Line {rule['line']}: "
            f"{rule['pattern']} -> {', '.join(rule['owners'])}"
        )

    print("\nInvalid Rules:")

    for rule in report["invalid_rules"]:
        print(
            f"- Line {rule['line']}: "
            f"{rule['reason']}"
        )

    print("\nDuplicate Patterns:")

    for item in report["duplicate_patterns"]:
        print(
            f"- Line {item['line']}: {item['pattern']}"
        )

    print("\nRecommendations:")

    for item in report["recommendations"]:
        print("-", item)


def export_report(report, filename="codeowners_report.json"):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    print("\nReport exported to", filename)


if __name__ == "__main__":
    sample_files = [
        {
            "path": ".github/CODEOWNERS",
            "content": """
# Default repository owner
* @project-admin

# Frontend ownership
/src/frontend/ @frontend-team

# Backend ownership
/src/backend/ @backend-team

# Documentation ownership
/docs/ @docs-team
"""
        }
    ]

    result = analyze_codeowners(sample_files)
    print_report(result)
    export_report(result)
