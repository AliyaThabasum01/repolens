
"""
RepoLens GitHub Actions Workflow Analyzer
------------------------------------------
Performs basic static checks on GitHub Actions YAML workflows.

Checks:
- Workflow trigger presence
- Jobs and steps
- Missing action versions
- Unpinned third-party actions
- Potentially risky pull_request_target usage
- Secrets referenced in workflow text
- Basic YAML structure indicators

Uses Python's standard library only.
Does not execute workflows or fully parse YAML.
"""

import json
import re
from datetime import datetime


def analyze_workflow(content, filename="workflow.yml"):
    """Analyze a GitHub Actions workflow as text."""

    if not isinstance(content, str):
        raise TypeError("Workflow content must be a string.")

    lines = content.splitlines()
    findings = []
    action_refs = []
    job_names = []
    triggers = set()

    def add_finding(severity, title, message, line=None):
        findings.append({
            "severity": severity,
            "title": title,
            "message": message,
            "line": line,
        })

    # Remove comments and blank lines for simple text checks.
    active_lines = []

    for line_number, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        active_lines.append((line_number, raw_line, stripped))

    # Check workflow triggers.
    for line_number, raw_line, stripped in active_lines:
        if re.match(r"^(on|['\"]on['\"])\s*:", stripped):
            trigger_text = stripped.split(":", 1)[1].strip()

            if trigger_text:
                triggers.update(
                    part.strip(" [],'\"")
                    for part in trigger_text.split(",")
                    if part.strip(" [],'\"")
                )

            # Capture common indented trigger names.
            continue

        if re.match(
            r"^\s{2,}(push|pull_request|pull_request_target|"
            r"workflow_dispatch|schedule|release|issues|"
            r"workflow_call|workflow_run)\s*:",
            raw_line,
        ):
            trigger_name = stripped.split(":", 1)[0].strip()
            triggers.add(trigger_name)

    if not re.search(r"(?m)^(?:on|['\"]on['\"])\s*:", content):
        add_finding(
            "High",
            "Missing workflow trigger",
            "Add an 'on:' section defining when this workflow should run."
        )

    # Check for jobs section.
    if not re.search(r"(?m)^jobs\s*:", content):
        add_finding(
            "High",
            "Missing jobs section",
            "A workflow normally needs a top-level 'jobs:' section."
        )

    # Approximate job-name detection using indentation.
    in_jobs = False

    for line_number, raw_line in enumerate(lines, start=1):
        if re.match(r"^jobs\s*:", raw_line):
            in_jobs = True
            continue

        if in_jobs:
            if raw_line and not raw_line[0].isspace():
                in_jobs = False
                continue

            match = re.match(r"^  ([A-Za-z0-9_-]+)\s*:\s*(?:#.*)?$", raw_line)

            if match:
                job_names.append({
                    "name": match.group(1),
                    "line": line_number,
                })

    if re.search(r"(?m)^jobs\s*:", content) and not job_names:
        add_finding(
            "Medium",
            "No jobs detected",
            "Check that at least one job is defined under 'jobs:'."
        )

    # Inspect steps and action references.
    for line_number, raw_line in enumerate(lines, start=1):
        step_match = re.search(
            r"(?<!\S)uses\s*:\s*['\"]?([^'\"#\s]+)",
            raw_line,
        )

        if not step_match:
            continue

        action = step_match.group(1).rstrip(",")
        action_refs.append({
            "action": action,
            "line": line_number,
        })

        # Local actions and Docker actions have different reference rules.
        if action.startswith("./") or action.startswith("docker://"):
            continue

        # A normal remote action usually has an @ref.
        if "@" not in action:
            add_finding(
                "High",
                "Action reference missing version",
                f"'{action}' does not specify an @version or @SHA reference.",
                line_number,
            )
            continue

        owner_repo, ref = action.rsplit("@", 1)

        # Flag tags such as @v1, @main, @master, or @latest.
        # A full 40-character commit SHA is preferable for immutable pinning.
        is_full_sha = bool(re.fullmatch(r"[0-9a-fA-F]{40}", ref))

        if not is_full_sha:
            add_finding(
                "Medium",
                "Action is not pinned to a full commit SHA",
                f"'{action}' uses a tag or branch reference. "
                "Consider pinning to a verified full commit SHA.",
                line_number,
            )

        if ref.lower() in {"main", "master", "latest"}:
            add_finding(
                "High",
                "Mutable action reference",
                f"'{action}' points to a commonly mutable reference. "
                "Use a verified, full commit SHA where practical.",
                line_number,
            )

    # Risky pull_request_target review.
    if re.search(
        r"(?m)^\s*pull_request_target\s*:",
        content,
    ):
        add_finding(
            "High",
            "Review pull_request_target permissions",
            "This trigger can access the base repository context. "
            "Never execute untrusted pull-request code with privileged "
            "secrets or write permissions.",
        )

    # Review write permissions.
    if re.search(
        r"(?m)^\s{2,}(?:contents|packages|pull-requests|issues|"
        r"deployments)\s*:\s*write\s*$",
        content,
    ):
        add_finding(
            "Medium",
            "Write permissions detected",
            "Review whether every write permission is necessary. "
            "Prefer least-privilege workflow permissions.",
        )

    # Look for secrets references; these are not necessarily leaks.
    secret_references = []

    for line_number, raw_line in enumerate(lines, start=1):
        if "${{ secrets." in raw_line:
            secret_references.append(line_number)

    if secret_references:
        add_finding(
            "Info",
            "Secrets are referenced",
            f"Found {len(secret_references)} line(s) referencing "
            "GitHub Actions secrets. References are normal in many "
            "workflows; ensure secrets are never printed or exposed.",
            secret_references[0],
        )

    # Check for a top-level name.
    if not re.search(r"(?m)^name\s*:", content):
        add_finding(
            "Info",
            "Workflow name is not explicit",
            "Consider adding a top-level 'name:' to improve readability."
        )

    # Sort findings by severity and line.
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

    return {
        "filename": filename,
        "analyzed_at": datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
        "total_lines": len(lines),
        "triggers_detected": sorted(triggers),
        "jobs_detected": job_names,
        "actions_detected": action_refs,
        "severity_summary": {
            severity: sum(
                1 for finding in findings
                if finding["severity"] == severity
            )
            for severity in ["High", "Medium", "Low", "Info"]
        },
        "total_findings": len(findings),
        "findings": findings,
        "limitations": [
            "Uses regular expressions rather than a complete YAML parser.",
            "Some valid workflow structures may not be detected.",
            "Findings are static warnings, not proof of a vulnerability.",
            "A full commit SHA should be verified as belonging to the intended action.",
        ],
    }


