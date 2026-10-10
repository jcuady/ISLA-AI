"""The chunker must never replace the committed corpus with an empty file.

`corpus/processed/chunks.jsonl` is tracked in git so the demo runs with no
network at all. `corpus/raw/` (the fetched PDFs and HTML) is git-ignored. So on
a machine where the fetch fails - BSP and SEC are unreachable from some
networks - `chunk_corpus.py` finds no sources, and its unconditional
`open(..., "w")` replaced 348 chunks with nothing.

The app still starts, reports `chunks: 0`, and answers every legal question
with a refusal. That reads as a working product, which is worse than a crash.

The guard makes the failure loud and leaves the file untouched.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
CHUNKS = REPO / "corpus" / "processed" / "chunks.jsonl"
PYTHON = sys.executable


def _run_chunker(cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PYTHON, "corpus/chunk_corpus.py"],
        cwd=cwd, capture_output=True, text=True, timeout=300,
    )


def _clone_without_raw_sources(tmp_path: Path) -> Path:
    """A working copy whose manifest points at files that are not there."""
    import shutil

    dst = tmp_path / "repo"
    dst.mkdir()
    for name in ("corpus", "services", "models"):
        shutil.copytree(REPO / name, dst / name, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__", "*.npy"))
    shutil.copy2(REPO / "requirements.txt", dst / "requirements.txt")
    return dst


@pytest.mark.skipif(not CHUNKS.exists(), reason="corpus not built")
def test_an_empty_fetch_does_not_overwrite_the_committed_corpus(tmp_path):
    original = CHUNKS.read_bytes()
    dst = _clone_without_raw_sources(tmp_path)

    # Reproduce a fresh clone, or a machine where the fetch failed: the
    # manifest is committed but the PDFs and HTML it points at are not there.
    raw = dst / "corpus" / "raw"
    assert (raw / "fetch_manifest.json").exists(), "manifest must stay: it is committed"
    for child in raw.iterdir():
        if child.suffix in {".pdf", ".html"}:
            child.unlink()

    before = (dst / "corpus" / "processed" / "chunks.jsonl").read_bytes()
    result = _run_chunker(dst)

    assert result.returncode != 0, "chunker exited 0 with no source documents"
    assert "REFUSING TO WRITE" in result.stderr
    after = (dst / "corpus" / "processed" / "chunks.jsonl").read_bytes()
    assert after == before, "chunker rewrote the corpus file despite the guard"
    assert json.loads(after.decode("utf-8").splitlines()[0])["chunk_id"]


@pytest.mark.skipif(not CHUNKS.exists(), reason="corpus not built")
def test_the_committed_corpus_is_intact_right_now():
    lines = CHUNKS.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 348, f"expected 348 chunks, found {len(lines)}"