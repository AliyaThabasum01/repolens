

import json
import re
import requests
import streamlit as st

from github_reader import get_repo_info, get_repo_files, get_readme
from analyzer import get_project_summary, analyze_code_quality, scan_security
from evaluator import evaluate_repository

GITHUB_API = "https://api.github.com"


def github_headers():
    return {
        "Accept": "application/vnd.github+json",
        "User-Agent": "RepoLens"
    }


def parse_github_url(url):
    match = re.match(
        r"^https?://github\.com/([^/\s]+)/([^/\s#?]+)",
        url.strip()
    )
    if not match:
        return None, None
    return match.group(1), match.group(2).removesuffix(".git")


def get_activity(owner, repo, branch):
    result = {
        "commits": [],
        "contributors": [],
        "commit_count": 0,
        "contributor_count": 0,
        "error": None
    }

    try:
        commit_response = requests.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/commits",
            headers=github_headers(),
            params={"per_page": 10, "sha": branch},
            timeout=15
        )

        if commit_response.status_code == 200:
            commits = commit_response.json()
            result["commits"] = commits
            result["commit_count"] = len(commits)
        else:
            result["error"] = (
                f"Commit API returned HTTP {commit_response.status_code}."
            )

        contributor_response = requests.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/contributors",
            headers=github_headers(),
            params={"per_page": 10},
            timeout=15
        )

        if contributor_response.status_code == 200:
            contributors = contributor_response.json()
            if isinstance(contributors, list):
                result["contributors"] = contributors
                result["contributor_count"] = len(contributors)

    except requests.RequestException as error:
        result["error"] = f"Could not retrieve activity: {error}"

    return result


def analyze_readme(readme):
    text = readme or ""
    lower = text.lower()

    checks = {
        "Project title": bool(
            re.search(r"^#\s+.+", text, re.MULTILINE)
        ),
        "Installation instructions": bool(
            re.search(r"installation|install|getting started|setup", lower)
        ),
        "Usage instructions": bool(
            re.search(r"usage|how to use|running|example", lower)
        ),
        "Features section": bool(
            re.search(r"features|key features", lower)
        ),
        "Technology stack": bool(
            re.search(
                r"requirements|prerequisites|technologies|tech stack|built with",
                lower
            )
        ),
        "Code example": "```" in text,
        "Contribution guidance": bool(
            re.search(r"contribut|pull request|issues", lower)
        ),
        "License information": "license" in lower
    }

    score = round(sum(checks.values()) / len(checks) * 100)
    missing = [name for name, passed in checks.items() if not passed]

    suggestions_map = {
        "Project title": "Add a clear project title.",
        "Installation instructions": "Explain how to install and configure the project.",
        "Usage instructions": "Add steps showing how to run the project.",
        "Features section": "List the main project features.",
        "Technology stack": "Document the technologies and prerequisites.",
        "Code example": "Add a useful command or code example.",
        "Contribution guidance": "Explain how people can contribute or report issues.",
        "License information": "Document the license if applicable."
    }

    status = (
        "Excellent" if score >= 85 else
        "Good" if score >= 65 else
        "Needs Improvement" if score >= 40 else
        "Incomplete"
    )

    return {
        "score": score,
        "status": status,
        "checks": checks,
        "missing_sections": missing,
        "suggestions": [suggestions_map[item] for item in missing],
        "word_count": len(text.split())
    }


def calculate_health_score(evaluation, quality, security, summary):
    score = 100

    for finding in security.get("findings", []):
        score -= {
            "High": 8,
            "Medium": 4,
            "Low": 2
        }.get(finding.get("severity"), 0)

    for finding in quality.get("findings", []):
        if finding.get("severity") == "Low":
            score -= 1

    if not summary.get("config_files"):
        score -= 3

    if summary.get("total_files", 0) < 3:
        score -= 5

    evaluation_score = evaluation.get("score", 0)

    if evaluation_score >= 80:
        score += 5
    elif evaluation_score < 50:
        score -= 5

    return max(0, min(score, 100))


def analyze_repository(owner, repo):
    repo_info = get_repo_info(owner, repo)
    branch = repo_info.get("default_branch", "main")
    files = get_repo_files(owner, repo, branch)
    readme = get_readme(owner, repo)
    summary = get_project_summary(files)

    evaluation = evaluate_repository(repo_info, files, readme)
    quality = analyze_code_quality(files, owner, repo, branch)
    security = scan_security(files, owner, repo, branch)
    readme_analysis = analyze_readme(readme)
    activity = get_activity(owner, repo, branch)

    health_score = calculate_health_score(
        evaluation, quality, security, summary
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
        "readme_analysis": readme_analysis,
        "activity": activity,
        "health_score": health_score
    }


