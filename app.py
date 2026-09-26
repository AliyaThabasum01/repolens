import streamlit as st
from github_reader import get_repo_info, get_repo_files


st.set_page_config(
    page_title="RepoLens",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 RepoLens")
st.caption("AI-powered GitHub Repository Analyzer")

repo_url = st.text_input(
    "GitHub Repository URL",
    placeholder="https://github.com/user/repository"
)

if st.button("🔍 Analyze Repository"):

    if not repo_url:
        st.warning("Enter a GitHub repository URL.")

    else:
        try:
            parts = repo_url.rstrip("/").split("/")

            owner = parts[-2]
            repo = parts[-1]

            with st.spinner("Reading repository..."):

                info = get_repo_info(owner, repo)
                files = get_repo_files(owner, repo)

            st.success("Repository loaded!")

            col1, col2, col3 = st.columns(3)

            col1.metric("⭐ Stars", info["stargazers_count"])
            col2.metric("🍴 Forks", info["forks_count"])
            col3.metric("🐛 Issues", info["open_issues_count"])

            st.subheader("📋 Repository")

            st.write(f"**Name:** {info['name']}")
            st.write(f"**Language:** {info['language']}")
            st.write(f"**Description:** {info['description'] or 'No description'}")

            st.subheader("📁 Repository Structure")

            for file in files:
                if file["type"] == "blob":
                    st.code(file["path"])

        except Exception as error:
            st.error(str(error))
