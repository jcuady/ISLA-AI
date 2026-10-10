"""Structure-aware chunker for Philippine legal documents.

Naive 512-token windows destroy legal citations: a chunk that begins mid-clause
cannot be cited as "Section 20(c)". This chunker splits on legal section headers
and carries the full citation metadata (issuer, section, effective date, URL)
into every record, because an answer a compliance officer cannot defend to an
examiner is worse than no answer.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "corpus" / "raw"
PROCESSED = REPO_ROOT / "corpus" / "processed"
MANIFEST = RAW_DIR / "fetch_manifest.json"

MIN_CHARS = 350
TARGET_CHARS = 2200
OVERLAP_CHARS = 260


@dataclass
class LegalChunk:
    """One citable unit of the corpus."""

    chunk_id: str
    text: str
    doc_id: str
    doc_title: str
    issuer: str
    section: str
    effective_date: str
    url: str
    doc_type: str
    authority_tier: int
    sha256: str
    char_len: int = 0
    ordinal: int = 0
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.char_len:
            self.char_len = len(self.text)


# Legal header patterns, most specific first.
SECTION_PATTERNS = [
    re.compile(r"^\s*(?:SECTION|Section)\s+(\d+[A-Za-z]?(?:\([a-zA-Z0-9]+\))*)[\s.:]\s*(.*)$"),
    re.compile(r"^\s*(?:ARTICLE|Article)\s+([IVXLC]+|\d+)[\s.:]\s*(.*)$"),
    re.compile(r"^\s*Rule\s+(\d+[A-Za-z]?)[\s.:]\s*(.*)$", re.IGNORECASE),
    re.compile(r"^\s*(\d+)\.\s+([A-Z][A-Za-z ,\-]{4,80})[.\s]*$"),
    re.compile(r"^\s*([IVXLC]+)\.\s+([A-Z][A-Z \-]{4,60})$"),
]

NOISE_LINE_RE = re.compile(r"^\s*(?:page\s+\d+|-\s*\d+\s*-|©|\|.*\|)\s*$", re.IGNORECASE)

# Trailing administrative clauses: they state when or by whom an instrument was
# approved, never what it requires. When a source document's text extraction
# emits pages out of order, one of these can end up labelling real body text -
# which is how the flagship breach answer came to cite
# "NPC-CIRC-16-03 SECTION 25. Effectivity" for a 72-hour notification duty.
# Not citable authority, so the chunker must not emit it.
BOILERPLATE_SECTION_RE = re.compile(
    r"\b(?:effectivity|effect\s+of\s+this|approval|approved|date\s+of\s+approval|"
    r"date\s+of\s+effectivity|signature|signatures|issuance|separability)\b",
    re.IGNORECASE,
)


# PyMuPDF cannot decode some glyphs in the official gazette PDFs and emits
# U+FFFD rather than failing. Across this corpus that happens in exactly two
# positions, and both are recoverable from context:
#
#   * between two letters, it is the possessive apostrophe
#     ("individual's", "Corporation's"); and
#   * anywhere else, it is the em dash that separates a section heading from
#     its body ("Short Title. -"). This is not a guess: the same PDFs emit a
#     real em dash in that position elsewhere, so "Access - Except as may be
#     allowed" is verbatim from the source with the dash rendered correctly.
#
# Both replacements are single characters, so this is length-preserving by
# construction - which is what stops the repair from moving a chunk boundary
# and invalidating the published chunk count. tests/test_corpus_text_integrity.py
# asserts that property directly, and asserts the committed corpus is clean.
_REPLACEMENT_JOINING_LETTERS = re.compile("(?<=[A-Za-z])\ufffd(?=[A-Za-z])")
_ANY_REPLACEMENT = re.compile("\ufffd")


def repair_glyphs(text: str) -> str:
    """Replace U+FFFD with the character it stood in for. Same length, always."""
    text = _REPLACEMENT_JOINING_LETTERS.sub("\u2019", text)
    return _ANY_REPLACEMENT.sub("\u2014", text)


def clean_text(raw: str) -> str:
    text = raw.replace("\r\n", "\n").replace("\xa0", " ")
    text = repair_glyphs(text)
    lines = [ln.rstrip() for ln in text.split("\n")]
    kept = [ln for ln in lines if not NOISE_LINE_RE.match(ln)]
    # Collapse runs of 3+ blank lines.
    out: list[str] = []
    blanks = 0
    for ln in kept:
        if ln.strip():
            blanks = 0
            out.append(ln)
        else:
            blanks += 1
            if blanks <= 1:
                out.append("")
    return "\n".join(out).strip()


def read_source(path: Path) -> str:
    data = path.read_bytes()
    if data[:5] == b"%PDF-":
        import pymupdf

        with pymupdf.open(stream=data, filetype="pdf") as doc:
            return "\n".join(page.get_text() for page in doc)
    import re as _re

    html = data.decode("utf-8", errors="replace")
    html = _re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=_re.S | _re.I)
    return _re.sub(r"<[^>]+>", "\n", html)


# A section heading is a title: "Section 11. Retention of call recordings".
# Body text that merely begins a line with a cross-reference reads as
# "Section 11(f) requires that personal information be kept" - a sentence whose
# first word after the number is a finite verb. Treating that as a header
# relabels the paragraph it opens and swallows the real header after it.
_HEADING_LEADING_VERBS = frozenset(
    {
        "requires", "require", "shall", "must", "is", "are", "was", "were",
        "has", "have", "can", "may", "will", "means", "means", "refers",
        "states", "provides", "sets", "applies", "covers", "gives", "allows",
        "prohibits", "imposes", "mandates", "becomes", "takes", "does", "do",
        "contains", "includes", "lists", "describes", "governs", "applies",
    }
)


def find_headers(lines: list[str]) -> list[tuple[int, str]]:
    """Return (line_index, section_label) for every legal header we can cite.

    Administrative trailing clauses are skipped: they are not authority for
    anything, and when a source's text order is scrambled they would otherwise
    label the body text that follows them. See BOILERPLATE_SECTION_RE.

    Two further guards keep cross-references from being mistaken for headers:

      * a line that mentions "Section" more than once is not a header - a real
        header names its own section and nothing else; and
      * a line whose first word after the number is a finite verb is a
        sentence, not a title.

    Both exist because the Isla AI operational guide shipped sections labelled
    "Section 12. RA 10173 Section 11(f) requires that personal information be
    kept", which is a citation to nothing at all.
    """
    found: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or len(stripped) > 200:
            continue
        if BOILERPLATE_SECTION_RE.search(stripped):
            continue
        if len(re.findall(r"\bsections?\b", stripped, re.IGNORECASE)) > 1:
            continue
        for pat in SECTION_PATTERNS:
            m = pat.match(stripped)
            if not m:
                continue
            groups = m.groups()
            # The last group is the trailing title text for every pattern here.
            trailing = (groups[-1] or "").strip()
            first_word = re.split(r"[\s(,;:]", trailing, maxsplit=1)[0].lower()
            if first_word in _HEADING_LEADING_VERBS:
                break
            found.append((i, stripped[:120]))
            break
    return found


def tag_text(text: str) -> list[str]:
    """Light topical tags used for retrieval boosting and demo filtering."""
    low = text.lower()
    tags: list[str] = []
    probes = {
        "breach": ["breach", "notification", "72 hour"],
        "consent": ["consent", "profiling"],
        "outbound-transfer": ["outbound", "transfer", "offshore"],
        "registration": ["registration", "register", "data protection officer"],
        "ai-systems": ["artificial intelligence", "automated decision", "ai system"],
        "security": ["security", "safeguard", "confidential"],
        "rights": ["right of access", "right to be informed", "amend"],
        "penalties": ["fine", "penalt", "administrative"],
        "pii-handling": ["personally identifiable", "sensitive personal"],
    }
    for tag, keys in probes.items():
        if any(k in low for k in keys):
            tags.append(tag)
    return tags


def chunk_document(doc: dict, text: str) -> list[LegalChunk]:
    lines = clean_text(text).split("\n")
    headers = find_headers(lines)

    # Group lines into sections bounded by headers.
    #
    # A header line labels everything from ITSELF to the next header, so the
    # body that PRECEDES a header belongs to the PREVIOUS label. Labelling that
    # leading body with the upcoming header would shift every citation by one
    # section - e.g. label "Section 26" carrying Section 25 text.
    sections: list[tuple[str, list[str]]] = []
    if headers:
        current_label = "Preamble"
        cursor = 0
        for idx, label in headers:
            body = lines[cursor:idx]
            if any(b.strip() for b in body):
                sections.append((current_label, body))
            current_label = label
            cursor = idx + 1  # the header line itself starts the new section
        tail = lines[cursor:]
        if any(b.strip() for b in tail):
            sections.append((current_label if len(current_label) > 2 else "Full text", tail))
    else:
        sections.append(("Full text", lines))

    chunks: list[LegalChunk] = []
    ordinal = 0
    for label, body in sections:
        body_text = "\n".join(body).strip()
        if len(body_text) < 40:
            continue

        # Split oversized sections with overlap so a clause is never cut in half.
        pieces: list[str] = []
        if len(body_text) <= TARGET_CHARS:
            pieces.append(body_text)
        else:
            start = 0
            while start < len(body_text):
                end = min(start + TARGET_CHARS, len(body_text))
                if end < len(body_text):
                    window = body_text[start:end]
                    cut = window.rfind(". ")
                    if cut > TARGET_CHARS // 2:
                        end = start + cut + 1
                pieces.append(body_text[start:end].strip())
                if end >= len(body_text):
                    break
                start = max(end - OVERLAP_CHARS, start + 1)

        for part_no, piece in enumerate(pieces):
            if len(piece) < MIN_CHARS and chunks:
                # Too small to stand alone - fold into the previous chunk.
                prev = chunks[-1]
                prev.text = f"{prev.text}\n{piece}"
                prev.char_len = len(prev.text)
                prev.tags = sorted(set(prev.tags) | set(tag_text(piece)))
                continue
            section_label = label if part_no == 0 else f"{label} (cont.)"
            slug = re.sub(r"[^A-Za-z0-9]+", "-", section_label).strip("-")[:40]
            chunks.append(
                LegalChunk(
                    chunk_id=f"{doc['doc_id']}-{slug}-{ordinal:03d}",
                    text=piece,
                    doc_id=doc["doc_id"],
                    doc_title=doc["title"],
                    issuer=doc["issuer"],
                    section=section_label,
                    effective_date=doc.get("effective_date", ""),
                    url=doc["origin_url"],
                    doc_type=doc["doc_type"],
                    authority_tier=doc.get("authority_tier", 3),
                    sha256=doc.get("sha256", ""),
                    ordinal=ordinal,
                    tags=tag_text(piece),
                )
            )
            ordinal += 1
    return chunks


def main() -> int:
    if not MANIFEST.exists():
        print(f"missing {MANIFEST}; run corpus/fetch_corpus.py first", file=sys.stderr)
        return 1

    PROCESSED.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED / "chunks.jsonl"
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    all_chunks: list[LegalChunk] = []
    for doc in manifest:
        if not doc.get("local_path"):
            print(f"[skip] {doc['doc_id']:18} not fetched")
            continue
        src = REPO_ROOT / doc["local_path"]
        if not src.exists():
            print(f"[skip] {doc['doc_id']:18} file missing")
            continue
        try:
            text = read_source(src)
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {doc['doc_id']:18} {type(exc).__name__}: {exc}")
            continue

        chunks = chunk_document(doc, text)
        all_chunks.extend(chunks)
        total = sum(c.char_len for c in chunks)
        print(f"[ok  ] {doc['doc_id']:18} {len(chunks):>3} chunks  {total:>7,} chars")

    # Refuse to destroy the committed corpus. This file is tracked in git
    # precisely so the demo runs with no network, so a failed fetch must not
    # silently replace 348 chunks with an empty file: the app would still
    # start, serve zero documents, and answer every legal question as a
    # refusal - which looks like a working product with an empty corpus.
    if not all_chunks:
        print(
            "REFUSING TO WRITE: no source documents were read.\n"
            "  corpus/raw holds the fetched PDFs/HTML and is git-ignored, so a\n"
            "  failed fetch leaves it empty. corpus/processed/chunks.jsonl is\n"
            "  committed and is all the app needs - restore it with\n"
            "      git checkout -- corpus/processed/chunks.jsonl\n"
            "  and only re-run the chunker once corpus/raw is actually populated.",
            file=sys.stderr,
        )
        return 1

    with out_path.open("w", encoding="utf-8") as fh:
        for chunk in all_chunks:
            fh.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")

    print(f"\nTOTAL: {len(all_chunks)} chunks across {len(manifest)} docs")
    print(f"      -> {out_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())