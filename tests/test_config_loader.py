from pathlib import Path

from code_review.config_loader import load_config


def test_load_config_flat(tmp_path: Path):
    p = tmp_path / "c.toml"
    p.write_text(
        'adapter = "local"\n'
        'model = "qwen3"\n'
        'api_key = "k"\n'
        'source = "a"\n'
        'target = "b"\n',
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg["adapter"] == "local"
    assert cfg["model"] == "qwen3"
    assert cfg["source"] == "a"


def test_load_config_section_aliases(tmp_path: Path):
    p = tmp_path / "c.toml"
    p.write_text(
        '[local]\n'
        'source = "feat"\n'
        'target = "main"\n',
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg["source"] == "feat"
    assert cfg["target"] == "main"


def test_load_config_env_substitution(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MY_KEY", "from-env")
    p = tmp_path / "c.toml"
    p.write_text('api_key = "env:MY_KEY"\n', encoding="utf-8")
    cfg = load_config(p)
    assert cfg["api_key"] == "from-env"
