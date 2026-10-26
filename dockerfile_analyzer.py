
"""
RepoLens Dockerfile Analyzer
----------------------------
Checks Dockerfiles for common configuration issues
and provides practical improvement suggestions.

Uses Python's standard library only.
"""

import json
import re
from datetime import datetime


def analyze_dockerfile(content, filename="Dockerfile"):
    """Analyze Dockerfile text and return a structured report."""

    if not isinstance(content, str):
        raise TypeError("Dockerfile content must be a string.")

    lines = content.splitlines()
    instructions = []

    for line_number, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        # Remove inline comments for basic instruction parsing.
        instruction_match = re.match(
            r"^([A-Za-z]+)\s+(.*)$", stripped
        )

        if instruction_match:
            instruction = instruction_match.group(1).upper()
            argument = instruction_match.group(2).strip()

            instructions.append({
                "line": line_number,
                "instruction": instruction,
                "argument": argument,
            })

    instruction_names = [
        item["instruction"] for item in instructions
    ]

    findings = []

    def add_finding(severity, title, message, line=None):
        findings.append({
            "severity": severity,
            "title": title,
            "message": message,
            "line": line,
        })

    # 1. Check whether a base image is specified.
    from_items = [
        item for item in instructions
        if item["instruction"] == "FROM"
    ]

    if not from_items:
        add_finding(
            "High",
            "Missing FROM instruction",
            "Add a FROM instruction to define the base image."
        )

    # 2. Check for floating latest tags.
    for item in from_items:
        image = item["argument"].split()[0] if item["argument"] else ""

        if image.lower().endswith(":latest") or (
            ":" not in image and not image.startswith("--")
        ):
            add_finding(
                "Medium",
                "Unpinned base image",
                "Use a deliberate, tested image version instead "
                "of relying on the implicit or explicit latest tag.",
                item["line"],
            )

    # 3. Check whether a working directory is configured.
    if "WORKDIR" not in instruction_names:
        add_finding(
            "Low",
            "Missing WORKDIR",
            "Consider setting WORKDIR to make file locations clearer."
        )

    # 4. Check whether a non-root user is configured.
    user_items = [
        item for item in instructions
        if item["instruction"] == "USER"
    ]

    if not user_items:
        add_finding(
            "High",
            "No USER instruction",
            "Consider running the application as a dedicated "
            "non-root user where supported."
        )
    elif user_items[-1]["argument"].strip().lower() in {
        "root", "0", "0:0"
    }:
        add_finding(
            "High",
            "Final USER is root",
            "Consider switching to a dedicated non-root user "
            "before running the application.",
            user_items[-1]["line"],
        )

    # 5. Flag potentially broad COPY instructions.
    for item in instructions:
        if item["instruction"] == "COPY":
            argument = re.sub(
                r"^--\S+\s+", "", item["argument"]
            ).strip()

            if argument.startswith(". ") or argument == ".":
                add_finding(
                    "Medium",
                    "Broad COPY instruction",
                    "COPY . can include unnecessary files. "
                    "Use a suitable .dockerignore file and "
                    "copy only what the image needs.",
                    item["line"],
                )

    # 6. Flag ADD for manual review.
    for item in instructions:
        if item["instruction"] == "ADD":
            add_finding(
                "Low",
                "Review ADD instruction",
                "Use COPY for ordinary file copying. Keep ADD "
                "when its extra behavior is intentionally needed.",
                item["line"],
            )

    # 7. Check for a possible missing .dockerignore file.
    # This is a reminder because this function receives only
    # Dockerfile text, not the repository's complete file list.
    add_finding(
        "Info",
        "Check .dockerignore",
        "Verify that unnecessary files, local secrets, caches, "
        "and version-control data are excluded from the build context."
    )

    # 8. Check whether a HEALTHCHECK is defined.
    if "HEALTHCHECK" not in instruction_names:
        add_finding(
            "Info",
            "No HEALTHCHECK instruction",
            "For services that need container health monitoring, "
            "consider adding a suitable HEALTHCHECK."
        )

    # 9. Check whether package installation may leave cache files.
    for item in instructions:
        if item["instruction"] == "RUN":
            command = item["argument"].lower()

            if (
                "apt-get install" in command
                and "rm -rf /var/lib/apt/lists" not in command
            ):
                add_finding(
                    "Low",
                    "Review package cache cleanup",
                    "For apt-based images, consider cleaning package "
                    "lists in the same build layer to reduce image size.",
                    item["line"],
                )

    # 10. Check for a likely missing image tag on an exposed port.
    for item in instructions:
        if item["instruction"] == "EXPOSE":
            if not re.search(r"\d+", item["argument"]):
                add_finding(
                    "Low",
                    "Review EXPOSE instruction",
                    "Specify a valid port number if this container "
                    "needs to document a listening port.",
                    item["line"],
                )

    severity_order = {
        "High": 0,
        "Medium": 1,
        "Low": 2,
        "Info": 3,
    }

    findings.sort(
        key=lambda item: (
            severity_order.get(item["severity"], 4),
            item["line"] or 0,
            item["title"],
        )
    )

    severity_counts = {
        severity: sum(
            1 for finding in findings
            if finding["severity"] == severity
        )
        for severity in ["High", "Medium", "Low", "Info"]
    }

    return {
        "filename": filename,
        "analyzed_at": datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
        "instruction_count": len(instructions),
        "instructions_found": instruction_names,
        "severity_summary": severity_counts,
        "total_findings": len(findings),
        "findings": findings,
        "limitations": [
            "Static checks only; the image is not built or executed.",
            "Some findings require manual review and may not apply "
            "to every project.",
            "The .dockerignore file cannot be verified from Dockerfile "
            "text alone.",
        ],
    }


def print_report(report):
    """Print the analyzer results in a readable format."""

    print("=" * 60)
    print("          REPOLENS DOCKERFILE ANALYZER")
    print("=" * 60)
    print(f"File: {report['filename']}")
    print(f"Instructions found: {report['instruction_count']}")
    print(f"Total findings: {report['total_findings']}")

    print("\nSeverity Summary")
    for severity, count in report["severity_summary"].items():
        print(f"  {severity}: {count}")

    if not report["findings"]:
        print("\nNo findings detected.")
        return

    print("\nRecommendations")
    print("-" * 60)

    for finding in report["findings"]:
        location = (
            f" (line {finding['line']})"
            if finding["line"] is not None
            else ""
        )

        print(
            f"[{finding['severity']}] "
            f"{finding['title']}{location}"
        )
        print(f"  {finding['message']}")


if __name__ == "__main__":
    sample_dockerfile = """
FROM python:latest

WORKDIR /app

COPY . .

RUN apt-get update && apt-get install -y curl

EXPOSE 8000

CMD ["python", "app.py"]
"""

    report = analyze_dockerfile(
        sample_dockerfile,
        filename="Dockerfile",
    )

    print_report(report)

    with open(
        "dockerfile_report.json",
        "w",
        encoding="utf-8",
    ) as output_file:
        json.dump(report, output_file, indent=2)

    print("\nJSON report saved to dockerfile_report.json")
