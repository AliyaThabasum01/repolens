
"""
RepoLens - Secret & API Key Scanner
Detects common patterns that may indicate exposed credentials.
Uses Python's standard library only.
"""

import re
from pathlib import PurePosixPath


SECRET_PATTERNS = [
    (
        "Generic API Key",
        re.compile(
            r"""(?i)\bapi[_-]?key\b\s*[:=]\s*["']([^"'\s]{8,})["']"""
        ),
    ),
    (
        "Generic Access Token",
        re.compile(
            r"""(?i)\baccess[_-]?token\b\s*[:=]\s*["']([^"'\s]{8,})["']"""
        ),
    ),
    (
        "Generic Secret",
        re.compile(
            r"""(?i)\b(?:client[_-]?secret|app[_-]?secret)\b"""
            r"""\s*[:=]\s*["']([^"'\s]{8,})["']"""
        ),
    ),
    (
        "Password Assignment",
        re.compile(
            r"""(?i)\b(?:password|passwd|pwd)\b"""
            r"""\s*[:=]\s*["']([^"'\s]{4,})["']"""
        ),
    ),
    (
        "GitHub Token",
        re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    ),
    (
        "GitHub Fine-Grained Token",
        re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    ),
    (
        "OpenAI-Style API Key",
        re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    ),
    (
        "AWS Access Key ID",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    ),
    (
        "Google API Key",
        re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    ),
    (
        "Private Key Header",
        re.compile(
            r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"
        ),
    ),
]

IGNORED_DIRECTORIES = {
    ".git", ".venv", "venv", "node_modules",
    "__pycache__", "dist", "build",
}

IGNORED_FILENAMES = {
    "secret_scanner.py",
}

SENSITIVE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx",
    ".java", ".go", ".rb", ".php", ".cs",
    ".json", ".yaml", ".yml", ".toml",
    ".ini", ".cfg", ".conf", ".env",
    ".sh", ".bash", ".sql", ".xml",
    ".properties", ".txt", ".md",
}


def should_scan_file(path):
    """Decide whether a repository file is suitable for scanning."""
    file_path = PurePosixPath(path)

    if any(part in IGNORED_DIRECTORIES for part in file_path.parts):
        return False

    if file_path.name in IGNORED_FILENAMES:
        return False

    # Avoid treating the scanner's own regex patterns as findings.
    if file_path.name == "secret_scanner.py":
        return False

    return (
        file_path.suffix.lower() in SENSITIVE_EXTENSIONS
        or file_path.name.lower() in {
            ".env", ".env.local", ".env.production",
            "dockerfile",
        }
    )


def looks_like_placeholder(value):
    """Reduce obvious placeholder and example-value false positives."""
    normalized = value.strip().lower()

    placeholders = {
        "your_api_key",
        "your-api-key",
        "replace_me",
        "changeme",
        "change_me",
        "example",
        "placeholder",
        "your_secret",
        "your_token",
        "insert_key_here",
        "xxxxxxxx",
        "dummy",
        "test",
    }

    if normalized in placeholders:
        return True

    return any(
        marker in normalized
        for marker in (
            "your_api_key",
            "your_secret",
            "your_token",
            "replace_me",
            "insert_key",
            "placeholder",
            "example_key",
        )
    )


def redact(value):
    """Never print the full credential candidate."""
    if len(value) <= 8:
        return "*" * len(value)

    return value[:3] + "*" * min(len(value) - 3, 16)


def scan_text(path, content):
    """Scan a single file's text and return potential findings."""
    findings = []

    for line_number, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()

        # Skip obvious comment lines to reduce noisy findings.
        if stripped.startswith(("#", "//", "*")):
            continue

        for category, pattern in SECRET_PATTERNS:
            for match in pattern.finditer(line):
                # Some patterns capture only the credential value;
                # others match the entire token.
                candidate = (
                    match.group(1)
                    if match.lastindex
                    else match.group(0)
                )

                if looks_like_placeholder(candidate):
                    continue

                findings.append({
                    "file": path,
                    "line": line_number,
                    "type": category,
                    "redacted_value": redact(candidate),
                    "severity": "High",
                })

    return findings


def scan_repository(file_contents):
    """
    Scan a dictionary of {file_path: file_text}.

    File content should come from repository text files.
    Never log or print original credential values.
    """
    if not isinstance(file_contents, dict):
        raise TypeError("file_contents must be a dictionary.")

    findings = []
    scanned_files = 0
    skipped_files = 0

    for path, content in file_contents.items():
        if not isinstance(path, str) or not isinstance(content, str):
            skipped_files += 1
            continue

        if not should_scan_file(path):
            skipped_files += 1
            continue

        scanned_files += 1
        findings.extend(scan_text(path, content))

    severity_counts = {}

    for finding in findings:
        severity_counts[finding["severity"]] = (
            severity_counts.get(finding["severity"], 0) + 1
        )

    return {
        "files_scanned": scanned_files,
        "files_skipped": skipped_files,
        "potential_secrets": len(findings),
        "severity_counts": severity_counts,
        "findings": findings,
        "recommendations": [
            "Review each finding manually; pattern matches can be false positives.",
            "Store credentials in environment variables or a secret manager.",
            "Never commit real .env files or credentials to public repositories.",
            "If a credential was exposed, revoke or rotate it immediately.",
        ],
    }


def print_report(report):
    """Print findings without exposing full credential values."""
    print("\n" + "=" * 48)
    print("        REPOLENS SECRET SCAN REPORT")
    print("=" * 48)

    print(f"Files scanned: {report['files_scanned']}")
    print(f"Files skipped: {report['files_skipped']}")
    print(f"Potential secrets: {report['potential_secrets']}")

    if not report["findings"]:
        print("\nNo matching credential patterns detected.")
    else:
        print("\nPOTENTIAL FINDINGS")

        for finding in report["findings"]:
            print(
                f"\n[{finding['severity']}] {finding['type']}"
            )
            print(
                f"  Location: {finding['file']}:"
                f"{finding['line']}"
            )
            print(
                f"  Redacted value: "
                f"{finding['redacted_value']}"
            )

    print("\nRECOMMENDATIONS")

    for recommendation in report["recommendations"]:
        print(f"  - {recommendation}")

    print("\nNote: This scanner cannot detect every secret.")
    print("=" * 48)


if __name__ == "__main__":
    # Safe demonstration using fake placeholder credentials.
    sample_files = {
        "app.py": '''
API_KEY = "your_api_key"
password = "example_password"
message = "Welcome to RepoLens"
''',
        "config.json": '''
{
    "api_key": "REPLACE_WITH_YOUR_API_KEY"
}
''',
        "README.md": '''
# My Project
This project demonstrates secret scanning.
''',
    }

    result = scan_repository(sample_files)
    print_report(result)
