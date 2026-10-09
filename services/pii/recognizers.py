"""Deterministic Philippine PII recognizers.

Stage 1 of the Egress Guard ensemble. These are regex + checksum validators that
run in microseconds and carry the structured identifiers that make up almost all
high-risk leakage in a bank: SSS, TIN, card PAN, mobile numbers, GCash numbers.

Design note: the "PH gotchas" called out in the brief are handled explicitly here
rather than left to the neural stage:
  * A GCash/e-wallet account IS the mobile number - no separate marker, so it gets
    its own label driven by nearby context.
  * Remittance references (Cebuana Lhuillier / Western Union / Palawan) identify
    people indirectly and no generic NER covers them.
  * Taglish digit spacing ("09 17 123 4567") must normalise to the same entity as
    "+63 917 123 4567".
  * PERSON is a *risk signal*, not an auto-redaction trigger - Philippine names
    ("de la Cruz", "Santos") are extremely common and redacting them destroys
    every message.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class EntityType(str, Enum):
    """Regulated Philippine banking PII types."""

    PH_SSS = "PH_SSS"
    PH_TIN = "PH_TIN"
    CARD_PAN = "CARD_PAN"
    CARD_CVV = "CARD_CVV"
    PH_MOBILE = "PH_MOBILE"
    GCASH_MOBILE = "GCASH_MOBILE"
    EMAIL = "EMAIL"
    PH_IBAN = "PH_IBAN"
    BANK_ACCOUNT = "BANK_ACCOUNT"
    REMITTANCE_REF = "REMITTANCE_REF"
    PASSPORT = "PASSPORT"
    DRIVERS_LICENSE = "DRIVERS_LICENSE"
    PHILSYS_ID = "PHILSYS_ID"
    PERSON = "PERSON"  # risk signal only - never auto-redacted
    DATE_OF_BIRTH = "DATE_OF_BIRTH"
    HOME_ADDRESS = "HOME_ADDRESS"
    SALARY = "SALARY"


# Types that must be redacted. PERSON is deliberately absent.
HIGH_RISK_TYPES = frozenset(
    {
        EntityType.PH_SSS,
        EntityType.PH_TIN,
        EntityType.CARD_PAN,
        EntityType.CARD_CVV,
        EntityType.PH_MOBILE,
        EntityType.GCASH_MOBILE,
        EntityType.EMAIL,
        EntityType.PH_IBAN,
        EntityType.BANK_ACCOUNT,
        EntityType.REMITTANCE_REF,
        EntityType.PASSPORT,
        EntityType.DRIVERS_LICENSE,
        EntityType.PHILSYS_ID,
        EntityType.DATE_OF_BIRTH,
        EntityType.HOME_ADDRESS,
        EntityType.SALARY,
    }
)


@dataclass
class Entity:
    """One detected entity with its provenance and confidence inputs."""

    entity_type: EntityType
    start: int
    end: int
    text: str
    score: float
    stage: str  # "regex" | "ner" | "ensemble"
    validated: bool = False  # checksum passed (Luhn) or well-formed
    context_boost: float = 0.0
    raw_score: float = 0.0
    reasons: list[str] = field(default_factory=list)

    @property
    def length(self) -> int:
        return self.end - self.start


# --------------------------------------------------------------------------
# Checksums
# --------------------------------------------------------------------------

def luhn_ok(digits: str) -> bool:
    """Validate a card PAN. The cheapest precision win available - rejects
    random 13-19 digit strings that the PAN regex would otherwise match."""
    nums = [int(c) for c in re.sub(r"\D", "", digits)]
    if not 13 <= len(nums) <= 19:
        return False
    checksum, parity = 0, len(nums) % 2
    for i, n in enumerate(nums):
        if i % 2 == parity:
            n *= 2
            if n > 9:
                n -= 9
        checksum += n
    return checksum % 10 == 0


def normalize_ph_mobile(raw: str) -> str | None:
    """Canonicalise any Taglish mobile spelling to +639XXXXXXXXX.

    '09 17 123 4567', '+63 917 123 4567' and '639171234567' are one entity.
    A Philippine mobile has 10 national digits (9 + 9 more), so the international
    form carries a 12-digit body: 63 + 10 digits.
    """
    digits = re.sub(r"\D", "", raw)

    # 63 + 10 national digits -> 12 digits total.
    if len(digits) == 12 and digits.startswith("63"):
        return "+63" + digits[2:]

    # 11 digits, domestic 0-prefix: 0 + 917 + 7 more = 0917 123 4567.
    # The national number is 09171234567; dropping the leading "0" and adding
    # the country code gives +639171234567.
    if len(digits) == 11 and digits.startswith("09"):
        return "+63" + digits[1:]

    # 10 national digits, no prefix.
    if len(digits) == 10 and digits.startswith("9"):
        return "+63" + digits

    # 11 digits with 63 prefix but no country code (63 + 9 digits).
    if len(digits) == 11 and digits.startswith("63"):
        return "+63" + digits[2:]

    return None


# --------------------------------------------------------------------------
# Patterns
# --------------------------------------------------------------------------

PH_MOBILE_RE = re.compile(
    r"(?<![\d+])(?:\+?63[\s\-]?|0)9\d{2}[\s\-]?\d{3}[\s\-]?\d{4}(?![\d])"
)
# GCash / e-wallet: the number is indistinguishable from a mobile, so context decides.
GCASH_CONTEXT_RE = re.compile(
    r"\b(?:gcash|gc\s?cash|maya|palawan\s?express|wallet|e-?wallet|"
    r"paymaya|metrobank\s?wallet|bdminfo|bdo\s?pay|instapay)\b",
    re.IGNORECASE,
)
# SSS surface forms seen in the wild: 3-2-4 (canonical), 2-3-4, 3-3-4 with
# spaces, and bare 9 digits. Anchored so a 10-digit account number never matches.
SSS_RE = re.compile(
    r"(?<![\d-])(?:"
    r"\d{3}-\d{2}-\d{4}"          # 123-45-6789
    r"|\d{2}-\d{3}-\d{4}"         # 12-345-6789
    r"|\d{3} \d{3} \d{3}"         # 523 456 7890
    r"|\d{9}(?![\d-])"            # bare 9
    r")(?![\d-])"
)
TIN_RE = re.compile(
    r"(?<![\d-])(?:\d{3}-\d{3}-\d{3}(?:-\d{1,4})?|\d{9}(?:-\d{1,4})?)(?![\d-])"
)
CARD_PAN_RE = re.compile(r"(?<![\d])(?:\d[ \-]?){12,18}\d(?![\d])")
CVV_RE = re.compile(
    r"\b(?:cvv|cvc|cvv2|security\s+code|card\s+verification)\b\s*[:=#]?\s*(\d{3,4})\b",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PH_IBAN_RE = re.compile(r"\bPH\d{2}[A-Z]{3}\d{10,18}\b")
# Bank account numbers are usually labelled rather than self-identifying.
BANK_ACCT_CONTEXT_RE = re.compile(
    r"(?:account\s*(?:no|number|#)?|acct\s*(?:no|number)?|a/c\s*(?:no)?|"
    r"kas account|account)\s*[:.#-]?\s*([0-9][0-9\-\s]{5,20}[0-9])",
    re.IGNORECASE,
)
REMITTANCE_RE = re.compile(
    r"(?:cebuana(?:\s+lhuillier)?|western\s+union|\bwu\b|palawan(?:'s)?\s+express|"
    r"moneygram|remittance|padala)\s*(?:ref(?:erence)?|control\s*number|ctr|for)?\s*"
    r"[:#-]?\s*([A-Z0-9][A-Z0-9\-]{4,24})",
    re.IGNORECASE,
)
PASSPORT_RE = re.compile(r"\b[A-Z]\d{7}[A-Z]\b|\b[A-Z]{2}\d{7}[A-Z]?\b")
DL_LICENSE_RE = re.compile(
    r"\b[A-Z]{2}\d{2}[-\s]?\d{3,4}\b|\b\d{2}[-\s]\d{3}[-\s]\d{4}\b"
)
PHILSYS_RE = re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{4}\b")
DOB_CONTEXT_RE = re.compile(
    r"\b(?:DOB|D\.O\.B|born|birthdate|birth\s*date|date\s+of\s+birth)\b",
    re.IGNORECASE,
)
DOB_RE = re.compile(
    r"\b(?:DOB|D\.O\.B\.?|born|birthdate)?\s*[:\-]?\s*"
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}|"
    r"\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})\b",
    re.IGNORECASE,
)
ADDRESS_CONTEXT_RE = re.compile(
    r"\b(?:address|addressing|residing\s+at|living\s+at|addr)\b\s*[:\-]?\s*"
    r"([^\n.,;]{6,90})",
    re.IGNORECASE,
)
SALARY_RE = re.compile(
    r"(?:₱|PHP|P|PhP)\s?([\d,]{4,}(?:\.\d{2})?)\s*(?:k\b|thousand|per\s+month|"
    r"monthly|mo\b|a\s+month|annually|/mo|/month)?|"
    r"(?:monthly\s+salary|salary|basic\s+pay|compensation)\s*(?:is|:|=)?\s*"
    r"(?:₱|PHP|P)?\s?([\d,]{4,}(?:\.\d{2})?)",
    re.IGNORECASE,
)

# Tokens that must NOT be treated as SSS/PAN even though they look numeric.
ORDER_CONTEXT_RE = re.compile(
    r"\b(?:invoice|inv|order|ref|reference|receipt|or#|transaction|txn|"
    r"terminal|merchant|acct\s*ending|batch|journal|document)\b",
    re.IGNORECASE,
)

# KALIX redaction tokens look like ordinary text to every recognizer above.
# Every stage masks these spans BEFORE matching, so the verification pass can
# never "rediscover" what we already redacted and spin to BLOCK_ESCALATE.
REDACTION_TOKEN_RE = re.compile(r"\[[A-Z]{2,10}-[0-9A-F]{4,}\]")


def mask_tokens(text: str) -> tuple[str, list[tuple[int, int]]]:
    """Replace existing [TAG-HASH] tokens with spaces, preserving offsets.

    Returns the masked string and the spans occupied by tokens. Detection is
    performed on the masked copy; offsets map straight back to the original.
    """
    spans: list[tuple[int, int]] = []
    if not text:
        return text, spans
    chars = list(text)
    for m in REDACTION_TOKEN_RE.finditer(text):
        spans.append((m.start(), m.end()))
        for i in range(m.start(), m.end()):
            chars[i] = " "
    return "".join(chars), spans


def _context_window(text: str, start: int, end: int, pad: int = 60) -> str:
    return text[max(0, start - pad) : min(len(text), end + pad)]


def detect_regex(text: str) -> list[Entity]:
    """Stage 1: deterministic recognizers over the whole string.

    Order matters: higher-precision formats claim their character spans first,
    so an SSS like 12-345-6789 is not also reported as a TIN.
    """
    found: list[Entity] = []
    claimed: list[tuple[int, int]] = []

    # Already-redacted KALIX tokens are masked out so the verification pass can
    # never re-detect its own output and escalate to BLOCK_ESCALATE.
    haystack, _token_spans = mask_tokens(text)

    def claimed_by(start: int, end: int) -> bool:
        return any(s < end and start < e for s, e in claimed)

    def claim(start: int, end: int) -> None:
        claimed.append((start, end))

    def add(etype, s, e, score, validated, ctx=0.0, reasons=None):
        found.append(
            Entity(
                entity_type=etype,
                start=s,
                end=e,
                text=text[s:e],
                score=score,
                stage="regex",
                validated=validated,
                context_boost=ctx,
                reasons=list(reasons or []),
            )
        )

    for m in EMAIL_RE.finditer(haystack):
        add(EntityType.EMAIL, m.start(), m.end(), 0.99, True, reasons=["regex"])
        claim(m.start(), m.end())

    for m in PH_IBAN_RE.finditer(haystack):
        add(EntityType.PH_IBAN, m.start(), m.end(), 0.95, True, reasons=["regex"])
        claim(m.start(), m.end())

    for m in PH_MOBILE_RE.finditer(haystack):
        canon = normalize_ph_mobile(m.group())
        window = _context_window(haystack, m.start(), m.end())
        is_wallet = bool(GCASH_CONTEXT_RE.search(window))
        add(
            EntityType.GCASH_MOBILE if is_wallet else EntityType.PH_MOBILE,
            m.start(),
            m.end(),
            0.96 if is_wallet else 0.95,
            canon is not None,
            0.05 if is_wallet else 0.0,
            ["regex", "wallet-context" if is_wallet else "mobile"],
        )
        claim(m.start(), m.end())

    # SSS before TIN: both accept dashed forms and the shapes overlap, so the
    # higher-precision SSS pattern runs first and claims its span.
    # Note: an SSS is NINE digits (unlike a US SSN's nine - but commonly written
    # 3-2-4 or 2-3-4 with dashes), which is why a bare 10-digit guard is wrong here.
    for m in SSS_RE.finditer(haystack):
        if claimed_by(m.start(), m.end()):
            continue
        raw = re.sub(r"\D", "", m.group())
        if len(raw) != 9:
            continue
        window = _context_window(haystack, m.start(), m.end())
        sss_ctx = bool(re.search(r"\b(?:sss|social\s+security)\b", window, re.I))
        raw = m.group()
        dashed = "-" in raw
        spaced = " " in raw
        # A bare/space-separated 9-digit run is indistinguishable from an account
        # number, so it needs explicit SSS context. Dashed forms are canonical.
        if not (dashed or sss_ctx):
            if not (spaced and sss_ctx):
                continue
        add(
            EntityType.PH_SSS,
            m.start(),
            m.end(),
            0.97,
            True,
            0.05 if sss_ctx else 0.0,
            ["regex", "sss-context"] if sss_ctx else ["regex", "sss-dashed"],
        )
        claim(m.start(), m.end())

    for m in TIN_RE.finditer(haystack):
        if claimed_by(m.start(), m.end()):
            continue
        raw = re.sub(r"\D", "", m.group())
        if len(raw) not in (9, 10, 11, 12, 13):
            continue
        window = _context_window(haystack, m.start(), m.end())
        tin_ctx = bool(
            re.search(r"\b(?:tin|tax\s*id(?:entification)?(?:\s*number)?)\b", window, re.I)
        )
        dashed = "-" in m.group()
        if not (tin_ctx or dashed):
            continue  # bare 9-digit run: too ambiguous to auto-redact
        add(
            EntityType.PH_TIN,
            m.start(),
            m.end(),
            0.96 if tin_ctx else 0.92,
            True,
            0.05 if tin_ctx else 0.0,
            ["regex", "tin-context"] if tin_ctx else ["regex", "tin-dashed"],
        )
        claim(m.start(), m.end())

    for m in CARD_PAN_RE.finditer(haystack):
        if claimed_by(m.start(), m.end()):
            continue
        valid = luhn_ok(m.group())
        digits_only = re.sub(r"\D", "", m.group())
        window = _context_window(haystack, m.start(), m.end())
        card_ctx = bool(
            re.search(
                r"\b(?:card|credit|debit|mastercard|master|visa|gcash|bdo|gcash\s+card|"
                r"pan|exp(?:iry)?|magstripe|credit\s*card)\b",
                window,
                re.I,
            )
        )
        order_ctx = bool(ORDER_CONTEXT_RE.search(window))

        # A Luhn-valid PAN is always kept - the checksum is decisive.
        if not valid:
            # Non-valid digit runs that sit in an explicit order/invoice context
            # are reference numbers, not cards. Never redact those.
            if order_ctx:
                continue
            if not card_ctx:
                continue
        add(
            EntityType.CARD_PAN,
            m.start(),
            m.end(),
            0.99 if valid else 0.60,
            valid,
            0.05 if card_ctx else 0.0,
            ["regex", "luhn-valid" if valid else "luhn-failed"],
        )
        claim(m.start(), m.end())

    for m in CVV_RE.finditer(haystack):
        if claimed_by(m.start(1), m.end(1)):
            continue
        add(
            EntityType.CARD_CVV,
            m.start(1),
            m.end(1),
            0.95,
            True,
            0.05,
            ["regex", "cvv-context"],
        )
        claim(m.start(1), m.end(1))

    for m in BANK_ACCT_CONTEXT_RE.finditer(haystack):
        add(
            EntityType.BANK_ACCOUNT,
            m.start(1),
            m.end(1),
            0.85,
            True,
            0.05,
            ["regex", "account-context"],
        )

    for m in REMITTANCE_RE.finditer(haystack):
        add(
            EntityType.REMITTANCE_REF,
            m.start(1),
            m.end(1),
            0.85,
            True,
            0.05,
            ["regex", "remittance-context"],
        )

    for m in PHILSYS_RE.finditer(haystack):
        add(EntityType.PHILSYS_ID, m.start(), m.end(), 0.94, True, reasons=["regex"])

    for m in PASSPORT_RE.finditer(haystack):
        if not re.fullmatch(r"[A-Z]\d{7}[A-Z]|[A-Z]{2}\d{7}[A-Z]?", m.group()):
            continue
        window = _context_window(haystack, m.start(), m.end())
        ctx = bool(re.search(r"\bpassport\b", window, re.I))
        if not ctx:
            # Without an explicit "passport" marker a short alnum token is far too
            # ambiguous to redact.
            continue
        add(
            EntityType.PASSPORT,
            m.start(),
            m.end(),
            0.85,
            True,
            0.05,
            ["regex", "passport-context"],
        )

    for m in DOB_RE.finditer(haystack):
        prefix = m.group(1)
        if prefix and DOB_CONTEXT_RE.search(m.group(0)):
            add(
                EntityType.DATE_OF_BIRTH,
                m.start(1),
                m.end(1),
                0.90,
                True,
                0.05,
                ["regex", "dob-context"],
            )

    for m in SALARY_RE.finditer(haystack):
        # Only treat an amount as compensation when it sits in genuine salary
        # context. "Total of PHP 1,250.50 was charged to the account" is a
        # transaction amount, not personal employment data.
        window = _context_window(haystack, m.start(), m.end(), pad=40)
        salary_ctx = bool(
            re.search(
                r"\b(salary|payroll|pay\s*roll|basic\s+pay|net\s+pay|gross\s+pay|"
                r"compensation|remuneration|per\s+month|monthly|annual|"
                r"\/\s*mo\b|monthly\s+salary|depositary|employer)\b",
                window,
                re.IGNORECASE,
            )
        )
        if not salary_ctx:
            continue
        for gi in (1, 2):
            if m.group(gi):
                add(
                    EntityType.SALARY,
                    m.start(gi),
                    m.end(gi),
                    0.85,
                    True,
                    0.05,
                    ["regex", "salary-context"],
                )

    return found