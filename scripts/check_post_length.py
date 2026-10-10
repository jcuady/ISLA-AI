"""Check that every post in docs/X_POST.md still fits its platform.

X truncates at 280 characters and rewrites every URL to a t.co link of 23
characters regardless of its real length, so a naive len() both overstates
short posts and understates long ones. The single post here is written with a
bare `github.com/...` rather than a full URL precisely because a bare host is
not rewritten and so is counted honestly - which is why the numbers are tight.

Run this after editing any of the copy. It is the only thing standing between a
trimmed caption and a post the host never sees in full:

    .venv\\Scripts\\python.exe scripts\\check_post_length.py
"""
from __future__ import annotations

import pathlib
import re
import sys

DOC = pathlib.Path(__file__).resolve().parent.parent / "docs" / "X_POST.md"

# Order matches the fenced blocks as they appear in the document.
LABELS = [
    "A single post",
    "thread 1/4",
    "thread 2/4",
    "thread 3/4",
    "thread 4/4",
    "LinkedIn",
]


def x_len(text: str) -> int:
    """Length as X counts it: every http(s) URL collapses to 23 characters."""
    return len(re.sub(r"https?://\S+", "x" * 23, text))


def main() -> int:
    blocks = re.findall(r"```\n(.*?)```", DOC.read_text(encoding="utf-8"), re.S)
    if not blocks:
        print(f"FAIL  no fenced post blocks found in {DOC.name}")
        return 1

    over = 0
    for i, block in enumerate(blocks):
        body = block.rstrip("\n")
        name = LABELS[i] if i < len(LABELS) else f"block {i + 1}"
        budget = 3000 if name == "LinkedIn" else 280
        n = x_len(body)
        if n <= budget:
            print(f"  PASS  {name:16} {n:>4} / {budget} chars")
        else:
            over += 1
            print(f"  FAIL  {name:16} {n:>4} / {budget} chars  "
                  f"OVER by {n - budget}")

    print("\n" + ("all posts fit" if not over else f"{over} POST(S) TOO LONG"))
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main())