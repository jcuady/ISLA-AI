"""Corpus integrity: every chunk must be citable authority.

The chunker splits on legal section headers, so a chunk inherits the label of
the header that precedes it. That is correct - until a PDF's text extraction
emits pages out of order, in which case a *trailing* clause such as
"SECTION 25. Effectivity" ends up labelling the body text that follows it.

Observed symptom: the flagship 72-hour breach answer cited
"NPC-CIRC-16-03 SECTION 25. Effectivity. This Order shall take effect fifteen
(15) days after publication" - a clause with no bearing on breach notification.

Effectivity / approval / signature clauses are not authority for anything. The
chunker must not emit them, and the committed corpus must not contain them.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from corpus.chunk_corpus import (  # noqa: E402
    BOILERPLATE_SECTION_RE,
    find_headers,
)

CHUNKS = REPO / "corpus" / "processed" / "chunks.jsonl"


def load_chunks() -> list[dict]:
    if not CHUNKS.exists():
        pytest.skip("corpus not built")
    return [json.loads(line) for line in CHUNKS.read_text(encoding="utf-8").splitlines() if line]


def test_the_pattern_matches_every_boilerplate_clause_form():
    for label in (
        "Section 25. Effectivity",
        "SECTION 25. Effectivity. This Order shall take effect",
        "Section 26. Approval",
        "SECTION 30. Date of Approval",
        "Section 12. Signature",
        "SECTION 24. Separability Clause. If any portion or provision",
    ):
        assert BOILERPLATE_SECTION_RE.search(label), label


def test_a_line_mentioning_section_twice_is_not_a_header():
    """Body text that opens with a cross-reference must not relabel itself.

    A real header names its own section and nothing else. This guard exists
    because the Isla AI guide's sections came out labelled "Section 12. RA 10173
    Section 11(f) requires that personal information be kept" - a sentence
    that merely began a line with a cross-reference.
    """
    lines = [
        "Section 10. Retention of call recordings",
        "The duty rests on RA 10173",
        "Section 11(f) requires that personal information be kept",
        "in a form which permits identification for no longer.",
        "Section 11. Screenshots and note-taking",
        "Never paste a card number into a chat tool.",
    ]
    labels = [label for _, label in find_headers(lines)]
    assert labels == [
        "Section 10. Retention of call recordings",
        "Section 11. Screenshots and note-taking",
    ], labels


def test_the_pattern_does_not_match_substantive_provisions():
    # A regulation about data subject rights must never be filtered out.
    for label in (
        "Section 20. Principles of processing",
        "Section 20(c) Data Breach Notification",
        "SECTION 11. Scope",
        "Section 7. Registration of Systems",
        "Section 41. Breach Report",
        "Section 38. Data Breach Notification",
        "SECTION 3. Definition of Terms.  For the purpose of this Circular",
        "Section 17.  Notification of the Commission. The personal information",
        "Section 26. Organizational Security Measures. Where appropriate",
    ):
        assert not BOILERPLATE_SECTION_RE.search(label), label


def test_find_headers_drops_boilerplate_headers():
    lines = [
        "Section 20. Principles of processing",
        "Some substantive text.",
        "SECTION 25. Effectivity. This Order shall take effect fifteen (15) days after publication",
        "More text.",
        "Section 26. Approval",
        "Signed.",
    ]
    headers = find_headers(lines)
    labels = [label for _, label in headers]
    assert labels == ["Section 20. Principles of processing"], labels


def test_no_committed_chunk_is_labelled_with_a_boilerplate_clause():
    offenders = sorted(
        {
            c["section"]
            for c in load_chunks()
            if BOILERPLATE_SECTION_RE.search(c["section"])
        }
    )
    assert not offenders, (
        "chunks cite non-substantive clauses as authority: "
        + "; ".join(offenders)
        + ". Rebuild with corpus/chunk_corpus.py."
    )


def test_citation_labels_stay_short_enough_to_display():
    """A citation chip shows the label verbatim; a paragraph is not a citation."""
    for chunk in load_chunks():
        assert len(chunk["section"]) <= 120, chunk["section"]


def test_every_chunk_is_attributable_to_a_real_document():
    known = {
        "RA-10173",
        "IRR-RA10173",
        "NPC-ADV-2024-04",
        "NPC-CIRC-16-03",
        "NPC-CIRC-2022-01",
        "NPC-CIRC-2022-04",
        "NPC-CIRC-2023-04",
        "ISLA-GUIDE-CS",
    }
    unknown = {c["doc_id"] for c in load_chunks()} - known
    assert not unknown, unknown


def test_duplicate_labels_are_rare_enough_to_be_readable():
    """Repeated labels are the fingerprint of mis-ordered source text."""
    chunks = load_chunks()
    seen: dict[tuple[str, str], int] = {}
    for chunk in chunks:
        seen[(chunk["doc_id"], chunk["section"])] = seen.get(
            (chunk["doc_id"], chunk["section"]), 0
        ) + 1
    repeated = sum(v - 1 for v in seen.values() if v > 1)
    assert repeated <= len(chunks) * 0.10, (
        f"{repeated}/{len(chunks)} chunks share a label with another chunk; "
        "header/body association has drifted again"
    )