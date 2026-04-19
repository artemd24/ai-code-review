import json
from unittest.mock import Mock, patch

import pytest

from code_review.adapters.github_adapter import GitHubAdapter


@pytest.fixture
def github_context():
    return {
        "repo": "test-owner/test-repo",
        "pr_number": 42,
        "token": "fake-token",
    }


class TestGitHubAdapter:

    def test_get_diff_success(self, github_context):
        adapter = GitHubAdapter()
        mock_files_response = [
            {"filename": "file1.py", "patch": "@@ -1 +1 @@\n-old\n+new"},
            {"filename": "file2.py", "patch": "@@ -10 +10 @@\n-old2\n+new2"},
        ]
        mock_pr_response = {
            "base": {"sha": "base-sha-123"},
            "head": {"sha": "head-sha-456"},
        }

        with patch("requests.get") as mock_get:
            mock_get.side_effect = [
                Mock(status_code=200, json=lambda: mock_files_response),
                Mock(status_code=200, json=lambda: mock_pr_response),
            ]

            diff = adapter.get_diff(github_context)

        expected_diff = (
            "--- file1.py\n@@ -1 +1 @@\n-old\n+new\n"
            "--- file2.py\n@@ -10 +10 @@\n-old2\n+new2"
        )
        assert diff == expected_diff

        assert adapter._reviews_url == (
            "https://api.github.com/repos/test-owner/test-repo/pulls/42/reviews"
        )
        assert adapter._pull_review_comments_url == (
            "https://api.github.com/repos/test-owner/test-repo/pulls/42/comments"
        )
        assert adapter._issue_comments_url == (
            "https://api.github.com/repos/test-owner/test-repo/issues/42/comments"
        )
        assert adapter._headers["Authorization"] == "Bearer fake-token"
        assert adapter.base_sha == "base-sha-123"
        assert adapter.head_sha == "head-sha-456"

        assert mock_get.call_count == 2
        files_call = mock_get.call_args_list[0]
        assert files_call[0][0] == (
            "https://api.github.com/repos/test-owner/test-repo/pulls/42/files"
        )
        assert files_call[1]["params"] == {"per_page": 100, "page": 1}
        pr_call_args = mock_get.call_args_list[1][0][0]
        assert pr_call_args == (
            "https://api.github.com/repos/test-owner/test-repo/pulls/42"
        )

    def test_get_diff_requires_token(self):
        adapter = GitHubAdapter()
        with pytest.raises(RuntimeError, match="--token"):
            adapter.get_diff({"repo": "o/r", "pr_number": 1, "token": ""})

    def test_get_diff_files_error(self, github_context):
        adapter = GitHubAdapter()
        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=404, text="Not Found")
            with pytest.raises(RuntimeError, match="GitHub API error: Not Found"):
                adapter.get_diff(github_context)

    def test_get_diff_pr_data_error(self, github_context):
        adapter = GitHubAdapter()
        mock_files_response = [{"filename": "f.py", "patch": "..."}]
        with patch("requests.get") as mock_get:
            mock_get.side_effect = [
                Mock(status_code=200, json=lambda: mock_files_response),
                Mock(status_code=403, text="Forbidden"),
            ]
            with pytest.raises(RuntimeError, match="Ошибка GitHub API: 403 - Forbidden"):
                adapter.get_diff(github_context)

    def test_post_comment_inline_success(self):
        adapter = GitHubAdapter()
        adapter._headers = {
            "Authorization": "Bearer token",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }
        adapter._pull_review_comments_url = (
            "https://api.github.com/repos/owner/repo/pulls/42/comments"
        )
        adapter._issue_comments_url = (
            "https://api.github.com/repos/owner/repo/issues/42/comments"
        )
        adapter.head_sha = "head-sha-456"

        comment = {
            "comment": "This is a review",
            "suggestion": "print('hello')",
            "file": "src/main.py",
            "line": 10,
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value = Mock(status_code=201)
            adapter.post_comment(comment)

        expected_payload = {
            "body": "### 💬 Code Review\nThis is a review\n\n```diff\nprint('hello')\n```",
            "commit_id": "head-sha-456",
            "path": "src/main.py",
            "line": 10,
            "side": "RIGHT",
        }
        mock_post.assert_called_once_with(
            "https://api.github.com/repos/owner/repo/pulls/42/comments",
            headers=adapter._headers,
            data=json.dumps(expected_payload),
        )

    def test_post_comment_general_as_issue_comment(self):
        adapter = GitHubAdapter()
        adapter._headers = {
            "Authorization": "Bearer token",
            "Content-Type": "application/json",
        }
        adapter._pull_review_comments_url = (
            "https://api.github.com/repos/owner/repo/pulls/42/comments"
        )
        adapter._issue_comments_url = (
            "https://api.github.com/repos/owner/repo/issues/42/comments"
        )
        adapter.head_sha = "head-sha-456"

        comment = {
            "comment": "Overall note",
            "file": "src/main.py",
            "line": 0,
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value = Mock(status_code=201)
            adapter.post_comment(comment)

        expected_body = "`src/main.py`\n\n### 💬 Code Review\nOverall note"
        mock_post.assert_called_once_with(
            "https://api.github.com/repos/owner/repo/issues/42/comments",
            headers=adapter._headers,
            data=json.dumps({"body": expected_body}),
        )

    def test_post_comment_failure(self):
        adapter = GitHubAdapter()
        adapter._headers = {"Authorization": "Bearer t"}
        adapter._pull_review_comments_url = "https://api.github.com/repos/o/r/pulls/1/comments"
        adapter._issue_comments_url = "https://api.github.com/repos/o/r/issues/1/comments"
        adapter.head_sha = "sha"

        comment = {"comment": "x", "file": "f.py", "line": 1}
        with patch("requests.post") as mock_post:
            mock_post.return_value = Mock(status_code=500, text="Internal Server Error")
            with pytest.raises(RuntimeError, match="GitHub comment error: 500"):
                adapter.post_comment(comment)

    def test_post_summary_success(self):
        adapter = GitHubAdapter()
        adapter._headers = {
            "Authorization": "Bearer token",
            "Content-Type": "application/json",
        }
        adapter._reviews_url = "https://api.github.com/repos/owner/repo/pulls/42/reviews"
        adapter.head_sha = "abc123"

        summary_text = "Overall review looks good."
        with patch("requests.post") as mock_post:
            mock_post.return_value = Mock(status_code=200)
            adapter.post_summary(summary_text)

        expected_payload = {
            "body": "## 🤖 AI Code Review Summary\n\nOverall review looks good.",
            "event": "COMMENT",
            "commit_id": "abc123",
        }
        mock_post.assert_called_once_with(
            "https://api.github.com/repos/owner/repo/pulls/42/reviews",
            headers=adapter._headers,
            data=json.dumps(expected_payload),
        )
