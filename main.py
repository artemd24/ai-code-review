from code_review.adapters.github_adapter import GitHubAdapter
from code_review.adapters.gitlab_adapter import GitLabAdapter
from code_review.adapters.local_adapter import LocalAdapter
from code_review.cli import parse_args
from code_review.lib.llm_manager import LLMAPIManager
from code_review.lib.prompt_builder import PromptBuilder, PromptAdvancementLevel
from code_review.lib.supperted_models import SupportedModel
from code_review.review_orchestrator import ReviewOrchestrator


def create_adapter(adapter_type: str, args):
    if adapter_type == "local":
        return LocalAdapter(args.output)

    if adapter_type == "gitlab":
        return GitLabAdapter()

    if adapter_type == "github":
        return GitHubAdapter()

    raise ValueError("Unknown adapter")


def build_context(adapter_type: str, args) -> dict:
    if adapter_type == "local":
        return {
            "source_branch": args.source,
            "target_branch": args.target,
        }

    if adapter_type == "gitlab":
        return {
            "project_id": args.project_id,
            "mr_iid": args.mr_iid,
            "token": args.token,
            "ci_server_url": args.url,
        }

    if adapter_type == "github":
        if not (hasattr(args, 'repo') and args.repo and hasattr(args, 'pr') and args.pr):
            raise ValueError("Для GitHub укажите --repo и --pr")
        return {
            "repo": args.repo,
            "pr_number": args.pr,
            "token": args.token,
        }

    raise ValueError("Unknown adapter")


def main():
    args = parse_args()

    adapter = create_adapter(args.adapter, args)
    context = build_context(args.adapter, args)

    model = SupportedModel(args.model)

    llm = LLMAPIManager(
        api_key=args.api_key,
        nodel_id=model.openrouter_id,
    )

    prompt_builder = PromptBuilder(
        PromptAdvancementLevel(args.level)
    )

    orchestrator = ReviewOrchestrator(
        adapter=adapter,
        llm_manager=llm,
        prompt_builder=prompt_builder,
    )

    orchestrator.run(context)


if __name__ == "__main__":
    main()
