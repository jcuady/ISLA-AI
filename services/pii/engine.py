"""Egress Guard: ensemble detection, redaction, verification pass, risk verdict.

This is the product's opening act and the clearest demonstration of why local
inference matters: the text never leaves the machine in order to decide whether
it is sensitive.

Pipeline (brief section 6.1):
  Stage 1  deterministic regex + checksum recognizers   (services.pii.recognizers)
  Stage 2  GLiNER zero-shot contextual NER              (services.pii.ner, optional)
  Stage 3  conflict-aware ensemble scoring
  Stage 4  redaction verification pass - re-run detection over the OUTPUT
  Stage 5  risk verdict
"""

from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

from services.pii.recognizers import (
    HIGH_RISK_TYPES,
    Entity,
    EntityType,
    detect_regex,
)

MAX_VERIFICATION_PASSES = 3
DEFAULT_KEY_ENV = "ISLA_PSEUDONYM_KEY"


class Verdict(str, Enum):
    """Stage 5 output. A decision, not a diff."""

    SAFE_TO_SEND = "SAFE_TO_SEND"
    REDACT_THEN_SEND = "REDACT_THEN_SEND"
    BLOCK_ESCALATE = "BLOCK_ESCALATE"

    @property
    def label(self) -> str:
        return {
            Verdict.SAFE_TO_SEND: "SAFE TO SEND",
            Verdict.REDACT_THEN_SEND: "REDACT, THEN SEND",
            Verdict.BLOCK_ESCALATE: "BLOCK & ESCALATE",
        }[self]


@dataclass
class ScanResult:
    """Full result of one scan/redact cycle."""

    original: str
    redacted: str
    entities: list[Entity]
    verdict: Verdict
    passes: int
    residual_leakage: float
    verified_clean: bool
    redaction_map: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "original": self.original,
            "redacted": self.redacted,
            "verdict": self.verdict.value,
            "verdict_label": self.verdict.label,
            "verified_clean": self.verified_clean,
            "residual_leakage": self.residual_leakage,
            "passes": self.passes,
            "latency_ms": round(self.latency_ms, 1),
            "notes": self.notes,
            "redaction_map": self.redaction_map,
            "entities": [
                {
                    "type": e.entity_type.value,
                    "start": e.start,
                    "end": e.end,
                    "text": e.text,
                    "score": round(e.score, 3),
                    "stage": e.stage,
                    "validated": e.validated,
                    "reasons": e.reasons,
                }
                for e in self.entities
            ],
            "entity_counts": self.counts(),
        }

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for e in self.entities:
            if e.entity_type in HIGH_RISK_TYPES:
                out[e.entity_type.value] = out.get(e.entity_type.value, 0) + 1
        return out


# --------------------------------------------------------------------------
# Ensemble
# --------------------------------------------------------------------------

def _overlaps(a: Entity, b: Entity) -> bool:
    return a.start < b.end and b.start < a.end


def ensemble(regex_entities: Iterable[Entity], ner_entities: Iterable[Entity]) -> list[Entity]:
    """Stage 3. Union the two stages, resolving overlaps by confidence.

    A regex hit confirmed by context/validation outranks a bare NER guess, so the
    union is never simply "concatenate and trust both".
    """
    merged: list[Entity] = []

    for ent in regex_entities:
        final = (
            0.45 * (1.0 if ent.validated else 0.6)
            + 0.35 * ent.score
            + 0.20 * ent.context_boost
        )
        ent.score = round(min(final, 0.99), 3)
        ent.stage = "ensemble:regex"
        merged.append(ent)

    for ent in ner_entities:
        # GLiNER score is the raw model confidence.
        final = 0.45 * (1.0 if ent.validated else 0.6) + 0.35 * ent.score + 0.20 * ent.context_boost
        ent.score = round(min(final, 0.99), 3)

        conflicting = [m for m in merged if _overlaps(m, ent)]
        if conflicting:
            # Same span already covered by the deterministic stage: keep the stronger
            # one but record that NER agreed (agreement is a recall signal).
            for m in conflicting:
                m.reasons.append("ner-agrees")
                if ent.score > m.score:
                    ent.reasons.append("supersedes-regex")
                    m.score = max(m.score, ent.score * 0.9)
            continue
        ent.stage = "ensemble:ner"
        merged.append(ent)

    merged.sort(key=lambda e: (e.start, -e.score))
    return merged


