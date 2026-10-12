

import json
import re
import requests
import streamlit as st

from github_reader import get_repo_info, get_repo_files, get_readme
from analyzer import get_project_summary, analyze_code_quality, scan_security
from evaluator import evaluate_repository


st.set_page_config(
    page_title="RepoLens | Repository Insights",
    page_icon="🔍",
    layout="wide"
)

GITHUB_API = "https://api.github.com"


def parse_github_url(url):
    match = re.match(
        r"^https?://github\.com/([^/\s]+)/([^/\s#?]+)",
        url.strip()
    )
    if not match:
        return None, None

    return match.group(1), match.group(2).removesuffix(".git")


def analyze_readme(readme):
    text = readme or ""
    lower = text.lower()

    checks = {
        "Project title": bool(
            re.search(r"^#\s+.+", text, re.MULTILINE)
        ),
        "Installation instructions": bool(
            re.search(r"installation|install|setup|getting started", lower)
        ),
        "Usage instructions": bool(
            re.search(r"usage|how to use|running|example", lower)
        ),
        "Features section": "features" in lower,
        "Technology stack": bool(
            re.search(r"tech stack|technologies|built with|prerequisites", lower)
        ),
        "Code example": "```" in text,
        "Contribution guidance": bool(
            re.search(r"contribut|pull request", lower)
        ),
        "License information": "license" in lower
    }

    score = round(sum(checks.values()) / len(checks) * 100)
    missing = [key for key, value in checks.items() if not value]

    return {
        "score": score,
        "status": (
            "Excellent" if score >= 85 else
            "Good" if score >= 65 else
            "Needs Improvement" if score >= 40 else
            "Incomplete"
        ),
        "checks": checks,
        "missing_sections": missing,
        "word_count": len(text.split())
    }


def get_recent_activity(owner, repo, branch):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "RepoLens"
    }

    result = {
        "commits": [],
        "contributors": [],
        "error": None
    }

    try:
        response = requests.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/commits",
            headers=headers,
            params={"per_page": 10, "sha": branch},
            timeout=15
        )

        if response.ok:
            result["commits"] = response.json()
        else:
            result["error"] = f"GitHub commits API returned HTTP {response.status_code}."

        response = requests.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/contributors",
            headers=headers,
            params={"per_page": 10},
            timeout=15
        )

        if response.ok:
            contributors = response.json()
            if isinstance(contributors, list):
                result["contributors"] = contributors

    except requests.RequestException as error:
        result["error"] = str(error)

    return result


def calculate_health_score(evaluation, quality, security, summary):
    score = 100

    for finding in security.get("findings", []):
        severity = finding.get("severity", "")
        score -= {"High": 8, "Medium": 4, "Low": 2}.get(severity, 0)

    for finding in quality.get("findings", []):
        if finding.get("severity") == "Low":
            score -= 1

    if summary.get("total_files", 0) < 3:
        score -= 5

    if evaluation.get("score", 0) >= 80:
        score += 5
    elif evaluation.get("score", 0) < 50:
        score -= 5

    return max(0, min(100, score))


def analyze_repository(owner, repo):
    info = get_repo_info(owner, repo)
    branch = info.get("default_branch", "main")

    files = get_repo_files(owner, repo, branch)
    readme = get_readme(owner, repo)
    summary = get_project_summary(files)

    evaluation = evaluate_repository(info, files, readme)
    quality = analyze_code_quality(files, owner, repo, branch)
    security = scan_security(files, owner, repo, branch)
    readme_report = analyze_readme(readme)
    activity = get_recent_activity(owner, repo, branch)

    health = calculate_health_score(
        evaluation, quality, security, summary
    )

    return {
        "info": info,
        "branch": branch,
        "files": files,
        "readme": readme,
        "summary": summary,
        "evaluation": evaluation,
        "quality": quality,
        "security": security,
        "readme_report": readme_report,
        "activity": activity,
        "health": health
    }


def count_severity(data, severity):
    return sum(
        1 for finding in data["security"].get("findings", [])
        if finding.get("severity") == severity
    )


def build_report(data):
    info = data["info"]

    return {
        "repository": info.get("full_name"),
        "description": info.get("description"),
        "health_score": data["health"],
        "evaluation": data["evaluation"],
        "readme_quality": data["readme_report"],
        "project_summary": data["summary"],
        "code_quality": data["quality"],
        "security": data["security"],
        "recent_activity": {
            "commits": data["activity"]["commits"],
            "contributors": data["activity"]["contributors"]
        }
    }


