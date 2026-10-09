"""Unit tests for the deterministic Philippine PII recognizers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.pii.recognizers import (  # noqa: E402
    detect_regex,
    luhn_ok,
    mask_tokens,
    normalize_ph_mobile,
)


def types_found(text: str) -> set[str]:
    return {e.entity_type.value for e in detect_regex(text)}


def spans_for(text: str, etype: str) -> list[str]:
    return [e.text for e in detect_regex(text) if e.entity_type.value == etype]


class TestLuhn:
    @pytest.mark.parametrize("pan", ["4539578763621486", "4111111111111111", "4012888888881881"])
    def test_valid_pans(self, pan: str) -> None:
        assert luhn_ok(pan)

    @pytest.mark.parametrize("pan", ["4539578763621487", "1234567890123456"])
    def test_mutated_pans_rejected(self, pan: str) -> None:
        assert not luhn_ok(pan)

    def test_wrong_length_rejected(self) -> None:
        assert not luhn_ok("123456789012")     # 12 digits
        assert not luhn_ok("12345678901234567890123")  # 23 digits


class TestMobileNormalisation:
    @pytest.mark.parametrize(
        "raw",
        ["0917 123 4567", "0917-123-4567", "+639171234567", "639171234567", "+63 917 123 4567"],
    )
    def test_taglish_forms_are_one_entity(self, raw: str) -> None:
        assert normalize_ph_mobile(raw) == "+639171234567"


class TestSSS:
    @pytest.mark.parametrize("sss", ["123-45-6789", "12-345-6789", "523 456 789"])
    def test_dashed_and_spaced_forms(self, sss: str) -> None:
        assert sss in spans_for(f"SSS {sss}", "PH_SSS")

    def test_bare_nine_digits_needs_context(self) -> None:
        assert "523456789" not in spans_for("Reference 523456789", "PH_SSS")
        assert "523456789" in spans_for("SSS 523456789", "PH_SSS")

    def test_ten_digit_run_is_not_an_sss(self) -> None:
        # Ten digits is a reference number, not an SSS.
        assert "523 456 7890" not in spans_for("SSS 523 456 7890", "PH_SSS")


class TestPrecision:
    @pytest.mark.parametrize(
        "text",
        [
            "Please process invoice INV-2024-00123456 for batch 20240315.",
            "Order reference 9988776655443 was shipped yesterday.",
            "Terminal ID 12-34567 printed the receipt.",
            "Republic Act No. 10173 is the Data Privacy Act of 2012.",
            "The meeting is scheduled for 2024-03-15 at 09:00 in Room 3.",
        ],
    )
    def test_negatives_stay_clean(self, text: str) -> None:
        from services.pii.recognizers import HIGH_RISK_TYPES

        found = {e.entity_type.value for e in detect_regex(text)} & HIGH_RISK_TYPES
        assert not found, f"false positive in {text!r}: {found}"

    def test_balance_is_not_salary(self) -> None:
        assert "18,450.00" not in spans_for(
            "Outstanding balance PHP 18,450.00.", "SALARY"
        )

    def test_salary_is_salary(self) -> None:
        assert "42,500" in spans_for("Monthly salary PHP 42,500", "SALARY")


class TestContextualTypes:
    def test_gcash_is_distinguished_from_mobile(self) -> None:
        wallet = types_found("Send to GCash number 09181234567")
        plain = types_found("Reach me at 09181234567")
        assert "GCASH_MOBILE" in wallet
        assert "PH_MOBILE" in plain

    def test_remittance_reference(self) -> None:
        assert "CEB-88213-4455" in spans_for(
            "Remittance via Cebuana Lhuillier ref #CEB-88213-4455 was released.",
            "REMITTANCE_REF",
        )

    def test_passport_requires_context(self) -> None:
        assert "P1234567A" in spans_for("Passport P1234567A expires next year.", "PASSPORT")

    def test_cvv_requires_context(self) -> None:
        assert "456" in spans_for("CVV: 456 on the back of the card.", "CARD_CVV")


class TestTokenMasking:
    def test_tokens_are_masked_before_detection(self) -> None:
        masked, spans = mask_tokens("Call [PHONE-9C1E] about [PAN-4F2A]")
        assert len(spans) == 2
        assert "PHONE" not in masked

    def test_masking_preserves_offsets(self) -> None:
        original = "a [PHONE-9C1E] b"
        masked, _ = mask_tokens(original)
        assert len(masked) == len(original)