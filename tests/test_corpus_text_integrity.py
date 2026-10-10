"""Corpus text integrity: the corpus must not contain undecodable glyphs.

PyMuPDF cannot map some glyphs in the official gazette PDFs and emits U+FFFD
instead. Observed symptom, caught while verifying the 60-second demo script: the
copilot answered "Pwede ba ipasa ang CDR..." with

    Principle of Accountability. <U+FFFD> Each personal information controller...

i.e. the replacement character was being shown to a compliance officer, inside a
sentence the product then quotes as authority. 107 occurrences across 68 of the
348 chunks, all in RA-10173, RA-9160, RA-10927 and RA-11967.

The mojibake is confined to two characters, both recoverable from context:
a possessive apostrophe ("individual-s") and the em dash separating a section
heading from its body ("Short Title. -"). Both are single characters, so the
repair is length-preserving by construction - see the length test, which is what
keeps the published chunk count and every chunk boundary from moving.

The companion guarantee is the embedding cache. `enable_dense` used to validate
a cached matrix by row count alone, so editing chunk text without changing the
chunk count left the index silently stale. `corpus_fingerprint` closes that.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from corpus.chunk_corpus import clean_text  # noqa: E402
from services.copilot.retrieval import corpus_fingerprint  # noqa: E402

CHUNKS = REPO / "corpus" / "processed" / "chunks.jsonl"
REPLACEMENT = "\ufffd"


def load_chunks() -> list[dict]:
    if not CHUNKS.exists():
        pytest.skip("corpus not built")
    return [json.loads(line) for line in CHUNKS.read_text(encoding="utf-8").splitlines() if line]


# ── the repair itself ───────────────────────────────────────────────────────


def test_joins_a_possessive_apostrophe():
    out = clean_text("about an individual" + REPLACEMENT + "s personal data")
    assert REPLACEMENT not in out
    assert "individual\u2019s personal" in out


def test_recovers_the_em_dash_between_a_heading_and_its_body():
    # The PDFs already emit a real em dash in the same position elsewhere, so
    # this is not a guess: "Access - Except as may be allowed" is verbatim.
    out = clean_text("Section 20. Non-Applicability.\n" + REPLACEMENT + " The immediately")
    assert REPLACEMENT not in out
    assert "Non-Applicability.\n\u2014 The immediately" in out


def test_a_trailing_em_dash_is_recovered():
    out = clean_text("Short Title. " + REPLACEMENT + "\nThis Act shall be known")
    assert "Short Title. \u2014\nThis Act" in out


def test_repair_preserves_length():
    """The whole reason this is safe to run over a committed corpus.

    Chunk boundaries are decided by character counts (MIN_CHARS, TARGET_CHARS).
    If the repair changed any length, chunk segmentation - and therefore the
    published "348 chunks" figure and every citation boundary - could shift.
    """
    raw = (
        "CHAPTER I\nGENERAL PROVISIONS\nShort Title. " + REPLACEMENT + "\n"
        "Scope.\n" + REPLACEMENT + " This Act applies.\n"
        "About an individual" + REPLACEMENT + "s data.\n"
    )
    assert len(clean_text(raw)) == len(clean_text(raw.replace(REPLACEMENT, "x")))


# ── the committed corpus ────────────────────────────────────────────────────


def test_committed_corpus_has_no_replacement_characters():
    """The one that actually failed before the repair."""
    chunks = load_chunks()
    offenders = [
        (c["chunk_id"], c["text"].count(REPLACEMENT))
        for c in chunks
        if REPLACEMENT in c["text"]
    ]
    assert offenders == [], (
        f"{sum(n for _, n in offenders)} undecodable glyph(s) across "
        f"{len(offenders)} chunk(s); first: {offenders[:3]}"
    )


def test_cleaning_the_committed_corpus_again_would_change_nothing():
    """clean_text is idempotent on already-clean text.

    Guards against a repair that only works once: re-running the chunker over a
    clean corpus must be a no-op, or the corpus would drift on every rebuild.
    """
    chunks = load_chunks()
    for c in chunks[:120]:
        assert clean_text(c["text"]) == c["text"].strip()


# ── the embedding cache fingerprint ─────────────────────────────────────────


def _mk(text: str) -> dict:
    return {"chunk_id": "RA-10173-x-000", "text": text}


def test_fingerprint_is_stable_for_an_identical_corpus():
    a = [_mk("one"), _mk("two")]
    b = [_mk("one"), _mk("two")]
    assert corpus_fingerprint(a) == corpus_fingerprint(b)


def test_fingerprint_changes_when_only_the_text_changes():
    """The regression the row-count check missed.

    Same chunk ids, same row count, same lengths - only the characters differ.
    A cache validated on row count alone stays stale here and silently serves
    vectors encoded from text that is no longer in the corpus.
    """
    before = [_mk("Short Title. \ufffd"), _mk("Scope.")]
    after = [_mk("Short Title. \u2014"), _mk("Scope.")]
    assert len(before) == len(after)
    assert corpus_fingerprint(before) != corpus_fingerprint(after)


def test_fingerprint_changes_when_a_chunk_id_is_reordered():
    """Rows are positional: search() indexes cosines by chunk position."""
    a = [_mk("one"), _mk("two")]
    b = [_mk("two"), _mk("one")]
    assert corpus_fingerprint(a) != corpus_fingerprint(b)


def test_fingerprint_of_an_empty_corpus_is_stable():
    assert corpus_fingerprint([]) == corpus_fingerprint([])