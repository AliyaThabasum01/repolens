def evaluate_repository(info, analysis, readme):

    strengths = []
    weaknesses = []
    suggestions = []

    # README
    if readme and len(readme.strip()) >= 200:
        strengths.append(
            "The repository contains a reasonably detailed README."
        )
    else:
        weaknesses.append(
            "The project documentation is limited."
        )
        suggestions.append(
            "Improve the README with features, setup steps, "
            "usage instructions, screenshots and architecture."
        )

    # Description
    if info.get("description"):
        strengths.append(
            "The project has a clear repository description."
        )
    else:
        weaknesses.append(
            "No repository description was provided."
        )
        suggestions.append(
            "Add a concise description explaining the project's purpose."
        )

    # Project structure
    if analysis["total_files"] >= 10:
        strengths.append(
            "The repository contains a reasonably developed codebase."
        )
    else:
        weaknesses.append(
            "The repository currently has a small codebase."
        )

    # Technologies
    if analysis["languages"]:
        strengths.append(
            "The project's primary technologies were successfully detected."
        )
    else:
        weaknesses.append(
            "No supported programming language was detected."
        )

    # Configuration
    if analysis["tools"]:
        strengths.append(
            "Project configuration or dependency files were detected."
        )
    else:
        suggestions.append(
            "Add dependency and configuration files "
            "to make the project easier to reproduce."
        )

    # Folder structure
    if analysis["directories"]:
        strengths.append(
            "The repository uses multiple directories "
            "to organize project files."
        )
    else:
        suggestions.append(
            "Consider separating source code, assets, "
            "configuration and documentation."
        )

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "suggestions": suggestions
    }
