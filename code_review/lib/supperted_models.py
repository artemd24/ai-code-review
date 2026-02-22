from enum import Enum


class SupportedModel(str, Enum):
    OPEN_AI = "open-ai"
    QWEN3 = "qwen3"
    QWEN_25 = "qwen2.5"
    QWEN_35 = "qwen3.5"
    LLAMA_31 = "llama3.1"

    @property
    def openrouter_id(self) -> str:
        return {
            SupportedModel.OPEN_AI: "openai/gpt-oss-20b:free",
            SupportedModel.QWEN3: "qwen/qwen3-coder:free",
            SupportedModel.QWEN_25: "qwen/qwen2.5-coder-7b-instruct",
            SupportedModel.QWEN_35: "qwen/qwen3.5-plus-02-15",
            SupportedModel.LLAMA_31: "nvidia/llama-3.1-nemotron-ultra-253b-v1"
        }[self]