def merge_overlapping(entities: list[Entity]) -> list[Entity]:
    """Collapse duplicate spans produced by overlapping patterns."""
    out: list[Entity] = []
    for ent in sorted(entities, key=lambda e: (e.start, -(e.end - e.start), -e.score)):
        prev = out[-1] if out else None
        if prev is not None and ent.start < prev.end and ent.end > prev.start:
            # Keep the longer span but adopt the higher score and richer type.
            if (ent.end - ent.start) > (prev.end - prev.start):
                prev_score, prev_reasons = prev.score, prev.reasons
                out[-1] = ent
                out[-1].score = max(ent.score, prev_score)
                out[-1].reasons = sorted(set(prev_reasons) | set(ent.reasons))
            else:
                prev.score = max(prev.score, ent.score)
                prev.reasons = sorted(set(prev.reasons) | set(ent.reasons))
            continue
        out.append(ent)
    return out


# --------------------------------------------------------------------------
# Redaction
# --------------------------------------------------------------------------

def _key() -> bytes:
    raw = os.environ.get(DEFAULT_KEY_ENV, "")
    if raw:
        return raw.encode("utf-8")
    # Stable per-machine fallback so demo output is reproducible. Documented in
    # docs/THREAT_MODEL.md: production deployments MUST set the env var.
    seed = hashlib.sha256(b"isla-local-pseudonym-key").hexdigest()
    return seed.encode("utf-8")


def pseudonym(entity_type: EntityType, raw: str) -> str:
    """Irreversible HMAC pseudonym - keeps joins intact across records."""
    digest = hmac.new(_key(), raw.encode("utf-8"), hashlib.sha256).hexdigest().upper()
    short = digest[:4]
    tag = {
        EntityType.PH_MOBILE: "PHONE",
        EntityType.GCASH_MOBILE: "GCASH",
        EntityType.CARD_PAN: "PAN",
        EntityType.CARD_CVV: "CVV",
        EntityType.PH_SSS: "SSS",
        EntityType.PH_TIN: "TIN",
        EntityType.EMAIL: "EMAIL",
        EntityType.PH_IBAN: "IBAN",
        EntityType.BANK_ACCOUNT: "ACCT",
        EntityType.REMITTANCE_REF: "REMIT",
        EntityType.PASSPORT: "PASSPORT",
        EntityType.DRIVERS_LICENSE: "DL",
        EntityType.PHILSYS_ID: "PHILSYS",
        EntityType.DATE_OF_BIRTH: "DOB",
        EntityType.SALARY: "AMOUNT",
    }.get(entity_type, "REDACTED")
    return f"[{tag}-{short}]"


def apply_redactions(text: str, entities: list[Entity]) -> tuple[str, list[dict]]:
    """Replace entity spans with pseudonyms. Right-to-left so offsets stay valid."""
    mapping: list[dict] = []
    out = text
    for ent in sorted(entities, key=lambda e: e.start, reverse=True):
        if ent.entity_type is EntityType.PERSON:
            continue  # risk signal only - never auto-redacted
        if ent.entity_type not in HIGH_RISK_TYPES:
            continue
        token = pseudonym(ent.entity_type, ent.text)
        out = out[: ent.start] + token + out[ent.end :]
        mapping.append(
            {
                "type": ent.entity_type.value,
                "original_length": ent.length,
                "replacement": token,
                "mode": "hmac-pseudonym",
                "score": round(ent.score, 3),
            }
        )
    mapping.reverse()
    return out, mapping


# --------------------------------------------------------------------------
# Verdict
# --------------------------------------------------------------------------

