from collections import Counter
import os


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
    ".sql": "SQL",
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
    "next.config.mjs": "Next.js",
}


def analyze_files(files):

    file_paths = [
        file["path"]
        for file in files
        if file.get("type") == "blob"
    ]

    extensions = []

    for path in file_paths:

        _, extension = os.path.splitext(path)

        if extension:
            extensions.append(extension.lower())

    extension_counts = Counter(extensions)

    languages = []

    for extension, count in extension_counts.items():

        if extension in LANGUAGE_MAP:

            languages.append({
                "language": LANGUAGE_MAP[extension],
                "files": count
            })

    languages.sort(
        key=lambda item: item["files"],
        reverse=True
    )

    detected_tools = []

    filenames = [
        os.path.basename(path).lower()
        for path in file_paths
    ]

    for filename, tool in CONFIG_FILES.items():

        if filename.lower() in filenames:
            detected_tools.append(tool)

    directories = set()

    for path in file_paths:

        parts = path.split("/")

        if len(parts) > 1:
            directories.add(parts[0])

    return {
        "total_files": len(file_paths),
        "extensions": dict(extension_counts),
        "languages": languages,
        "tools": detected_tools,
        "directories": sorted(directories)
    }


def get_project_summary(analysis):

    total_files = analysis["total_files"]
    languages = analysis["languages"]

    if not languages:

        return (
            f"The repository contains {total_files} files, "
            "but no supported programming languages were detected."
        )

    main_languages = [
        item["language"]
        for item in languages[:3]
    ]

    return (
        f"The repository contains {total_files} files. "
        f"The main technologies detected are "
        f"{', '.join(main_languages)}."
    )
