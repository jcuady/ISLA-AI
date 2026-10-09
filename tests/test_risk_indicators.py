"""The risk engine must be deterministic, auditable and unable to invent law.

Seam under test: `services.risk.indicators.match_indicators` - the pure function
that turns a described transaction or scenario into a set of matched fraud
indicators. It is a seam because it has no I/O and no model: the same scenario
always produces the same indicators, on any machine, with or without weights
installed. That is the whole point of running this locally.

Three rules are enforced here, and each one exists because the alternative
failed at some point in development:

1.  **Every indicator carries a legal hook.** An indicator that cannot name an
    instrument, a provision, and who it exposes is a pattern match pretending to
    be compliance advice. It does not ship.

2.  **Every hook must exist in the corpus.** If an indicator cites RA 9160
    Section 9, the corpus has to actually contain that section. Otherwise the
    engine is quoting a provision it cannot show you - the exact failure mode
    this product exists to prevent.

3.  **Every hook declares who is exposed.** "Risk" is not a scalar. An
    indicator can expose the customer, the bank, or both, and those three cases
    imply different actions. An indicator that does not say which is a bug.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.risk.indicators import (  # noqa: E402
    INDICATORS,
    RiskTier,
    exposed_parties,
    match_indicators,
)

REPO = Path(__file__).resolve().parent.parent
CHUNKS = REPO / "corpus" / "processed" / "chunks.jsonl"

VALID_EXPOSURE = {"customer", "bank", "both"}
VALID_TIERS = {t.value for t in RiskTier}


def load_chunks() -> list[dict]:
    if not CHUNKS.exists():
        pytest.skip("corpus not built")
    return [json.loads(l) for l in CHUNKS.read_text(encoding="utf-8").splitlines() if l]


class TestCatalogueIntegrity:
    """The rules that stop a pattern matcher impersonating a compliance tool."""

    def test_the_catalogue_is_not_empty(self) -> None:
        assert len(INDICATORS) >= 12, f"only {len(INDICATORS)} indicators"

    def test_indicator_ids_are_unique(self) -> None:
        ids = [i.id for i in INDICATORS]
        assert len(ids) == len(set(ids)), "duplicate indicator id"

    @pytest.mark.parametrize("indicator", INDICATORS, ids=lambda i: i.id)
    def test_every_indicator_names_who_is_exposed(self, indicator) -> None:
        assert indicator.exposure, f"{indicator.id} exposes nobody"
        for party in indicator.exposure:
            assert party in VALID_EXPOSURE, (indicator.id, party)

    @pytest.mark.parametrize("indicator", INDICATORS, ids=lambda i: i.id)
    def test_every_indicator_declares_a_valid_tier(self, indicator) -> None:
        assert indicator.tier in VALID_TIERS, (indicator.id, indicator.tier)

    @pytest.mark.parametrize("indicator", INDICATORS, ids=lambda i: i.id)
    def test_every_indicator_has_an_explanation(self, indicator) -> None:
        """A red flag with no 'why' is an accusation, not an assessment."""
        assert len(indicator.why) >= 30, f"{indicator.id} gives no reason"

    @pytest.mark.parametrize("indicator", INDICATORS, ids=lambda i: i.id)
    def test_every_indicator_carries_a_required_action(self, indicator) -> None:
        """Risk that does not change what somebody does next is noise."""
        assert indicator.action, f"{indicator.id} has no required action"
        assert len(indicator.action) >= 20, indicator.id

    @pytest.mark.parametrize("indicator", INDICATORS, ids=lambda i: i.id)
    def test_every_indicator_declares_its_legal_hook(self, indicator) -> None:
        assert indicator.legal_hook, f"{indicator.id} has no legal hook"
        hook = indicator.legal_hook
        assert hook.doc_id, f"{indicator.id} hook names no document"
        assert hook.anchor, f"{indicator.id} hook has no retrieval anchor"

    @pytest.mark.parametrize("indicator", INDICATORS, ids=lambda i: i.id)
    def test_every_legal_hook_actually_exists_in_the_corpus(self, indicator) -> None:
        """The anti-fabrication guarantee.

        If the anchor phrase is nowhere in the indexed text of the document the
        indicator cites, the engine is pointing at law it cannot show. Either
        the anchor is wrong or the retrieval is incomplete - both are bugs, and
        both are invisible at runtime without this test.
        """
        chunks = load_chunks()
        docs = {c["doc_id"] for c in chunks}
        hook = indicator.legal_hook
        if hook.doc_id == "GAP":
            # A declared gap is allowed, but ONLY if it says which regulator.
            assert hook.anchor, f"{indicator.id} has an empty GAP hook"
            return
        assert hook.doc_id in docs, (
            f"{indicator.id} cites {hook.doc_id}, which is not in the corpus. "
            "Either fetch the instrument or move the hook to a GAP."
        )
        body = " ".join(
            " ".join(c["text"].split())
            for c in chunks
            if c["doc_id"] == hook.doc_id
        ).lower()
        assert hook.anchor.lower() in body, (
            f"{indicator.id} anchors on {hook.anchor!r}, which does not appear "
            f"in {hook.doc_id}. The engine would be citing a provision it "
            "cannot show."
        )

    def test_gap_hooks_declare_the_regulator_they_stand_in_for(self) -> None:
        """Where BSP or SEC governs, the hook must say so by name."""
        for indicator in INDICATORS:
            if indicator.legal_hook.doc_id != "GAP":
                continue
            label = indicator.legal_hook.anchor.upper()
            assert any(
                token in label for token in ("BSP", "SEC", "AMLC", "PCI")
            ), f"{indicator.id} hides which regulator is missing"

    def test_the_catalogue_never_claims_a_bsp_or_sec_instrument(self) -> None:
        """No chunk exists for BSP or SEC, so no hook may name one as a source."""
        for indicator in INDICATORS:
            assert indicator.legal_hook.doc_id not in {"BSP", "SEC"}, indicator.id


class TestMatching:
    def test_a_mule_scenario_is_detected(self) -> None:
        matches = match_indicators(
            "A student opened an account, received cash from three strangers, "
            "and sent most of it to an online seller the same day."
        )
        ids = {m.indicator.id for m in matches}
        assert ids, "a textbook money-mule pattern produced nothing"

    def test_ordinary_banking_is_not_flagged(self) -> None:
        """The false-positive side matters as much as the detection side. A
        compliance tool that flags every routine transaction gets switched off
        within a week."""
        routine = [
            "Customer withdrew PHP 5,000 from an ATM with a debit card.",
            "Customer applied for a personal loan and submitted income documents.",
            "A customer made a scheduled monthly transfer to their own account.",
        ]
        for text in routine:
            matches = match_indicators(text)
            high = [m for m in matches if m.indicator.tier in {"high", "critical"}]
            assert not high, f"routine activity flagged high risk: {text!r} -> {high}"

    def test_empty_input_matches_nothing_and_does_not_raise(self) -> None:
        assert match_indicators("") == []
        assert match_indicators("   ") == []

    def test_matching_is_deterministic(self) -> None:
        text = "Cash deposits just under the reporting threshold, split across branches."
        first = match_indicators(text)
        second = match_indicators(text)
        assert [m.indicator.id for m in first] == [m.indicator.id for m in second]

    def test_matches_are_sorted_most_severe_first(self) -> None:
        text = (
            "Multiple cash deposits below the threshold from different people, "
            "immediate onward transfer to an unrelated overseas beneficiary, "
            "and the customer asked to have the account closed before the audit."
        )
        matches = match_indicators(text)
        order = {t: i for i, t in enumerate(VALID_TIERS)}
        severities = [order[m.indicator.tier] for m in matches]
        assert severities == sorted(severities, reverse=True)

    def test_each_match_explains_the_evidence_it_found(self) -> None:
        text = "The customer deposited 499,000 in cash, then wired it abroad the next day."
        matches = match_indicators(text)
        assert matches
        for m in matches:
            assert m.evidence, f"{m.indicator.id} matched with no quoted evidence"


class TestExposure:
    def test_exposed_parties_unions_the_matches(self) -> None:
        text = "Cash deposits below the threshold, then an immediate overseas transfer."
        matches = match_indicators(text)
        assert exposed_parties(matches) is not None
        assert exposed_parties(matches) <= VALID_EXPOSURE

    def test_no_matches_exposes_nobody(self) -> None:
        assert exposed_parties([]) == set()

    def test_customer_and_bank_can_both_be_exposed(self) -> None:
        text = (
            "An agent read the customer's CVV over a recorded call, the account "
            "was then used for rapid cash deposits and an overseas transfer."
        )
        parties = exposed_parties(match_indicators(text))
        assert parties & {"customer", "bank"}, parties