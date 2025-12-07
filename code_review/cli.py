import argparse

from code_review.lib.prompt_builder import PromptAdvancementLevel
from code_review.lib.supperted_models import SupportedModel


def parse_args():
    parser = argparse.ArgumentParser("LLM Code Review")

    parser.add_argument("--adapter", required=True, choices=["local", "gitlab", "github"])
    parser.add_argument("--level", default="FULL",
                        choices=[l.value for l in PromptAdvancementLevel])
    parser.add_argument(
        "--model",
        required=True,
        choices=[m.value for m in SupportedModel],
    )
    parser.add_argument("--api-key", required=True)

    # local
    parser.add_argument("--source")
    parser.add_argument("--target")
    parser.add_argument("--output", default="review.md")

    # gitlab
    parser.add_argument("--url")
    parser.add_argument("--project-id")
    parser.add_argument("--mr-iid")

    # github
    parser.add_argument("--repo")
    parser.add_argument("--pr", type=int)

    parser.add_argument("--token")

    return parser.parse_args()
