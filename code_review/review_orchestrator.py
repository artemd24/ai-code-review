import json

from code_review.lib.diff_splitter import split_diff
from code_review.lib.prompt_builder import PromptBuilder


class ReviewOrchestrator:
    def __init__(
        self,
        adapter,
        llm_manager,
        prompt_builder: PromptBuilder,
        max_diff_tokens: int,
    ):
        self.adapter = adapter
        self.llm = llm_manager
        self.prompt_builder = prompt_builder
        self.max_diff_tokens = max_diff_tokens

    def run(self, context: dict):
        diff = self.adapter.get_diff(context)

        chunks = split_diff(diff, self.max_diff_tokens)

        merged_comments: list = []
        summary_parts: list[str] = []

        for idx, chunk in enumerate(chunks):
            batch = (idx + 1, len(chunks)) if len(chunks) > 1 else None
            prompt = self.prompt_builder.get_prompt(chunk, batch=batch)
            response = self.llm.get_response(prompt)
            merged_comments.extend(response.get("comments", []))
            part = response.get("summary", "").strip()
            if part:
                if len(chunks) > 1:
                    summary_parts.append(f"### Часть {idx + 1} / {len(chunks)}\n\n{part}")
                else:
                    summary_parts.append(part)

        for comment in merged_comments:
            self.adapter.post_comment(comment)

        final_summary = (
            "\n\n---\n\n".join(summary_parts)
            if summary_parts
            else "_Нет текста summary от модели._"
        )
        self.adapter.post_summary(final_summary)

    def _parse_response(self, response: str) -> dict:
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"LLM вернул невалидный JSON:\n{response}"
            ) from e

        if "comments" not in parsed or "summary" not in parsed:
            raise RuntimeError("JSON не содержит обязательных полей")

        return parsed
