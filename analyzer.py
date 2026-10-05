import re
import requests

BASE_URL = "https://api.github.com"

SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java",
    ".cpp", ".c", ".cs", ".php", ".go", ".rb",
    ".html", ".css", ".json", ".yml", ".yaml"
}

SECRET_PATTERNS = [
    ("Possible API key", re.compile(
        r"""(?i)(api[_-]?key|access[_-]?token)\s*[:=]\s*["'][^"']{8,}["']"""
    )),
    ("Possible password", re.compile(
        r"""(?i)(password|passwd|secret)\s*[:=]\s*["'][^"']{4,}["']"""
    )),
    ("Possible private key", re.compile(
        r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"
    )),
    ("Possible GitHub token", re.compile(
        r"gh[pousr]_[A-Za-z0-9_]{20,}"
    )),
]

def analyze_files(files):
    extensions = {}
    folders = set()
    config_files = []

    for file in files:
        path = file.get("path", "")
        if "/" in path:
            folders.add(path.split("/")[0])

        if "." in path.split("/")[-1]:
            extension = "." + path.split(".")[-1].lower()
            extensions[extension] = extensions.get(extension, 0) + 1

        filename = path.split("/")[-1].lower()
        if filename in {
            "requirements.txt", "package.json", "pom.xml",
            "dockerfile", "pyproject.toml", "cargo.toml",
            "go.mod", "composer.json"
        }:
            config_files.append(path)

    return {
        "extensions": extensions,
        "folders": sorted(folders),
        "config_files": config_files,
        "total_files": len(files)
    }


def get_project_summary(files):
    analysis = analyze_files(files)

    languages = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".jsx": "React",
        ".tsx": "React + TypeScript",
        ".java": "Java",
        ".cpp": "C++",
        ".c": "C",
        ".cs": "C#",
        ".php": "PHP",
        ".go": "Go",
        ".rb": "Ruby",
        ".html": "HTML",
        ".css": "CSS"
    }

    detected = {}
    for extension, count in analysis["extensions"].items():
        if extension in languages:
            name = languages[extension]
            detected[name] = detected.get(name, 0) + count

    return {
        "languages": detected,
        "folders": analysis["folders"],
        "config_files": analysis["config_files"],
        "total_files": analysis["total_files"]
    }


def analyze_code_quality(files, owner, repo, branch):
    findings = []
    checked = 0

    source_files = [
        item for item in files
        if item.get("type") == "blob"
        and any(item.get("path", "").lower().endswith(ext)
                for ext in SOURCE_EXTENSIONS)
        and item.get("size", 0) <= 200_000
    ][:30]

    for item in source_files:
        path = item.get("path", "")
        url = (
            f"https://raw.githubusercontent.com/"
            f"{owner}/{repo}/{branch}/{path}"
        )

        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                continue

            content = response.text
            checked += 1
            lines = content.splitlines()

            if len(lines) > 300:
                findings.append({
                    "severity": "Low",
                    "file": path,
                    "issue": f"Large source file ({len(lines)} lines)"
                })

            if not content.strip():
                findings.append({
                    "severity": "Low",
                    "file": path,
                    "issue": "Empty source file"
                })

            for line_number, line in enumerate(lines, start=1):
                if len(line) > 120:
                    findings.append({
                        "severity": "Low",
                        "file": path,
                        "issue": f"Long line at line {line_number}"
                    })

        except requests.RequestException:
            continue

    return {
        "checked_files": checked,
        "findings": findings
    }


def scan_security(files, owner, repo, branch):
    findings = []
    checked = 0

    paths = [item.get("path", "") for item in files]
    lowered_paths = [path.lower() for path in paths]

    if ".gitignore" not in lowered_paths:
        findings.append({
            "severity": "Medium",
            "file": "Repository",
            "issue": "Missing .gitignore file"
        })

    sensitive_names = (
        ".env", ".env.local", ".env.production",
        "id_rsa", "id_ed25519", "private.key",
        "credentials.json"
    )

    for path in paths:
        filename = path.split("/")[-1].lower()

        if filename in sensitive_names or filename.startswith(".env."):
            findings.append({
                "severity": "High",
                "file": path,
                "issue": "Potentially sensitive file is present"
            })

    source_files = [
        item for item in files
        if item.get("type") == "blob"
        and item.get("size", 0) <= 200_000
        and any(item.get("path", "").lower().endswith(ext)
                for ext in SOURCE_EXTENSIONS)
    ][:30]

    for item in source_files:
        path = item.get("path", "")
        url = (
            f"https://raw.githubusercontent.com/"
            f"{owner}/{repo}/{branch}/{path}"
        )

        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                continue

            checked += 1
            content = response.text

            for line_number, line in enumerate(
                content.splitlines(), start=1
            ):
                for label, pattern in SECRET_PATTERNS:
                    if pattern.search(line):
                        findings.append({
                            "severity": "High",
                            "file": path,
                            "issue": f"{label} detected at line {line_number}"
                        })
                        break

        except requests.RequestException:
            continue

    return {
        "checked_files": checked,
        "findings": findings
    }
