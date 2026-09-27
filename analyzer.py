from collections import Counter
from pathlib import Path


LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".cpp": "C++",
    ".c": "C",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".php": "PHP",
    ".html": "HTML",
    ".css": "CSS",
    ".sql": "SQL",
}


def analyze_files(files):
    file_paths = [
        file["path"]
        for file in files
        if file.get("type") == "blob"
    ]

    extensions = []

    for path in file_paths:
        extension = Path(path).suffix.lower()

        if extension:
            extensions.append(extension)

    extension_counts = Counter(extensions)

    languages = {}

    for extension, count in extension_counts.items():
        language = LANGUAGE_MAP.get(extension)

        if language:
            languages[language] = languages.get(language, 0) + count

    tech_stack = []

    filenames = {Path(path).name.lower() for path in file_paths}

    if "requirements.txt" in filenames:
        tech_stack.append("Python")

    if "package.json" in filenames:
        tech_stack.append("Node.js")

    if "dockerfile" in filenames:
        tech_stack.append("Docker")

    if "pom.xml" in filenames:
        tech_stack.append("Maven")

    if "vite.config.js" in filenames or "vite.config.ts" in filenames:
        tech_stack.append("Vite")

    if "streamlit" in filenames:
        tech_stack.append("Streamlit")

    return {
        "total_files": len(file_paths),
        "languages": languages,
        "extensions": dict(extension_counts),
        "tech_stack": tech_stack,
    }
