from enum import Enum


class SupportedModel(str, Enum):
    OPEN_AI = "open-ai"
    QWEN3 = "qwen3"
    QWEN_25 = "qwen2.5"
    QWEN_35 = "qwen3.5"
    LLAMA_31 = "llama3.1"
    NEMOTRON = "nemotron"
    GEMMA_4 = "gemma4"
    MINI_MAX = "mini_max"
    LIQUID = "liquid"

    @property
    def openrouter_id(self) -> str:
        return {
            SupportedModel.OPEN_AI: "openai/gpt-oss-20b:free",
            SupportedModel.QWEN3: "qwen/qwen3-coder:free",
            SupportedModel.QWEN_25: "qwen/qwen2.5-coder-7b-instruct",
            SupportedModel.QWEN_35: "qwen/qwen3.5-plus-02-15",
            SupportedModel.LLAMA_31: "nvidia/llama-3.1-nemotron-ultra-253b-v1",
            SupportedModel.NEMOTRON: "nvidia/nemotron-nano-12b-v2-vl:free",
            SupportedModel.GEMMA_4: "google/gemma-4-26b-a4b-it",
            SupportedModel.MINI_MAX: "minimax/minimax-m2.5:free",
            SupportedModel.LIQUID: "liquid/lfm-2.5-1.2b-thinking:free"
        }[self]

    @property
    def context_window_tokens(self) -> int:
        """Approximate context length from provider docs; used for diff batching."""
        return {
            SupportedModel.OPEN_AI: 128_000,
            SupportedModel.QWEN3: 128_000,
            SupportedModel.QWEN_25: 128_000,
            SupportedModel.QWEN_35: 128_000,
            SupportedModel.LLAMA_31: 128_000,
            SupportedModel.NEMOTRON: 128_000,
            SupportedModel.GEMMA_4: 128_000,
            SupportedModel.MINI_MAX: 128_000,
            SupportedModel.LIQUID: 128_000
        }[self]
