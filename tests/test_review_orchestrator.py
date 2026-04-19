from unittest.mock import Mock, patch

from code_review.lib.prompt_builder import PromptAdvancementLevel, PromptBuilder
from code_review.review_orchestrator import ReviewOrchestrator


def test_orchestrator_single_batch():
    adapter = Mock()
    adapter.get_diff.return_value = "small diff"

    llm = Mock()
    llm.get_response.return_value = {
        "comments": [{"file": "a.py", "line": 1, "comment": "ok", "suggestion": ""}],
        "summary": "LGTM",
    }

    pb = PromptBuilder(PromptAdvancementLevel.FULL)
    orch = ReviewOrchestrator(adapter, llm, pb, max_diff_tokens=50_000)
    orch.run({})

    adapter.get_diff.assert_called_once()
    llm.get_response.assert_called_once()
    adapter.post_comment.assert_called_once()
    adapter.post_summary.assert_called_once_with("LGTM")


def test_orchestrator_merges_batches():
    adapter = Mock()
    adapter.get_diff.return_value = "ignored"

    llm = Mock()
    llm.get_response.side_effect = [
        {"comments": [{"file": "a.py", "line": 1, "comment": "c1", "suggestion": ""}], "summary": "s1"},
        {"comments": [{"file": "b.py", "line": 2, "comment": "c2", "suggestion": ""}], "summary": "s2"},
    ]

    pb = PromptBuilder(PromptAdvancementLevel.FULL)
    with patch(
        "code_review.review_orchestrator.split_diff",
        return_value=["diff-a", "diff-b"],
    ):
        orch = ReviewOrchestrator(adapter, llm, pb, max_diff_tokens=100)
        orch.run({})

    assert llm.get_response.call_count == 2
    assert adapter.post_comment.call_count == 2
    summary = adapter.post_summary.call_args[0][0]
    assert "Часть" in summary
    assert "s1" in summary and "s2" in summary