def print_report(report):
    """Print a readable workflow analysis report."""

    print("=" * 60)
    print("       REPOLENS GITHUB ACTIONS WORKFLOW ANALYZER")
    print("=" * 60)

    print(f"File: {report['filename']}")
    print(f"Total lines: {report['total_lines']}")
    print(f"Triggers: {', '.join(report['triggers_detected']) or 'None detected'}")
    print(f"Jobs detected: {len(report['jobs_detected'])}")
    print(f"Actions detected: {len(report['actions_detected'])}")
    print(f"Total findings: {report['total_findings']}")

    print("\nSeverity Summary")

    for severity, count in report["severity_summary"].items():
        print(f"  {severity}: {count}")

    print("\nFindings")

    if not report["findings"]:
        print("  No findings detected.")

    for finding in report["findings"]:
        location = (
            f"Line {finding['line']}"
            if finding["line"] is not None
            else "General"
        )

        print(
            f"  [{finding['severity']}] "
            f"{finding['title']} — {location}"
        )
        print(f"    {finding['message']}")


if __name__ == "__main__":
    sample_workflow = """
name: Python Tests

on:
  push:
  pull_request:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@main
      - name: Run tests
        run: python -m unittest
"""

    report = analyze_workflow(
        sample_workflow,
        filename=".github/workflows/tests.yml",
    )

    print_report(report)

    with open(
        "workflow_report.json",
        "w",
        encoding="utf-8",
    ) as output_file:
        json.dump(report, output_file, indent=2)

    print("\nJSON report saved to workflow_report.json")
