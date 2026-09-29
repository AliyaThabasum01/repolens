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
st.caption("GitHub Repository Analyzer")


repo_url = st.text_input(
    "GitHub Repository URL",
    placeholder="https://github.com/user/repository"
)


if st.button("🚀 Analyze Repository"):

    if not repo_url:
        st.warning("Enter a GitHub repository URL.")
        st.stop()

    try:

        parts = repo_url.rstrip("/").split("/")

        if len(parts) < 5 or parts[2] != "github.com":
            raise Exception("Enter a valid GitHub repository URL.")

        owner = parts[3]
        repo = parts[4]

        with st.spinner("🔎 Analyzing repository..."):

            info = get_repo_info(owner, repo)

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

        analysis = analyze_files(files)

        evaluation = evaluate_repository(
            info,
            analysis,
            readme
        )

        st.success("Repository analyzed successfully!")


        # -------------------------
        # Statistics
        # -------------------------

        st.subheader("📊 Repository Overview")

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
            analysis["total_files"]
        )


        # -------------------------
        # Project Summary
        # -------------------------

        st.subheader("🧠 Project Understanding")

        st.info(
            get_project_summary(analysis)
        )


        # -------------------------
        # Repository Info
        # -------------------------

        st.subheader("📋 Repository Information")

        st.write(
            f"**Name:** {info.get('name', 'Unknown')}"
        )

        st.write(
            f"**Language:** "
            f"{info.get('language') or 'Not detected'}"
        )

        st.write(
            f"**Branch:** {branch}"
        )

        st.write(
            f"**Description:** "
            f"{info.get('description') or 'No description'}"
        )


        # -------------------------
        # Technologies
        # -------------------------

        st.subheader("💻 Technologies")

        if analysis["languages"]:

            for item in analysis["languages"]:

                st.write(
                    f"• **{item['language']}** "
                    f"— {item['files']} files"
                )

        else:

            st.write("No supported technologies detected.")


        # -------------------------
        # Tools
        # -------------------------

        st.subheader("🧩 Detected Tools")

        if analysis["tools"]:

            for tool in analysis["tools"]:
                st.write(f"• {tool}")

        else:

            st.write("No major configuration tools detected.")


        # -------------------------
        # Evaluation Report
        # -------------------------

        st.divider()

        st.header("🤖 RepoLens Evaluation Report")

        st.subheader("💪 Strengths")

        for item in evaluation["strengths"]:
            st.success(f"✓ {item}")


        st.subheader("⚠️ Weaknesses")

        if evaluation["weaknesses"]:

            for item in evaluation["weaknesses"]:
                st.warning(f"• {item}")

        else:

            st.write("No major weaknesses detected.")


        st.subheader("💡 Improvement Suggestions")

        for item in evaluation["suggestions"]:
            st.info(f"→ {item}")


        # -------------------------
        # README
        # -------------------------

        if readme:

            st.divider()

            st.subheader("📖 Repository README")

            with st.expander("View README"):

                st.markdown(readme)


        # -------------------------
        # File Structure
        # -------------------------

        st.divider()

        st.subheader("📁 Repository Structure")

        with st.expander("View Files"):

            for file in files:

                if file.get("type") == "blob":

                    st.code(file["path"])


        st.divider()

        st.caption(
            "RepoLens • GitHub Repository Analysis Engine"
        )


    except Exception as error:

        st.error(f"❌ {error}")
