import os

import requests


class GitLabAdapter:
    def get_diff(self, project_id: str, mr_iid: str, token: str) -> str:
        """Получает diff merge request через GitLab API."""
        api_url = f"{os.getenv('CI_SERVER_URL')}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/changes"
        headers = {"PRIVATE-TOKEN": token}
        resp = requests.get(api_url, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"Ошибка GitLab API: {resp.status_code} - {resp.text}")

        data = resp.json()
        diff_text = ""
        for change in data.get("changes", []):
            old_path = change.get("old_path", "")
            new_path = change.get("new_path", "")
            diff_text += f"--- {old_path}\n+++ {new_path}\n{change['diff']}\n"

        return diff_text.strip()