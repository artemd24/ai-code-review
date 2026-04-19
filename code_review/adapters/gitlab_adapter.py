import json

import requests

from code_review.adapters.common_adapter import CommonAdapter


class GitLabAdapter(CommonAdapter):
    def __init__(self):
        self._notes_url = None
        self._headers = None

    def _get_mr_data(self, base_url: str, project_id: str, mr_iid: str, token: str) -> dict:
        """Получаем данные MR, включая diff_refs для inline-комментариев."""
        api_url = f"{base_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}"
        headers = {"PRIVATE-TOKEN": token}
        resp = requests.get(api_url, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"Ошибка GitLab API: {resp.status_code} - {resp.text}")
        return resp.json()

    def get_diff(self, context: dict) -> str:
        project_id = context["project_id"]
        mr_iid = context["mr_iid"]
        token = context["token"]
        base_url = context["ci_server_url"].rstrip("/")

        self._headers = {"PRIVATE-TOKEN": token, "Content-Type": "application/json"}
        changes_url = (
            f"{base_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/changes"
        )
        self._notes_url = (
            f"{base_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/notes"
        )

        resp = requests.get(changes_url, headers=self._headers)
        if resp.status_code != 200:
            raise RuntimeError(f"GitLab API error: {resp.text}")

        data = resp.json()
        diffs = []

        for change in data.get("changes", []):
            diffs.append(
                f"--- {change['old_path']}\n+++ {change['new_path']}\n{change['diff']}"
            )

        mr_data = self._get_mr_data(base_url, project_id, mr_iid, token)
        diff_refs = mr_data.get("diff_refs", {})
        self.base_sha = diff_refs.get("base_sha")
        self.start_sha = diff_refs.get("start_sha")
        self.head_sha = diff_refs.get("head_sha")

        return "\n".join(diffs)

    def post_comment(self, comment) -> None:
        # Markdown формат комментария
        print(f"Comment={comment}")

        body = f"### 💬 Code Review\n{comment['comment']}"
        if "suggestion" in comment and comment["suggestion"]:
            body += f"\n\n```diff\n{comment['suggestion']}\n```"

        payload = {
            "body": body,
            "position": {
                "position_type": "text",
                "base_sha": self.base_sha,
                "start_sha": self.start_sha,
                "head_sha": self.head_sha,
                "new_path": comment["file"],
                "new_line": comment["line"],
            },
        }

        resp = requests.post(
            self._notes_url,
            headers=self._headers,
            data=json.dumps(payload),
        )

        if resp.status_code not in (200, 201):
            raise RuntimeError(f"GitLab comment error: {resp.status_code} {resp.text}")

    def post_summary(self, summary: str) -> None:
        payload = {
            "body": f"## 🤖 AI Code Review Summary\n\n{summary}",
        }
        resp = requests.post(
            self._notes_url,
            headers=self._headers,
            data=json.dumps(payload),
        )
        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"GitLab summary error: {resp.status_code} {resp.text}"
            )
