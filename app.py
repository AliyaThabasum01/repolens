import streamlit as st

from github_reader import get_repo_info, get_repo_files
from analyzer import analyze_files


st.set_page_config(
    page_title="RepoLens",
    page_icon="🔍",
    layout="wide"
)


# -----------------------------
# Header
# -----------------------------

st.title("🔍 RepoLens")
st.caption("AI-powered GitHub Repository Analyzer")


# -----------------------------
# Repository Input
# -----------------------------

repo_url = st.text_input(
    "GitHub Repository URL",
    placeholder="https://github.com/user/repository"
)


# -----------------------------
# Analyze Button
# -----------------------------

if st.button("🔍 Analyze Repository", use_container_width=True):

    if not repo_url:
        st.warning("Please enter a GitHub repository URL.")

    else:

        try:
            # -----------------------------
            # Extract owner and repository
            # -----------------------------

            parts = repo_url.rstrip("/").split("/")

            owner = parts[-2]
            repo = parts[-1]

            # -----------------------------
            # Read Repository
            # -----------------------------

            with st.spinner("🔄 Reading repository..."):

                info = get_repo_info(owner, repo)
                files = get_repo_files(owner, repo)

            st.success("✅ Repository loaded successfully!")

            # -----------------------------
            # Repository Statistics
            # -----------------------------

            st.subheader("📊 Repository Statistics")

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "⭐ Stars",
                info["stargazers_count"]
            )

            col2.metric(
                "🍴 Forks",
                info["forks_count"]
            )

            col3.metric(
                "🐛 Open Issues",
                info["open_issues_count"]
            )

            # -----------------------------
            # Repository Information
            # -----------------------------

            st.subheader("📋 Repository Information")

            st.write(f"**Name:** {info['name']}")

            st.write(
                f"**Language:** "
                f"{info['language'] or 'Not detected'}"
            )

            st.write(
                f"**Description:** "
                f"{info['description'] or 'No description provided'}"
            )

            st.write(
                f"**Default Branch:** "
                f"{info['default_branch']}"
            )

            # -----------------------------
            # Project Analysis
            # -----------------------------

            analysis = analyze_files(files)

            st.subheader("🧠 Project Analysis")

            col1, col2 = st.columns(2)

            col1.metric(
                "📁 Total Files",
                analysis["total_files"]
            )

            col2.metric(
                "💻 Languages",
                len(analysis["languages"])
            )

            # -----------------------------
            # Languages
            # -----------------------------

            st.write("### 💻 Languages")

            if analysis["languages"]:

                for language, count in analysis["languages"].items():

                    st.write(
                        f"**{language}:** {count} files"
                    )

            else:

                st.info(
                    "No recognized programming languages found."
                )

            # -----------------------------
            # Tech Stack
            # -----------------------------

            st.write("### 🧰 Detected Tech Stack")

            if analysis["tech_stack"]:

                for tech in analysis["tech_stack"]:

                    st.write(f"• {tech}")

            else:

                st.info(
                    "No specific technologies detected yet."
                )

            # -----------------------------
            # Repository Structure
            # -----------------------------

            st.subheader("📁 Repository Structure")

            file_paths = [
                file["path"]
                for file in files
                if file["type"] == "blob"
            ]

            if file_paths:

                st.code(
                    "\n".join(file_paths),
                    language="text"
                )

            else:

                st.info(
                    "No files found in this repository."
                )

        except Exception as error:

            st.error(
                f"❌ Something went wrong: {error}"
            )