def security_count(data, severity):
    return sum(
        1 for finding in data["security"].get("findings", [])
        if finding.get("severity") == severity
    )


def get_languages(data):
    languages = data["summary"].get("languages", {})
    return ", ".join(languages.keys()) if languages else "None detected"


def create_report(data):
    repo = data["repo_info"]
    activity = data["activity"]
    evaluation = data["evaluation"]
    readme = data["readme_analysis"]

    lines = [
        "REPOLENS REPOSITORY REPORT",
        "=" * 45,
        f"Repository: {repo.get('full_name', 'Unknown')}",
        f"Description: {repo.get('description') or 'No description'}",
        f"Files: {data['summary'].get('total_files', 0)}",
        f"Stars: {repo.get('stargazers_count', 0)}",
        f"Forks: {repo.get('forks_count', 0)}",
        f"Health score: {data['health_score']}/100",
        f"Evaluation score: {evaluation.get('score', 0)}/100",
        "",
        "README QUALITY",
        "-" * 45,
        f"Score: {readme['score']}/100",
        f"Status: {readme['status']}",
        f"Word count: {readme['word_count']}",
        "Missing checklist items: " +
        (", ".join(readme["missing_sections"]) or "None"),
        "",
        "GITHUB ACTIVITY",
        "-" * 45,
        f"Recent commits retrieved: {activity['commit_count']}",
        f"Contributors retrieved: {activity['contributor_count']}",
        "",
        "RECENT COMMITS"
    ]

    for commit in activity["commits"]:
        message = commit.get("commit", {}).get("message", "")
        lines.append("- " + message.split("\n")[0])

    lines.extend(["", "CONTRIBUTORS"])
    for person in activity["contributors"]:
        lines.append(
            f"- {person.get('login', 'Unknown')}: "
            f"{person.get('contributions', 0)} contributions"
        )

    lines.extend(["", "README SUGGESTIONS"])
    lines.extend("- " + item for item in readme["suggestions"])

    lines.extend(["", "STRENGTHS"])
    lines.extend(
        "- " + str(item)
        for item in evaluation.get("strengths", [])
    )

    lines.extend(["", "WEAKNESSES"])
    lines.extend(
        "- " + str(item)
        for item in evaluation.get("weaknesses", [])
    )

    lines.extend([
        "",
        "Note: Activity counts show only the latest API results, "
        "not the complete project history.",
        "RepoLens uses automated rule-based checks."
    ])

    return "\n".join(lines)


