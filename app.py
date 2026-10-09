
import json
import re
import streamlit as st

from github_reader import get_repo_info, get_repo_files, get_readme
from analyzer import get_project_summary, analyze_code_quality, scan_security
from evaluator import evaluate_repository


st.set_page_config(page_title="RepoLens", page_icon="🔍", layout="wide")


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
        "Project title or description": bool(
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
        "Technology stack or prerequisites": bool(
            re.search(r"requirements|prerequisites|technologies|tech stack|built with", lower)
        ),
        "Code example": "```" in text,
        "Contribution guidance": bool(
            re.search(r"contribut|pull request|issues", lower)
        ),
        "License information": "license" in lower,
    }

    score = round(sum(checks.values()) / len(checks) * 100)
    missing = [name for name, passed in checks.items() if not passed]

    suggestions = {
        "Project title or description":
            "Add a project title and short description.",
        "Installation instructions":
            "Explain how to install dependencies and set up the project.",
        "Usage instructions":
            "Show users how to run and use the project.",
        "Features section":
            "Add a section listing the project's main features.",
        "Technology stack or prerequisites":
            "Document the technology stack and prerequisites.",
        "Code example":
            "Add a helpful command or code example.",
        "Contribution guidance":
            "Explain how users can report issues or contribute.",
        "License information":
            "Add license information if applicable.",
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
        "suggestions": [suggestions[item] for item in missing],
        "word_count": len(text.split()),
    }


def calculate_health_score(evaluation, quality, security, summary):
    score = 100

    for finding in security.get("findings", []):
        severity = finding.get("severity", "Low")
        score -= {"High": 8, "Medium": 4, "Low": 2}.get(severity, 0)

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


def get_health_status(score):
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 50:
        return "Needs Improvement"
    return "Poor"


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
        "health_score": health_score,
        "health_status": get_health_status(health_score),
    }


def security_count(data, severity):
    return sum(
        1 for finding in data["security"].get("findings", [])
        if finding.get("severity") == severity
    )


def get_languages(data):
    languages = data["summary"].get("languages", {})
    return ", ".join(languages.keys()) if languages else "None detected"


def create_evaluation_report(data):
    repo = data["repo_info"]
    summary = data["summary"]
    evaluation = data["evaluation"]
    quality = data["quality"]
    security = data["security"]
    readme = data["readme_analysis"]

    lines = [
        "=" * 60,
        "REPOLENS - REPOSITORY EVALUATION REPORT",
        "=" * 60,
        "",
        "REPOSITORY OVERVIEW",
        "-" * 60,
        f"Repository: {repo.get('full_name', 'Unknown')}",
        f"Description: {repo.get('description') or 'No description'}",
        f"Stars: {repo.get('stargazers_count', 0)}",
        f"Forks: {repo.get('forks_count', 0)}",
        f"Total files: {summary.get('total_files', 0)}",
        "",
        "REPOSITORY HEALTH",
        "-" * 60,
        f"Health score: {data['health_score']}/100",
        f"Health status: {data['health_status']}",
        "",
        "PROJECT EVALUATION",
        "-" * 60,
        f"Evaluation score: {evaluation.get('score', 0)}/100",
        f"Status: {evaluation.get('status', 'Not available')}",
        "",
        "SCORE BREAKDOWN",
    ]

    for category, score in evaluation.get("scores", {}).items():
        lines.append(f"- {category}: {score}/20")

    lines.extend([
        "",
        "TECHNOLOGY STACK",
        "-" * 60,
    ])

    for language, count in summary.get("languages", {}).items():
        lines.append(f"- {language}: {count} file(s)")

    lines.extend([
        "",
        "README QUALITY",
        "-" * 60,
        f"Documentation score: {readme['score']}/100",
        f"Status: {readme['status']}",
        f"Word count: {readme['word_count']}",
        "Missing checklist items: " +
        (", ".join(readme["missing_sections"]) or "None detected"),
        "",
        "README SUGGESTIONS",
    ])
    lines.extend("- " + item for item in readme["suggestions"])

    lines.extend(["", "CODE QUALITY", "-" * 60])
    lines.append(f"Files checked: {quality.get('checked_files', 0)}")
    for finding in quality.get("findings", []):
        lines.append(
            f"- [{finding.get('severity', 'Unknown')}] "
            f"{finding.get('issue', '')} ({finding.get('file', '')})"
        )
    if not quality.get("findings"):
        lines.append("No code quality findings detected.")

    lines.extend(["", "SECURITY", "-" * 60])
    for finding in security.get("findings", []):
        lines.append(
            f"- [{finding.get('severity', 'Unknown')}] "
            f"{finding.get('issue', '')} ({finding.get('file', '')})"
        )
    if not security.get("findings"):
        lines.append("No security findings detected.")

    for title, key in [
        ("STRENGTHS", "strengths"),
        ("WEAKNESSES", "weaknesses"),
        ("SUGGESTIONS", "suggestions"),
    ]:
        lines.extend(["", title, "-" * 60])
        items = evaluation.get(key, [])
        lines.extend("- " + str(item) for item in items)
        if not items:
            lines.append("None recorded.")

    lines.extend([
        "",
        "REPOLENS VERDICT",
        "-" * 60,
        f"{data['health_status']} repository health.",
        "Automated rule-based report; not a professional security audit.",
        "",
        "Generated by RepoLens",
        "=" * 60,
    ])
    return "\n".join(lines)


