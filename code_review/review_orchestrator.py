import json

from code_review.lib.prompt_builder import PromptBuilder


class ReviewOrchestrator:
    def __init__(
        self,
        adapter,
        llm_manager,
        prompt_builder: PromptBuilder,
    ):
        self.adapter = adapter
        self.llm = llm_manager
        self.prompt_builder = prompt_builder

    def run(self, context: dict):
        diff = self.adapter.get_diff(context)

        prompt = self.prompt_builder.get_prompt(diff)

        response = self.llm.get_response(prompt)

        for comment in response.get("comments", []):
            self.adapter.post_comment(comment)

        self.adapter.post_summary(response["summary"])

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
