
from collections import Counter
import os
import requests


LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".java": "Java",
    ".cpp": "C++",
    ".c": "C",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".php": "PHP",
    ".html": "HTML",
    ".css": "CSS",
    ".jsx": "React",
    ".tsx": "React / TypeScript",
    ".sql": "SQL"
}

CONFIG_FILES = {
    "requirements.txt": "Python Dependencies",
    "package.json": "Node.js",
    "pom.xml": "Maven",
    "build.gradle": "Gradle",
    "dockerfile": "Docker",
    "docker-compose.yml": "Docker Compose",
    "docker-compose.yaml": "Docker Compose",
    "vercel.json": "Vercel",
    "vite.config.js": "Vite",
    "vite.config.ts": "Vite",
    "next.config.js": "Next.js",
    "next.config.mjs": "Next.js"
}

SOURCE_EXTENSIONS = set(LANGUAGE_MAP.keys())


def analyze_files(files):
    paths = [
        item["path"]
        for item in files
        if item.get("type") == "blob"
    ]

    extensions = []

    for path in paths:
        _, extension = os.path.splitext(path)

        if extension:
            extensions.append(extension.lower())

    counts = Counter(extensions)

    languages = [
        {
            "language": LANGUAGE_MAP[extension],
            "files": count
        }
        for extension, count in counts.items()
        if extension in LANGUAGE_MAP
    ]

    languages.sort(
        key=lambda item: item["files"],
        reverse=True
    )

    filenames = [
        os.path.basename(path).lower()
        for path in paths
    ]

    tools = [
        tool
        for filename, tool in CONFIG_FILES.items()
        if filename.lower() in filenames
    ]

    directories = sorted({
        path.split("/")[0]
        for path in paths
        if "/" in path
    })

    return {
        "total_files": len(paths),
        "extensions": dict(counts),
        "languages": languages,
        "tools": tools,
        "directories": directories
    }


def get_project_summary(analysis):
    total = analysis["total_files"]
    languages = analysis["languages"]

    if not languages:
        return f"The repository contains {total} files."

    top_languages = [
        item["language"]
        for item in languages[:3]
    ]

    return (
        f"The repository contains {total} files, "
        f"with {', '.join(top_languages)} "
        f"as the primary detected technologies."
    )


def analyze_code_quality(files, owner, repo, branch):
    source_files = [
        item for item in files
        if item.get("type") == "blob"
        and os.path.splitext(item["path"])[1].lower()
        in SOURCE_EXTENSIONS
        and item.get("size", 0) <= 200_000
    ]

    # Limit network requests for large repositories.
    source_files = source_files[:30]

    findings = []
    scanned_files = 0
    total_lines = 0
    empty_files = 0
    long_lines = 0
    large_files = 0

    for file in source_files:
        path = file["path"]

        url = (
            f"https://raw.githubusercontent.com/"
            f"{owner}/{repo}/{branch}/{path}"
        )

        try:
            response = requests.get(url, timeout=10)

            if response.status_code != 200:
                continue

            content = response.text
            lines = content.splitlines()

            scanned_files += 1
            total_lines += len(lines)

            if not content.strip():
                empty_files += 1
                findings.append({
                    "file": path,
                    "issue": "Empty source file",
                    "severity": "Low"
                })
                continue

            if len(lines) > 300:
                large_files += 1
                findings.append({
                    "file": path,
                    "issue": f"Large source file ({len(lines)} lines)",
                    "severity": "Medium"
                })

            long_line_count = sum(
                1 for line in lines if len(line) > 120
            )

            if long_line_count:
                long_lines += long_line_count
                findings.append({
                    "file": path,
                    "issue": (
                        f"{long_line_count} lines exceed "
                        "120 characters"
                    ),
                    "severity": "Low"
                })

        except requests.RequestException:
            continue

    return {
        "scanned_files": scanned_files,
        "total_lines": total_lines,
        "empty_files": empty_files,
        "long_lines": long_lines,
        "large_files": large_files,
        "findings": findings,
        "scan_limit": 30
    }
