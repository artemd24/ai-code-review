"""Split large unified diffs into batches that fit an approximate token budget."""

from __future__ import annotations

import re


def estimate_tokens(text: str) -> int:
    """Rough token count (~4 chars per token) without external deps."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def _split_oversized(segment: str, max_content_tokens: int) -> list[str]:
    max_chars = max(1, max_content_tokens * 4)
    if len(segment) <= max_chars and estimate_tokens(segment) <= max_content_tokens:
        return [segment]
    lines = segment.splitlines(keepends=True)
    out: list[str] = []
    cur: list[str] = []
    cur_len = 0

    def flush_line_chunks(line: str) -> list[str]:
        if len(line) <= max_chars:
            return [line]
        return [line[i : i + max_chars] for i in range(0, len(line), max_chars)]

    for line in lines:
        for piece in flush_line_chunks(line):
            ln = len(piece)
            if cur_len + ln > max_chars and cur:
                out.append("".join(cur))
                cur = [piece]
                cur_len = ln
            else:
                cur.append(piece)
                cur_len += ln
    if cur:
        out.append("".join(cur))
    return out


def _file_segments(diff: str) -> list[str]:
    """Split concatenated unified diffs on file headers."""
    s = diff.strip()
    if not s:
        return []
    parts = re.split(r"\n(?=--- )", s)
    return [p for p in parts if p.strip()]


def split_diff(diff: str, max_content_tokens: int) -> list[str]:
    """Return one or more diff strings, each within ``max_content_tokens`` (estimated)."""
    if max_content_tokens <= 0:
        raise ValueError("max_content_tokens must be positive")

    if estimate_tokens(diff) <= max_content_tokens:
        return [diff]

    segments = _file_segments(diff)
    if not segments:
        return _split_oversized(diff, max_content_tokens)

    normalized: list[str] = []
    for seg in segments:
        if estimate_tokens(seg) <= max_content_tokens:
            normalized.append(seg)
        else:
            normalized.extend(_split_oversized(seg, max_content_tokens))

    batches: list[str] = []
    cur: list[str] = []
    cur_tokens = 0
    for seg in normalized:
        t = estimate_tokens(seg)
        if t > max_content_tokens:
            for piece in _split_oversized(seg, max_content_tokens):
                pt = estimate_tokens(piece)
                if cur and cur_tokens + pt > max_content_tokens:
                    batches.append("\n".join(cur))
                    cur = [piece]
                    cur_tokens = pt
                elif not cur:
                    cur = [piece]
                    cur_tokens = pt
                else:
                    cur.append(piece)
                    cur_tokens += pt
            continue

        if not cur:
            cur = [seg]
            cur_tokens = t
            continue
        if cur_tokens + t > max_content_tokens:
            batches.append("\n".join(cur))
            cur = [seg]
            cur_tokens = t
        else:
            cur.append(seg)
            cur_tokens += t

    if cur:
        batches.append("\n".join(cur))

    return batches if batches else [diff]


def default_max_diff_tokens(
    context_window_tokens: int,
    *,
    prompt_reserve_tokens: int = 12_000,
    response_reserve_tokens: int = 8_000,
) -> int:
    """Leave headroom for system prompt and model output."""
    return max(4096, context_window_tokens - prompt_reserve_tokens - response_reserve_tokens)
