
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
    get_project_summary
)

from evaluator import evaluate_repository


st.set_page_config(
    page_title="RepoLens",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 RepoLens")
st.caption("GitHub Repository Analyzer & Project Evaluator")

if "history" not in st.session_state:
    st.session_state.history = []

repo_url = st.text_input(
    "GitHub Repository URL",
    placeholder="https://github.com/user/repository"
)


def create_report(info, analysis, evaluation):
    return {
        "report": {
            "generated_at": datetime.now().astimezone().isoformat(),
            "repository": {
                "name": info.get("name"),
                "owner": info.get("owner", {}).get("login"),
                "url": info.get("html_url"),
                "description": info.get("description"),
                "primary_language": info.get("language"),
                "default_branch": info.get("default_branch"),
                "stars": info.get("stargazers_count", 0),
                "forks": info.get("forks_count", 0),
                "open_issues": info.get("open_issues_count", 0)
            },
            "analysis": analysis,
            "evaluation": evaluation
        }
    }


if st.button("🚀 Analyze Repository", type="primary"):

    if not repo_url.strip():
        st.warning("Please enter a GitHub repository URL.")
        st.stop()

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
        with st.spinner("Scanning repository..."):
            info = get_repo_info(owner, repo)
            branch = info.get("default_branch", "main")

            files = get_repo_files(owner, repo, branch)
            readme = get_readme(owner, repo)

            analysis = analyze_files(files)
            evaluation = evaluate_repository(
                info,
                analysis,
                readme
            )

            report = create_report(
                info,
                analysis,
                evaluation
            )

        # Save to session history
        st.session_state.history.append({
            "repository": info.get("full_name", repo),
            "score": evaluation["score"],
            "status": evaluation["status"],
            "date": report["report"]["generated_at"],
            "report": report
        })

        st.success("Analysis completed!")

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

        st.subheader("📊 Evaluation Breakdown")

        for category, value in evaluation["scores"].items():
            col1, col2 = st.columns([4, 1])

            with col1:
                st.write(f"**{category}**")
                st.progress(value / 20)

            with col2:
                st.write(f"**{value}/20**")

        st.divider()
        st.subheader("📦 Repository Overview")

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("⭐ Stars", info.get("stargazers_count", 0))
        col2.metric("🍴 Forks", info.get("forks_count", 0))
        col3.metric("🐛 Issues", info.get("open_issues_count", 0))
        col4.metric("📁 Files", analysis["total_files"])

        st.subheader("📋 Repository Information")

        st.write(f"**Name:** {info.get('name', 'Unknown')}")
        st.write(f"**Owner:** {owner}")
        st.write(f"**Branch:** {branch}")
        st.write(f"**Language:** {info.get('language') or 'Not detected'}")
        st.write(f"**Description:** {info.get('description') or 'No description'}")

        st.divider()
        st.subheader("🧠 Project Understanding")
        st.info(get_project_summary(analysis))

        st.subheader("💻 Technologies")

        if analysis["languages"]:
            for item in analysis["languages"]:
                st.write(
                    f"• **{item['language']}** — {item['files']} files"
                )
        else:
            st.write("No supported technologies detected.")

        st.subheader("🧩 Detected Tools")

        if analysis["tools"]:
            for tool in analysis["tools"]:
                st.write(f"• {tool}")
        else:
            st.write("No major configuration files detected.")

        st.divider()
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

        if evaluation["suggestions"]:
            for item in evaluation["suggestions"]:
                st.info(f"→ {item}")
        else:
            st.write("No suggestions available.")

        if readme:
            st.divider()
            st.subheader("📖 Repository README")

            with st.expander("View README"):
                st.markdown(readme)

        st.divider()
        st.subheader("📁 Repository Structure")

        with st.expander("View all files"):
            for file in files:
                if file.get("type") == "blob":
                    st.code(file["path"])

        st.divider()
        st.header("📥 Export Evaluation Report")

        report_json = json.dumps(
            report,
            indent=4,
            ensure_ascii=False
        )

        st.download_button(
            label="⬇️ Download JSON Report",
            data=report_json,
            file_name=f"{repo}_evaluation_report.json",
            mime="application/json"
        )

    except Exception as error:
        st.error(f"Analysis failed: {error}")


# Evaluation history
st.divider()
st.header("📜 Evaluation History")

history = st.session_state.history

if history:
    st.caption(
        "Previous analyses stored in this browser session."
    )

    history_table = [
        {
            "Repository": item["repository"],
            "Score": item["score"],
            "Status": item["status"],
            "Date": item["date"][:19].replace("T", " ")
        }
        for item in reversed(history)
    ]

    st.dataframe(
        history_table,
        use_container_width=True,
        hide_index=True
    )

    if len(history) >= 2:
        st.subheader("📊 Score Comparison")

        comparison = {}

        for item in history:
            comparison[item["repository"]] = item["score"]

        st.bar_chart(
            comparison,
            y_label="Project Score",
            x_label="Repository"
        )

    if st.button("🗑️ Clear History"):
        st.session_state.history = []
        st.rerun()

else:
    st.info(
        "No previous analyses in this session. "
        "Analyze a repository to start tracking results."
    )

st.divider()
st.caption("RepoLens • Repository Analysis Engine")
