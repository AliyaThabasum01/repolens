
import json
from datetime import datetime

import streamlit as st

from github_reader import (
    get_repo_info,
    get_repo_files,
    get_readme
)

from analyzer import (
    analyze_files,
    analyze_code_quality,
    get_project_summary
)

from evaluator import evaluate_repository


st.set_page_config(
    page_title="RepoLens",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 RepoLens")
st.caption("GitHub Repository Analyzer & Code Quality Inspector")

if "history" not in st.session_state:
    st.session_state.history = []


def create_report(info, analysis, quality, evaluation):
    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "repository": {
            "name": info.get("name"),
            "owner": info.get("owner", {}).get("login"),
            "url": info.get("html_url"),
            "description": info.get("description"),
            "language": info.get("language"),
            "stars": info.get("stargazers_count", 0),
            "forks": info.get("forks_count", 0)
        },
        "analysis": analysis,
        "code_quality": quality,
        "evaluation": evaluation
    }


repo_url = st.text_input(
    "GitHub Repository URL",
    placeholder="https://github.com/user/repository"
)

if st.button("🚀 Analyze Repository", type="primary"):

    parts = repo_url.strip().rstrip("/").split("/")

    if (
        len(parts) < 5
        or parts[0] not in ("https:", "http:")
        or parts[2].lower() != "github.com"
    ):
        st.error("Enter a valid GitHub repository URL.")
        st.stop()

    owner = parts[3]
    repo = parts[4].removesuffix(".git")

    try:
        with st.spinner("Scanning repository and source code..."):
            info = get_repo_info(owner, repo)
            branch = info.get("default_branch", "main")

            files = get_repo_files(owner, repo, branch)
            readme = get_readme(owner, repo)

            analysis = analyze_files(files)

            quality = analyze_code_quality(
                files,
                owner,
                repo,
                branch
            )

            evaluation = evaluate_repository(
                info,
                analysis,
                readme
            )

            report = create_report(
                info,
                analysis,
                quality,
                evaluation
            )

        st.success("Analysis completed!")

        # Project score
        st.header("🤖 Project Evaluation")

        col1, col2 = st.columns([1, 2])

        with col1:
            st.metric(
                "Project Score",
                f"{evaluation['score']}/100"
            )

        with col2:
            st.subheader(evaluation["status"])
            st.progress(evaluation["score"] / 100)

        # Overview
        st.divider()
        st.subheader("📦 Repository Overview")

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("⭐ Stars", info.get("stargazers_count", 0))
        col2.metric("🍴 Forks", info.get("forks_count", 0))
        col3.metric("🐛 Issues", info.get("open_issues_count", 0))
        col4.metric("📁 Files", analysis["total_files"])

        st.write(f"**Repository:** {info.get('full_name', repo)}")
        st.write(f"**Description:** {info.get('description') or 'No description'}")
        st.info(get_project_summary(analysis))

        # Existing evaluation breakdown
        st.divider()
        st.subheader("📊 Evaluation Breakdown")

        for category, value in evaluation["scores"].items():
            st.write(f"**{category}: {value}/20**")
            st.progress(value / 20)

        # Code quality section
        st.divider()
        st.header("🧹 Code Quality Analysis")

        st.caption(
            "Static checks on up to 30 source files. "
            "These checks do not prove code correctness or security."
        )

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Scanned Files", quality["scanned_files"])
        col2.metric("Lines of Code", quality["total_lines"])
        col3.metric("Long Lines", quality["long_lines"])
        col4.metric("Large Files", quality["large_files"])

        st.write(
            f"**Empty files:** {quality['empty_files']}"
        )

        if quality["findings"]:
            st.subheader("🔎 Findings")

            for finding in quality["findings"]:
                with st.expander(
                    f"{finding['severity']}: {finding['file']}"
                ):
                    st.write(finding["issue"])
        else:
            st.success(
                "No issues were detected by these basic checks."
            )

        if quality["scanned_files"] == 0:
            st.warning(
                "No source files could be scanned. "
                "The repository may be empty, inaccessible, "
                "or contain unsupported files."
            )

        # Evaluation feedback
        st.divider()
        st.subheader("💪 Strengths")

        for item in evaluation["strengths"]:
            st.success(item)

        st.subheader("⚠️ Weaknesses")

        for item in evaluation["weaknesses"]:
            st.warning(item)

        st.subheader("💡 Suggestions")

        for item in evaluation["suggestions"]:
            st.info(item)

        # README
        if readme:
            st.divider()
            st.subheader("📖 README")

            with st.expander("View README"):
                st.markdown(readme)

        # Download report
        st.divider()
        st.header("📥 Export Report")

        st.download_button(
            "⬇️ Download JSON Report",
            data=json.dumps(
                report,
                indent=4,
                ensure_ascii=False
            ),
            file_name=f"{repo}_report.json",
            mime="application/json"
        )

        # Session history
        st.session_state.history.append({
            "repository": info.get("full_name", repo),
            "score": evaluation["score"],
            "date": report["generated_at"]
        })

    except Exception as error:
        st.error(f"Analysis failed: {error}")


# History
st.divider()
st.header("📜 Evaluation History")

if st.session_state.history:
    st.dataframe(
        list(reversed(st.session_state.history)),
        use_container_width=True,
        hide_index=True
    )

    if len(st.session_state.history) >= 2:
        st.subheader("📊 Score Comparison")

        comparison = {}

        for item in st.session_state.history:
            comparison[item["repository"]] = item["score"]

        st.bar_chart(comparison)

    if st.button("🗑️ Clear History"):
        st.session_state.history = []
        st.rerun()
else:
    st.info("No analyses in this session yet.")

st.divider()
st.caption("RepoLens • Code Quality & Repository Analysis")
