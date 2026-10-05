import json
import re
import streamlit as st

from github_reader import (
    get_repo_info,
    get_repo_files,
    get_readme
)
from analyzer import (
    analyze_files,
    get_project_summary,
    analyze_code_quality,
    scan_security
)
from evaluator import evaluate_repository


st.set_page_config(
    page_title="RepoLens",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 RepoLens")
st.caption("GitHub Repository Analyzer and Evaluator")

st.markdown(
    "Analyze repository structure, evaluate project quality, "
    "and identify basic security risks."
)


def parse_github_url(url):
    match = re.match(
        r"^https?://github\.com/([^/\s]+)/([^/\s#?]+)",
        url.strip()
    )

    if not match:
        return None, None

    owner = match.group(1)
    repo = match.group(2).removesuffix(".git")
    return owner, repo


def show_findings(findings):
    if not findings:
        st.success("No findings detected by this scan.")
        return

    for finding in findings:
        severity = finding["severity"]
        title = f'{severity}: {finding["issue"]}'
        with st.expander(title):
            st.write(f'**File:** {finding["file"]}')


repo_url = st.text_input(
    "GitHub repository URL",
    placeholder="https://github.com/username/repository"
)

if st.button("Analyze Repository", type="primary"):
    owner, repo = parse_github_url(repo_url)

    if not owner or not repo:
        st.error("Enter a valid public GitHub repository URL.")
        st.stop()

    try:
        with st.spinner("Analyzing repository..."):
            repo_info = get_repo_info(owner, repo)
            branch = repo_info.get("default_branch", "main")
            files = get_repo_files(owner, repo, branch)
            readme = get_readme(owner, repo)

            summary = get_project_summary(files)
            structure = analyze_files(files)
            evaluation = evaluate_repository(
                repo_info, files, readme
            )
            quality = analyze_code_quality(
                files, owner, repo, branch
            )
            security = scan_security(
                files, owner, repo, branch
            )

        report = {
            "repository": {
                "name": repo_info.get("full_name"),
                "description": repo_info.get("description"),
                "url": repo_info.get("html_url"),
                "stars": repo_info.get("stargazers_count", 0),
                "forks": repo_info.get("forks_count", 0),
                "default_branch": branch
            },
            "summary": summary,
            "evaluation": evaluation,
            "code_quality": quality,
            "security": security
        }

        st.session_state["latest_report"] = report

        st.success("Analysis completed!")

        st.subheader("Repository Overview")

        col1, col2, col3 = st.columns(3)
        col1.metric("Files", summary["total_files"])
        col2.metric("Stars", repo_info.get("stargazers_count", 0))
        col3.metric("Forks", repo_info.get("forks_count", 0))

        st.write(
            "**Description:**",
            repo_info.get("description") or "No description available."
        )

        st.divider()
        st.subheader("Project Evaluation")

        st.metric(
            "Evaluation Score",
            f'{evaluation.get("score", 0)}/100'
        )

        st.write(
            "**Status:**",
            evaluation.get("status", "Not available")
        )

        scores = evaluation.get("scores", {})
        if scores:
            st.write("### Score Breakdown")
            for category, score in scores.items():
                st.write(f"**{category}:** {score}/20")
                st.progress(min(max(score / 20, 0), 1))

        col1, col2 = st.columns(2)

        with col1:
            st.write("### Strengths")
            for item in evaluation.get("strengths", []):
                st.write(f"✅ {item}")

        with col2:
            st.write("### Weaknesses")
            for item in evaluation.get("weaknesses", []):
                st.write(f"⚠️ {item}")

        st.write("### Suggestions")
        for item in evaluation.get("suggestions", []):
            st.write(f"💡 {item}")

        st.divider()
        st.subheader("Repository Structure")

        st.write("### Detected Languages")
        if summary["languages"]:
            st.json(summary["languages"])
        else:
            st.info("No supported language files detected.")

        st.write("### Configuration Files")
        if summary["config_files"]:
            for item in summary["config_files"]:
                st.write(f"- {item}")
        else:
            st.info("No common configuration files detected.")

        st.divider()
        st.subheader("Code Quality Checks")

        st.metric(
            "Source Files Checked",
            quality["checked_files"]
        )

        show_findings(quality["findings"])

        st.divider()
        st.subheader("Security Scan")

        security_findings = security["findings"]
        high_count = sum(
            1 for item in security_findings
            if item["severity"] == "High"
        )
        medium_count = sum(
            1 for item in security_findings
            if item["severity"] == "Medium"
        )
        low_count = sum(
            1 for item in security_findings
            if item["severity"] == "Low"
        )

        col1, col2, col3 = st.columns(3)
        col1.metric("High", high_count)
        col2.metric("Medium", medium_count)
        col3.metric("Low", low_count)

        st.caption(
            f'Source files checked: {security["checked_files"]}'
        )

        show_findings(security_findings)

        st.divider()
        st.subheader("README Preview")

        if readme:
            st.markdown(readme[:5000])
            if len(readme) > 5000:
                st.caption("Preview limited to the first 5,000 characters.")
        else:
            st.info("No README found.")

        st.divider()
        st.download_button(
            label="Download JSON Report",
            data=json.dumps(report, indent=4),
            file_name=f"{repo}-repolens-report.json",
            mime="application/json"
        )

    except Exception as error:
        st.error(f"Analysis failed: {error}")


st.divider()
st.caption(
    "RepoLens uses rule-based evaluation and basic static checks. "
    "It does not replace a professional security audit."
)