def show_repository(data):
    repo = data["repo_info"]
    summary = data["summary"]
    evaluation = data["evaluation"]
    activity = data["activity"]
    readme = data["readme_analysis"]

    st.header("📊 Repository Overview")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Files", summary.get("total_files", 0))
    c2.metric("⭐ Stars", repo.get("stargazers_count", 0))
    c3.metric("🍴 Forks", repo.get("forks_count", 0))
    c4.metric("❤️ Health", f"{data['health_score']}/100")

    st.write("**Description:**", repo.get("description") or "No description available.")

    st.divider()
    st.header("🧠 Project Evaluation")
    st.metric("Evaluation score", f"{evaluation.get('score', 0)}/100")
    st.write("**Status:**", evaluation.get("status", "Not available"))

    left, right = st.columns(2)

    with left:
        st.subheader("✅ Strengths")
        for item in evaluation.get("strengths", []):
            st.write("• " + str(item))

    with right:
        st.subheader("⚠️ Weaknesses")
        for item in evaluation.get("weaknesses", []):
            st.write("• " + str(item))

    st.subheader("💡 Suggestions")
    for item in evaluation.get("suggestions", []):
        st.write("• " + str(item))

    st.divider()
    st.header("💻 Technology Stack")

    languages = summary.get("languages", {})
    if languages:
        for language, count in languages.items():
            st.write(f"**{language}:** {count} file(s)")
    else:
        st.info("No supported programming languages detected.")

    st.divider()
    st.header("🧹 Code Quality")
    quality = data["quality"]
    st.metric("Source files checked", quality.get("checked_files", 0))

    if quality.get("findings"):
        for finding in quality["findings"]:
            st.warning(
                f"{finding.get('severity', 'Unknown')}: "
                f"{finding.get('issue', '')} — "
                f"{finding.get('file', '')}"
            )
    else:
        st.success("No code quality findings detected.")

    st.divider()
    st.header("🔐 Security Scan")
    security = data["security"]

    c1, c2, c3 = st.columns(3)
    c1.metric("🔴 High", security_count(data, "High"))
    c2.metric("🟠 Medium", security_count(data, "Medium"))
    c3.metric("🟡 Low", security_count(data, "Low"))

    for finding in security.get("findings", []):
        st.warning(
            f"{finding.get('severity', 'Unknown')}: "
            f"{finding.get('issue', '')} — "
            f"{finding.get('file', '')}"
        )

    st.divider()
    st.header("📝 README Quality Analysis")

    c1, c2, c3 = st.columns(3)
    c1.metric("Documentation score", f"{readme['score']}/100")
    c2.metric("Status", readme["status"])
    c3.metric("Word count", readme["word_count"])
    st.progress(readme["score"] / 100)

    with st.expander("README checklist", expanded=True):
        for name, passed in readme["checks"].items():
            st.write(("✅ " if passed else "⚠️ ") + name)

    for suggestion in readme["suggestions"]:
        st.write("• " + suggestion)

    st.divider()
    st.header("📈 GitHub Activity Analyzer")

    c1, c2 = st.columns(2)
    c1.metric("Recent commits retrieved", activity["commit_count"])
    c2.metric("Contributors retrieved", activity["contributor_count"])

    st.caption(
        "This view displays up to 10 recent commits and up to 10 contributors. "
        "These are API result counts, not lifetime totals."
    )

    if activity["error"]:
        st.warning(activity["error"])

    st.subheader("📝 Recent Commits")
    if activity["commits"]:
        for commit in activity["commits"]:
            details = commit.get("commit", {})
            message = details.get("message", "No commit message").split("\n")[0]
            author = details.get("author") or {}
            date = author.get("date", "Date unavailable")
            url = commit.get("html_url", "")

            with st.expander(message[:120]):
                st.write("**Author:**", author.get("name", "Unknown"))
                st.write("**Date:**", date)
                if url:
                    st.markdown(f"[View commit]({url})")
    else:
        st.info("No recent commits were returned by GitHub.")

    st.subheader("👥 Contributors")
    if activity["contributors"]:
        for person in activity["contributors"]:
            login = person.get("login", "Unknown")
            contributions = person.get("contributions", 0)
            profile = person.get("html_url", "")
            if profile:
                st.markdown(
                    f"- [{login}]({profile}) — {contributions} contributions"
                )
            else:
                st.write(f"- {login} — {contributions} contributions")
    else:
        st.info("No contributor data was returned by GitHub.")

    st.divider()
    st.header("📖 README Preview")
    if data["readme"]:
        st.markdown(data["readme"][:5000])
    else:
        st.warning("No README found.")

    st.divider()
    st.header("📥 Export Reports")

    report = {
        "repository": repo,
        "health_score": data["health_score"],
        "evaluation": evaluation,
        "readme_analysis": readme,
        "summary": summary,
        "code_quality": quality,
        "security": security,
        "activity": {
            "recent_commits_retrieved": activity["commit_count"],
            "contributors_retrieved": activity["contributor_count"],
            "commits": activity["commits"],
            "contributors": activity["contributors"]
        }
    }

    c1, c2 = st.columns(2)

    with c1:
        st.download_button(
            "📄 Download Text Report",
            data=create_report(data),
            file_name=f"{repo.get('name', 'repository')}-repolens-report.txt",
            mime="text/plain"
        )

    with c2:
        st.download_button(
            "📋 Download JSON Report",
            data=json.dumps(report, indent=4),
            file_name=f"{repo.get('name', 'repository')}-repolens-report.json",
            mime="application/json"
        )


st.title("🔍 RepoLens")
st.caption("GitHub Repository Analyzer, Evaluator & Comparison Agent")
st.write(
    "Analyze GitHub projects, review documentation, inspect potential "
    "security findings, explore activity, and compare repositories."
)

tab1, tab2 = st.tabs(["🔍 Analyze Repository", "⚔️ Compare Repositories"])

