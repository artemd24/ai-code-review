from unittest.mock import Mock, patch

import pytest

from code_review.adapters.local_adapter import LocalAdapter


@pytest.fixture
def local_context():
    return {
        "target_branch": "main",
        "source_branch": "feature"
    }


# ----------------------------------------------------------------------
# Тесты для LocalAdapter (с unittest.mock.patch)
# ----------------------------------------------------------------------
class TestLocalAdapter:

    def test_get_diff_success(self, local_context):
        adapter = LocalAdapter()
        with patch("code_review.adapters.local_adapter.Repo") as mock_repo_class:
            mock_repo = Mock()
            mock_repo.git.diff.return_value = "diff --git a/file b/file\n..."
            mock_repo_class.return_value = mock_repo

            diff = adapter.get_diff(local_context)

        assert diff == "diff --git a/file b/file\n..."
        mock_repo.git.diff.assert_called_once_with("main..feature")

    def test_get_diff_empty(self, local_context):
        adapter = LocalAdapter()
        with patch("code_review.adapters.local_adapter.Repo") as mock_repo_class:
            mock_repo = Mock()
            mock_repo.git.diff.return_value = "   \n"
            mock_repo_class.return_value = mock_repo

            with pytest.raises(RuntimeError, match="Diff пуст"):
                adapter.get_diff(local_context)

    def test_post_comment_appends_to_file(self, tmp_path):
        output_file = tmp_path / "review.md"
        adapter = LocalAdapter(output_file=str(output_file))

        comment = {
            "file": "src/module.py",
            "line": 15,
            "comment": "Consider renaming",
            "suggestion": "new_name = var"
        }

        adapter.post_comment(comment)

        content = output_file.read_text(encoding="utf-8")
        expected = (
            "\n### src/module.py:15\n"
            "Consider renaming\n\n"
            "```diff\n"
            "new_name = var\n"
            "```\n"
        )
        assert content == expected

        comment2 = {
            "file": "other.py",
            "line": 3,
            "comment": "LGTM",
            "suggestion": None
        }
        adapter.post_comment(comment2)

        content = output_file.read_text(encoding="utf-8")
        assert "### other.py:3" in content
        assert "LGTM" in content

    def test_post_summary_overwrites_file(self, tmp_path):
        output_file = tmp_path / "review.md"
        adapter = LocalAdapter(output_file=str(output_file))

        adapter.post_comment({"file": "a.py", "line": 1, "comment": "old", "suggestion": None})
        assert output_file.exists()

        summary = "All good!"
        adapter.post_summary(summary)

        content = output_file.read_text(encoding="utf-8")
        expected = "# Code Review Summary\n\nAll good!\n"
        assert content == expected

    def test_post_comment_no_suggestion(self, tmp_path):
        output_file = tmp_path / "review.md"
        adapter = LocalAdapter(output_file=str(output_file))

        comment = {
            "file": "f.py",
            "line": 7,
            "comment": "Just a note",
            "suggestion": None
        }
        adapter.post_comment(comment)

        content = output_file.read_text(encoding="utf-8")
        assert "```diff" not in content
        assert "Just a note" in content
