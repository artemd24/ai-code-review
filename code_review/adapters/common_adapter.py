from abc import ABC, abstractmethod


class CommonAdapter(ABC):
    @abstractmethod
    def get_diff(self, context: dict) -> str:
        pass

    @abstractmethod
    def post_comment(self, comment: str) -> None:
        pass

    @abstractmethod
    def post_summary(self, summary: str) -> None:
        pass
