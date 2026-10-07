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


# =========================================================
# PAGE HEADER
# =========================================================

st.title("🔍 RepoLens")

st.caption(
    "GitHub Repository Analyzer, Evaluator & Comparison Agent"
)

st.write(
    "Analyze repositories, evaluate project quality, "
    "identify security issues, and compare two projects."
)


# =========================================================
# HELPER FUNCTIONS
# =========================================================

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


def calculate_health_score(
    evaluation,
    quality,
    security,
    summary
):

    score = 100

    for finding in security.get("findings", []):

        if finding["severity"] == "High":
            score -= 8

        elif finding["severity"] == "Medium":
            score -= 4

        else:
            score -= 2

    for finding in quality.get("findings", []):

        if finding["severity"] == "Low":
            score -= 1

    if not summary.get("config_files"):
        score -= 3

    if summary.get("total_files", 0) < 3:
        score -= 5

    evaluation_score = evaluation.get(
        "score",
        0
    )

    if evaluation_score >= 80:
        score += 5

    elif evaluation_score < 50:
        score -= 5

    return max(
        0,
        min(score, 100)
    )


def get_health_status(score):

    if score >= 85:
        return "Excellent"

    elif score >= 70:
        return "Good"

    elif score >= 50:
        return "Needs Improvement"

    return "Poor"


def analyze_repository(owner, repo):

    repo_info = get_repo_info(
        owner,
        repo
    )

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

    summary = get_project_summary(
        files
    )

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

    return {
        "repo_info": repo_info,
        "branch": branch,
        "files": files,
        "readme": readme,
        "summary": summary,
        "evaluation": evaluation,
        "quality": quality,
        "security": security,
        "health_score": health_score,
        "health_status": get_health_status(
            health_score
        )
    }


def security_count(data, severity):

    return sum(
        1
        for finding in data["security"].get(
            "findings",
            []
        )
        if finding["severity"] == severity
    )


def get_languages(data):

    languages = data["summary"].get(
        "languages",
        {}
    )

    if not languages:
        return "None detected"

    return ", ".join(
        languages.keys()
    )


def get_winner(score_a, score_b):

    if score_a > score_b:
        return "Repository A 🏆"

    elif score_b > score_a:
        return "Repository B 🏆"

    return "Tie 🤝"


# =========================================================
# TABS
# =========================================================

tab1, tab2 = st.tabs(
    [
        "🔍 Analyze Repository",
        "⚔️ Compare Repositories"
    ]
)


# =========================================================
# SINGLE REPOSITORY ANALYZER
# =========================================================

