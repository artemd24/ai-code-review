from git import Repo


class LocalAdapter:
    def get_diff(self, source_branch: str, target_branch: str) -> str:
        """Возвращает полный diff между двумя ветками."""
        repo = Repo(".")
        if repo.bare:
            raise RuntimeError("Репозиторий не найден или пустой.")
        try:
            diff_text = repo.git.diff(f"{target_branch}..{source_branch}")
        except Exception as e:
            raise RuntimeError(f"Ошибка при получении diff: {e}")
        if not diff_text.strip():
            raise ValueError("Diff пуст. Возможно, между ветками нет изменений.")
        return diff_text