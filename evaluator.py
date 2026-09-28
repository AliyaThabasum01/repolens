def evaluate_repository(info, analysis, readme):

    strengths = []
    suggestions = []

    # README check
    if readme and len(readme.strip()) > 100:

        strengths.append(
            "The repository contains a detailed README."
        )

    else:

        suggestions.append(
            "Improve the README with project overview, "
            "installation steps, features and usage instructions."
        )

    # Description check
    if info.get("description"):

        strengths.append(
            "The repository has a project description."
        )

    else:

        suggestions.append(
            "Add a clear GitHub repository description."
        )

    # Project size
    if analysis["total_files"] >= 5:

        strengths.append(
            "The project contains a reasonably structured codebase."
        )

    else:

        suggestions.append(
            "Consider organizing the project into separate "
            "modules and components."
        )

    # Languages
    if analysis["languages"]:

        strengths.append(
            "Programming languages were successfully detected."
        )

    else:

        suggestions.append(
            "Add recognizable source files or improve the "
            "repository structure."
        )

    # Configuration
    if analysis["tools"]:

        strengths.append(
            "Project configuration or dependency files were detected."
        )

    else:

        suggestions.append(
            "Add dependency and configuration files to make "
            "the project easier to install and run."
        )

    return {
        "strengths": strengths,
        "suggestions": suggestions
    }
