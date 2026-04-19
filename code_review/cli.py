import argparse
import sys
from pathlib import Path

from code_review.lib.prompt_builder import PromptAdvancementLevel
from code_review.lib.supperted_models import SupportedModel


def parse_args(argv=None):
    argv = argv if argv is not None else sys.argv[1:]

    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--config", type=Path, default=None)
    pre_args, remaining = pre.parse_known_args(argv)

    defaults = {}
    if pre_args.config:
        from code_review.config_loader import load_config

        raw = load_config(pre_args.config)
        allowed = {
            "adapter",
            "level",
            "model",
            "api_key",
            "max_diff_tokens",
            "source",
            "target",
            "output",
            "url",
            "project_id",
            "mr_iid",
            "repo",
            "pr",
            "token",
        }
        defaults = {k: v for k, v in raw.items() if k in allowed}

    parser = argparse.ArgumentParser("LLM Code Review")
    if defaults:
        parser.set_defaults(**defaults)

    parser.add_argument(
        "--config",
        type=Path,
        default=pre_args.config,
        help="TOML-файл с параметрами по умолчанию (CLI переопределяет).",
    )
    parser.add_argument(
        "--adapter",
        choices=["local", "gitlab", "github"],
        help="Источник diff: локальный репозиторий, GitLab MR или GitHub PR.",
    )
    parser.add_argument(
        "--level",
        default="FULL",
        choices=[l.value for l in PromptAdvancementLevel],
    )
    parser.add_argument(
        "--model",
        choices=[m.value for m in SupportedModel],
        help="Имя модели из SupportedModel (OpenRouter).",
    )
    parser.add_argument("--api-key", help="Ключ OpenRouter API.")
    parser.add_argument(
        "--max-diff-tokens",
        type=int,
        default=None,
        help="Оценка макс. токенов на один запрос для текста diff; "
        "если не задано — из размера контекста модели с запасом под промпт и ответ.",
    )

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

    args = parser.parse_args(remaining)

    missing = []
    if not args.adapter:
        missing.append("--adapter")
    if not args.model:
        missing.append("--model")
    if not args.api_key:
        missing.append("--api-key")
    if missing:
        parser.error("Отсутствуют обязательные параметры: " + ", ".join(missing))

    return args
