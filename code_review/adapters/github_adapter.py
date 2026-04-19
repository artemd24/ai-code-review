import json

import requests


class GitHubAdapter:
    """Публикация review на GitHub Pull Request через REST API v3."""

    def __init__(self):
        self.repo = None
        self.pr_number = None
        self._reviews_url = None
        self._pull_review_comments_url = None
        self._issue_comments_url = None
        self._headers = None
        self.base_sha = None
        self.head_sha = None

    def _get_pr_data(self, repo: str, pr_number, token: str) -> dict:
        api_base = "https://api.github.com"
        pr_url = f"{api_base}/repos/{repo}/pulls/{pr_number}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        resp = requests.get(pr_url, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"Ошибка GitHub API: {resp.status_code} - {resp.text}")
        return resp.json()

    def _list_pr_files(self, repo: str, pr_number, headers: dict) -> list:
        """Список файлов PR с пагинацией (GitHub по умолчанию отдаёт 30 записей)."""
        api_base = "https://api.github.com"
        files_url = f"{api_base}/repos/{repo}/pulls/{pr_number}/files"
        all_files: list = []
        page = 1
        per_page = 100
        while True:
            resp = requests.get(
                files_url,
                headers=headers,
                params={"per_page": per_page, "page": page},
            )
            if resp.status_code != 200:
                raise RuntimeError(f"GitHub API error: {resp.text}")
            batch = resp.json()
            if not batch:
                break
            chunk = batch if isinstance(batch, list) else batch.get("files", [])
            all_files.extend(chunk)
            if len(chunk) < per_page:
                break
            page += 1
        return all_files

    def get_diff(self, context: dict) -> str:
        repo = context["repo"].strip().replace(" ", "")
        pr_number = context["pr_number"]
        token = context.get("token") or ""
        if not token:
            raise RuntimeError(
                "GitHub: нужен personal access token или fine-grained token "
                "(права repo для частного репозитория). Укажите --token."
            )

        self.repo = repo
        self.pr_number = int(pr_number) if not isinstance(pr_number, int) else pr_number

        api_base = "https://api.github.com"
        self._reviews_url = f"{api_base}/repos/{repo}/pulls/{self.pr_number}/reviews"
        self._pull_review_comments_url = (
            f"{api_base}/repos/{repo}/pulls/{self.pr_number}/comments"
        )
        self._issue_comments_url = (
            f"{api_base}/repos/{repo}/issues/{self.pr_number}/comments"
        )

        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }

        files = self._list_pr_files(repo, self.pr_number, self._headers)
        diffs = []
        for file in files:
            patch = file.get("patch")
            if patch:
                diffs.append(f"--- {file['filename']}\n{patch}")

        pr_data = self._get_pr_data(repo, self.pr_number, token)
        self.base_sha = pr_data["base"]["sha"]
        self.head_sha = pr_data["head"]["sha"]

        return "\n".join(diffs)

    def _format_comment_body(self, comment: dict) -> str:
        body = f"### 💬 Code Review\n{comment['comment']}"
        if comment.get("suggestion"):
            body += f"\n\n```diff\n{comment['suggestion']}\n```"
        return body

    def post_comment(self, comment) -> None:
        """
        Строковые комментарии к строке: POST .../pulls/{n}/comments (line + side).
        Общий комментарий (line == 0 или без привязки): POST .../issues/{n}/comments.
        """
        body = self._format_comment_body(comment)
        path = comment.get("file") or ""
        line = int(comment.get("line", 0) or 0)

        if line > 0 and path and self.head_sha:
            payload = {
                "body": body,
                "commit_id": self.head_sha,
                "path": path,
                "line": line,
                "side": "RIGHT",
            }
            url = self._pull_review_comments_url
        else:
            payload = {"body": body}
            if path:
                payload["body"] = f"`{path}`\n\n{body}"
            url = self._issue_comments_url

        resp = requests.post(url, headers=self._headers, data=json.dumps(payload))
        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"GitHub comment error: {resp.status_code} {resp.text}"
            )

    def post_summary(self, summary: str) -> None:
        payload = {
            "body": f"## 🤖 AI Code Review Summary\n\n{summary}",
            "event": "COMMENT",
            "commit_id": self.head_sha,
        }
        resp = requests.post(self._reviews_url, headers=self._headers, data=json.dumps(payload))
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"GitHub summary error: {resp.status_code} {resp.text}")
