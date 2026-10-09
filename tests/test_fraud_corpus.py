"""The fraud corpus must be real, quotable law - never authored filler.

The product claim is that a compliance officer can defend a citation to an
examiner. That claim is only true for instruments this process actually
retrieved and content-validated. An earlier version of this file asserted the
corpus had "the AMLA" without checking which AMLA, and a summariser happily
filled the gap with plausible text nobody had read.

So the rules here are deliberately strict:

  * every fraud instrument in the corpus must have been fetched from a public
    mirror, recorded in the manifest with a sha256, and matched its own
    identity tokens before being accepted;
  * the text must actually contain the provisions the product relies on, so a
    truncated or wrong-page fetch fails loudly instead of producing thin
    citations;
  * and the instruments this machine could NOT reach - BSP and SEC - are named
    in a test so the gap is a tracked fact, not a forgotten one.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

REPO = Path(__file__).resolve().parent.parent
CHUNKS = REPO / "corpus" / "processed" / "chunks.jsonl"
MANIFEST = REPO / "corpus" / "raw" / "fetch_manifest.json"

# Instruments this feature depends on. Each entry names the fragments that must
# survive into the indexed text, so a fetch that returns the wrong page, a
# listing, or a partial document is rejected rather than indexed.
FRAUD_INSTRUMENTS = {
    "RA-9160": {
        "title_contains": "Anti-Money Laundering",
        "must_contain": [
            "covered transaction",
            "money laundering",
            "covered institution",
            "covered transaction report",
        ],
    },
    "RA-10927": {
        "title_contains": "10927",
        "must_contain": [
            "9160",
        ],
    },
    "RA-8792": {
        "title_contains": "Electronic Commerce",
        "must_contain": [
            "unauthorized",
            "liability",
            "electronic data message",
        ],
    },
    "RA-11967": {
        "title_contains": "Internet Transactions",
        "must_contain": [
            "online merchant",
            "consumer",
        ],
    },
}

# Everything the product is asked to cover that this build could NOT verify.
# Kept as data so the gap is asserted, not just remembered.
KNOWN_UNVERIFIABLE = ("BSP", "SEC")


def load_chunks() -> list[dict]:
    if not CHUNKS.exists():
        pytest.skip("corpus not built")
    return [json.loads(l) for l in CHUNKS.read_text(encoding="utf-8").splitlines() if l]


class TestFraudCorpusIsRealLaw:
    @pytest.mark.parametrize("doc_id", sorted(FRAUD_INSTRUMENTS))
    def test_the_instrument_is_in_the_corpus(self, doc_id: str) -> None:
        docs = {c["doc_id"] for c in load_chunks()}
        assert doc_id in docs, (
            f"{doc_id} is missing from the corpus. If it could not be fetched, "
            "it belongs in KNOWN_UNVERIFIABLE, not silently absent."
        )

    @pytest.mark.parametrize("doc_id", sorted(FRAUD_INSTRUMENTS))
    def test_the_instrument_was_fetched_not_authored(self, doc_id: str) -> None:
        manifest = {d["doc_id"]: d for d in json.loads(MANIFEST.read_text(encoding="utf-8"))}
        row = manifest.get(doc_id)
        assert row is not None, f"{doc_id} is not in the fetch manifest"
        assert row["local_path"], f"{doc_id} has no local_path: it was never fetched"
        assert (REPO / row["local_path"]).exists(), row["local_path"]
        assert row["sha256"], f"{doc_id} has no sha256"
        assert not row.get("local_only"), (
            f"{doc_id} is flagged local_only, but it is a statute: it must be "
            "retrieved from a public source, not written by us."
        )

    @pytest.mark.parametrize("doc_id", sorted(FRAUD_INSTRUMENTS))
    def test_the_indexed_text_contains_the_provisions_we_rely_on(self, doc_id: str) -> None:
        spec = FRAUD_INSTRUMENTS[doc_id]
        chunks = [c for c in load_chunks() if c["doc_id"] == doc_id]
        assert chunks, doc_id
        body = " ".join(" ".join(c["text"].split()) for c in chunks).lower()
        assert spec["title_contains"].lower() in body[:4000], (
            f"{doc_id} does not look like {spec['title_contains']!r}: this is "
            "probably the wrong page"
        )
        for fragment in spec["must_contain"]:
            assert fragment.lower() in body, (
                f"{doc_id} indexed text never mentions {fragment!r}. Either the "
                "fetch was partial or the product is citing a provision it does "
                "not actually hold."
            )

    def test_the_fraud_instruments_are_primary_authority(self) -> None:
        for c in load_chunks():
            if c["doc_id"] in FRAUD_INSTRUMENTS:
                assert c["doc_type"] == "statute", (c["doc_id"], c["doc_type"])
                assert c["authority_tier"] == 1, (c["doc_id"], c["authority_tier"])

    def test_no_fraud_instrument_is_a_compiled_guide(self) -> None:
        """The front-line guide is ours; the statutes are not. Keep them apart."""
        for c in load_chunks():
            if c["doc_id"] in FRAUD_INSTRUMENTS:
                assert "not a legal source" not in c["issuer"].lower()


class TestTheCoverageGapIsTracked:
    def test_bsp_and_sec_are_documented_as_unverifiable(self) -> None:
        """If a future build makes BSP or SEC reachable, this test is meant to
        fail loudly so the gap is closed deliberately rather than forgotten."""
        readme = (REPO / "README.md").read_text(encoding="utf-8")
        sources = (REPO / "docs" / "CORPUS_SOURCES.md").read_text(encoding="utf-8")
        for regulator in KNOWN_UNVERIFIABLE:
            assert regulator in readme, f"{regulator} coverage gap is undocumented in README"
            assert regulator in sources, f"{regulator} gap is undocumented in CORPUS_SOURCES.md"

    def test_the_amla_capture_is_declared_abridged(self) -> None:
        """The lawphil RA 9160 is the 2001 text and is missing its reporting
        provisions. Shipping it as though it were complete would let the product
        quote a chunk and imply the copilot can answer a reporting question it
        cannot. The abridgement is asserted here so it stays declared."""
        chunks = [c for c in load_chunks() if c["doc_id"] == "RA-9160"]
        body = " ".join(" ".join(c["text"].split()) for c in chunks).lower()
        assert "suspicious transaction" not in body, (
            "this capture now contains the suspicious-transaction provisions - "
            "re-fetch, drop the abridgement notice, and widen the corpus tests"
        )
        notice = (REPO / "docs" / "CORPUS_SOURCES.md").read_text(encoding="utf-8").lower()
        assert "abridged" in notice, "the RA 9160 abridgement is undocumented"

    def test_the_corpus_never_claims_to_hold_bsp_or_sec_documents(self) -> None:
        issuers = " ".join(c["issuer"] for c in load_chunks())
        assert "Bangko Sentral" not in issuers, (
            "a chunk claims BSP as its issuer: no BSP document was retrievable, "
            "so this would be fabricated"
        )
        assert "Securities and Exchange Commission" not in issuers, (
            "a chunk claims SEC as its issuer: no SEC document was retrievable"
        )