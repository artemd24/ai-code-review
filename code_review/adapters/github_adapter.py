import requests

from code_review.adapters.common_adapter import CommonAdapter


class GitHubAdapter(CommonAdapter):
    def __init__(self):
        self._comments_url = None
        self._headers = None

    def get_diff(self, context: dict) -> str:
        repo = context["repo"]
        pr_number = context["pr_number"]
        token = context["token"]

        api_base = "https://api.github.com"
        diff_url = f"{api_base}/repos/{repo}/pulls/{pr_number}"
        files_url = f"{diff_url}/files"
        self._comments_url = f"{diff_url}/comments"

        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
        }

        resp = requests.get(files_url, headers=self._headers)
        if resp.status_code != 200:
            raise RuntimeError(f"GitHub API error: {resp.text}")

        diff_chunks = []
        for file in resp.json():
            patch = file.get("patch")
            if patch:
                diff_chunks.append(f"--- {file['filename']}\n{patch}")

        return "\n".join(diff_chunks)

    def post_comment(self, comment: str) -> None:
        requests.post(
            self._comments_url,
            headers=self._headers,
            json={"body": comment},
        )

    def post_summary(self, summary: str) -> None:
        self.post_comment(f"## Summary\n\n{summary}")
