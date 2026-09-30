import streamlit as st

from github_reader import (
    get_repo_info,
    get_repo_files,
    get_readme
)

from analyzer import (
    analyze_files,
    get_project_summary
)

from evaluator import evaluate_repository


st.set_page_config(
    page_title="RepoLens",
    page_icon="🔍",
    layout="wide"
)


# -------------------------
# Header
# -------------------------

st.title("🔍 RepoLens")

st.caption(
    "GitHub Repository Analyzer & Project Evaluator"
)


# -------------------------
# Repository Input
# -------------------------

repo_url = st.text_input(
    "GitHub Repository URL",
    placeholder="https://github.com/user/repository"
)


if st.button("🚀 Analyze Repository"):

    if not repo_url:

        st.warning(
            "Please enter a GitHub repository URL."
        )

        st.stop()


    try:

        # -------------------------
        # Validate URL
        # -------------------------

        parts = repo_url.rstrip("/").split("/")

        if (
            len(parts) < 5
            or parts[2] != "github.com"
        ):

            raise Exception(
                "Please enter a valid GitHub repository URL."
            )


        owner = parts[3]
        repo = parts[4]


        # -------------------------
        # Read Repository
        # -------------------------

        with st.spinner(
            "🔎 Scanning repository..."
        ):

            info = get_repo_info(
                owner,
                repo
            )

            branch = info.get(
                "default_branch",
                "main"
            )

            files = get_repo_files(
                owner,
                repo,
                branch
            )

            readme = get_readme(
                owner,
                repo
            )


        # -------------------------
        # Analyze
        # -------------------------

        analysis = analyze_files(files)

        evaluation = evaluate_repository(
            info,
            analysis,
            readme
        )


        st.success(
            "Repository analyzed successfully!"
        )


        # =====================================================
        # PROJECT SCORE
        # =====================================================

        st.header("🤖 Project Evaluation")


        score = evaluation["score"]

        col1, col2 = st.columns([1, 2])


        with col1:

            st.metric(
                "Project Score",
                f"{score}/100"
            )


        with col2:

            st.write(
                f"### {evaluation['status']}"
            )

            st.progress(
                score / 100
            )


        # =====================================================
        # SCORE BREAKDOWN
        # =====================================================

        st.subheader("📊 Evaluation Breakdown")


        score_data = evaluation["scores"]


        for category, value in score_data.items():

            col1, col2 = st.columns([3, 1])

            with col1:

                st.write(
                    f"**{category}**"
                )

                st.progress(
                    value / 20
                )

            with col2:

                st.write(
                    f"**{value}/20**"
                )


        # =====================================================
        # REPOSITORY OVERVIEW
        # =====================================================

        st.divider()

        st.subheader("📦 Repository Overview")


        col1, col2, col3, col4 = st.columns(4)


        col1.metric(
            "⭐ Stars",
            info.get(
                "stargazers_count",
                0
            )
        )


        col2.metric(
            "🍴 Forks",
            info.get(
                "forks_count",
                0
            )
        )


        col3.metric(
            "🐛 Issues",
            info.get(
                "open_issues_count",
                0
            )
        )


        col4.metric(
            "📁 Files",
            analysis["total_files"]
        )


        # =====================================================
        # PROJECT UNDERSTANDING
        # =====================================================

        st.subheader("🧠 Project Understanding")


        st.info(
            get_project_summary(
                analysis
            )
        )


        # =====================================================
        # REPOSITORY INFORMATION
        # =====================================================

        st.subheader("📋 Repository Information")


        st.write(
            f"**Name:** "
            f"{info.get('name', 'Unknown')}"
        )


        st.write(
            f"**Owner:** "
            f"{owner}"
        )


        st.write(
            f"**Default Branch:** "
            f"{branch}"
        )


        st.write(
            f"**Primary Language:** "
            f"{info.get('language') or 'Not detected'}"
        )


        st.write(
            f"**Description:** "
            f"{info.get('description') or 'No description'}"
        )


        # =====================================================
        # TECHNOLOGIES
        # =====================================================

        st.subheader("💻 Technologies")


        if analysis["languages"]:

            for item in analysis["languages"]:

                st.write(
                    f"• **{item['language']}** "
                    f"— {item['files']} files"
                )

        else:

            st.write(
                "No supported technologies detected."
            )


        # =====================================================
        # DETECTED TOOLS
        # =====================================================

        st.subheader("🧩 Detected Tools")


        if analysis["tools"]:

            for tool in analysis["tools"]:

                st.write(
                    f"• {tool}"
                )

        else:

            st.write(
                "No major configuration files detected."
            )


        # =====================================================
        # STRENGTHS
        # =====================================================

        st.divider()

        st.subheader("💪 Strengths")


        if evaluation["strengths"]:

            for strength in evaluation["strengths"]:

                st.success(
                    f"✓ {strength}"
                )

        else:

            st.write(
                "No strengths detected."
            )


        # =====================================================
        # WEAKNESSES
        # =====================================================

        st.subheader("⚠️ Weaknesses")


        if evaluation["weaknesses"]:

            for weakness in evaluation["weaknesses"]:

                st.warning(
                    f"• {weakness}"
                )

        else:

            st.write(
                "No major weaknesses detected."
            )


        # =====================================================
        # SUGGESTIONS
        # =====================================================

        st.subheader(
            "💡 Improvement Suggestions"
        )


        if evaluation["suggestions"]:

            for suggestion in evaluation["suggestions"]:

                st.info(
                    f"→ {suggestion}"
                )

        else:

            st.write(
                "No suggestions available."
            )


        # =====================================================
        # README
        # =====================================================

        if readme:

            st.divider()

            st.subheader(
                "📖 Repository README"
            )


            with st.expander(
                "View README"
            ):

                st.markdown(
                    readme
                )


        # =====================================================
        # FILE STRUCTURE
        # =====================================================

        st.divider()

        st.subheader(
            "📁 Repository Structure"
        )


        with st.expander(
            "View all files"
        ):

            for file in files:

                if file.get("type") == "blob":

                    st.code(
                        file["path"]
                    )


        # =====================================================
        # FOOTER
        # =====================================================

        st.divider()

        st.caption(
            "RepoLens • GitHub Repository Analysis Engine"
        )


    except Exception as error:

        st.error(
            f"❌ {error}"
        )
