import json

import requests


class GitHubAdapter:
    def __init__(self):
        self._reviews_url = None
        self._headers = None
        self.base_sha = None
        self.head_sha = None

    def _get_pr_data(self, repo: str, pr_number: str, token: str) -> dict:
        api_base = "https://api.github.com"
        pr_url = f"{api_base}/repos/{repo}/pulls/{pr_number}"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}
        resp = requests.get(pr_url, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"Ошибка GitHub API: {resp.status_code} - {resp.text}")
        return resp.json()

    def get_diff(self, context: dict) -> str:
        repo = context["repo"]
        pr_number = context["pr_number"]
        token = context["token"]

        api_base = "https://api.github.com"
        files_url = f"{api_base}/repos/{repo}/pulls/{pr_number}/files"
        pr_url = f"{api_base}/repos/{repo}/pulls/{pr_number}"
        self._reviews_url = f"{api_base}/repos/{repo}/pulls/{pr_number}/reviews"

        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }

        resp = requests.get(files_url, headers=self._headers)
        if resp.status_code != 200:
            raise RuntimeError(f"GitHub API error: {resp.text}")

        data = resp.json()
        diffs = []
        for file in data:
            patch = file.get("patch")
            if patch:
                diffs.append(f"--- {file['filename']}\n{patch}")

        pr_data = self._get_pr_data(repo, pr_number, token)
        self.base_sha = pr_data["base"]["sha"]
        self.head_sha = pr_data["head"]["sha"]

        return "\n".join(diffs)

    def post_comment(self, comment) -> None:
        # Markdown формат комментария (по аналогии с GitLab)
        print(f"Comment={comment}")

        body = f"### 💬 Code Review\n{comment['comment']}"
        if "suggestion" in comment and comment["suggestion"]:
            body += f"\n\n```diff\n{comment['suggestion']}\n```"

        payload = {
            "commit_id": self.head_sha,
            "comments": [{
                "path": comment["file"],
                "position": comment.get("position", comment["line"]),
                "body": body,
                "line": comment["line"],
                "side": "RIGHT"
            }]
        }

        resp = requests.post(self._reviews_url, headers=self._headers, data=json.dumps(payload))
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"GitHub comment error: {resp.status_code} {resp.text}")

    def post_summary(self, summary: str) -> None:
        payload = {"body": f"## 🤖 AI Code Review Summary\n\n{summary}", "event": "COMMENT"}
        resp = requests.post(self._reviews_url, headers=self._headers, data=json.dumps(payload))
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"GitHub summary error: {resp.status_code} {resp.text}")
