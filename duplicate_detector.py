
"""
RepoLens - Duplicate Code Detector
Detects repeated blocks of code across source files.
"""

import hashlib
from collections import defaultdict
from pathlib import PurePosixPath


SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx",
    ".java", ".c", ".cpp", ".cs", ".go",
    ".php", ".rb", ".swift", ".kt",
}

DEFAULT_BLOCK_SIZE = 5


def normalize_code_line(line):
    """Normalize whitespace for comparison."""
    return " ".join(line.strip().split())


def get_file_path(item):
    """Support either a path string or a GitHub file dictionary."""
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return item.get("path", "")
    return ""


def is_supported_file(path):
    """Return True for supported source-code extensions."""
    return PurePosixPath(path).suffix.lower() in SUPPORTED_EXTENSIONS


def detect_duplicates(file_contents, block_size=DEFAULT_BLOCK_SIZE):
    """
    Find repeated consecutive code blocks across files.

    Args:
        file_contents: Dictionary mapping file paths to source text.
        block_size: Minimum number of normalized lines per block.

    Returns:
        A report containing duplicate blocks and summary statistics.
    """
    if block_size < 2:
        raise ValueError("block_size must be at least 2.")

    if not isinstance(file_contents, dict):
        raise TypeError("file_contents must be a dictionary.")

    occurrences = defaultdict(list)
    total_lines = 0
    scanned_files = 0

    for path, content in file_contents.items():
        if not isinstance(path, str) or not is_supported_file(path):
            continue

        if not isinstance(content, str):
            continue

        scanned_files += 1
        lines = content.splitlines()
        total_lines += len(lines)

        normalized = [
            normalize_code_line(line)
            for line in lines
        ]

        for index in range(len(normalized) - block_size + 1):
            block = normalized[index:index + block_size]

            # Ignore blocks containing only blank lines.
            if not any(block):
                continue

            block_text = "\n".join(block)
            fingerprint = hashlib.sha256(
                block_text.encode("utf-8")
            ).hexdigest()

            occurrences[fingerprint].append({
                "file": path,
                "start_line": index + 1,
                "end_line": index + block_size,
                "code": block_text,
            })

    duplicates = []

    for fingerprint, locations in occurrences.items():
        if len(locations) < 2:
            continue

        # Avoid counting overlapping matches within the same file
        # as separate duplicate locations.
        unique_locations = []
        seen = set()

        for location in locations:
            key = (
                location["file"],
                location["start_line"],
            )
            if key not in seen:
                seen.add(key)
                unique_locations.append(location)

        if len(unique_locations) < 2:
            continue

        duplicates.append({
            "fingerprint": fingerprint,
            "occurrences": unique_locations,
            "files_affected": sorted({
                item["file"] for item in unique_locations
            }),
            "occurrence_count": len(unique_locations),
        })

    duplicates.sort(
        key=lambda item: item["occurrence_count"],
        reverse=True,
    )

    duplicate_locations = sum(
        item["occurrence_count"] for item in duplicates
    )

    return {
        "scanned_files": scanned_files,
        "total_lines": total_lines,
        "block_size": block_size,
        "duplicate_blocks": len(duplicates),
        "duplicate_locations": duplicate_locations,
        "duplicates": duplicates,
    }


def print_report(report):
    """Display duplicate detection results."""
    print("\n" + "=" * 50)
    print("       REPOLENS DUPLICATE CODE REPORT")
    print("=" * 50)

    print(f"Files scanned: {report['scanned_files']}")
    print(f"Lines scanned: {report['total_lines']}")
    print(f"Minimum block size: {report['block_size']} lines")
    print(f"Duplicate blocks: {report['duplicate_blocks']}")
    print(f"Duplicate locations: {report['duplicate_locations']}")

    if not report["duplicates"]:
        print("\nNo repeated code blocks detected.")
    else:
        for number, duplicate in enumerate(
            report["duplicates"], start=1
        ):
            print(f"\nDuplicate block #{number}")
            print(f"Occurrences: {duplicate['occurrence_count']}")

            for location in duplicate["occurrences"]:
                print(
                    f"  - {location['file']}:"
                    f"{location['start_line']}-"
                    f"{location['end_line']}"
                )

            print("\n  Repeated code:")
            for line in duplicate["occurrences"][0]["code"].splitlines():
                print(f"    {line}")

    print("\nNote: Repeated code is a review suggestion,")
    print("not necessarily a software defect.")
    print("=" * 50)


if __name__ == "__main__":
    sample_files = {
        "main.py": """
def greet(name):
    message = "Hello"
    print(message, name)
    return True
""",
        "utils.py": """
def welcome(name):
    message = "Hello"
    print(message, name)
    return True
""",
        "unique.py": """
def calculate_total(price, quantity):
    return price * quantity
""",
    }

    report = detect_duplicates(sample_files, block_size=3)
    print_report(report)