def show_dashboard(data):
    info = data["info"]
    evaluation = data["evaluation"]
    summary = data["summary"]
    readme = data["readme_report"]
    security = data["security"]
    activity = data["activity"]

    st.header("📊 Repository Insights Dashboard")

    st.markdown(
        f"### [{info.get('full_name', 'Repository')}]"
        f"(https://github.com/{info.get('full_name', '')})"
    )

    st.write(info.get("description") or "No repository description provided.")

    st.caption(
        f"Default branch: {data['branch']} | "
        f"Visibility: {'Private' if info.get('private') else 'Public'}"
    )

    st.divider()

    st.subheader("📌 Key Metrics")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("❤️ Health Score", f"{data['health']}/100")
    col2.metric("⭐ Stars", info.get("stargazers_count", 0))
    col3.metric("🍴 Forks", info.get("forks_count", 0))
    col4.metric("📁 Files", summary.get("total_files", 0))

    col1, col2, col3 = st.columns(3)
    col1.metric("🧠 Evaluation", f"{evaluation.get('score', 0)}/100")
    col2.metric("📝 README Quality", f"{readme['score']}/100")
    col3.metric("👥 Contributors Listed", len(activity["contributors"]))

    st.divider()

    st.subheader("📈 Project Health")

    st.progress(data["health"] / 100)

    if data["health"] >= 80:
        st.success("Strong automated health score. Continue maintaining the project.")
    elif data["health"] >= 60:
        st.info("The project has room for improvement.")
    else:
        st.warning("Review the findings and improve the project before relying on this score.")

    st.caption(
        "Health is a heuristic indicator, not a validated measure of software quality."
    )

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("📝 README Quality")
        st.progress(readme["score"] / 100)
        st.write(f"**Status:** {readme['status']}")
        st.write(f"**Word count:** {readme['word_count']}")

        for name, passed in readme["checks"].items():
            st.write(("✅ " if passed else "⚠️ ") + name)

        if readme["missing_sections"]:
            st.markdown("**Suggested improvements**")
            for section in readme["missing_sections"]:
                st.write(f"• Add or improve: {section}")

    with right:
        st.subheader("🔐 Security Findings")

        c1, c2, c3 = st.columns(3)
        c1.metric("High", count_severity(data, "High"))
        c2.metric("Medium", count_severity(data, "Medium"))
        c3.metric("Low", count_severity(data, "Low"))

        findings = security.get("findings", [])

        if findings:
            for finding in findings:
                st.warning(
                    f"{finding.get('severity', 'Unknown')}: "
                    f"{finding.get('issue', 'Finding detected')} "
                    f"({finding.get('file', 'file unknown')})"
                )
        else:
            st.success("No findings were reported by the current automated scan.")

    st.divider()

    st.subheader("💻 Technology Stack")

    languages = summary.get("languages", {})

    if languages:
        st.bar_chart(languages)
    else:
        st.info("No language statistics are available.")

    st.divider()

    st.subheader("🧹 Code Quality")

    findings = data["quality"].get("findings", [])
    st.write(f"**Files checked:** {data['quality'].get('checked_files', 0)}")

    if findings:
        for finding in findings:
            st.write(
                f"• **{finding.get('severity', 'Unknown')}** — "
                f"{finding.get('issue', 'Issue detected')} "
                f"({finding.get('file', 'unknown file')})"
            )
    else:
        st.success("No code quality findings were reported.")

    st.divider()

    st.subheader("📈 Recent GitHub Activity")

    c1, c2 = st.columns(2)
    c1.metric("Recent commits retrieved", len(activity["commits"]))
    c2.metric("Contributors listed", len(activity["contributors"]))

    st.caption(
        "GitHub API results are limited to the latest 10 commits and up to "
        "10 listed contributors. These are not lifetime totals."
    )

    if activity["error"]:
        st.warning(activity["error"])

    with st.expander("📝 Recent Commits", expanded=True):
        if activity["commits"]:
            for commit in activity["commits"]:
                details = commit.get("commit", {})
                message = details.get("message", "No message").split("\n")[0]
                author = details.get("author") or {}

                st.markdown(
                    f"**[{message}]({commit.get('html_url', '#')})**"
                )
                st.caption(
                    f"{author.get('name', 'Unknown author')} · "
                    f"{author.get('date', 'Date unavailable')}"
                )
        else:
            st.info("No recent commits are available.")

    with st.expander("👥 Contributors"):
        if activity["contributors"]:
            for person in activity["contributors"]:
                st.markdown(
                    f"- [{person.get('login', 'Unknown')}]"
                    f"({person.get('html_url', '#')}) — "
                    f"{person.get('contributions', 0)} contributions"
                )
        else:
            st.info("No contributor data is available.")

    st.divider()

    st.subheader("🧠 Evaluation Summary")

    st.write("**Strengths**")
    for item in evaluation.get("strengths", []):
        st.write(f"• {item}")

    st.write("**Weaknesses**")
    for item in evaluation.get("weaknesses", []):
        st.write(f"• {item}")

    st.write("**Suggestions**")
    for item in evaluation.get("suggestions", []):
        st.write(f"• {item}")

    st.divider()

    st.subheader("📖 README Preview")

    if data["readme"]:
        st.markdown(data["readme"][:6000])
    else:
        st.info("This repository does not have a README.")

    st.divider()

    st.subheader("📥 Export Insights")

    report = build_report(data)
    filename = info.get("name", "repository")

    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            "Download JSON Report",
            data=json.dumps(report, indent=2),
            file_name=f"{filename}-insights.json",
            mime="application/json"
        )

    with col2:
        text_report = (
            f"RepoLens Insights Report\n"
            f"Repository: {info.get('full_name')}\n"
            f"Health Score: {data['health']}/100\n"
            f"Evaluation Score: {evaluation.get('score', 0)}/100\n"
            f"README Score: {readme['score']}/100\n"
            f"Stars: {info.get('stargazers_count', 0)}\n"
            f"Forks: {info.get('forks_count', 0)}\n"
            f"Recent commits retrieved: {len(activity['commits'])}\n"
            f"Contributors listed: {len(activity['contributors'])}\n"
        )

        st.download_button(
            "Download Text Report",
            data=text_report,
            file_name=f"{filename}-insights.txt",
            mime="text/plain"
        )


