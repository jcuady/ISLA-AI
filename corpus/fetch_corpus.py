"""Fetch the Philippine privacy corpus from reachable mirrors.

privacy.gov.ph and bsp.gov.ph both return HTTP 403 from this network (verified),
so every source is fetched through a mirror chain:

  1. direct       - origin URL, tried first
  2. wayback      - web.archive.org/web/2024id_/<url>  (raw, un-rewritten)
  3. lawphil      - lawphil.net mirror for RA 10173

All documents are public government publications; nothing here requires clearance.

One document is NOT fetched: ISLA-GUIDE-CS is authored in-repo (corpus/raw/
ISLA-GUIDE-CS.md) and marked local_only. It still travels through this script,
the manifest and the chunker so it inherits the same citation metadata, but no
network request is made for it.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "corpus" / "raw"
METADATA_PATH = REPO_ROOT / "corpus" / "raw" / "fetch_manifest.json"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
WAYBACK_PREFIX = "https://web.archive.org/web/2024id_/"


@dataclass
class SourceDoc:
    """One document in the corpus, with the citation metadata every chunk inherits."""

    doc_id: str
    title: str
    issuer: str
    doc_type: str  # statute | irr | circular | advisory | bsp_memo | morb
    origin_url: str
    authority_tier: int  # 1 = statute/NPC, 2 = BSP, 3 = internal
    effective_date: str = ""
    supersedes: str | None = None
    mirrors: list[str] = field(default_factory=list)
    local_path: str | None = None
    sha256: str | None = None
    fetch_status: str = "pending"
    notes: str = ""
    # Authored in-repo instead of fetched. Used for the operational guide, which
    # is Isla AI's own compilation and has no origin URL to retrieve. It still
    # has to travel through the manifest and the chunker like everything else,
    # otherwise it would be invisible to retrieval and to the citation metadata.
    local_only: bool = False


# Target set for the shipped scope. Prioritised by what the demo queries actually cite.
SOURCES: list[SourceDoc] = [
    SourceDoc(
        doc_id="RA-10173",
        title="Republic Act No. 10173 - Data Privacy Act of 2012",
        issuer="Congress of the Philippines",
        doc_type="statute",
        origin_url="https://lawphil.net/statutes/repacts/ra2012/ra_10173_2012.html",
        authority_tier=1,
        effective_date="2012-08-15",
        mirrors=["https://lawphil.net/statutes/repacts/ra2012/ra_10173_2012.html"],
        notes="Primary statute. Sections 12-20 (rights), 25 (security), 26 (breach), "
               "30 (concealment), 32 (penalties).",
    ),
    SourceDoc(
        doc_id="IRR-RA10173",
        title="Implementing Rules and Regulations of RA 10173 (as amended)",
        issuer="National Privacy Commission",
        doc_type="irr",
        origin_url="https://privacy.gov.ph/wp-content/uploads/2023/06/IRR_RA-10173-as-amended.pdf",
        authority_tier=1,
        effective_date="2016-09-09",
        mirrors=[
            WAYBACK_PREFIX
            + "https://privacy.gov.ph/wp-content/uploads/2023/06/IRR_RA-10173-as-amended.pdf"
        ],
        notes="IRR SS38-39 breach notification; SS16(c)(6) ADS notice. Verified: "
              "98k chars, 'Section 38' and 'Section 39' present.",
    ),
    SourceDoc(
        doc_id="NPC-ADV-2024-04",
        title="NPC Advisory No. 2024-04 - Guidelines on Artificial Intelligence "
              "and Sensitive Personal Data",
        issuer="National Privacy Commission",
        doc_type="advisory",
        origin_url=(
            "https://privacy.gov.ph/wp-content/uploads/2024/12/"
            "Advisory-2024.12.19-Guidelines-on-Artificial-Intelligence-w-SGD.pdf"
        ),
        authority_tier=1,
        effective_date="2024-12-19",
        mirrors=[
            WAYBACK_PREFIX
            + "https://privacy.gov.ph/wp-content/uploads/2024/12/"
            "Advisory-2024.12.19-Guidelines-on-Artificial-Intelligence-w-SGD.pdf"
        ],
        notes="THE AI-systems advisory. Transparency, accountability, fairness, accuracy, "
               "data minimisation, human intervention.",
    ),
    SourceDoc(
        doc_id="NPC-CIRC-2022-04",
        title="NPC Circular No. 2022-04 - Registration of Data Processing Systems, "
              "Notification Regarding Automated Decision-Making or Profiling, "
              "Designation of Data Protection Officer",
        issuer="National Privacy Commission",
        doc_type="circular",
        origin_url="https://privacy.gov.ph/wp-content/uploads/2023/05/Circular-2022-04-2.pdf",
        authority_tier=1,
        effective_date="2022-06-22",
        mirrors=[
            WAYBACK_PREFIX + "https://privacy.gov.ph/wp-content/uploads/2023/05/Circular-2022-04-2.pdf"
        ],
        notes="DPS registration, DPO designation, ADS/profiling notification.",
    ),
    SourceDoc(
        doc_id="NPC-CIRC-16-03",
        title="NPC Circular No. 16-03 - Personal Data Breach Management",
        issuer="National Privacy Commission",
        doc_type="circular",
        origin_url=(
            "https://privacy.gov.ph/wp-content/uploads/2022/01/"
            "sgd-npc-circular-16-03-personal-data-breach-management.pdf"
        ),
        authority_tier=1,
        effective_date="2016-12-15",
        mirrors=[
            WAYBACK_PREFIX
            + "https://privacy.gov.ph/wp-content/uploads/2022/01/"
            "sgd-npc-circular-16-03-personal-data-breach-management.pdf"
        ],
        notes="The 72-hour rule, delay conditions, 100-subject threshold. Verified: "
              "'72 hours' present in source text.",
    ),
    SourceDoc(
        doc_id="NPC-CIRC-2022-01",
        title="NPC Circular No. 2022-01 - Guidelines on Administrative Fines",
        issuer="National Privacy Commission",
        doc_type="circular",
        origin_url=(
            "https://privacy.gov.ph/wp-content/uploads/2022/08/"
            "NPC-CIRCULAR-NO.-2022-01-GUIDELINES-ON-ADMINISTRATIVE-FINES-"
            "dated-08-AUGUST-2022-w-SGD.pdf"
        ),
        authority_tier=1,
        effective_date="2022-08-08",
        mirrors=[
            WAYBACK_PREFIX
            + "https://privacy.gov.ph/wp-content/uploads/2022/08/"
            "NPC-CIRCULAR-NO.-2022-01-GUIDELINES-ON-ADMINISTRATIVE-FINES-"
            "dated-08-AUGUST-2022-w-SGD.pdf"
        ],
        notes="0.25%-2% of annual gross income fine for failure to notify.",
    ),
    SourceDoc(
        doc_id="NPC-CIRC-2023-04",
        title="NPC Circular No. 2023-04 - Guidelines on Consent",
        issuer="National Privacy Commission",
        doc_type="circular",
        origin_url=(
            "https://privacy.gov.ph/wp-content/uploads/2023/11/"
            "NPC-Circular-No.-2023-04_Guidelines-on-Consent_07Nov2023.pdf"
        ),
        authority_tier=1,
        effective_date="2023-11-07",
        mirrors=[
            WAYBACK_PREFIX
            + "https://privacy.gov.ph/wp-content/uploads/2023/11/"
            "NPC-Circular-No.-2023-04_Guidelines-on-Consent_07Nov2023.pdf"
        ],
        notes="SS18 profiling and automated processing consent.",
    ),
    SourceDoc(
        doc_id="ISLA-GUIDE-CS",
        title="Isla AI Operational Guide - Front-line and Customer-Facing "
              "Data Handling in Philippine Banking",
        issuer="Isla AI (compiled aid; not a legal source)",
        doc_type="sector_guidance",
        origin_url="isla-ai://corpus/ISLA-GUIDE-CS",
        authority_tier=3,
        effective_date="2026-10-09",
        local_path="corpus/raw/ISLA-GUIDE-CS.md",
        local_only=True,
        notes="NOT primary law. Compiled by Isla AI to route front-line questions "
              "to the right instrument. Cites the indexed DPA sections, and names "
              "PCI DSS and BSP regulations as pointers it does not hold. Ranked "
              "below every statute, circular and advisory so it can never "
              "outrank a real source.",
    ),
]

# Optional documents: fetched when reachable, but the product does not depend on them.
# BSP 403s from this network and has no usable Wayback capture of the memo page.
OPTIONAL_SOURCES: list[SourceDoc] = [
    SourceDoc(
        doc_id="BSP-M-2024-019",
        title="BSP Memorandum M-2024-019 - Reminders on the Handling of PII "
              "and Other Sensitive Data",
        issuer="Bangko Sentral ng Pilipinas",
        doc_type="bsp_memo",
        origin_url="https://www.bsp.gov.ph/SitePages/Regulations/MemorandaCirculars.aspx",
        authority_tier=2,
        effective_date="2024-09-20",
        mirrors=[
            WAYBACK_PREFIX + "https://www.bsp.gov.ph/SitePages/Regulations/MemorandaCirculars.aspx"
        ],
        notes="Cited in README as supervisory context; not required by the copilot corpus.",
    ),
]


def fetch(url: str, timeout: int = 60) -> tuple[bytes, str]:
    """Return (bytes, content_type). Raises on failure."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/pdf,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return resp.read(), resp.headers.get("Content-Type", "")


