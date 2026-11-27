
import json
from pathlib import Path


SUPPORTED_ECOSYSTEMS = {
    "pip",
    "npm",
    "yarn",
    "pnpm",
    "bundler",
    "cargo",
    "composer",
    "gomod",
    "maven",
    "gradle",
    "docker",
    "github-actions",
    "nuget",
    "hex",
    "pub",
    "terraform"
}

VALID_INTERVALS = {
    "daily",
    "weekly",
    "monthly",
    "quarterly",
    "semiannually",
    "yearly"
}


def parse_simple_yaml(text):
    """
    Minimal parser for common Dependabot YAML structures.
    This is not a complete YAML parser.
    """
    config = {
        "version": None,
        "updates": []
    }

    current = None
    in_updates = False

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if line == "updates:":
            in_updates = True
            continue

        if line.startswith("version:"):
            value = line.split(":", 1)[1].strip()
            try:
                config["version"] = int(value)
            except ValueError:
                config["version"] = value.strip("'\"")
            continue

        if in_updates and line.startswith("- "):
            current = {}
            config["updates"].append(current)
            line = line[2:]

        if in_updates and current is not None and ":" in line:
            key, value = line.split(":", 1)
            value = value.strip().strip("'\"")
            current[key.strip()] = value

    return config


def analyze_dependabot(repo_path):
    root = Path(repo_path)

    config_path = (
        root / ".github" / "dependabot.yml"
    )

    if not config_path.exists():
        config_path = (
            root / ".github" / "dependabot.yaml"
        )

    findings = []

    if not config_path.exists():
        return [{
            "severity": "HIGH",
            "issue": "Dependabot configuration file is missing.",
            "recommendation": (
                "Create .github/dependabot.yml "
                "to configure dependency updates."
            )
        }]

    try:
        content = config_path.read_text(
            encoding="utf-8"
        )
    except (OSError, UnicodeError) as error:
        return [{
            "severity": "ERROR",
            "issue": f"Unable to read configuration: {error}",
            "recommendation": "Check file access and encoding."
        }]

    config = parse_simple_yaml(content)

    if config["version"] != 2:
        findings.append({
            "severity": "HIGH",
            "issue": "Dependabot version should be 2.",
            "recommendation": "Set version: 2."
        })

    updates = config["updates"]

    if not updates:
        findings.append({
            "severity": "HIGH",
            "issue": "No dependency update rules found.",
            "recommendation": "Add at least one update configuration."
        })

    seen = set()

    for index, update in enumerate(updates, start=1):

        ecosystem = update.get("package-ecosystem")
        directory = update.get("directory")
        interval = update.get("schedule-interval")

        if not ecosystem:
            findings.append({
                "severity": "HIGH",
                "issue": f"Update rule {index} is missing package-ecosystem.",
                "recommendation": "Specify a supported package ecosystem."
            })

        elif ecosystem not in SUPPORTED_ECOSYSTEMS:
            findings.append({
                "severity": "MEDIUM",
                "issue": (
                    f"Update rule {index} has an unrecognized "
                    f"ecosystem: {ecosystem}."
                ),
                "recommendation": "Check the ecosystem name."
            })

        if not directory:
            findings.append({
                "severity": "HIGH",
                "issue": f"Update rule {index} is missing directory.",
                "recommendation": "Specify the manifest directory, such as /."
            })

        if not interval:
            findings.append({
                "severity": "HIGH",
                "issue": f"Update rule {index} is missing schedule interval.",
                "recommendation": "Add a schedule interval."
            })

        elif interval not in VALID_INTERVALS:
            findings.append({
                "severity": "MEDIUM",
                "issue": (
                    f"Update rule {index} has an unrecognized "
                    f"schedule interval: {interval}."
                ),
                "recommendation": "Review the supported schedule intervals."
            })

        if ecosystem and directory:
            key = (ecosystem, directory)

            if key in seen:
                findings.append({
                    "severity": "MEDIUM",
                    "issue": (
                        f"Duplicate update rule for "
                        f"{ecosystem} in {directory}."
                    ),
                    "recommendation": "Review duplicate configurations."
                })

            seen.add(key)

    return findings


def generate_report(findings):
    return {
        "total_findings": len(findings),
        "high_risk": sum(
            item["severity"] == "HIGH"
            for item in findings
        ),
        "medium_risk": sum(
            item["severity"] == "MEDIUM"
            for item in findings
        ),
        "errors": sum(
            item["severity"] == "ERROR"
            for item in findings
        ),
        "findings": findings
    }


if __name__ == "__main__":
    folder = input(
        "Enter repository folder path: "
    ).strip()

    try:
        findings = analyze_dependabot(folder)
        report = generate_report(findings)

        print("\n===== DEPENDABOT ANALYSIS REPORT =====")
        print(json.dumps(report, indent=4))

        with open(
            "dependabot_analysis_report.json",
            "w",
            encoding="utf-8"
        ) as output:
            json.dump(report, output, indent=4)

        print("\nReport saved successfully!")

    except (OSError, ValueError) as error:
        print("Error:", error)