with tab1:
    repo_url = st.text_input(
        "GitHub Repository URL",
        placeholder="https://github.com/username/repository"
    )

    if st.button("🚀 Analyze Repository", type="primary"):
        owner, repo = parse_github_url(repo_url)

        if not owner or not repo:
            st.error("Enter a valid public GitHub repository URL.")
        else:
            try:
                with st.spinner("RepoLens is analyzing the repository..."):
                    data = analyze_repository(owner, repo)

                st.success("Analysis completed!")
                show_repository(data)
            except Exception as error:
                st.error(f"Analysis failed: {error}")


with tab2:
    st.header("⚔️ Compare Two GitHub Repositories")

    col_a, col_b = st.columns(2)

    with col_a:
        url_a = st.text_input(
            "Repository A URL",
            placeholder="https://github.com/user/project-a"
        )

    with col_b:
        url_b = st.text_input(
            "Repository B URL",
            placeholder="https://github.com/user/project-b"
        )

    if st.button("⚔️ Compare Repositories", type="primary"):
        owner_a, repo_a = parse_github_url(url_a)
        owner_b, repo_b = parse_github_url(url_b)

        if not owner_a or not repo_a:
            st.error("Repository A URL is invalid.")
        elif not owner_b or not repo_b:
            st.error("Repository B URL is invalid.")
        else:
            try:
                with st.spinner("Comparing repositories..."):
                    data_a = analyze_repository(owner_a, repo_a)
                    data_b = analyze_repository(owner_b, repo_b)

                score_a = data_a["health_score"]
                score_b = data_b["health_score"]

                st.header("🏆 Comparison Result")

                if score_a > score_b:
                    st.success(f"{repo_a} leads by {score_a - score_b} health points.")
                elif score_b > score_a:
                    st.success(f"{repo_b} leads by {score_b - score_a} health points.")
                else:
                    st.info("Both repositories have equal health scores.")

                comparison = {
                    "Metric": [
                        "Health score",
                        "Evaluation score",
                        "README quality",
                        "Files",
                        "Stars",
                        "Forks",
                        "Languages",
                        "Recent commits retrieved",
                        "Contributors retrieved",
                        "High security findings",
                        "Medium security findings",
                        "Low security findings"
                    ],
                    repo_a: [
                        score_a,
                        data_a["evaluation"].get("score", 0),
                        data_a["readme_analysis"]["score"],
                        data_a["summary"].get("total_files", 0),
                        data_a["repo_info"].get("stargazers_count", 0),
                        data_a["repo_info"].get("forks_count", 0),
                        get_languages(data_a),
                        data_a["activity"]["commit_count"],
                        data_a["activity"]["contributor_count"],
                        security_count(data_a, "High"),
                        security_count(data_a, "Medium"),
                        security_count(data_a, "Low")
                    ],
                    repo_b: [
                        score_b,
                        data_b["evaluation"].get("score", 0),
                        data_b["readme_analysis"]["score"],
                        data_b["summary"].get("total_files", 0),
                        data_b["repo_info"].get("stargazers_count", 0),
                        data_b["repo_info"].get("forks_count", 0),
                        get_languages(data_b),
                        data_b["activity"]["commit_count"],
                        data_b["activity"]["contributor_count"],
                        security_count(data_b, "High"),
                        security_count(data_b, "Medium"),
                        security_count(data_b, "Low")
                    ]
                }

                st.subheader("📊 Detailed Comparison")
                st.table(comparison)

                comparison_report = {
                    "repository_a": {
                        "name": data_a["repo_info"].get("full_name"),
                        "health_score": score_a,
                        "evaluation": data_a["evaluation"],
                        "readme_analysis": data_a["readme_analysis"]
                    },
                    "repository_b": {
                        "name": data_b["repo_info"].get("full_name"),
                        "health_score": score_b,
                        "evaluation": data_b["evaluation"],
                        "readme_analysis": data_b["readme_analysis"]
                    },
                    "winner": (
                        repo_a if score_a > score_b else
                        repo_b if score_b > score_a else "Tie"
                    )
                }

                st.download_button(
                    "📥 Download Comparison JSON",
                    data=json.dumps(comparison_report, indent=4),
                    file_name="repolens-comparison.json",
                    mime="application/json"
                )

            except Exception as error:
                st.error(f"Comparison failed: {error}")


st.divider()
st.caption(
    "RepoLens uses automated rule-based analysis and GitHub's public API. "
    "Activity is a limited snapshot, not a complete historical count. "
    "Security results do not replace a professional security audit."
)
