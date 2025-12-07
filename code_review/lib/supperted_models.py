from enum import Enum


class SupportedModel(str, Enum):
    OPEN_AI = "open-ai"
    QWEN3 = "qwen3"
    QWEN_25 = "qwen2.5"

    @property
    def openrouter_id(self) -> str:
        return {
            SupportedModel.OPEN_AI: "openai/gpt-oss-20b:free",
            SupportedModel.QWEN3: "qwen/qwen3-coder:free",
            SupportedModel.QWEN_25: "qwen/qwen-2.5-coder-32b-instruct:free",
        }[self]