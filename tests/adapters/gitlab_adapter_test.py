import json
from unittest.mock import Mock, patch

import pytest

from code_review.adapters.gitlab_adapter import GitLabAdapter


@pytest.fixture
def gitlab_context():
    return {
        "project_id": "123",
        "mr_iid": "5",
        "token": "fake-token",
        "ci_server_url": "https://gitlab.example.com"
    }


# ----------------------------------------------------------------------
# Тесты для GitLabAdapter (с unittest.mock.patch)
# ----------------------------------------------------------------------
class TestGitLabAdapter:

    def test_get_diff_success(self, gitlab_context):
        adapter = GitLabAdapter()
        changes_response = {
            "changes": [
                {
                    "old_path": "old.py",
                    "new_path": "new.py",
                    "diff": "@@ -1 +1 @@\n-old\n+new"
                }
            ]
        }
        mr_data_response = {
            "diff_refs": {
                "base_sha": "base-111",
                "start_sha": "start-222",
                "head_sha": "head-333"
            }
        }

        with patch("requests.get") as mock_get:
            mock_get.side_effect = [
                Mock(status_code=200, json=lambda: changes_response),
                Mock(status_code=200, json=lambda: mr_data_response)
            ]
            diff = adapter.get_diff(gitlab_context)

        expected_diff = "--- old.py\n+++ new.py\n@@ -1 +1 @@\n-old\n+new"
        assert diff == expected_diff

        assert adapter._notes_url == "https://gitlab.example.com/api/v4/projects/123/merge_requests/5/notes"
        assert adapter._headers == {
            "PRIVATE-TOKEN": "fake-token",
            "Content-Type": "application/json"
        }
        assert adapter.base_sha == "base-111"
        assert adapter.start_sha == "start-222"
        assert adapter.head_sha == "head-333"

        changes_call = mock_get.call_args_list[0][0][0]
        mr_data_call = mock_get.call_args_list[1][0][0]
        assert changes_call == "https://gitlab.example.com/api/v4/projects/123/merge_requests/5/changes"
        assert mr_data_call == "https://gitlab.example.com/api/v4/projects/123/merge_requests/5"

    def test_get_diff_changes_error(self, gitlab_context):
        adapter = GitLabAdapter()
        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=404, text="Not Found")
            with pytest.raises(RuntimeError, match="GitLab API error: Not Found"):
                adapter.get_diff(gitlab_context)

    def test_get_diff_mr_data_error(self, gitlab_context):
        adapter = GitLabAdapter()
        with patch("requests.get") as mock_get:
            mock_get.side_effect = [
                Mock(status_code=200, json=lambda: {"changes": []}),
                Mock(status_code=403, text="Forbidden")
            ]
            with pytest.raises(RuntimeError, match="Ошибка GitLab API: 403 - Forbidden"):
                adapter.get_diff(gitlab_context)

    def test_post_comment_success(self):
        adapter = GitLabAdapter()
        adapter._headers = {"PRIVATE-TOKEN": "token"}
        adapter._notes_url = "https://gitlab.example.com/api/v4/projects/123/merge_requests/5/notes"
        adapter.base_sha = "base-111"
        adapter.start_sha = "start-222"
        adapter.head_sha = "head-333"

        comment = {
            "comment": "Good catch",
            "suggestion": "fix = True",
            "file": "src/app.py",
            "line": 42
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value = Mock(status_code=201)
            adapter.post_comment(comment)

        expected_payload = {
            "body": "### 💬 Code Review\nGood catch\n\n```diff\nfix = True\n```",
            "position": {
                "position_type": "text",
                "base_sha": "base-111",
                "start_sha": "start-222",
                "head_sha": "head-333",
                "new_path": "src/app.py",
                "new_line": 42
            }
        }
        mock_post.assert_called_once_with(
            "https://gitlab.example.com/api/v4/projects/123/merge_requests/5/notes",
            headers={"PRIVATE-TOKEN": "token"},
            data=json.dumps(expected_payload)
        )

    def test_post_comment_failure(self):
        adapter = GitLabAdapter()
        adapter._headers = {}
        adapter._notes_url = "url"
        adapter.base_sha = adapter.start_sha = adapter.head_sha = "sha"

        comment = {"comment": "x", "file": "f", "line": 1}
        with patch("requests.post") as mock_post:
            mock_post.return_value = Mock(status_code=500, text="Internal Error")
            with pytest.raises(RuntimeError, match="GitLab comment error: 500 Internal Error"):
                adapter.post_comment(comment)

    def test_post_summary_success(self):
        adapter = GitLabAdapter()
        adapter._headers = {"PRIVATE-TOKEN": "token"}
        adapter._notes_url = (
            "https://gitlab.example.com/api/v4/projects/123/merge_requests/5/notes"
        )

        summary_text = "Overall good."
        with patch("requests.post") as mock_post:
            mock_post.return_value = Mock(status_code=201)
            adapter.post_summary(summary_text)

        expected_payload = {
            "body": "## 🤖 AI Code Review Summary\n\nOverall good.",
        }
        mock_post.assert_called_once_with(
            "https://gitlab.example.com/api/v4/projects/123/merge_requests/5/notes",
            headers={"PRIVATE-TOKEN": "token"},
            data=json.dumps(expected_payload),
        )
