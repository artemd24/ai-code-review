from pathlib import Path

from git import Repo

from code_review.adapters.common_adapter import CommonAdapter


class LocalAdapter(CommonAdapter):
    def __init__(self, output_file: str = "review.md"):
        self.output_file = Path(output_file)

    def get_diff(self, context: dict) -> str:
        repo = Repo(".")
        diff = repo.git.diff(
            f"{context['target_branch']}..{context['source_branch']}"
        )
        if not diff.strip():
            raise RuntimeError("Diff пуст")
        return diff

    def post_comment(self, comment: dict) -> None:
        with self.output_file.open("a", encoding="utf-8") as f:
            f.write(
                f"\n### {comment['file']}:{comment['line']}\n"
                f"{comment['comment']}\n\n"
            )
            if comment.get("suggestion"):
                f.write("```diff\n")
                f.write(comment["suggestion"])
                f.write("\n```\n")

    def post_summary(self, summary: str) -> None:
        with self.output_file.open("w", encoding="utf-8") as f:
            f.write("# Code Review Summary\n\n")
            f.write(summary + "\n")
