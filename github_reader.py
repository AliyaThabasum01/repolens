import requests


def get_repo_info(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}"

    response = requests.get(url, timeout=10)

    if response.status_code != 200:
        raise Exception("Repository not found.")

    return response.json()


def get_repo_files(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1"

    response = requests.get(url, timeout=10)

    if response.status_code != 200:
        raise Exception("Could not read repository files.")

    return response.json().get("tree", [])
