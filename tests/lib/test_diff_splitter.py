from code_review.lib.diff_splitter import (
    default_max_diff_tokens,
    estimate_tokens,
    split_diff,
)


def test_estimate_tokens_empty():
    assert estimate_tokens("") == 0


def test_split_diff_single_chunk_when_small():
    d = "--- a.py\n+++ b.py\n@@ -1 +1 @@\n-x\n+y\n"
    assert split_diff(d, 10_000) == [d]


def test_split_diff_multiple_files():
    parts = [
        "--- f1.py\n+++ f1.py\n@@ -1 +1 @@\n-a\n+b\n",
        "--- f2.py\n+++ f2.py\n@@ -1 +1 @@\n-c\n+d\n",
    ]
    diff = "\n".join(parts)
    chunks = split_diff(diff, max_content_tokens=8)
    assert len(chunks) >= 2


def test_default_max_diff_tokens():
    assert default_max_diff_tokens(128_000) > 0
