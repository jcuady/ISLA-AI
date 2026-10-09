"""Build the labelled Philippine PII evaluation set.

Hand-built from realistic artefacts a bank actually produces: a collections
ticket, a bank email, a remittance slip, a CDR, an ops chat message. Published
with the repo so the scoreboard is reproducible and checkable by judges.

Each record carries the exact surface forms that make Philippine PII hard:
Taglish digit spacing, GCash-as-mobile, remittance references, and bare 10-digit
strings that must NOT be redacted.
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "datasets" / "pii_ph.jsonl"

# (text, [(expected_entity_type, expected_substring), ...])
CASES: list[tuple[str, list[tuple[str, str]]]] = [
    # ---------------------------------------------------------------- SSS
    ("Kustomer ay may SSS 12-345-6789 na nakaparehistro.", [("PH_SSS", "12-345-6789")]),
    ("Please verify SSS 123-45-6789 before releasing the loan.", [("PH_SSS", "123-45-6789")]),
    # A Philippine SSS is NINE digits. "523 456 7890" is ten and is therefore a
    # reference number, not an SSS - the label here is the spaced 3-3-3 form.
    ("Record update: SSS 523 456 789.", [("PH_SSS", "523 456 789")]),
    ("Ten-digit run that is NOT an SSS: 523 456 7890.", []),
    # ---------------------------------------------------------------- TIN
    ("TIN 456-789-012 is on file for this corporation.", [("PH_TIN", "456-789-012")]),
    ("Taxpayer identification number: 123-456-789.", [("PH_TIN", "123-456-789")]),
    ("TIN 987-654-321 registered to the branch.", [("PH_TIN", "987-654-321")]),
    # ---------------------------------------------------------------- PAN
    ("Card on file: 4539578763621486.", [("CARD_PAN", "4539578763621486")]),
    ("Credit card 4111 1111 1111 1111 was declined.", [("CARD_PAN", "4111 1111 1111 1111")]),
    ("Visa 4012888888881881 exp 09/28.", [("CARD_PAN", "4012888888881881")]),
    # 6011000000000004 is a genuine Luhn-valid Mastercard test PAN. Using a real
    # checksum-valid number matters: the Luhn pass-rate gate measures whether the
    # PANs KALIX flags are genuine, so fabricated 16-digit strings would make the
    # metric meaningless.
    ("GCash card number 6011000000000004 charged twice.", [("CARD_PAN", "6011000000000004")]),
    # ---------------------------------------------------------------- CVV
    ("CVV: 456 on the back of the card.", [("CARD_CVV", "456")]),
    ("Security code 789 belongs to this card.", [("CARD_CVV", "789")]),
    # ---------------------------------------------------------------- mobile
    ("Reach the customer at 0917 123 4567.", [("PH_MOBILE", "0917 123 4567")]),
    ("Mobile number +63 917 555 0199.", [("PH_MOBILE", "+63 917 555 0199")]),
    ("Contact 639175550199 during business hours.", [("PH_MOBILE", "639175550199")]),
    ("Text the borrower at 0922 445 6677 today.", [("PH_MOBILE", "0922 445 6677")]),
    # ---------------------------------------------------------------- GCash
    ("Send the refund to GCash number 09181234567.", [("GCASH_MOBILE", "09181234567")]),
    ("Maya wallet registered as 0917 333 4444.", [("GCASH_MOBILE", "0917 333 4444")]),
    # ------------------------------------------------------------- accounts
    ("Account number: 0056-12345678 is the subject of the complaint.",
     [("BANK_ACCOUNT", "0056-12345678")]),
    ("Debit the account no. 001234567890 please.", [("BANK_ACCOUNT", "001234567890")]),
    # ------------------------------------------------------------ remittance
    ("Remittance via Cebuana Lhuillier ref #CEB-88213-4455 was released.",
     [("REMITTANCE_REF", "CEB-88213-4455")]),
    ("Western Union reference WU-4471200 to the recipient.",
     [("REMITTANCE_REF", "WU-4471200")]),
    # ------------------------------------------------------------ PhilSys/passport
    ("PhilSys ID 1234-5678-9012-3456 presented at branch.",
     [("PHILSYS_ID", "1234-5678-9012-3456")]),
    ("Passport P1234567A expires next year.", [("PASSPORT", "P1234567A")]),
    ("Forward the complaint from juan.delacruz@usapalmabank.com.ph.",
     [("EMAIL", "juan.delacruz@usapalmabank.com.ph")]),
    # ---------------------------------------------------------------- salary
    ("Monthly salary PHP 42,500 was credited last payday.", [("SALARY", "42,500")]),
    ("Basic pay: 185,000 per month.", [("SALARY", "185,000")]),
    # ----------------------------------------------------- realistic narrative
    (
        "Magandang araw po Maria. Nag-apply po ng overdue notice si Maria Concepcion "
        "de los Santos, SSS 12-345-6789, TIN 456-789-012. Registered mobile "
        "0917 123 4567, GCash number +639171234568. Credit card ending "
        "4539578763621486, CVV 123. Account number: 0056-12345678. Monthly salary "
        "PHP 42,500. Pakisuri na po bago mag-escalate.",
        [
            ("PH_SSS", "12-345-6789"),
            ("PH_TIN", "456-789-012"),
            ("GCASH_MOBILE", "0917 123 4567"),
            ("GCASH_MOBILE", "+639171234568"),
            ("CARD_PAN", "4539578763621486"),
            ("CARD_CVV", "123"),
            ("BANK_ACCOUNT", "0056-12345678"),
            ("SALARY", "42,500"),
        ],
    ),
    # An outstanding BALANCE is a debt figure, not employment data, so it must
    # not be redacted as salary.
    (
        "Collections ticket CDR-2024-8891. Borrower: D Dela Cruz. "
        "Contact 0928 777 1234. Outstanding balance PHP 18,450.00. Sent via SMS.",
        [("PH_MOBILE", "0928 777 1234")],
    ),
    # ============================================================ NEGATIVES
    # These must NOT be redacted. A redactor that mangles these is unusable.
    ("Please process invoice INV-2024-00123456 for batch 20240315.", []),
    ("Order reference 9988776655443 was shipped yesterday.", []),
    ("Terminal ID 12-34567 printed the receipt.", []),
    ("Jealousy ng customer ay malaking bagay, ayon sa Santos (2024).", []),
    ("The meeting is scheduled for 2024-03-15 at 09:00 in Room 3.", []),
    ("Our BIC code is PHPBGSH but the branch code is 12-34567.", []),
    ("Total of PHP 1,250.50 was charged to the account this month.", []),
    ("Republic Act No. 10173 is the Data Privacy Act of 2012.", []),
    ("Please update the customer about the new product launch.", []),
    ("Ate, pwede bang i-advance yung salary loan ko?", []),
]


def build() -> list[dict]:
    records = []
    for i, (text, expectations) in enumerate(CASES):
        records.append(
            {
                "id": f"ph-{i:03d}",
                "text": text,
                "expect": [{"type": t, "value": v} for t, v in expectations],
                "is_negative": not expectations,
            }
        )
    return records


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    records = build()
    with OUT.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    positives = sum(1 for r in records if not r["is_negative"])
    total_expected = sum(len(r["expect"]) for r in records)
    print(f"wrote {len(records)} cases to {OUT.name}")
    print(f"  positives: {positives}   negatives: {len(records) - positives}")
    print(f"  total expected entity spans: {total_expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())