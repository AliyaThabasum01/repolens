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


st.title("🔍 RepoLens")

st.caption(
    "GitHub Repository Analyzer"
)


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
        # Load repository
        # -------------------------

        with st.spinner(
            "🔎 Analyzing repository..."
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


        st.success(
            "Repository analyzed successfully!"
        )


        # -------------------------
        # Statistics
        # -------------------------

        total_files = len([
            file
            for file in files
            if file.get("type") == "blob"
        ])


        col1, col2, col3, col4 = st.columns(4)


        col1.metric(
            "⭐ Stars",
            info.get("stargazers_count", 0)
        )


        col2.metric(
            "🍴 Forks",
            info.get("forks_count", 0)
        )


        col3.metric(
            "🐛 Issues",
            info.get("open_issues_count", 0)
        )


        col4.metric(
            "📁 Files",
            total_files
        )


        # -------------------------
        # Repository information
        # -------------------------

        st.subheader("📋 Repository Information")


        st.write(
            f"**Name:** {info.get('name', 'Unknown')}"
        )


        st.write(
            f"**Owner:** {owner}"
        )


        st.write(
            f"**Default Branch:** {branch}"
        )


        st.write(
            f"**Primary Language:** "
            f"{info.get('language') or 'Not detected'}"
        )


        st.write(
            f"**Description:** "
            f"{info.get('description') or 'No description'}"
        )


        # -------------------------
        # Analysis
        # -------------------------

        analysis = analyze_files(files)


        st.subheader("📊 Project Analysis")


        st.info(
            get_project_summary(analysis)
        )


        col1, col2 = st.columns(2)


        with col1:

            st.write("### 💻 Technologies")


            if analysis["languages"]:

                for item in analysis["languages"]:

                    st.write(
                        f"• **{item['language']}** "
                        f"— {item['files']} files"
                    )

            else:

                st.write(
                    "No supported languages detected."
                )


        with col2:

            st.write("### 🧩 Detected Tools")


            if analysis["tools"]:

                for tool in analysis["tools"]:

                    st.write(
                        f"• {tool}"
                    )

            else:

                st.write(
                    "No major configuration files detected."
                )


        # -------------------------
        # Project folders
        # -------------------------

        st.subheader("📂 Project Folders")


        if analysis["directories"]:

            for directory in analysis["directories"]:

                st.write(
                    f"📁 `{directory}`"
                )

        else:

            st.write(
                "No folders detected."
            )


        # -------------------------
        # Repository structure
        # -------------------------

        st.subheader("📁 Repository Structure")


        with st.expander(
            "View all repository files"
        ):

            for file in files:

                if file.get("type") == "blob":

                    st.code(
                        file["path"]
                    )


        # -------------------------
        # README
        # -------------------------

        st.subheader("📖 README")


        if readme:

            with st.expander(
                "View README"
            ):

                st.markdown(readme)

        else:

            st.warning(
                "README not found."
            )


        # -------------------------
        # Evaluation
        # -------------------------

        evaluation = evaluate_repository(
            info,
            analysis,
            readme
        )


        st.subheader("💪 Strengths")


        if evaluation["strengths"]:

            for strength in evaluation["strengths"]:

                st.success(
                    f"✓ {strength}"
                )

        else:

            st.write(
                "No strengths detected yet."
            )


        st.subheader("💡 Improvement Suggestions")


        if evaluation["suggestions"]:

            for suggestion in evaluation["suggestions"]:

                st.warning(
                    f"→ {suggestion}"
                )

        else:

            st.write(
                "No suggestions generated."
            )


        # -------------------------
        # Footer
        # -------------------------

        st.divider()


        st.caption(
            "RepoLens • Repository Analysis Engine"
        )


    except Exception as error:

        st.error(
            f"❌ {error}"
        )
