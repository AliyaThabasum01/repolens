
import re
from pathlib import PurePosixPath


LICENSE_FILENAMES = {
    "LICENSE",
    "LICENSE.md",
    "LICENSE.txt",
    "LICENSE-MIT",
    "LICENCE",
    "LICENCE.md",
    "LICENCE.txt",
    "COPYING",
    "COPYING.md",
    "COPYING.txt",
    "UNLICENSE",
}


KNOWN_LICENSES = {
    "MIT": [
        r"MIT License",
        r"Permission is hereby granted, free of charge"
    ],
    "Apache-2.0": [
        r"Apache License",
        r"Version 2\.0"
    ],
    "GPL-3.0": [
        r"GNU GENERAL PUBLIC LICENSE",
        r"Version 3"
    ],
    "GPL-2.0": [
        r"GNU GENERAL PUBLIC LICENSE",
        r"Version 2"
    ],
    "BSD": [
        r"Redistribution and use in source and binary forms"
    ],
    "MPL-2.0": [
        r"Mozilla Public License",
        r"Version 2\.0"
    ],
    "Unlicense": [
        r"This is free and unencumbered software"
    ],
}


def identify_license(text):
    """Identify common license text using simple pattern matching."""
    if not text or not isinstance(text, str):
        return "Unknown"

    for license_name, patterns in KNOWN_LICENSES.items():
        if all(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in patterns
        ):
            return license_name

    return "Unknown"


def find_license_files(files):
    """Find likely license files in a repository file listing."""
    results = []

    for item in files:
        if isinstance(item, str):
            path = item
        elif isinstance(item, dict):
            path = item.get("path", item.get("name", ""))
        else:
            continue

        filename = PurePosixPath(path).name

        if (
            filename.upper() in {name.upper() for name in LICENSE_FILENAMES}
            or filename.upper().startswith("LICENSE-")
            or filename.upper().startswith("LICENCE-")
        ):
            results.append(path)

    return sorted(set(results))


def check_license_compliance(files, file_contents=None, readme=""):
    """
    Inspect license-related repository information.

    files:
        List of paths or dictionaries containing a path/name.

    file_contents:
        Optional dictionary mapping file paths to their text contents.

    readme:
        README text, if available.

    This is a preliminary documentation check, not legal advice.
    """
    file_contents = file_contents or {}
    license_files = find_license_files(files)

    detected = []

    for path in license_files:
        content = file_contents.get(path, "")

        detected.append({
            "file": path,
            "license": identify_license(content),
            "content_available": bool(content)
        })

    readme_text = readme or ""

    readme_mentions_license = bool(
        re.search(r"\blicen[cs]e\b", readme_text, re.IGNORECASE)
    )

    if not license_files:
        status = "License file not found"
        suggestions = [
            "Check whether the project is intended to have a license.",
            "If you want to publish reusable code, consider choosing an appropriate license.",
            "Review the license terms before distributing or reusing code."
        ]
    elif any(item["license"] != "Unknown" for item in detected):
        status = "Recognized license text found"
        suggestions = [
            "Verify that the license matches the project's intended terms.",
            "Check that third-party dependencies comply with their own licenses."
        ]
    else:
        status = "License file found; manual review needed"
        suggestions = [
            "Review the license text to identify its exact license and terms.",
            "Ensure the complete license text is present."
        ]

    if license_files and not readme_mentions_license:
        suggestions.append(
            "Consider adding a license section or linking the license file in the README."
        )

    return {
        "status": status,
        "license_files": license_files,
        "detected_licenses": detected,
        "readme_mentions_license": readme_mentions_license,
        "suggestions": suggestions
    }


if __name__ == "__main__":
    sample_files = [
        "README.md",
        "LICENSE",
        "app.py"
    ]

    sample_contents = {
        "LICENSE": (
            "MIT License\n\n"
            "Permission is hereby granted, free of charge"
        )
    }

    result = check_license_compliance(
        files=sample_files,
        file_contents=sample_contents,
        readme="# Sample Project\n\nSee the license."
    )

    print("License Compliance Report")
    print("=" * 30)
    print("Status:", result["status"])
    print("License files:", result["license_files"])
    print("Detected licenses:", result["detected_licenses"])
    print("README mentions license:", result["readme_mentions_license"])

    print("\nSuggestions:")
    for suggestion in result["suggestions"]:
        print("-", suggestion)
