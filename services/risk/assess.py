"""Turn a described transaction or scenario into an actionable risk verdict.

This is the join between two deliberately separate things:

    * `services.risk.indicators` decides WHAT the risk is. Pure rules, no
      model, no network, reproducible on any machine.
    * `services.copilot.retrieval` decides WHAT THE LAW SAYS. The same local
      hybrid index the copilot uses, queried with the indicator's own anchor.

Keeping them apart is the point. The red flags stay explainable and testable
without a corpus, and the legal text stays quotable without a rule engine. When
retrieval is unavailable the assessment still runs; it simply reports the
statutory hooks without quoting them, which is a visible degradation rather
than a silent one.

Two rules this module enforces:

  1. A hook into a real document is only reported as a citation if retrieval
     actually returned a span from that document. A hook we cannot resolve
     degrades to "citation unavailable", never to an unsourced assertion.

  2. Where the governing rule sits with BSP, SEC, the AMLC or the PCI SSC, the
     response says so by name. The gap is part of the answer.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from services.risk.indicators import (
    GAP,
    SEVERITY,
    IndicatorMatch,
    RiskTier,
    exposed_parties,
    match_indicators,
)

# Stated on every assessment, because it is true of this build regardless of
# which indicators happen to have fired.
COVERAGE_GAP: tuple[str, ...] = (
    "BSP - the Manual of Regulations for Banks, the circulars on suspicious "
    "transaction reporting and the consumer protection circulars are not in "
    "this corpus. bsp.gov.ph refused this machine on 2026-10-10 and the "
    "Wayback Machine has no usable capture, so no BSP rule is quoted here.",
    "SEC - circulars and advisories, including the UITAP advisories, are not "
    "in this corpus. sec.gov.ph refused this machine on 2026-10-10.",
    "AMLC - the reporting issuances are not in this corpus. Reporting "
    "deadlines cannot be quoted from here; confirm with the MLRO.",
    "PCI DSS - the PCI Security Standards Council documents are not in this "
    "corpus. Cardholder-data rules below are flagged as industry practice, "
    "not as cited law.",
    "The retrievable RA 9160 capture is abridged: it omits the covered and "
    "suspicious transaction reporting provisions, so no reporting deadline is "
    "stated by this product.",
)

FOOTER = (
    "Deterministic red-flag screening, computed locally against the verified "
    "corpus. Not legal advice and not a substitute for your compliance "
    "officer or MLRO. Rules this build cannot verify are named above rather "
    "than guessed at."
)

TIER_ORDER = ("none", "low", "medium", "high", "critical")


@dataclass
class Assessment:
    scenario: str
    tier: str
    exposed: set[str]
    red_flags: list[dict]
    required_actions: list[str]
    summary: str
    coverage_gap: list[str] = field(default_factory=list)
    citation_count: int = 0
    latency_ms: float = 0.0
    degraded: bool = False

    def to_dict(self) -> dict:
        return {
            "tier": self.tier,
            "risk_tier": self.tier,
            "exposed": sorted(self.exposed),
            "red_flags": self.red_flags,
            "required_actions": self.required_actions,
            "summary": self.summary,
            "coverage_gap": self.coverage_gap,
            "citation_count": self.citation_count,
            "degraded": self.degraded,
            "footer": FOOTER,
            "latency_ms": round(self.latency_ms, 1),
        }


def _resolve_citation(index, doc_id: str, anchor: str) -> dict | None:
    """Find a real span in the corpus for this hook, or return None.

    Deliberately strict. If the anchor does not retrieve a chunk from the
    document the indicator names, the honest answer is that we cannot show the
    provision right now - not a citation with the text invented around it.

    Two passes. First, take the highest-ranked chunk from `doc_id` that actually
    contains the anchor phrase, because a citation whose quote does not contain
    the thing it is quoting is worse than no citation: it shows the officer a
    confident-looking paragraph that says something else. Only if the anchor is
    nowhere in that document's text do we fall back to the best-ranked chunk,
    flagged so the UI can mark it as approximate rather than exact.
    """
    if index is None or doc_id == GAP:
        return None
    try:
        hits = index.search(anchor, top_k=20)
    except Exception:  # noqa: BLE001 - retrieval must never break screening
        return None

    def _shape(hit, approximate: bool) -> dict:
        text = " ".join(hit.chunk["text"].split())
        return {
            "doc_id": hit.chunk["doc_id"],
            "doc_title": hit.chunk["doc_title"],
            "issuer": hit.chunk["issuer"],
            "section": hit.chunk["section"],
            "url": hit.chunk["url"],
            "doc_type": hit.chunk["doc_type"],
            "label": hit.citation,
            "text": text[:600],
            # A window centred on the anchor, so the reader sees the words that
            # fired the indicator rather than the first 600 characters of a
            # section that may be pages away from them.
            "excerpt": _window_around(text, anchor),
            "score": round(float(hit.score), 4),
            "anchor_in_text": not approximate,
        }

    in_doc = [h for h in hits if h.chunk["doc_id"] == doc_id]
    if not in_doc:
        return None

    needle = " ".join(anchor.lower().split())
    for hit in in_doc:
        if needle in " ".join(hit.chunk["text"].lower().split()):
            return _shape(hit, approximate=False)
    return _shape(in_doc[0], approximate=True)


def _window_around(text: str, anchor: str, pad: int = 260) -> str:
    """A readable excerpt centred on the anchor phrase, cut on word boundaries."""
    low = text.lower()
    needle = " ".join(anchor.lower().split())
    i = low.find(needle)
    if i < 0:
        return text[: pad * 2]
    start = max(0, i - pad)
    end = min(len(text), i + len(needle) + pad)
    if start > 0:
        space = text.find(" ", start)
        start = space + 1 if 0 <= space < end else start
    if end < len(text):
        space = text.rfind(" ", start, end)
        end = space if space > start else end
    excerpt = text[start:end].strip()
    return f"{'...' if start > 0 else ''}{excerpt}{'...' if end < len(text) else ''}"


def _summarise(tier: str, flags: list[dict], exposed: set[str]) -> str:
    if not flags:
        return (
            "No red-flag indicator matched this scenario against the "
            "catalogue. That is not a clearance: it means only that none of "
            "the known typologies were described in the text given."
        )
    top = flags[0]
    who = " and ".join(sorted(exposed)) if exposed else "the bank"
    party_word = {"customer": "the customer", "bank": "the bank"}.get(who, who)
    return (
        f"{tier.upper()} risk. {len(flags)} indicator"
        f"{'' if len(flags) == 1 else 's'} matched, the strongest being "
        f"\"{top['label']}\". The evidence quoted was \"{top['evidence']}\". "
        f"On this reading the exposure falls on {party_word}. "
        f"Required actions are listed below; anything governed by BSP, SEC, "
        f"the AMLC or PCI DSS is outside what this build can verify."
    )


def assess(scenario: str, index=None) -> Assessment:
    """Assess a described transaction or scenario. Pure apart from retrieval."""
    started = time.perf_counter()
    scenario = (scenario or "").strip()
    matches: list[IndicatorMatch] = match_indicators(scenario)

    if not matches:
        result = Assessment(
            scenario=scenario,
            tier=RiskTier.NONE.value,
            exposed=set(),
            red_flags=[],
            required_actions=[
                "Continue normal monitoring. A clean screen is the absence of a "
                "known pattern in the description, not a positive assurance.",
            ],
            summary=_summarise(RiskTier.NONE.value, [], set()),
            coverage_gap=list(COVERAGE_GAP),
        )
        result.latency_ms = (time.perf_counter() - started) * 1000
        return result

    tier = matches[0].indicator.tier
    exposed = exposed_parties(matches)

    flags: list[dict] = []
    actions: list[str] = []
    citations = 0
    degraded = False

    for m in matches:
        ind = m.indicator
        hook = ind.legal_hook
        citation = None
        if hook.doc_id == GAP:
            degraded = True
        else:
            citation = _resolve_citation(index, hook.doc_id, hook.anchor)
            if citation is None:
                degraded = True
            else:
                citations += 1

        flags.append(
            {
                "id": ind.id,
                "label": ind.label,
                "tier": ind.tier,
                "exposure": list(ind.exposure),
                "evidence": m.evidence,
                "why": ind.why,
                "action": ind.action,
                "regulator": ind.regulator,
                "legal_hook": {
                    "doc_id": hook.doc_id,
                    "anchor": hook.anchor,
                    "note": hook.note,
                    "is_gap": hook.is_gap,
                },
                "citation": citation,
            }
        )
        if ind.action not in actions:
            actions.append(ind.action)

    result = Assessment(
        scenario=scenario,
        tier=tier,
        exposed=exposed,
        red_flags=flags,
        required_actions=actions,
        summary=_summarise(tier, flags, exposed),
        coverage_gap=list(COVERAGE_GAP),
        citation_count=citations,
        degraded=degraded,
    )
    result.latency_ms = (time.perf_counter() - started) * 1000
    return result


def tier_rank(tier: str) -> int:
    try:
        return SEVERITY[tier]
    except KeyError:
        return 0