def extract_text(data: bytes, ext: str) -> str:
    """Plain-text extraction used to reject index/listing pages masquerading as documents."""
    if ext == "pdf":
        try:
            import io

            import pymupdf

            with pymupdf.open(stream=data, filetype="pdf") as doc:
                return " ".join("".join(p.get_text() for p in doc).split())
        except Exception as exc:  # noqa: BLE001
            print(f"      (pdf extract failed: {exc})")
            return ""
    if ext == "html":
        text = data.decode("utf-8", errors="replace")
        text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", text, flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        return " ".join(text.split())
    return ""


def validate(doc: SourceDoc, data: bytes, ext: str) -> tuple[bool, str]:
    """Reject pages that are index listings or search forms rather than the document itself."""
    text = extract_text(data, ext)
    if len(text) < 2000:
        return False, f"too little text ({len(text)} chars)"

    low = text.lower()

    # An index page lists many circulars; a real circular discusses its own subject.
    if ext == "html" and low.count("advisory no.") >= 8:
        return False, "looks like an index/listing page, not the document"

    # Each document must mention its own identity, not just the issuing body.
    identity_tokens = {
        "RA-10173": ["data privacy act"],
        "IRR-RA10173": ["implementing rules"],
        "NPC-ADV-2024-04": ["artificial intelligence"],
        "NPC-CIRC-2022-04": ["data protection officer"],
        "NPC-CIRC-16-03": ["personal data breach"],
        "NPC-CIRC-2022-01": ["administrative fine"],
        "NPC-CIRC-2023-04": ["consent"],
    }.get(doc.doc_id, [])
    for token in identity_tokens:
        if token not in low:
            return False, f"does not mention {token!r} (not the real document)"

    return True, f"{len(text)} chars verified"


