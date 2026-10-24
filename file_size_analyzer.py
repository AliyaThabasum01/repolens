
"""
RepoLens - Repository File Size Analyzer
Finds large files and provides repository storage recommendations.
Uses Python's standard library only.
"""

from pathlib import PurePosixPath


DEFAULT_WARNING_KB = 500
DEFAULT_CRITICAL_KB = 5000

LARGE_ASSET_EXTENSIONS = {
    ".zip", ".rar", ".7z", ".tar", ".gz",
    ".mp4", ".mov", ".avi", ".mkv",
    ".psd", ".ai", ".blend",
    ".exe", ".dll", ".so", ".bin",
    ".iso", ".dmg",
}

SOURCE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx",
    ".java", ".c", ".cpp", ".cs", ".go",
    ".html", ".css", ".json", ".md",
    ".yml", ".yaml", ".toml", ".sql",
}


def format_size(size_bytes):
    """Convert bytes into a readable size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"

    if size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.2f} KB"

    if size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.2f} MB"

    return f"{size_bytes / (1024 ** 3):.2f} GB"


def analyze_file_sizes(
    files,
    warning_kb=DEFAULT_WARNING_KB,
    critical_kb=DEFAULT_CRITICAL_KB,
):
    """
    Analyze file metadata.

    Accepted input:
        [
            {"path": "app.py", "size": 12000},
            {"path": "assets/video.mp4", "size": 8000000},
        ]

    Size must be provided in bytes.
    """
    if warning_kb <= 0 or critical_kb <= 0:
        raise ValueError("File size thresholds must be positive.")

    if critical_kb < warning_kb:
        raise ValueError(
            "critical_kb must be greater than or equal to warning_kb."
        )

    if not isinstance(files, (list, tuple)):
        raise TypeError("files must be a list or tuple of file metadata.")

    analyzed_files = []
    invalid_files = []

    for item in files:
        if not isinstance(item, dict):
            invalid_files.append("Invalid file metadata entry.")
            continue

        path = item.get("path")
        size = item.get("size")

        if not isinstance(path, str) or not path.strip():
            invalid_files.append("A file entry has no valid path.")
            continue

        # bool is a subclass of int in Python, so reject it explicitly.
        if isinstance(size, bool) or not isinstance(size, (int, float)):
            invalid_files.append(f"{path}: missing or invalid file size.")
            continue

        if size < 0:
            invalid_files.append(f"{path}: file size cannot be negative.")
            continue

        if not float(size).is_integer():
            invalid_files.append(f"{path}: file size must be a whole number.")
            continue

        size = int(size)
        suffix = PurePosixPath(path).suffix.lower()

        if size >= critical_kb * 1024:
            status = "Critical"
        elif size >= warning_kb * 1024:
            status = "Warning"
        else:
            status = "Normal"

        analyzed_files.append({
            "path": path,
            "size_bytes": size,
            "readable_size": format_size(size),
            "extension": suffix or "No extension",
            "status": status,
            "is_large_asset": suffix in LARGE_ASSET_EXTENSIONS,
            "is_source_file": suffix in SOURCE_EXTENSIONS,
        })

    analyzed_files.sort(
        key=lambda item: item["size_bytes"],
        reverse=True,
    )

    total_bytes = sum(
        item["size_bytes"] for item in analyzed_files
    )

    large_files = [
        item for item in analyzed_files
        if item["status"] in {"Warning", "Critical"}
    ]

    critical_files = [
        item for item in analyzed_files
        if item["status"] == "Critical"
    ]

    large_assets = [
        item for item in analyzed_files
        if item["is_large_asset"]
    ]

    recommendations = []

    if critical_files:
        recommendations.append(
            "Review critical-size files. Consider Git LFS for large "
            "assets when appropriate."
        )

    if large_assets:
        recommendations.append(
            "Review large media, archive, and binary files. Store "
            "generated artifacts outside Git when suitable."
        )

    if large_files:
        recommendations.append(
            "Check whether large files are necessary for the source "
            "repository or could be hosted separately."
        )

    if not large_files:
        recommendations.append(
            "No files exceeded the configured size warning threshold."
        )

    recommendations.append(
        "This report uses the supplied file metadata; ensure the input "
        "includes all repository files you want to inspect."
    )

    return {
        "files_analyzed": len(analyzed_files),
        "invalid_entries": invalid_files,
        "total_size_bytes": total_bytes,
        "total_size": format_size(total_bytes),
        "warning_threshold": f"{warning_kb} KB",
        "critical_threshold": f"{critical_kb} KB",
        "large_file_count": len(large_files),
        "critical_file_count": len(critical_files),
        "large_asset_count": len(large_assets),
        "largest_files": analyzed_files[:10],
        "large_files": large_files,
        "large_assets": large_assets,
        "recommendations": recommendations,
    }


def print_report(report):
    """Print a readable repository file-size report."""
    print("\n" + "=" * 52)
    print("       REPOLENS FILE SIZE ANALYSIS")
    print("=" * 52)

    print(f"Files analyzed: {report['files_analyzed']}")
    print(f"Combined reported size: {report['total_size']}")
    print(f"Warning threshold: {report['warning_threshold']}")
    print(f"Critical threshold: {report['critical_threshold']}")
    print(f"Large files: {report['large_file_count']}")
    print(f"Critical files: {report['critical_file_count']}")
    print(f"Large assets: {report['large_asset_count']}")

    print("\nLARGEST FILES")

    if not report["largest_files"]:
        print("No valid file metadata supplied.")

    for item in report["largest_files"]:
        print(
            f"  [{item['status']}] {item['path']} "
            f"- {item['readable_size']}"
        )

    print("\nLARGE ASSETS")

    if not report["large_assets"]:
        print("No files with configured large-asset extensions found.")

    for item in report["large_assets"]:
        print(f"  - {item['path']} ({item['readable_size']})")

    print("\nRECOMMENDATIONS")

    for recommendation in report["recommendations"]:
        print(f"  - {recommendation}")

    if report["invalid_entries"]:
        print("\nINVALID ENTRIES")

        for entry in report["invalid_entries"]:
            print(f"  - {entry}")

    print("\nNote: Large files are not automatically bad.")
    print("This tool does not measure Git history or repository storage.")
    print("=" * 52)


if __name__ == "__main__":
    sample_files = [
        {"path": "app.py", "size": 12000},
        {"path": "README.md", "size": 8000},
        {"path": "assets/demo.mp4", "size": 8000000},
        {"path": "data/archive.zip", "size": 6500000},
        {"path": "requirements.txt", "size": 1200},
        {"path": "assets/logo.png", "size": 700000},
    ]

    result = analyze_file_sizes(sample_files)
    print_report(result)
