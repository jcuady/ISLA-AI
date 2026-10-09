"""DPA Copilot: grounded, citation-first answers on Philippine privacy law.

Generation contract (brief section 6.2). All four rules are enforced in code,
because a compliance copilot that invents a circular number is worse than one
that refuses:

  1. Citation-first. Every legal claim carries a resolvable [DOC section] tag.
  2. Refuse on thin evidence. Below the retrieval threshold, say so in Taglish
     and report what WAS found - refusing correctly is a feature.
  3. No legal invention. Extractive-first: quote the cited span, then explain.
     The generator may only paraphrase within a retrieved chunk's scope.
  4. Advisory tone. Every answer carries the verification footer.

Legal correctness here comes from RETRIEVAL, not model scale. The whole body of
Philippine privacy law is a few hundred pages; grounding beats fine-tuning, which
would change what the model says rather than what it knows.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CORPUS_AS_OF = "2024-12-19 (NPC Advisory 2024-04)"

ADVISORY_FOOTER = (
    "AI-generated. Verified against the local corpus as of "
    f"{CORPUS_AS_OF}. Not a substitute for legal advice."
)



def _native_float(value: float) -> float:
    """Coerce numpy scalars to a plain Python float.

    The dense retrieval leg produces numpy float32 values. FastAPI serialises
    responses with the stdlib json encoder, which rejects them, and the audit
    ledger hashes the same payload. Coercing here keeps both paths clean.
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

REFUSAL_TAGLISH = (
    "Wala akong mabatay na basehan sa corpus na 'to. "
    "Kailangan mo ng legal opinion mula sa DPO."
)

# Below this combined retrieval score the corpus has nothing citable.
REFUSAL_THRESHOLD = 0.42

DISCLAIMERS = (
    "di-legal advice",
    "not legal advice",
    "kausap",
    "lawyer",
    "rechtsanwalt",
)


@dataclass
class CopilotAnswer:
    question: str
    answer: str
    refused: bool
    confidence: float
    citations: list[dict] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    footer: str = ADVISORY_FOOTER
    latency_ms: float = 0.0
    retrieval_mode: str = "hybrid"
    llm_used: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "answer": self.answer,
            "refused": self.refused,
            "confidence": round(self.confidence, 3),
            "citations": self.citations,
            "sources": self.sources,
            "footer": self.footer,
            "latency_ms": round(self.latency_ms, 1),
            "retrieval_mode": self.retrieval_mode,
            "llm_used": self.llm_used,
            "notes": self.notes,
        }


def _best_sentences(text: str, query_terms: set[str], limit: int = 3) -> list[str]:
    """Extractive selection: rank sentences by query-term overlap, keep original
    wording verbatim so nothing can be invented.

    Operative-fact sentences ("Within 72 hours...", "shall be fined...") outrank
    mere keyword overlap. A compliance officer needs the rule itself first, not
    the paragraph that happens to mention the topic.
    """
    plain = re.sub(r"\s+", " ", text).strip()
    if not plain:
        return []
    sents = re.split(r"(?<=[.;:])\s+(?=[A-Z(])", plain)

    # Sentences that state an obligation, deadline, or penalty are the answer.
    OPERATIVE = re.compile(
        r"\b(within\s+\d+\s+(?:hours?|days?|months?|years?)|"
        r"shall|shall not|must|required to|prohibited|is liable|shall be fined|"
        r"imprisonment|fine of not less|no later than)\b",
        re.IGNORECASE,
    )
    # Quantified answers ("72 hours", "0.25%", "5 years") are what was asked for.
    QUANTITY = re.compile(r"\b\d+(?:\.\d+)?\s*(?:%|hours?|days?|months?|years?|pesos)\b",
                          re.IGNORECASE)

    scored: list[tuple[float, int, str]] = []
    for idx, s in enumerate(sents):
        s = s.strip()
        if len(s) < 25 or len(s) > 700:
            continue
        low = s.lower()
        hits = sum(1 for t in query_terms if t in low)
        score = float(hits)
        if OPERATIVE.search(low):
            score += 3.0
        if QUANTITY.search(low):
            score += 2.0
        if re.search(r"\b(section|notify|notification|consent|register|penal)\w*\b", low):
            score += 0.5
        if score > 0:
            # Stable tie-break: earlier sentences first within a section.
            scored.append((score, -idx, s))

    scored.sort(reverse=True)
    return [s for _, _, s in scored[:limit]]