def show_repository(data):
    repo_info = data["repo_info"]
    summary = data["summary"]
    evaluation = data["evaluation"]
    quality = data["quality"]
    security = data["security"]
    readme = data["readme_analysis"]

    st.header("📊 Repository Overview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Files", summary.get("total_files", 0))
    c2.metric("⭐ Stars", repo_info.get("stargazers_count", 0))
    c3.metric("🍴 Forks", repo_info.get("forks_count", 0))
    c4.metric("❤️ Health", f"{data['health_score']}/100")
    st.write("**Description:**", repo_info.get("description") or "No description available.")

    st.divider()
    st.header("❤️ Repository Health")
    st.metric("Health status", data["health_status"])
    st.progress(data["health_score"] / 100)

    st.divider()
    st.header("🧠 Project Evaluation")
    st.metric("Evaluation score", f"{evaluation.get('score', 0)}/100")
    st.write("**Status:**", evaluation.get("status", "Not available"))

    for category, score in evaluation.get("scores", {}).items():
        st.write(f"**{category}:** {score}/20")
        st.progress(min(max(score / 20, 0), 1))

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
    st.metric("Source files checked", quality.get("checked_files", 0))
    quality_findings = quality.get("findings", [])
    if quality_findings:
        for finding in quality_findings:
            with st.expander(
                f"⚠️ {finding.get('severity', 'Unknown')}: "
                f"{finding.get('issue', 'Finding')}"
            ):
                st.write("**File:**", finding.get("file", "Unknown"))
    else:
        st.success("No code quality findings detected.")

    st.divider()
    st.header("🔐 Security Scan")
    c1, c2, c3 = st.columns(3)
    c1.metric("🔴 High", security_count(data, "High"))
    c2.metric("🟠 Medium", security_count(data, "Medium"))
    c3.metric("🟡 Low", security_count(data, "Low"))

    findings = security.get("findings", [])
    if findings:
        for finding in findings:
            with st.expander(
                f"🔎 {finding.get('severity', 'Unknown')}: "
                f"{finding.get('issue', 'Finding')}"
            ):
                st.write("**File:**", finding.get("file", "Unknown"))
    else:
        st.success("No security findings detected.")

    st.divider()
    st.header("📝 README Quality Analysis")
    c1, c2, c3 = st.columns(3)
    c1.metric("Documentation score", f"{readme['score']}/100")
    c2.metric("Documentation status", readme["status"])
    c3.metric("Word count", readme["word_count"])
    st.progress(readme["score"] / 100)

    with st.expander("README checklist", expanded=True):
        for name, passed in readme["checks"].items():
            st.write(("✅ " if passed else "⚠️ ") + name)

    if readme["suggestions"]:
        st.subheader("📌 README Improvement Suggestions")
        for item in readme["suggestions"]:
            st.write("• " + item)
    else:
        st.success("The README covers every item in this checklist.")

    st.divider()
    st.header("📖 README Preview")
    if data["readme"]:
        st.markdown(data["readme"][:5000])
        if len(data["readme"]) > 5000:
            st.caption("Preview limited to 5,000 characters.")
    else:
        st.warning("No README found.")

    st.divider()
    st.header("📥 Export Reports")
    report = {
        "repository": repo_info,
        "health_score": data["health_score"],
        "health_status": data["health_status"],
        "evaluation": evaluation,
        "readme_analysis": readme,
        "summary": summary,
        "code_quality": quality,
        "security": security,
    }

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "📄 Download Evaluation Report",
            data=create_evaluation_report(data),
            file_name=f"{repo_info.get('name', 'repository')}-repolens-report.txt",
            mime="text/plain",
        )
    with c2:
        st.download_button(
            "📋 Download JSON Report",
            data=json.dumps(report, indent=4),
            file_name=f"{repo_info.get('name', 'repository')}-repolens-report.json",
            mime="application/json",
        )


