import requests

from code_review.adapters.common_adapter import CommonAdapter


class GitLabAdapter(CommonAdapter):
    def __init__(self):
        self._notes_url = None
        self._headers = None

    def get_diff(self, context: dict) -> str:
        project_id = context["project_id"]
        mr_iid = context["mr_iid"]
        token = context["token"]
        base_url = context["ci_server_url"].rstrip("/")

        self._headers = {"PRIVATE-TOKEN": token}
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

        return "\n".join(diffs)

    def post_comment(self, comment: str) -> None:
        resp = requests.post(
            self._notes_url,
            headers=self._headers,
            json={"body": comment},
        )

        if resp.status_code not in (200, 201):
            raise RuntimeError(f"GitLab comment error: {resp.status_code} {resp.text}")

    def post_summary(self, summary: str) -> None:
        self.post_comment(f"## Summary\n\n{summary}")
