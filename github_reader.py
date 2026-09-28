import base64
import requests


BASE_URL = "https://api.github.com"


def get_headers():
    return {
        "Accept": "application/vnd.github+json",
        "User-Agent": "RepoLens"
    }


def get_repo_info(owner, repo):
    url = f"{BASE_URL}/repos/{owner}/{repo}"

    response = requests.get(
        url,
        headers=get_headers(),
        timeout=10
    )

    if response.status_code != 200:
        raise Exception("Repository not found or inaccessible.")

    return response.json()


def get_repo_files(owner, repo, branch):
    url = f"{BASE_URL}/repos/{owner}/{repo}/git/trees/{branch}"

    response = requests.get(
        url,
        headers=get_headers(),
        params={"recursive": "1"},
        timeout=15
    )

    if response.status_code != 200:
        raise Exception("Could not read repository files.")

    return response.json().get("tree", [])


def get_readme(owner, repo):
    url = f"{BASE_URL}/repos/{owner}/{repo}/readme"

    response = requests.get(
        url,
        headers=get_headers(),
        timeout=10
    )

    if response.status_code != 200:
        return None

    data = response.json()

    try:
        return base64.b64decode(
            data["content"]
        ).decode("utf-8")

    except Exception:
        return None
