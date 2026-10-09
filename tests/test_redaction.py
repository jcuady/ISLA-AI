"""Tests for the redaction pipeline, verification pass, and verdict logic.

The verification pass is the product's central safety claim: "0.00% residual
leakage" is only meaningful if the loop actually converges and a resistant
string escalates rather than being released.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.pii.engine import EgressGuard, Verdict, pseudonym  # noqa: E402
from services.pii.recognizers import HIGH_RISK_TYPES  # noqa: E402

BANK_EMAIL = """From: Collections Team <collections@usapalmabank.com.ph>
Subject: Urgent - overdue notice for DELOS SANTOS, Maria Concepcion

Nag-apply po ng overdue notice si Maria Concepcion de los Santos.
SSS 12-345-6789, TIN 456-789-012.
Registered mobile 0917 123 4567, GCash number +639171234568.
Credit card ending 4539578763621486, CVV 123, exp 09/28.
Account number: 0056-12345678. Monthly salary PHP 42,500.
Remittance via Cebuana Lhuillier ref #CEB-88213-4455.
"""


@pytest.fixture(scope="module")
def guard() -> EgressGuard:
    return EgressGuard()


class TestRedaction:
    def test_every_entity_is_redacted(self, guard: EgressGuard) -> None:
        result = guard.scan(BANK_EMAIL)
        for value in [
            "12-345-6789", "456-789-012", "0917 123 4567", "+639171234568",
            "4539578763621486", "123", "0056-12345678", "42,500", "CEB-88213-4455",
        ]:
            assert value not in result.redacted, f"{value} survived redaction"

    def test_verdict_blocks_on_card_bundle(self, guard: EgressGuard) -> None:
        assert guard.scan(BANK_EMAIL).verdict is Verdict.BLOCK_ESCALATE

    def test_safe_text_passes_through(self, guard: EgressGuard) -> None:
        clean = "Please process invoice INV-2024-00123456 for batch 20240315."
        result = guard.scan(clean)
        assert result.verdict is Verdict.SAFE_TO_SEND
        assert result.redacted == clean
        assert result.redaction_map == []

    def test_partial_risk_is_redact_not_block(self, guard: EgressGuard) -> None:
        result = guard.scan("Reach the customer at 0917 123 4567.")
        assert result.verdict is Verdict.REDACT_THEN_SEND

    def test_person_names_are_not_auto_redacted(self, guard: EgressGuard) -> None:
        # Philippine names are ubiquitous; redacting them destroys every message.
        text = "Maria Concepcion de los Santos called about her account."
        assert "Maria" in guard.scan(text).redacted


class TestVerificationPass:
    def test_converges_within_budget(self, guard: EgressGuard) -> None:
        result = guard.scan(BANK_EMAIL)
        assert result.verified_clean is True
        assert result.residual_leakage == 0.0
        assert 1 <= result.passes <= 3

    def test_residual_detection_escalates(self, guard: EgressGuard) -> None:
        # A detector that keeps flagging after redaction must force BLOCK rather
        # than releasing text that still trips the scanner.
        from services.pii.engine import decide_verdict
        from services.pii.recognizers import Entity, EntityType

        stubborn = [
            Entity(
                entity_type=EntityType.PH_SSS,
                start=0,
                end=5,
                text="12345",
                score=0.9,
                stage="regex",
                validated=True,
            )
        ]
        verdict, notes = decide_verdict(stubborn, verified_clean=False, residual=stubborn)
        assert verdict is Verdict.BLOCK_ESCALATE
        assert notes

    def test_redaction_is_idempotent(self, guard: EgressGuard) -> None:
        once = guard.scan(BANK_EMAIL).redacted
        twice = guard.scan(once).redacted
        assert once == twice


class TestPseudonym:
    def test_same_input_same_token(self) -> None:
        from services.pii.recognizers import EntityType

        a = pseudonym(EntityType.PH_MOBILE, "09171234567")
        b = pseudonym(EntityType.PH_MOBILE, "09171234567")
        assert a == b

    def test_different_input_different_token(self) -> None:
        from services.pii.recognizers import EntityType

        a = pseudonym(EntityType.PH_MOBILE, "09171234567")
        b = pseudonym(EntityType.PH_MOBILE, "09171234568")
        assert a != b

    def test_token_is_tagged(self) -> None:
        from services.pii.recognizers import EntityType

        assert pseudonym(EntityType.CARD_PAN, "4539578763621486").startswith("[PAN-")