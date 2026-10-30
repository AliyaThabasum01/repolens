
"""
RepoLens Repository Language Analyzer
--------------------------------------
Analyzes programming languages based on repository file extensions.

Features:
- Detects common programming languages
- Counts files by language
- Calculates percentage distribution
- Identifies the dominant language
- Lists unsupported file extensions
- Exports results as JSON

Uses Python's standard library only.
"""

import json
from collections import Counter
from datetime import datetime
from pathlib import PurePosixPath


LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".c": "C",
    ".h": "C/C++ Header",
    ".cpp": "C++",
    ".hpp": "C++",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".dart": "Dart",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sql": "SQL",
    ".sh": "Shell",
    ".bat": "Batch",
    ".ps1": "PowerShell",
    ".r": "R",
    ".m": "MATLAB",
    ".scala": "Scala",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".lua": "Lua",
    ".pl": "Perl",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".jl": "Julia",
    ".ipynb": "Jupyter Notebook",
}


def detect_language(file_path):
    """Detect language from a file extension."""

    extension = PurePosixPath(file_path).suffix.lower()

    if not extension:
        return "Unknown"

    return LANGUAGE_MAP.get(extension, "Unknown")


def analyze_languages(files):
    """
    Analyze repository file metadata.

    Expected input:
    [
        {"path": "app.py", "size": 1200},
        {"path": "index.js", "size": 800}
    ]

    Only the path field is required.
    """

    language_counts = Counter()
    language_files = {}
    unknown_extensions = Counter()
    total_files = 0

    for item in files:
        if not isinstance(item, dict):
            continue

        path = item.get("path")

        if not isinstance(path, str) or not path.strip():
            continue

        # Ignore directories.
        if path.endswith("/"):
            continue

        total_files += 1

        language = detect_language(path)

        language_counts[language] += 1

        language_files.setdefault(language, []).append(path)

        if language == "Unknown":
            extension = PurePosixPath(path).suffix.lower()

            unknown_extensions[extension or "[no extension]"] += 1

    known_counts = {
        language: count
        for language, count in language_counts.items()
        if language != "Unknown"
    }

    known_total = sum(known_counts.values())

    distribution = []

    for language, count in sorted(
        known_counts.items(),
        key=lambda item: (-item[1], item[0]),
    ):
        percentage = (
            round((count / known_total) * 100, 2)
            if known_total else 0
        )

        distribution.append({
            "language": language,
            "file_count": count,
            "percentage": percentage,
            "files": language_files[language],
        })

    dominant_language = (
        distribution[0]["language"]
        if distribution else "Not detected"
    )

    return {
        "generated_at": datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
        "total_files": total_files,
        "known_language_files": known_total,
        "unknown_files": language_counts.get("Unknown", 0),
        "language_count": len(known_counts),
        "dominant_language": dominant_language,
        "language_distribution": distribution,
        "unknown_extensions": dict(
            unknown_extensions.most_common()
        ),
        "limitations": [
            "Language detection is based on file extensions only.",
            "Files without recognized extensions are classified as Unknown.",
            "Generated files and vendored code are not automatically excluded.",
            "File counts are not equivalent to lines of code.",
        ],
    }


def print_report(report):
    """Display language analysis in a readable format."""

    print("=" * 60)
    print("       REPOLENS REPOSITORY LANGUAGE ANALYZER")
    print("=" * 60)

    print(f"Total files: {report['total_files']}")
    print(f"Recognized files: {report['known_language_files']}")
    print(f"Unknown files: {report['unknown_files']}")
    print(f"Languages detected: {report['language_count']}")
    print(f"Dominant language: {report['dominant_language']}")

    print("\nLanguage Distribution")
    print("-" * 60)

    if not report["language_distribution"]:
        print("No recognized programming languages found.")

    for item in report["language_distribution"]:
        bar = "#" * int(item["percentage"] / 5)

        print(
            f"{item['language']:<18} "
            f"{item['file_count']:>4} files "
            f"{item['percentage']:>6.2f}% "
            f"{bar}"
        )

    print("\nUnknown Extensions")

    if report["unknown_extensions"]:
        for extension, count in report["unknown_extensions"].items():
            print(f"  {extension}: {count}")
    else:
        print("  None")


if __name__ == "__main__":

    sample_files = [
        {"path": "app.py"},
        {"path": "analyzer.py"},
        {"path": "utils.py"},
        {"path": "index.js"},
        {"path": "script.js"},
        {"path": "style.css"},
        {"path": "index.html"},
        {"path": "Main.java"},
        {"path": "server.ts"},
        {"path": "README.md"},
        {"path": "config.json"},
        {"path": "Dockerfile"},
        {"path": "main.cpp"},
    ]

    report = analyze_languages(sample_files)

    print_report(report)

    with open(
        "language_report.json",
        "w",
        encoding="utf-8",
    ) as output_file:
        json.dump(report, output_file, indent=2)

    print("\nJSON report saved to language_report.json")
