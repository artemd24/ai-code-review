from abc import ABC


class CommonAdapter(ABC):
    def get_diff(self, context) -> str:
        ...

    def post_comment(self, comment: str) -> None:
        ...

    def post_summary(self, summary: str) -> None:
        ...