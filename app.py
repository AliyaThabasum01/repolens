import json
import re
import streamlit as st

from github_reader import (
    get_repo_info,
    get_repo_files,
    get_readme
)
from analyzer import (
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
st.caption("GitHub Repository Analyzer & AI-Style Evaluation Agent")


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


def calculate_health_score(evaluation, quality, security, summary):
    score = 100

    # Security deductions
    for finding in security.get("findings", []):
        if finding["severity"] == "High":
            score -= 8
        elif finding["severity"] == "Medium":
            score -= 4
        else:
            score -= 2

    # Code quality deductions
    for finding in quality.get("findings", []):
        if finding["severity"] == "Low":
            score -= 1

    # Documentation
    if not summary.get("config_files"):
        score -= 3

    # Project structure
    if summary.get("total_files", 0) < 3:
        score -= 5

    # Evaluation score influence
    evaluation_score = evaluation.get("score", 0)

    if evaluation_score >= 80:
        score += 5
    elif evaluation_score < 50:
        score -= 5

    return max(0, min(100, score))


def get_health_status(score):
    if score >= 85:
        return "Excellent"
    elif score >= 70:
        return "Good"
    elif score >= 50:
        return "Needs Improvement"
    else:
        return "Poor"


def generate_verdict(score, security, quality, summary):
    security_findings = security.get("findings", [])
    quality_findings = quality.get("findings", [])

    high_security = sum(
        1 for item in security_findings
        if item["severity"] == "High"
    )

    if score >= 85:
        verdict = (
            "This repository has a strong overall health profile "
            "with good structure, documentation, and implementation."
        )
    elif score >= 70:
        verdict = (
            "This repository has a solid foundation, but a few "
            "areas should be improved before considering it production-ready."
        )
    elif score >= 50:
        verdict = (
            "This repository is functional but has several areas "
            "that require improvement in quality, structure, or security."
        )
    else:
        verdict = (
            "This repository requires significant improvements "
            "before it can be considered well-maintained."
        )

    if high_security > 0:
        verdict += (
            f" {high_security} high-severity security issue(s) "
            "were detected."
        )

    if quality_findings:
        verdict += (
            " Code-quality issues were also detected."
        )

    if not summary.get("config_files"):
        verdict += (
            " Adding standard configuration files would improve "
            "project completeness."
        )

    return verdict


def show_findings(findings):
    if not findings:
        st.success("No issues detected.")
        return

    for finding in findings:
        severity = finding["severity"]

        if severity == "High":
            icon = "🔴"
        elif severity == "Medium":
            icon = "🟠"
        else:
            icon = "🟡"

        with st.expander(
            f"{icon} {severity}: {finding['issue']}"
        ):
            st.write(f"**File:** {finding['file']}")


repo_url = st.text_input(
    "GitHub Repository URL",
    placeholder="https://github.com/username/repository"
)


if st.button("🚀 Analyze Repository", type="primary"):

    owner, repo = parse_github_url(repo_url)

    if not owner or not repo:
        st.error("Please enter a valid public GitHub repository URL.")
        st.stop()

    try:

        with st.spinner("🔍 RepoLens is analyzing the repository..."):

            repo_info = get_repo_info(owner, repo)

            branch = repo_info.get(
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

            summary = get_project_summary(files)

            evaluation = evaluate_repository(
                repo_info,
                files,
                readme
            )

            quality = analyze_code_quality(
                files,
                owner,
                repo,
                branch
            )

            security = scan_security(
                files,
                owner,
                repo,
                branch
            )

            health_score = calculate_health_score(
                evaluation,
                quality,
                security,
                summary
            )

            health_status = get_health_status(
                health_score
            )

            verdict = generate_verdict(
                health_score,
                security,
                quality,
                summary
            )

        st.success("✅ Repository analysis completed!")

        # --------------------------------------------------
        # REPOSITORY OVERVIEW
        # --------------------------------------------------

        st.divider()
        st.header("📊 Repository Overview")

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Files",
            summary.get("total_files", 0)
        )

        col2.metric(
            "Stars",
            repo_info.get("stargazers_count", 0)
        )

        col3.metric(
            "Forks",
            repo_info.get("forks_count", 0)
        )

        col4.metric(
            "Health",
            f"{health_score}/100"
        )

        st.write(
            "**Description:**",
            repo_info.get("description")
            or "No description available."
        )

        # --------------------------------------------------
        # HEALTH SCORE
        # --------------------------------------------------

        st.divider()
        st.header("❤️ Repository Health")

        col1, col2 = st.columns([1, 2])

        with col1:

            st.metric(
                "Health Score",
                f"{health_score}/100"
            )

            st.write(
                f"### Status: **{health_status}**"
            )

        with col2:

            st.progress(
                health_score / 100
            )

            st.write(
                "Repository Health measures the overall "
                "quality, structure, security and completeness "
                "of the analyzed repository."
            )

        # --------------------------------------------------
        # AI-STYLE VERDICT
        # --------------------------------------------------

        st.subheader("🤖 RepoLens Verdict")

        st.info(verdict)

        # --------------------------------------------------
        # EVALUATION
        # --------------------------------------------------

        st.divider()
        st.header("🧠 Project Evaluation")

        evaluation_score = evaluation.get(
            "score",
            0
        )

        st.metric(
            "Evaluation Score",
            f"{evaluation_score}/100"
        )

        st.write(
            "**Status:**",
            evaluation.get(
                "status",
                "Not available"
            )
        )

        scores = evaluation.get(
            "scores",
            {}
        )

        if scores:

            st.subheader("Score Breakdown")

            for category, score in scores.items():

                st.write(
                    f"**{category}:** {score}/20"
                )

                st.progress(
                    min(
                        max(score / 20, 0),
                        1
                    )
                )

        col1, col2 = st.columns(2)

        with col1:

            st.subheader("✅ Strengths")

            for item in evaluation.get(
                "strengths",
                []
            ):
                st.write(
                    f"• {item}"
                )

        with col2:

            st.subheader("⚠️ Weaknesses")

            for item in evaluation.get(
                "weaknesses",
                []
            ):
                st.write(
                    f"• {item}"
                )

        st.subheader("💡 Suggestions")

        for item in evaluation.get(
            "suggestions",
            []
        ):
            st.write(
                f"• {item}"
            )

        # --------------------------------------------------
        # PROJECT STRUCTURE
        # --------------------------------------------------

        st.divider()
        st.header("🏗️ Project Structure")

        languages = summary.get(
            "languages",
            {}
        )

        if languages:

            st.subheader("Detected Languages")

            for language, count in languages.items():

                st.write(
                    f"**{language}:** {count} file(s)"
                )

        else:

            st.info(
                "No supported programming languages detected."
            )

        config_files = summary.get(
            "config_files",
            []
        )

        st.subheader("⚙️ Configuration Files")

        if config_files:

            for file in config_files:

                st.write(
                    f"• {file}"
                )

        else:

            st.warning(
                "No common configuration files detected."
            )

        # --------------------------------------------------
        # CODE QUALITY
        # --------------------------------------------------

        st.divider()
        st.header("💻 Code Quality")

        st.metric(
            "Source Files Checked",
            quality.get(
                "checked_files",
                0
            )
        )

        show_findings(
            quality.get(
                "findings",
                []
            )
        )

        # --------------------------------------------------
        # SECURITY
        # --------------------------------------------------

        st.divider()
        st.header("🔐 Security Scan")

        security_findings = security.get(
            "findings",
            []
        )

        high = sum(
            1
            for item in security_findings
            if item["severity"] == "High"
        )

        medium = sum(
            1
            for item in security_findings
            if item["severity"] == "Medium"
        )

        low = sum(
            1
            for item in security_findings
            if item["severity"] == "Low"
        )

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "🔴 High",
            high
        )

        col2.metric(
            "🟠 Medium",
            medium
        )

        col3.metric(
            "🟡 Low",
            low
        )

        show_findings(
            security_findings
        )

        # --------------------------------------------------
        # README
        # --------------------------------------------------

        st.divider()
        st.header("📖 README Preview")

        if readme:

            st.markdown(
                readme[:5000]
            )

            if len(readme) > 5000:

                st.caption(
                    "README preview limited to 5,000 characters."
                )

        else:

            st.warning(
                "No README found."
            )

        # --------------------------------------------------
        # JSON REPORT
        # --------------------------------------------------

        report = {

            "repository": {
                "name": repo_info.get(
                    "full_name"
                ),
                "description": repo_info.get(
                    "description"
                ),
                "url": repo_info.get(
                    "html_url"
                ),
                "stars": repo_info.get(
                    "stargazers_count",
                    0
                ),
                "forks": repo_info.get(
                    "forks_count",
                    0
                ),
                "default_branch": branch
            },

            "health": {
                "score": health_score,
                "status": health_status,
                "verdict": verdict
            },

            "evaluation": evaluation,

            "project_summary": summary,

            "code_quality": quality,

            "security": security
        }

        st.divider()
        st.header("📥 Export Report")

        st.download_button(
            "Download JSON Report",
            data=json.dumps(
                report,
                indent=4
            ),
            file_name=f"{repo}-repolens-report.json",
            mime="application/json"
        )

    except Exception as error:

        st.error(
            f"❌ Analysis failed: {error}"
        )


st.divider()

st.caption(
    "RepoLens provides automated rule-based analysis and "
    "AI-style evaluation. It is not a professional security audit."
)