def try_mirrors(doc: SourceDoc, retries: int = 2) -> Path | None:
    """Try direct origin, then each mirror. Saves to corpus/raw/<doc_id>.<ext>."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    candidates: list[tuple[str, str]] = [(doc.origin_url, "origin")]
    candidates += [(m, "wayback") for m in doc.mirrors]

    last_err = "no candidates"
    for url, kind in candidates:
        for attempt in range(retries):
            try:
                data, ctype = fetch(url)
            except (urllib.error.URLError, OSError, ValueError) as exc:
                last_err = f"{type(exc).__name__}: {exc}"
                time.sleep(1.5 * (attempt + 1))
                continue

            if len(data) < 512:
                last_err = f"suspiciously small ({len(data)} bytes)"
                continue

            # Extension inferred from magic bytes first, content-type second.
            if data[:5] == b"%PDF-":
                ext = "pdf"
            elif b"<" in data[:400].lstrip() or "html" in ctype.lower():
                ext = "html"
            else:
                ext = "bin"

            ok, reason = validate(doc, data, ext)
            if not ok:
                last_err = f"{kind}: {reason}"
                print(f"      reject {doc.doc_id} via {kind}: {reason}")
                continue

            dest = RAW_DIR / f"{doc.doc_id}.{ext}"
            dest.write_bytes(data)
            doc.local_path = str(dest.relative_to(REPO_ROOT))
            doc.sha256 = hashlib.sha256(data).hexdigest()
            doc.fetch_status = f"ok:{kind}:{ext}:{len(data)}b:{reason}"
            print(f"[ok  ] {doc.doc_id:18} via {kind:8} {len(data):>9,}b  {ext}  {reason}")
            return dest

    doc.fetch_status = f"FAILED: {last_err}"
    print(f"[FAIL] {doc.doc_id:18} {last_err}", file=sys.stderr)
    return None


def adopt_local(doc: SourceDoc) -> Path | None:
    """Verify an authored in-repo source instead of downloading it."""
    src = REPO_ROOT / (doc.local_path or "")
    if not src.exists():
        print(f"[FAIL] {doc.doc_id:18} local file missing: {src}", file=sys.stderr)
        return None
    data = src.read_bytes()
    text = data.decode("utf-8", errors="replace")
    if len(text) < 4000:
        print(f"[FAIL] {doc.doc_id:18} local file too short ({len(text)} chars)",
              file=sys.stderr)
        return None
    doc.sha256 = hashlib.sha256(data).hexdigest()
    doc.fetch_status = f"ok:local:{len(data)}b:authored"
    print(f"[ok  ] {doc.doc_id:18} via local    {len(data):>9,}b  md   authored in repo")
    return src


def adopt_existing(doc: SourceDoc) -> Path | None:
    """Adopt a raw file already on disk instead of downloading it again.

    This is what makes `fetch_corpus.py --offline` possible, which matters for
    a product whose central claim is that it runs air-gapped: the corpus has to
    be buildable on a box that cannot reach privacy.gov.ph at all.
    """
    for ext in ("pdf", "html", "md"):
        candidate = RAW_DIR / f"{doc.doc_id}.{ext}"
        if not candidate.exists():
            continue
        data = candidate.read_bytes()
        doc.local_path = str(candidate.relative_to(REPO_ROOT))
        doc.sha256 = hashlib.sha256(data).hexdigest()
        doc.fetch_status = f"ok:existing:{len(data)}b:{ext}"
        print(f"[ok  ] {doc.doc_id:18} via disk     {len(data):>9,}b  {ext}  "
              "already in corpus/raw")
        return candidate
    return None


def write_manifest() -> None:
    """Write the manifest, preserving local_path for documents this run skipped.

    A partial run (`fetch_corpus.py ISLA-GUIDE-CS`) must not erase the seven
    other documents' local_path entries. Doing so silently rebuilt the chunk
    file from one document and dropped the corpus from 227 chunks to 19 with
    no error anywhere: the chunker skips a document with no local_path and
    prints "[skip] ... not fetched", which reads like a download problem
    rather than a build one. An entry is only allowed to lose its local_path
    if the file it pointed at has actually gone.
    """
    previous: dict[str, dict] = {}
    if METADATA_PATH.exists():
        try:
            previous = {d["doc_id"]: d for d in json.loads(
                METADATA_PATH.read_text(encoding="utf-8")
            )}
        except (json.JSONDecodeError, KeyError, TypeError):
            previous = {}

    entries = []
    for doc in SOURCES:
        row = asdict(doc)
        if not row["local_path"]:
            prior = previous.get(doc.doc_id, {})
            prior_path = prior.get("local_path")
            if prior_path and (REPO_ROOT / prior_path).exists():
                row["local_path"] = prior_path
                row["sha256"] = prior.get("sha256") or row["sha256"]
                row["fetch_status"] = prior.get("fetch_status") or row["fetch_status"]
                print(f"[keep] {doc.doc_id:18} reusing {prior_path}")
        entries.append(row)

    METADATA_PATH.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main() -> int:
    argv = [a for a in sys.argv[1:] if not a.startswith("-")]
    offline = "--offline" in sys.argv[1:]
    only = set(argv)
    docs = [d for d in SOURCES if not only or d.doc_id in only]
    print(f"Isla AI corpus fetch - {len(docs)} required document(s)"
          f"{' [offline]' if offline else ''}\n")

    ok = 0
    for doc in docs:
        if doc.local_only:
            got = adopt_local(doc)
        elif offline:
            got = adopt_existing(doc)
            if got is None and not only:
                print(f"[FAIL] {doc.doc_id:18} not in corpus/raw and --offline",
                      file=sys.stderr)
        else:
            got = try_mirrors(doc)
            if got is None:
                got = adopt_existing(doc)
        if got:
            ok += 1

    print("\n-- optional (non-blocking) --")
    for doc in OPTIONAL_SOURCES:
        if only and doc.doc_id not in only:
            continue
        if not offline and try_mirrors(doc) is not None:
            continue
        if adopt_existing(doc) is None:
            print(f"      (continuing without {doc.doc_id} - not required by the copilot)")

    write_manifest()
    print(f"\nfetched {ok}/{len(docs)} required  ->  {METADATA_PATH.relative_to(REPO_ROOT)}")
    return 0 if ok == len(docs) else 1


if __name__ == "__main__":
    raise SystemExit(main())