st.title("🔍 RepoLens")
st.caption("GitHub Repository Analyzer, Evaluator & Comparison Agent")
st.write(
    "Analyze repositories, evaluate project quality, identify potential "
    "security issues, assess README documentation, compare projects, "
    "and generate reports."
)

tab1, tab2 = st.tabs(["🔍 Analyze Repository", "⚔️ Compare Repositories"])

with tab1:
    repo_url = st.text_input(
        "GitHub Repository URL",
        placeholder="https://github.com/username/repository",
        key="single_repo",
    )

    if st.button("🚀 Analyze Repository", type="primary"):
        owner, repo = parse_github_url(repo_url)

        if not owner or not repo:
            st.error("Please enter a valid public GitHub repository URL.")
        else:
            try:
                with st.spinner("🔍 RepoLens is analyzing the repository..."):
                    data = analyze_repository(owner, repo)
                st.success("✅ Analysis completed!")
                show_repository(data)
            except Exception as error:
                st.error(f"❌ Analysis failed: {error}")


with tab2:
    st.header("⚔️ Compare Two GitHub Repositories")
    st.write("Compare two projects using the same RepoLens evaluation criteria.")

    col_a, col_b = st.columns(2)
    with col_a:
        repo_a_url = st.text_input(
            "Repository A",
            placeholder="https://github.com/user/project-a",
            key="repo_a",
        )
    with col_b:
        repo_b_url = st.text_input(
            "Repository B",
            placeholder="https://github.com/user/project-b",
            key="repo_b",
        )

    if st.button("⚔️ Compare Repositories", type="primary"):
        owner_a, repo_a = parse_github_url(repo_a_url)
        owner_b, repo_b = parse_github_url(repo_b_url)

        if not owner_a or not repo_a:
            st.error("Repository A URL is invalid.")
        elif not owner_b or not repo_b:
            st.error("Repository B URL is invalid.")
        else:
            try:
                with st.spinner("⚔️ Comparing repositories..."):
                    data_a = analyze_repository(owner_a, repo_a)
                    data_b = analyze_repository(owner_b, repo_b)

                score_a = data_a["health_score"]
                score_b = data_b["health_score"]

                st.success("✅ Comparison completed!")
                st.header("🏆 Comparison Result")

                if score_a > score_b:
                    st.success(
                        f"🏆 {repo_a} has stronger repository health "
                        f"by {score_a - score_b} points."
                    )
                elif score_b > score_a:
                    st.success(
                        f"🏆 {repo_b} has stronger repository health "
                        f"by {score_b - score_a} points."
                    )
                else:
                    st.info("🤝 Both repositories have equal health scores.")

                c1, c2 = st.columns(2)
                with c1:
                    st.subheader(repo_a)
                    st.metric("Health", f"{score_a}/100")
                    st.progress(score_a / 100)
                    st.metric("Evaluation", f"{data_a['evaluation'].get('score', 0)}/100")
                    st.metric("README quality", f"{data_a['readme_analysis']['score']}/100")
                with c2:
                    st.subheader(repo_b)
                    st.metric("Health", f"{score_b}/100")
                    st.progress(score_b / 100)
                    st.metric("Evaluation", f"{data_b['evaluation'].get('score', 0)}/100")
                    st.metric("README quality", f"{data_b['readme_analysis']['score']}/100")

                comparison = {
                    "Metric": [
                        "Health score",
                        "Health status",
                        "Evaluation score",
                        "README quality score",
                        "Files",
                        "Stars",
                        "Forks",
                        "Languages",
                        "High security findings",
                        "Medium security findings",
                        "Low security findings",
                    ],
                    repo_a: [
                        score_a,
                        data_a["health_status"],
                        data_a["evaluation"].get("score", 0),
                        data_a["readme_analysis"]["score"],
                        data_a["summary"].get("total_files", 0),
                        data_a["repo_info"].get("stargazers_count", 0),
                        data_a["repo_info"].get("forks_count", 0),
                        get_languages(data_a),
                        security_count(data_a, "High"),
                        security_count(data_a, "Medium"),
                        security_count(data_a, "Low"),
                    ],
                    repo_b: [
                        score_b,
                        data_b["health_status"],
                        data_b["evaluation"].get("score", 0),
                        data_b["readme_analysis"]["score"],
                        data_b["summary"].get("total_files", 0),
                        data_b["repo_info"].get("stargazers_count", 0),
                        data_b["repo_info"].get("forks_count", 0),
                        get_languages(data_b),
                        security_count(data_b, "High"),
                        security_count(data_b, "Medium"),
                        security_count(data_b, "Low"),
                    ],
                }

                st.subheader("📊 Detailed Comparison")
                st.table(comparison)

                st.divider()
                st.subheader("✅ Strengths")

                left, right = st.columns(2)
                with left:
                    st.write(f"**{repo_a}**")
                    for item in data_a["evaluation"].get("strengths", []):
                        st.write("• " + str(item))
                with right:
                    st.write(f"**{repo_b}**")
                    for item in data_b["evaluation"].get("strengths", []):
                        st.write("• " + str(item))

                st.subheader("🤖 Final Verdict")
                if score_a > score_b:
                    st.write(f"{repo_a} leads by {score_a - score_b} health points.")
                elif score_b > score_a:
                    st.write(f"{repo_b} leads by {score_b - score_a} health points.")
                else:
                    st.write("Both repositories have equal health scores.")

                comparison_report = {
                    "repository_a": {
                        "repository": data_a["repo_info"].get("full_name"),
                        "health_score": score_a,
                        "evaluation": data_a["evaluation"],
                        "readme_analysis": data_a["readme_analysis"],
                    },
                    "repository_b": {
                        "repository": data_b["repo_info"].get("full_name"),
                        "health_score": score_b,
                        "evaluation": data_b["evaluation"],
                        "readme_analysis": data_b["readme_analysis"],
                    },
                    "winner": (
                        repo_a if score_a > score_b else
                        repo_b if score_b > score_a else "Tie"
                    ),
                }

                st.download_button(
                    "📥 Download Comparison JSON",
                    data=json.dumps(comparison_report, indent=4),
                    file_name="repolens-comparison.json",
                    mime="application/json",
                )

            except Exception as error:
                st.error(f"❌ Comparison failed: {error}")


st.divider()
st.caption(
    "RepoLens uses automated rule-based analysis. Results are intended "
    "for project evaluation and do not replace professional security audits."
)