with tab1:

    repo_url = st.text_input(
        "GitHub Repository URL",
        placeholder="https://github.com/username/repository",
        key="single_repo"
    )

    if st.button(
        "🚀 Analyze Repository",
        type="primary"
    ):

        owner, repo = parse_github_url(
            repo_url
        )

        if not owner or not repo:

            st.error(
                "Please enter a valid public GitHub repository URL."
            )

            st.stop()

        try:

            with st.spinner(
                "🔍 RepoLens is analyzing the repository..."
            ):

                data = analyze_repository(
                    owner,
                    repo
                )

            repo_info = data["repo_info"]
            summary = data["summary"]
            evaluation = data["evaluation"]
            quality = data["quality"]
            security = data["security"]

            st.success(
                "✅ Analysis completed!"
            )

            # -------------------------------------------------
            # OVERVIEW
            # -------------------------------------------------

            st.divider()

            st.header(
                "📊 Repository Overview"
            )

            col1, col2, col3, col4 = st.columns(4)

            col1.metric(
                "Files",
                summary.get(
                    "total_files",
                    0
                )
            )

            col2.metric(
                "⭐ Stars",
                repo_info.get(
                    "stargazers_count",
                    0
                )
            )

            col3.metric(
                "🍴 Forks",
                repo_info.get(
                    "forks_count",
                    0
                )
            )

            col4.metric(
                "❤️ Health",
                f'{data["health_score"]}/100'
            )

            st.write(
                "**Description:**",
                repo_info.get(
                    "description"
                ) or "No description available."
            )

            # -------------------------------------------------
            # HEALTH
            # -------------------------------------------------

            st.divider()

            st.header(
                "❤️ Repository Health"
            )

            col1, col2 = st.columns(
                [1, 2]
            )

            with col1:

                st.metric(
                    "Health Score",
                    f'{data["health_score"]}/100'
                )

                st.write(
                    f'### {data["health_status"]}'
                )

            with col2:

                st.progress(
                    data["health_score"] / 100
                )

                st.write(
                    "Health score combines project structure, "
                    "evaluation, code quality and security checks."
                )

            # -------------------------------------------------
            # EVALUATION
            # -------------------------------------------------

            st.divider()

            st.header(
                "🧠 Project Evaluation"
            )

            st.metric(
                "Evaluation Score",
                f'{evaluation.get("score", 0)}/100'
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

                st.subheader(
                    "Score Breakdown"
                )

                for category, score in scores.items():

                    st.write(
                        f"**{category}:** {score}/20"
                    )

                    st.progress(
                        min(
                            max(
                                score / 20,
                                0
                            ),
                            1
                        )
                    )

            col1, col2 = st.columns(2)

            with col1:

                st.subheader(
                    "✅ Strengths"
                )

                for item in evaluation.get(
                    "strengths",
                    []
                ):

                    st.write(
                        f"• {item}"
                    )

            with col2:

                st.subheader(
                    "⚠️ Weaknesses"
                )

                for item in evaluation.get(
                    "weaknesses",
                    []
                ):

                    st.write(
                        f"• {item}"
                    )

            st.subheader(
                "💡 Suggestions"
            )

            for item in evaluation.get(
                "suggestions",
                []
            ):

                st.write(
                    f"• {item}"
                )

            # -------------------------------------------------
            # LANGUAGES
            # -------------------------------------------------

            st.divider()

            st.header(
                "💻 Technology Stack"
            )

            languages = summary.get(
                "languages",
                {}
            )

            if languages:

                for language, count in languages.items():

                    st.write(
                        f"**{language}:** {count} file(s)"
                    )

            else:

                st.info(
                    "No supported programming languages detected."
                )

            # -------------------------------------------------
            # CODE QUALITY
            # -------------------------------------------------

            st.divider()

            st.header(
                "🧹 Code Quality"
            )

            st.metric(
                "Source Files Checked",
                quality.get(
                    "checked_files",
                    0
                )
            )

            quality_findings = quality.get(
                "findings",
                []
            )

            if quality_findings:

                for finding in quality_findings:

                    with st.expander(
                        f'⚠️ {finding["severity"]}: '
                        f'{finding["issue"]}'
                    ):

                        st.write(
                            f'**File:** {finding["file"]}'
                        )

            else:

                st.success(
                    "No code quality issues detected."
                )

            # -------------------------------------------------
            # SECURITY
            # -------------------------------------------------

            st.divider()

            st.header(
                "🔐 Security Scan"
            )

            high = security_count(
                data,
                "High"
            )

            medium = security_count(
                data,
                "Medium"
            )

            low = security_count(
                data,
                "Low"
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

            findings = security.get(
                "findings",
                []
            )

            if findings:

                for finding in findings:

                    with st.expander(
                        f'🔎 {finding["severity"]}: '
                        f'{finding["issue"]}'
                    ):

                        st.write(
                            f'**File:** {finding["file"]}'
                        )

            else:

                st.success(
                    "No security findings detected."
                )

            # -------------------------------------------------
            # README
            # -------------------------------------------------

            st.divider()

            st.header(
                "📖 README Preview"
            )

            if data["readme"]:

                st.markdown(
                    data["readme"][:5000]
                )

            else:

                st.warning(
                    "No README found."
                )

            # -------------------------------------------------
            # EXPORT
            # -------------------------------------------------

            st.divider()

            report = {
                "repository": repo_info,
                "health_score": data["health_score"],
                "health_status": data["health_status"],
                "evaluation": evaluation,
                "summary": summary,
                "code_quality": quality,
                "security": security
            }

            st.download_button(
                "📥 Download JSON Report",
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


# =========================================================
# REPOSITORY COMPARISON
# =========================================================

with tab2:

    st.header(
        "⚔️ Compare Two GitHub Repositories"
    )

    st.write(
        "Compare two projects using the same RepoLens "
        "evaluation criteria."
    )

    col1, col2 = st.columns(2)

    with col1:

        repo_a_url = st.text_input(
            "Repository A",
            placeholder="https://github.com/user/project-a",
            key="repo_a"
        )

    with col2:

        repo_b_url = st.text_input(
            "Repository B",
            placeholder="https://github.com/user/project-b",
            key="repo_b"
        )

    if st.button(
        "⚔️ Compare Repositories",
        type="primary"
    ):

        owner_a, repo_a = parse_github_url(
            repo_a_url
        )

        owner_b, repo_b = parse_github_url(
            repo_b_url
        )

        if not owner_a or not repo_a:

            st.error(
                "Repository A URL is invalid."
            )

            st.stop()

        if not owner_b or not repo_b:

            st.error(
                "Repository B URL is invalid."
            )

            st.stop()

        try:

            with st.spinner(
                "⚔️ RepoLens is comparing both repositories..."
            ):

                data_a = analyze_repository(
                    owner_a,
                    repo_a
                )

                data_b = analyze_repository(
                    owner_b,
                    repo_b
                )

            st.success(
                "✅ Comparison completed!"
            )

            # -------------------------------------------------
            # WINNER
            # -------------------------------------------------

            score_a = data_a["health_score"]
            score_b = data_b["health_score"]

            winner = get_winner(
                score_a,
                score_b
            )

            st.divider()

            st.header(
                "🏆 Comparison Result"
            )

            if score_a == score_b:

                st.info(
                    "Both repositories have the same health score."
                )

            else:

                st.success(
                    f"🏆 Current winner: **{winner}**"
                )

            # -------------------------------------------------
            # SCORE COMPARISON
            # -------------------------------------------------

            st.subheader(
                "❤️ Health Score"
            )

            col1, col2 = st.columns(2)

            with col1:

                st.metric(
                    repo_a,
                    f"{score_a}/100"
                )

                st.progress(
                    score_a / 100
                )

            with col2:

                st.metric(
                    repo_b,
                    f"{score_b}/100"
                )

                st.progress(
                    score_b / 100
                )

            # -------------------------------------------------
            # COMPARISON TABLE
            # -------------------------------------------------

            st.subheader(
                "📊 Detailed Comparison"
            )

            comparison = {

                "Metric": [
                    "Health Score",
                    "Health Status",
                    "Evaluation Score",
                    "Files",
                    "⭐ Stars",
                    "🍴 Forks",
                    "Languages",
                    "🔴 High Security Issues",
                    "🟠 Medium Security Issues",
                    "🟡 Low Security Issues"
                ],

                repo_a: [
                    data_a["health_score"],
                    data_a["health_status"],
                    data_a["evaluation"].get(
                        "score",
                        0
                    ),
                    data_a["summary"].get(
                        "total_files",
                        0
                    ),
                    data_a["repo_info"].get(
                        "stargazers_count",
                        0
                    ),
                    data_a["repo_info"].get(
                        "forks_count",
                        0
                    ),
                    get_languages(data_a),
                    security_count(
                        data_a,
                        "High"
                    ),
                    security_count(
                        data_a,
                        "Medium"
                    ),
                    security_count(
                        data_a,
                        "Low"
                    )
                ],

                repo_b: [
                    data_b["health_score"],
                    data_b["health_status"],
                    data_b["evaluation"].get(
                        "score",
                        0
                    ),
                    data_b["summary"].get(
                        "total_files",
                        0
                    ),
                    data_b["repo_info"].get(
                        "stargazers_count",
                        0
                    ),
                    data_b["repo_info"].get(
                        "forks_count",
                        0
                    ),
                    get_languages(data_b),
                    security_count(
                        data_b,
                        "High"
                    ),
                    security_count(
                        data_b,
                        "Medium"
                    ),
                    security_count(
                        data_b,
                        "Low"
                    )
                ]
            }

            st.table(
                comparison
            )

            # -------------------------------------------------
            # EVALUATION COMPARISON
            # -------------------------------------------------

            st.divider()

            st.subheader(
                "🧠 Evaluation Comparison"
            )

            eval_a = data_a["evaluation"].get(
                "score",
                0
            )

            eval_b = data_b["evaluation"].get(
                "score",
                0
            )

            col1, col2 = st.columns(2)

            with col1:

                st.metric(
                    f"{repo_a} Evaluation",
                    f"{eval_a}/100"
                )

            with col2:

                st.metric(
                    f"{repo_b} Evaluation",
                    f"{eval_b}/100"
                )

            # -------------------------------------------------
            # STRENGTHS
            # -------------------------------------------------

            st.divider()

            col1, col2 = st.columns(2)

            with col1:

                st.subheader(
                    f"✅ {repo_a} Strengths"
                )

                for item in data_a[
                    "evaluation"
                ].get(
                    "strengths",
                    []
                ):

                    st.write(
                        f"• {item}"
                    )

            with col2:

                st.subheader(
                    f"✅ {repo_b} Strengths"
                )

                for item in data_b[
                    "evaluation"
                ].get(
                    "strengths",
                    []
                ):

                    st.write(
                        f"• {item}"
                    )

            # -------------------------------------------------
            # FINAL VERDICT
            # -------------------------------------------------

            st.divider()

            st.header(
                "🤖 RepoLens Final Verdict"
            )

            if score_a > score_b:

                difference = score_a - score_b

                st.success(
                    f"🏆 **{repo_a}** has the stronger overall "
                    f"repository health by **{difference} points**."
                )

            elif score_b > score_a:

                difference = score_b - score_a

                st.success(
                    f"🏆 **{repo_b}** has the stronger overall "
                    f"repository health by **{difference} points**."
                )

            else:

                st.info(
                    "🤝 Both repositories have equal overall health."
                )

        except Exception as error:

            st.error(
                f"❌ Comparison failed: {error}"
            )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "RepoLens uses automated rule-based analysis. "
    "Results are intended for project evaluation and "
    "do not replace professional security audits."
)