st.title("🔍 RepoLens")
st.caption("Repository Insights Dashboard | Analyze. Evaluate. Improve.")

tab1, tab2 = st.tabs(["📊 Repository Insights", "⚔️ Compare Repositories"])

with tab1:
    url = st.text_input(
        "GitHub Repository URL",
        placeholder="https://github.com/username/repository"
    )

    if st.button("🚀 Generate Insights", type="primary"):
        owner, repo = parse_github_url(url)

        if not owner or not repo:
            st.error("Enter a valid GitHub repository URL.")
        else:
            try:
                with st.spinner("Generating repository insights..."):
                    result = analyze_repository(owner, repo)

                st.success("Repository insights generated!")
                show_dashboard(result)

            except Exception as error:
                st.error(f"Analysis failed: {error}")


with tab2:
    st.subheader("⚔️ Compare Two Repositories")

    col1, col2 = st.columns(2)

    with col1:
        url_a = st.text_input(
            "Repository A",
            placeholder="https://github.com/user/project-a"
        )

    with col2:
        url_b = st.text_input(
            "Repository B",
            placeholder="https://github.com/user/project-b"
        )

    if st.button("Compare Projects", type="primary"):
        owner_a, repo_a = parse_github_url(url_a)
        owner_b, repo_b = parse_github_url(url_b)

        if not owner_a or not repo_a or not owner_b or not repo_b:
            st.error("Enter valid URLs for both repositories.")
        else:
            try:
                with st.spinner("Analyzing both repositories..."):
                    a = analyze_repository(owner_a, repo_a)
                    b = analyze_repository(owner_b, repo_b)

                score_a = a["health"]
                score_b = b["health"]

                if score_a > score_b:
                    st.success(f"{repo_a} has the higher health score.")
                elif score_b > score_a:
                    st.success(f"{repo_b} has the higher health score.")
                else:
                    st.info("Both repositories have equal health scores.")

                st.table({
                    "Metric": [
                        "Health Score",
                        "Evaluation Score",
                        "README Quality",
                        "Stars",
                        "Forks",
                        "Files",
                        "Recent Commits Retrieved",
                        "Contributors Listed",
                        "High Security Findings",
                        "Medium Security Findings",
                        "Low Security Findings"
                    ],
                    repo_a: [
                        score_a,
                        a["evaluation"].get("score", 0),
                        a["readme_report"]["score"],
                        a["info"].get("stargazers_count", 0),
                        a["info"].get("forks_count", 0),
                        a["summary"].get("total_files", 0),
                        len(a["activity"]["commits"]),
                        len(a["activity"]["contributors"]),
                        count_severity(a, "High"),
                        count_severity(a, "Medium"),
                        count_severity(a, "Low")
                    ],
                    repo_b: [
                        score_b,
                        b["evaluation"].get("score", 0),
                        b["readme_report"]["score"],
                        b["info"].get("stargazers_count", 0),
                        b["info"].get("forks_count", 0),
                        b["summary"].get("total_files", 0),
                        len(b["activity"]["commits"]),
                        len(b["activity"]["contributors"]),
                        count_severity(b, "High"),
                        count_severity(b, "Medium"),
                        count_severity(b, "Low")
                    ]
                })

                comparison = {
                    "repository_a": build_report(a),
                    "repository_b": build_report(b),
                    "higher_health_score": (
                        repo_a if score_a > score_b else
                        repo_b if score_b > score_a else "Tie"
                    )
                }

                st.download_button(
                    "📥 Download Comparison JSON",
                    data=json.dumps(comparison, indent=2),
                    file_name="repolens-comparison.json",
                    mime="application/json"
                )

            except Exception as error:
                st.error(f"Comparison failed: {error}")


st.divider()
st.caption(
    "RepoLens provides automated rule-based insights. Scores and security "
    "findings are estimates, not guarantees or a professional audit."
)