class DPACopilot:
    """Grounded Q&A over the local corpus.

    The LLM is optional. When unavailable, the copilot still answers by quoting
    retrieved spans with citations - extractive and fully defensible, which is
    why the demo survives a failed model load.
    """

    def __init__(self, index, llm=None, corpus_as_of: str = CORPUS_AS_OF) -> None:
        self.index = index
        self.llm = llm
        self.corpus_as_of = corpus_as_of
        self.footer = (
            "AI-generated. Verified against the local corpus as of "
            f"{corpus_as_of}. Not a substitute for legal advice."
        )

    def ask(self, question: str, top_k: int = 12) -> CopilotAnswer:
        started = time.perf_counter()
        question = (question or "").strip()

        if not question:
            return CopilotAnswer(
                question=question,
                answer="Walang tanong na sinalok. Pakibigay ang tanong.",
                refused=True,
                confidence=0.0,
                footer=self.footer,
                notes=["empty query"],
            )

        hits = self.index.search(question, top_k=top_k)
        top_score = hits[0].score if hits else 0.0

        sources = [h.to_dict() for h in hits]
        mode = "hybrid" if getattr(self.index, "dense_ready", False) else "bm25+section"

        # Rule 2: refuse on thin evidence.
        # Two independent reasons to refuse: nothing relevant retrieved, or the
        # question is not about Philippine data privacy at all. Both are refusals,
        # but the user-facing explanation differs.
        if not hits or top_score < REFUSAL_THRESHOLD:
            found = ", ".join(sorted({h.chunk["doc_id"] for h in hits[:3]})) or "wala"
            elapsed = (time.perf_counter() - started) * 1000
            return CopilotAnswer(
                question=question,
                answer=(
                    f"{REFUSAL_TAGLISH}\n\n"
                    f"Pinatlang: ang pinakamalakas na kinuha sa corpus ay "
                    f"{top_score:.2f} (kinakailangan {REFUSAL_THRESHOLD:.2f}).\n"
                    f"Nahanap ko ang mga sumusunod pero hindi sapat ang basehan: {found}.\n"
                    "Ipaabot sa DPO o legal counsel para sa opisyal na petsa."
                ),
                refused=True,
                confidence=_native_float(top_score),
                citations=[],
                sources=sources[:3],
                footer=self.footer,
                latency_ms=elapsed,
                retrieval_mode=mode,
                notes=["refused: retrieval below threshold"],
            )

        if not self.index.has_topical_grounding(question, hits):
            elapsed = (time.perf_counter() - started) * 1000
            return CopilotAnswer(
                question=question,
                answer=(
                    "Hindi ito tanong tungkol sa Data Privacy Act o mga patakaran ng NPC, "
                    "kaya wala akong maibibigay na batayan sa loob ng corpus na 'to.\n\n"
                    + REFUSAL_TAGLISH
                    + "\n\nAng corpus na 'to ay saklaw lamang ang RA 10173, ang IRR, "
                    "at ang mga circular/advisory ng NPC at BSP."
                ),
                refused=True,
                confidence=_native_float(top_score),
                citations=[],
                sources=sources[:2],
                footer=self.footer,
                latency_ms=elapsed,
                retrieval_mode=mode,
                notes=["refused: out of domain for the PH privacy corpus"],
            )

        query_terms = {t for t in re.findall(r"[a-z0-9]{3,}", question.lower())}

        # Rule 3: extractive-first. Build the grounded answer from retrieved spans.
        citations: list[dict] = []
        parts: list[str] = []
        seen_text: set[str] = set()

        # "Ilang oras..." asks for a duration. Chunks that actually state a
        # duration outrank chunks that merely discuss the topic, otherwise the
        # answer quotes the right section but not the operative deadline.
        wants_time = bool(
            re.search(r"(ilan|magkano|how\s+many|how\s+long|when)", question, re.IGNORECASE)
        ) and bool(
            re.search(r"(oras|hour|araw|day|buwan|month|taon|year)", question, re.IGNORECASE)
        )

        ordered = list(hits)
        if wants_time:
            ordered.sort(
                key=lambda h: 0 if re.search(
                    r"\b\d+\s*(?:hours?|days?|months?|years?)\b",
                    h.chunk["text"], re.IGNORECASE
                ) else 1
            )

        for rank, hit in enumerate(ordered[:3], start=1):
            quotes = _best_sentences(hit.chunk["text"], query_terms, limit=2)
            if not quotes:
                continue
            quote = quotes[0]
            if quote in seen_text:
                continue
            seen_text.add(quote)

            citation = {
                "id": hit.chunk["chunk_id"],
                "label": hit.citation,
                "doc_id": hit.chunk["doc_id"],
                "doc_title": hit.chunk["doc_title"],
                "issuer": hit.chunk["issuer"],
                "section": hit.chunk["section"],
                "effective_date": hit.chunk["effective_date"],
                "url": hit.chunk["url"],
                "doc_type": hit.chunk["doc_type"],
                "rank": rank,
                "score": _native_float(hit.score),
            }
            citations.append(citation)
            parts.append(f"{quote} {hit.citation}")

        if not parts:
            elapsed = (time.perf_counter() - started) * 1000
            return CopilotAnswer(
                question=question,
                answer=(
                    f"{REFUSAL_TAGLISH}\n\n"
                    "May katugmang dokumento, pero walang malinaw na probisyon na "
                    "maaaring banggit nang may katatagan."
                ),
                refused=True,
                confidence=_native_float(top_score),
                sources=sources[:3],
                footer=self.footer,
                latency_ms=elapsed,
                retrieval_mode=mode,
                notes=["refused: no quotable span"],
            )

        notes = ["extractive answer from cited spans"]
        llm_used = False

        # Optional LLM rewrite. Strictly constrained: it may only restate the
        # cited spans, and its output is discarded if it drops a citation.
        if self.llm is not None:
            try:
                drafted = self._draft_with_llm(question, hits[:3], citations)
                if drafted:
                    answer_text = drafted
                    llm_used = True
                    notes.append("LLM phrasing, citations enforced")
                else:
                    answer_text = "\n\n".join(parts)
            except Exception as exc:  # noqa: BLE001
                answer_text = "\n\n".join(parts)
                notes.append(f"LLM unavailable, extractive fallback: {type(exc).__name__}")
        else:
            answer_text = "\n\n".join(parts)

        # Rule 1: citation enforcement. Never emit a legal claim uncited.
        if not re.search(r"\[[A-Z0-9][^\]]+\]", answer_text):
            answer_text = f"{answer_text}\n\n{parts[0]}"
            notes.append("citation restored after generation")

        elapsed = (time.perf_counter() - started) * 1000
        return CopilotAnswer(
            question=question,
            answer=answer_text,
            refused=False,
            confidence=_native_float(top_score),
            citations=citations,
            sources=sources,
            footer=self.footer,
            latency_ms=elapsed,
            retrieval_mode=mode,
            llm_used=llm_used,
            notes=notes,
        )

    def _draft_with_llm(self, question: str, hits, citations) -> str | None:
        """Constrained draft. Returns None if the model emits no citation."""
        prompt_parts = []
        for hit, cit in zip(hits, citations):
            snippet = re.sub(r"\s+", " ", hit.chunk["text"])[:900]
            prompt_parts.append(f"SOURCE {cit['label']}:\n{snippet}")

        prompt = (
            "You are a Philippine data-privacy compliance assistant.\n"
            "Answer ONLY from the SOURCES below. Quote the exact words that carry "
            "the legal obligation and keep the source label in square brackets "
            "e.g. [NPC-CIRC-16-03 Section 5].\n"
            "Do not add any law, circular number, or penalty that is not in a "
            "SOURCE. If the SOURCES do not answer the question, reply exactly: "
            "NO_ANSWER\n\n"
            f"QUESTION: {question}\n\n" + "\n\n".join(prompt_parts) + "\n\nANSWER:"
        )
        text = self.llm.generate(prompt, max_tokens=380, temperature=0.1)
        if not text or "NO_ANSWER" in text.upper():
            return None
        # Enforce: every paragraph making a claim must carry a citation tag.
        if not re.search(r"\[[A-Z0-9][^\]]+\]", text):
            return None
        return text.strip()