"""Integration tests for retrieval, citation enforcement, refusal, and the ledger."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.core.airgap import assert_loopback, run_probe  # noqa: E402
from services.core.ledger import AuditLedger  # noqa: E402
from services.copilot.copilot import DPACopilot  # noqa: E402
from services.copilot.retrieval import HybridIndex  # noqa: E402

DEMO_QUERIES = [
    "Pwede ba ipasa ang CDR ng customer ko sa vendor namin sa Singapore?",
    "Ilang oras dapat ko i-report ang data breach?",
    "Kailangan ba mag-register ng AI credit scoring model ang banko namin?",
    "May karapatang humingi ng data ng customer ko ang collection agency?",
    "Ilang taon dapat itinatago ang transaction records?",
    "Can our call center use AI to score our agents?",
]

OUT_OF_DOMAIN = [
    "Ano ang stock price ng BDO ngayong araw?",
    "Who won the 2025 FIFA World Cup?",
    "What is the capital of Kenya?",
    "How do I cook adobo?",
    "Best pizza recipe near me?",
]


@pytest.fixture(scope="module")
def index() -> HybridIndex:
    idx = HybridIndex()
    idx.enable_dense()  # no-op when the model is absent
    return idx


@pytest.fixture(scope="module")
def copilot(index: HybridIndex) -> DPACopilot:
    return DPACopilot(index)


class TestRetrieval:
    def test_corpus_loaded(self, index: HybridIndex) -> None:
        stats = index.stats()
        assert stats["chunks"] > 150
        assert stats["documents"] >= 6

    def test_breach_query_retrieves_the_right_document(self, index: HybridIndex) -> None:
        hits = index.search("Ilang oras dapat ko i-report ang data breach?", top_k=12)
        assert hits
        assert any(h.chunk["doc_id"] == "NPC-CIRC-16-03" for h in hits)

    def test_authority_weighting_applied(self, index: HybridIndex) -> None:
        hits = index.search("data privacy law", top_k=10)
        for h in hits:
            assert 0.5 <= h.authority <= 1.0


class TestCopilot:
    @pytest.mark.parametrize("q", DEMO_QUERIES)
    def test_demo_queries_answer_with_citations(self, copilot: DPACopilot, q: str) -> None:
        answer = copilot.ask(q)
        assert not answer.refused, f"unexpected refusal: {q}"
        assert len(answer.citations) > 0, f"no citation for: {q}"

    def test_answer_always_carries_a_citation_tag(self, copilot: DPACopilot) -> None:
        for q in DEMO_QUERIES:
            answer = copilot.ask(q)
            assert "[" in answer.answer and "]" in answer.answer

    def test_breach_answer_states_72_hours(self, copilot: DPACopilot) -> None:
        answer = copilot.ask("Ilang oras dapat ko i-report ang data breach?")
        assert not answer.refused
        assert "72 hour" in answer.answer.lower()

    @pytest.mark.parametrize("q", OUT_OF_DOMAIN)
    def test_out_of_domain_refuses(self, copilot: DPACopilot, q: str) -> None:
        answer = copilot.ask(q)
        assert answer.refused, f"should have refused: {q}"
        assert answer.citations == []

    def test_empty_question_refuses(self, copilot: DPACopilot) -> None:
        assert copilot.ask("   ").refused

    def test_answer_is_json_serialisable(self, copilot: DPACopilot) -> None:
        """Regression: numpy float32 from the dense leg broke the ledger hash."""
        import json

        for q in DEMO_QUERIES + OUT_OF_DOMAIN:
            json.dumps(copilot.ask(q).to_dict())

    def test_footers_present(self, copilot: DPACopilot) -> None:
        assert "Not a substitute for legal advice" in copilot.ask(DEMO_QUERIES[0]).footer


class TestAirGap:
    def test_refuses_routable_bind(self) -> None:
        with pytest.raises(RuntimeError):
            assert_loopback("0.0.0.0")

    def test_allows_loopback(self) -> None:
        assert_loopback("127.0.0.1")  # must not raise

    def test_probe_reports_observed_results(self) -> None:
        result = run_probe("127.0.0.1")
        assert result.bind_host == "127.0.0.1"
        assert isinstance(result.air_gapped, bool)
        # The badge must be derived from real attempts, so probes must exist.
        assert result.probes
        assert result.note


class TestLedger:
    def test_chain_verifies(self, tmp_path: Path) -> None:
        ledger = AuditLedger(tmp_path / "l.jsonl")
        for i in range(5):
            ledger.append("test_event", {"i": i, "verdict": "SAFE_TO_SEND"})
        result = ledger.verify()
        assert result["valid"] is True
        assert result["entries"] == 5

    def test_tampering_is_detected(self, tmp_path: Path) -> None:
        """Alter a historical record; the chain must break at that sequence."""
        import json

        ledger = AuditLedger(tmp_path / "l.jsonl")
        for i in range(4):
            ledger.append("test_event", {"i": i})

        # Rewrite history: change entry 1's payload without re-hashing it.
        lines = (tmp_path / "l.jsonl").read_text(encoding="utf-8").splitlines()
        record = json.loads(lines[1])
        record["summary"]["i"] = 999          # tampered
        lines[1] = json.dumps(record, ensure_ascii=False)
        (tmp_path / "l.jsonl").write_text("\n".join(lines), encoding="utf-8")

        reopened = AuditLedger(tmp_path / "l.jsonl")
        result = reopened.verify()
        assert result["valid"] is False
        assert result["broken_at"] == 1

    def test_handles_numpy_scalars(self, tmp_path: Path) -> None:
        """Regression: a numpy float must never be able to fail an audit append."""
        import numpy as np

        ledger = AuditLedger(tmp_path / "l.jsonl")
        ledger.append("copilot_answer", {"confidence": np.float32(0.7271)})
        assert ledger.verify()["valid"] is True

    def test_stats_report_no_raw_pii(self, tmp_path: Path) -> None:
        ledger = AuditLedger(tmp_path / "l.jsonl")
        ledger.append("pii_redaction", {"entities_redacted": 8})
        stats = ledger.stats()
        assert stats["contains_raw_pii"] is False
        assert stats["total"] == 1