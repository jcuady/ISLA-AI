"""Front-line and customer-facing questions must be answered, not refused.

Regression suite for the bug a judge would hit in the first minute of the
demo. A call-centre agent asks "pwede ba humingi ng CVV sa customer?" and the
copilot answered "Hindi ito tanong tungkol sa Data Privacy Act o mga patakaran
ng NPC" - refusing the single most common question a bank front-line officer
asks, on the grounds that it was out of scope.

It was not out of scope. Soliciting a card credential is the processing of
sensitive personal information, which is squarely what the Act governs. The
refusal came from two gaps, and both are pinned here:

  * the topical gate only knew legal register, so a question in plain Taglish
    with no legal vocabulary in it failed the domain check; and
  * the statute speaks in "adequate and not excessive" and "strict
    confidentiality", never in "CVV", so raw BM25 scored the question at zero
    against the provisions that actually decide it.

The second half of the fix is that these questions must NOT produce a confident
yes or no about operational policy. PCI DSS and the Bangko Sentral regulations
that decide whether staff may solicit a card secret are not in this corpus, so
the copilot cites what it holds and then says out loud where the boundary is.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.copilot.copilot import DPACopilot  # noqa: E402
from services.copilot.retrieval import (  # noqa: E402
    AUTHORITY_WEIGHT,
    HybridIndex,
    expand_query,
    scope_note_for,
)

REPO = Path(__file__).resolve().parent.parent
CHUNKS = REPO / "corpus" / "processed" / "chunks.jsonl"

GUIDE = "ISLA-GUIDE-CS"
GUIDE_TYPE = "sector_guidance"

# The exact question that was reported, plus the neighbouring front-line
# questions it is the same shape as. Taglish first, because that is the
# register the refusal failed on.
CARD_SECRET_QUESTIONS = [
    "yung pin sa likod ng credit card, pwede ba i-ask ng agent?",
    "pwede ba humingi ng CVV sa customer?",
    "Can I ask the customer for the PIN at the back of their credit card?",
    "Can an agent ask the customer for their password?",
    "Can the teller read the CVV to verify the card?",
    "Bakit hindi pwede ang OTP sa customer?",
    "Pwede ba i-save ng agent ang security code ng card ng customer?",
    "Is it allowed to ask the cardholder for the one-time password?",
]

OTHER_FRONTLINE_QUESTIONS = [
    "Can we record the call with the customer?",
    "Can a collection agent disclose the account to the caller?",
    "Pwede ba mag-screenshot ng agent ang record ng customer?",
    "Anong ID pwede kong hilingi sa customer sa counter?",
    "Ilang taon dapat itinatago ang call recording?",
]

STATUTE_DOCS = {"RA-10173", "IRR-RA10173", "NPC-CIRC-16-03", "NPC-CIRC-2022-01",
                "NPC-CIRC-2022-04", "NPC-CIRC-2023-04", "NPC-ADV-2024-04"}

GUIDE = "ISLA-GUIDE-CS"
GUIDE_TYPE = "sector_guidance"


@pytest.fixture(scope="module")
def index() -> HybridIndex:
    idx = HybridIndex()
    idx.enable_dense()
    return idx


@pytest.fixture(scope="module")
def copilot(index: HybridIndex) -> DPACopilot:
    return DPACopilot(index)


def load_chunks() -> list[dict]:
    if not CHUNKS.exists():
        pytest.skip("corpus not built")
    return [json.loads(l) for l in CHUNKS.read_text(encoding="utf-8").splitlines() if l]


class TestNoLongerRefused:
    """The reported failure: these used to come back as out-of-scope."""

    @pytest.mark.parametrize("q", CARD_SECRET_QUESTIONS)
    def test_card_secret_question_is_answered(self, copilot: DPACopilot, q: str) -> None:
        ans = copilot.ask(q)
        assert not ans.refused, f"refused a data-privacy question: {q!r} -> {ans.answer!r}"
        assert ans.citations, f"answered without citing anything: {q!r}"

    @pytest.mark.parametrize("q", OTHER_FRONTLINE_QUESTIONS)
    def test_other_frontline_question_is_answered(self, copilot: DPACopilot, q: str) -> None:
        ans = copilot.ask(q)
        assert not ans.refused, f"refused a data-privacy question: {q!r}"
        assert ans.citations, f"answered without citing anything: {q!r}"

    def test_the_answer_cites_the_statute_not_just_the_guide(self, copilot: DPACopilot) -> None:
        ans = copilot.ask("pwede ba humingi ng CVV sa customer?")
        cited = {c["doc_id"] for c in ans.citations}
        assert cited & STATUTE_DOCS, (
            f"card-secret answer rested on non-statutory sources only: {cited}"
        )


class TestTheCitedProvisionsAreTheOnesThatDecideIt:
    def test_agent_questions_reach_the_strict_confidentiality_rule(self, copilot: DPACopilot) -> None:
        """RA 10173 Section 20(e) names agents and representatives explicitly."""
        ans = copilot.ask("Can an agent ask the customer for their password?")
        assert "confidentiality" in ans.answer.lower(), ans.answer

    def test_agent_questions_reach_the_security_of_information_section(
        self, copilot: DPACopilot
    ) -> None:
        ans = copilot.ask("yung pin sa likod ng credit card, pwede ba i-ask ng agent?")
        assert "RA-10173" in ans.answer or "IRR-RA10173" in ans.answer, ans.answer

    def test_an_overlap_chunk_is_not_cited_twice(self, copilot: DPACopilot) -> None:
        """Section 20 and Section 20 (cont.) share an overlap window.

        Citing both and printing the same sentence twice under two labels reads
        as the copilot padding its answer.
        """
        ans = copilot.ask("Can I ask the customer for the PIN at the back of their credit card?")
        labels = [c["label"] for c in ans.citations]
        assert len(labels) == len(set(labels)), labels
        quotes = [line.strip() for line in ans.answer.split("\n\n") if "[" in line]
        assert len(quotes) == len(set(quotes)), "the same span was quoted twice"


class TestOperationalBoundary:
    """The honest half: cite what is held, name what is not."""

    @pytest.mark.parametrize("q", CARD_SECRET_QUESTIONS)
    def test_card_secret_answers_state_the_operational_boundary(
        self, copilot: DPACopilot, q: str
    ) -> None:
        ans = copilot.ask(q)
        assert "SCOPE NOTE" in ans.answer, (
            f"gave an unqualified answer to {q!r}; the PCI DSS / BSP rule that "
            "decides it is not in this corpus"
        )
        assert "PCI DSS" in ans.answer
        assert "Bangko Sentral" in ans.answer
        assert "data protection officer" in ans.answer.lower()

    def test_the_scope_note_does_not_fire_on_unrelated_questions(self) -> None:
        assert scope_note_for("Ilang oras dapat ko i-report ang data breach?") is None
        assert scope_note_for("Kailangan ba mag-register ng AI credit scoring model?") is None
        assert scope_note_for("Ano ang stock price ng BDO ngayong araw?") is None

    def test_a_refusal_never_carries_a_scope_note(self, copilot: DPACopilot) -> None:
        ans = copilot.ask("Who won the 2025 FIFA World Cup?")
        assert ans.refused
        assert "SCOPE NOTE" not in ans.answer


class TestTheDomainGateDidNotBecomeAPassThrough:
    """Widening the gate must not turn every question into a privacy question."""

    @pytest.mark.parametrize(
        "q",
        [
            "Magkano ang Porsche 911?",
            "Best pizza recipe near me?",
            "Ano ang stock price ng BDO ngayong araw?",
            "Who won the 2025 FIFA World Cup?",
            "How do I cook adobo?",
            "What is the capital of Kenya?",
        ],
    )
    def test_out_of_domain_still_refuses(self, copilot: DPACopilot, q: str) -> None:
        ans = copilot.ask(q)
        assert ans.refused, f"the domain gate let through {q!r} -> {ans.answer!r}"
        assert not ans.citations


class TestQueryExpansionReachesTheStatute:
    def test_a_card_question_expands_into_statutory_vocabulary(self) -> None:
        tokens = expand_query("pwede ba humingi ng CVV sa customer?")
        assert "cvv" in tokens
        assert "confidentiality" in tokens
        assert "adequate" in tokens and "excessive" in tokens

    def test_expansion_does_not_fire_on_an_unrelated_question(self) -> None:
        tokens = expand_query("Who won the 2025 FIFA World Cup?")
        assert "confidentiality" not in tokens
        assert "cvv" not in tokens

    def test_a_classification_question_reaches_the_spi_provisions(
        self, copilot: DPACopilot
    ) -> None:
        ans = copilot.ask("Is credit card information sensitive personal information?")
        assert not ans.refused
        cited = {c["doc_id"] for c in ans.citations}
        assert cited & {"RA-10173", "IRR-RA10173", "NPC-CIRC-16-03"}, cited


class TestTheOperationalGuideIsHonestAboutItself:
    """The guide is Isla AI's own writing, so it has to label itself as such."""

    def test_the_guide_is_in_the_corpus(self) -> None:
        guide = [c for c in load_chunks() if c["doc_id"] == GUIDE]
        assert guide, "the front-line guide is missing from the corpus"
        assert len(guide) >= 14, f"the guide chunked down to {len(guide)} sections"

    def test_the_guide_can_never_outrank_a_statute(self) -> None:
        assert AUTHORITY_WEIGHT[GUIDE_TYPE] < AUTHORITY_WEIGHT["statute"]
        assert AUTHORITY_WEIGHT[GUIDE_TYPE] < AUTHORITY_WEIGHT["irr"]
        assert AUTHORITY_WEIGHT[GUIDE_TYPE] < AUTHORITY_WEIGHT["circular"]

    def test_every_guide_chunk_declares_its_issuer_as_non_authoritative(self) -> None:
        """The citation chip shows the issuer. It must never read like a regulator."""
        for c in load_chunks():
            if c["doc_id"] == GUIDE:
                assert "not a legal source" in c["issuer"].lower(), c["issuer"]
                assert "privacy.gov.ph" not in c["url"]
                assert c["url"].startswith("isla-ai://"), c["url"]

    def test_the_guide_states_it_is_not_a_legal_source(self) -> None:
        raw = (REPO / "corpus" / "raw" / "ISLA-GUIDE-CS.md").read_text(encoding="utf-8")
        # Whitespace is normalised because the source is hard-wrapped at ~78
        # columns and the chunker normalises it too; a hard-wrapped phrase is
        # not an absent one.
        flat = " ".join(raw.split()).lower()
        assert "not a legal source" in flat[:1200]
        assert "must never" in flat[:1200]
        assert "internal operational aid" in flat[:1200]

    def test_the_guide_does_not_invent_bsp_circular_numbers(self) -> None:
        """It says BSP regulations govern and declines to guess which ones."""
        raw = (REPO / "corpus" / "raw" / "ISLA-GUIDE-CS.md").read_text(encoding="utf-8")
        flat = " ".join(raw.split())
        assert "not guess at them" in flat
        # No fabricated circular/memorandum number for BSP.
        import re

        assert not re.search(r"\bBSP\s+(?:Circular|Memorandum|Memo)\s+No\.?\s*\d", flat)
        assert not re.search(r"\bM-\d{4}-\d{3}\b", flat)

    def test_the_guide_points_at_pci_dss_without_reproducing_it(self) -> None:
        raw = (REPO / "corpus" / "raw" / "ISLA-GUIDE-CS.md").read_text(encoding="utf-8")
        flat = " ".join(raw.split())
        assert "PCI" in flat
        assert "no text from it is reproduced" in flat

    def test_the_guide_is_tier_three_not_primary_authority(self) -> None:
        for c in load_chunks():
            if c["doc_id"] == GUIDE:
                assert c["authority_tier"] == 3, c["authority_tier"]