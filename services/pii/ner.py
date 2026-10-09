"""GLiNER zero-shot contextual NER backend.

GLiNER's arbitrary-label NER is the unlock for Philippine-specific entities:
`PH_SSS`, `GCASH_MOBILE`, `CREDIT_CARD_PAN` can be named as labels with no
retraining, which no fixed-schema model can do.

Optional by design. The Egress Guard runs regex + Luhn regardless, and Stage 4
verification still runs, so a missing GLiNER degrades recall but never safety.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MODEL_DIR = REPO_ROOT / "models" / "weights" / "gliner-multi-v2.1"
THRESHOLD = float(os.environ.get("KALIX_GLINER_THRESHOLD", "0.45"))

# Philippine banking labels. Kept close to the brief's list, with the wallet and
# remittance additions that generic NER would miss.
GLINER_LABELS = [
    "customer name",
    "Philippine mobile number",
    "email address",
    "SSS number",
    "TIN number",
    "passport number",
    "LTO driver's license",
    "PhilSys ID number",
    "credit card number",
    "CVV",
    "expiry date",
    "bank account number",
    "GCash number",
    "employment or salary information",
    "medical or health information",
    "biometric identifier",
    "remittance reference number",
    "date of birth",
    "home address",
]

# Map GLiNER's free-text labels onto KALIX entity types.
LABEL_MAP = {
    "customer name": "PERSON",
    "philippine mobile number": "PH_MOBILE",
    "email address": "EMAIL",
    "sss number": "PH_SSS",
    "tin number": "PH_TIN",
    "passport number": "PASSPORT",
    "lto driver's license": "DRIVERS_LICENSE",
    "philsys id number": "PHILSYS_ID",
    "credit card number": "CARD_PAN",
    "cvv": "CARD_CVV",
    "expiry date": "CARD_CVV",
    "bank account number": "BANK_ACCOUNT",
    "gcash number": "GCASH_MOBILE",
    "employment or salary information": "SALARY",
    "medical or health information": "SALARY",
    "biometric identifier": "PERSON",
    "remittance reference number": "REMITTANCE_REF",
    "date of birth": "DATE_OF_BIRTH",
    "home address": "HOME_ADDRESS",
}


class GLiNERBackend:
    """Loads GLiNER lazily. Construction never raises."""

    def __init__(self) -> None:
        self._model = None
        self.available = False
        self.reason = "not loaded"

        if not (MODEL_DIR / "model.safetensors").exists():
            self.reason = "model not downloaded"
            return
        try:
            from gliner import GLiNER

            self._model = GLiNER.from_pretrained(str(MODEL_DIR))
            self.available = True
            self.reason = "ready"
        except Exception as exc:  # noqa: BLE001
            self.reason = f"{type(exc).__name__}: {exc}"
            self.available = False

    def predict(self, text: str) -> list:
        """Return KALIX Entity objects for contextually-detected spans."""
        from services.pii.recognizers import Entity, EntityType

        if not self.available or not text.strip():
            return []

        try:
            spans = self._model.predict_entities(text, GLINER_LABELS, threshold=THRESHOLD)
        except Exception:  # noqa: BLE001
            return []

        out: list[Entity] = []
        for span in spans or []:
            raw_label = str(span.get("label", "")).lower()
            etype_name = LABEL_MAP.get(raw_label)
            if not etype_name:
                continue
            start = int(span["start"])
            end = int(span["end"])
            score = float(span.get("score", 0.0))
            out.append(
                Entity(
                    entity_type=EntityType(etype_name),
                    start=start,
                    end=end,
                    text=text[start:end],
                    # GLiNER is the only model in the ensemble providing context,
                    # so its own confidence becomes the raw score.
                    score=score,
                    stage="ner",
                    validated=False,
                    context_boost=0.0,
                    reasons=[f"gliner:{raw_label}"],
                )
            )
        return out