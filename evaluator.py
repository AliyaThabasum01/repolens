def evaluate_repository(info, analysis, readme):

    strengths = []
    weaknesses = []
    suggestions = []

    scores = {
        "Documentation": 0,
        "Project Structure": 0,
        "Technology": 0,
        "Configuration": 0,
        "Repository Information": 0
    }

    # -------------------------
    # Documentation
    # -------------------------

    if readme and len(readme.strip()) >= 500:

        scores["Documentation"] = 20

        strengths.append(
            "The repository contains detailed documentation."
        )

    elif readme and len(readme.strip()) >= 200:

        scores["Documentation"] = 15

        strengths.append(
            "The repository contains a basic project README."
        )

        suggestions.append(
            "Expand the README with screenshots, architecture, "
            "usage examples and detailed setup instructions."
        )

    elif readme:

        scores["Documentation"] = 8

        weaknesses.append(
            "The README contains limited documentation."
        )

        suggestions.append(
            "Expand the README with setup instructions, "
            "features and usage examples."
        )

    else:

        scores["Documentation"] = 0

        weaknesses.append(
            "The repository does not contain a readable README."
        )

        suggestions.append(
            "Create a detailed README explaining the project."
        )


    # -------------------------
    # Project Structure
    # -------------------------

    if analysis["total_files"] >= 15:

        scores["Project Structure"] = 20

        strengths.append(
            "The repository contains a well-developed codebase."
        )

    elif analysis["total_files"] >= 5:

        scores["Project Structure"] = 15

        strengths.append(
            "The repository contains a reasonably structured codebase."
        )

    elif analysis["total_files"] > 0:

        scores["Project Structure"] = 8

        weaknesses.append(
            "The project currently has a small codebase."
        )

        suggestions.append(
            "Consider organizing the project into reusable modules."
        )


    # -------------------------
    # Technology
    # -------------------------

    if len(analysis["languages"]) >= 3:

        scores["Technology"] = 20

        strengths.append(
            "Multiple technologies were detected in the project."
        )

    elif len(analysis["languages"]) >= 1:

        scores["Technology"] = 15

        strengths.append(
            "The project's primary technology was detected."
        )

    else:

        scores["Technology"] = 5

        weaknesses.append(
            "No supported programming language was detected."
        )


    # -------------------------
    # Configuration
    # -------------------------

    if len(analysis["tools"]) >= 2:

        scores["Configuration"] = 20

        strengths.append(
            "The project contains multiple configuration "
            "or dependency files."
        )

    elif len(analysis["tools"]) == 1:

        scores["Configuration"] = 15

        strengths.append(
            "A project configuration or dependency file was detected."
        )

    else:

        scores["Configuration"] = 5

        suggestions.append(
            "Add dependency and configuration files "
            "to make the project easier to reproduce."
        )


    # -------------------------
    # Repository Information
    # -------------------------

    if info.get("description"):

        scores["Repository Information"] = 20

        strengths.append(
            "The repository has a clear project description."
        )

    else:

        scores["Repository Information"] = 5

        weaknesses.append(
            "The repository does not have a project description."
        )

        suggestions.append(
            "Add a concise description explaining the project's purpose."
        )


    # -------------------------
    # Overall Score
    # -------------------------

    total_score = sum(scores.values())


    if total_score >= 85:

        status = "Strong Project Foundation"

    elif total_score >= 70:

        status = "Good Project Foundation"

    elif total_score >= 50:

        status = "Needs Improvement"

    else:

        status = "Early Stage Project"


    return {
        "score": total_score,
        "status": status,
        "scores": scores,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "suggestions": suggestions
    }
