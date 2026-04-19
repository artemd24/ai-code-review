"""Load CLI defaults from a TOML file (Python 3.11+ tomllib)."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any


def _resolve_value(value: Any) -> Any:
    if isinstance(value, str) and value.startswith("env:"):
        var = value[4:].strip()
        return os.environ.get(var, "")
    return value


def _flatten_section(prefix: str, data: dict[str, Any], out: dict[str, Any]) -> None:
    for key, val in data.items():
        full = f"{prefix}.{key}" if prefix else key
        if isinstance(val, dict):
            _flatten_section(full, val, out)
        else:
            out[full.replace(".", "_")] = _resolve_value(val)


def load_config(path: Path | str) -> dict[str, Any]:
    """Load TOML config. Nested tables become keys like `local_source` → use flat keys instead.

    Supported:
    - Top-level scalar keys: adapter, model, level, api_key, token, url, ...
    - Optional sections [local], [gitlab], [github] merged with prefix local_, gitlab_, github_
      e.g. [local] source= → local_source (CLI uses --source, so we map below).
    """
    p = Path(path)
    raw = p.read_bytes()
    data = tomllib.loads(raw.decode("utf-8"))

    flat: dict[str, Any] = {}
    for key, val in data.items():
        if isinstance(val, dict):
            _flatten_section(key, val, flat)
        else:
            flat[key] = _resolve_value(val)

    # Map section-prefixed keys to argparse dest names (use top-level `token` for auth).
    alias = {
        "local_source": "source",
        "local_target": "target",
        "local_output": "output",
        "gitlab_url": "url",
        "gitlab_project_id": "project_id",
        "gitlab_mr_iid": "mr_iid",
        "github_repo": "repo",
        "github_pr": "pr",
    }
    for old, new in alias.items():
        if old in flat and new not in flat:
            flat[new] = flat[old]

    return flat