def decide_verdict(
    entities: list[Entity], verified_clean: bool, residual: list[Entity]
) -> tuple[Verdict, list[str]]:
    """Stage 5. DPA section 25(c)-(d) confidentiality & unauthorised access;
    BSP M-2024-019 handling of PII."""
    notes: list[str] = []
    counts: dict[EntityType, int] = {}
    for e in entities:
        if e.entity_type in HIGH_RISK_TYPES:
            counts[e.entity_type] = counts.get(e.entity_type, 0) + 1

    if not verified_clean or residual:
        notes.append(
            "Residual regulated data detected after redaction - "
            "DPA section 25(c)-(d) requires blocking until reviewed."
        )
        return Verdict.BLOCK_ESCALATE, notes

    types = set(counts)
    if not types:
        notes.append("No regulated Philippine banking PII detected.")
        return Verdict.SAFE_TO_SEND, notes

    has_pan = EntityType.CARD_PAN in types
    has_cvv = EntityType.CARD_CVV in types
    has_ssn = EntityType.PH_SSS in types
    has_acct = bool({EntityType.BANK_ACCOUNT, EntityType.PH_IBAN} & types)

    # Card credentials plus an identifier together is a classic fraud bundle.
    if has_pan and has_cvv and (has_ssn or has_acct):
        notes.append(
            "Card PAN + CVV + account identifier detected together - "
            "treat as a complete payment-credential compromise."
        )
        return Verdict.BLOCK_ESCALATE, notes

    sensitive = bool({EntityType.PH_SSS, EntityType.PH_TIN} & types)
    if sensitive:
        notes.append(
            "High-risk government identifiers (SSS/TIN) present - these are "
            "regulated under NPC Circular 2022-04."
        )
        return Verdict.BLOCK_ESCALATE, notes

    notes.append(
        f"{sum(counts.values())} regulated entit{'y' if sum(counts.values()) == 1 else 'ies'} "
        f"redacted and re-verified: {', '.join(sorted(t.value for t in types))}."
    )
    return Verdict.REDACT_THEN_SEND, notes


# --------------------------------------------------------------------------
# Orchestrator
# --------------------------------------------------------------------------

class EgressGuard:
    """Full detect -> redact -> verify loop.

    The NER stage is injected so the engine works standalone (regex only) if
    GLiNER is unavailable - it degrades recall, never safety, because Stage 4
    verification still runs.
    """

    def __init__(self, ner_backend=None) -> None:
        self._ner = ner_backend

    @property
    def ner_available(self) -> bool:
        return self._ner is not None

    def detect_all(self, text: str) -> tuple[list[Entity], list[Entity]]:
        """Return (regex_entities, ner_entities) - the raw stages."""
        regex_entities = detect_regex(text)
        ner_entities: list[Entity] = []
        if self._ner is not None:
            try:
                ner_entities = self._ner.predict(text)
            except Exception as exc:  # noqa: BLE001 - never let NER break redaction
                print(f"[warn] NER stage failed, continuing with regex only: {exc}")
                ner_entities = []
        return regex_entities, ner_entities

    def scan(self, text: str) -> ScanResult:
        """Stage 4. Redact, then re-run detection over the OUTPUT, up to 3 passes."""
        import time

        started = time.perf_counter()

        current = text
        all_map: list[dict] = []
        passes = 0
        residual: list[Entity] = []
        working_entities: list[Entity] = []
        ner_entities: list[Entity] = []

        for attempt in range(MAX_VERIFICATION_PASSES):
            passes = attempt + 1
            regex_entities, ner_entities = self.detect_all(current)
            working_entities = merge_overlapping(ensemble(regex_entities, ner_entities))

            redacting = [e for e in working_entities if e.entity_type in HIGH_RISK_TYPES]
            if not redacting:
                residual = []
                break

            current, mapping = apply_redactions(current, redacting)
            all_map.extend(mapping)

            # Re-detect on the NEW text - this is the verification pass.
            residual_regex, residual_ner = self.detect_all(current)
            residual = merge_overlapping(ensemble(residual_regex, residual_ner))
            residual = [r for r in residual if r.entity_type in HIGH_RISK_TYPES]
            if not residual:
                break

        verified_clean = not residual
        # Prefer reporting entities found on the ORIGINAL text - that is what the
        # user actually had, and it is what the UI highlights.
        original_regex, original_ner = self.detect_all(text)
        reported = merge_overlapping(ensemble(original_regex, original_ner))

        if not verified_clean:
            current, extra_map = apply_redactions(current, residual)
            all_map.extend(extra_map)

        verdict, notes = decide_verdict(reported, verified_clean, residual)
        elapsed = (time.perf_counter() - started) * 1000

        return ScanResult(
            original=text,
            redacted=current,
            entities=reported,
            verdict=verdict,
            passes=passes,
            residual_leakage=0.0 if verified_clean else 1.0,
            verified_clean=verified_clean,
            redaction_map=all_map,
            notes=notes,
            latency_ms=elapsed,
        )