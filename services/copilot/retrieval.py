"""Hybrid retrieval over the Philippine privacy corpus.

Pure vector search fails on exact legal references ("NPC Circular 16-03"), so
retrieval blends three signals:

    score = 0.60 * cosine(e5, chunk)      # semantic, handles Taglish -> English
          + 0.25 * BM25(query, chunk)     # lexical, exact legal tokens
          + 0.15 * section_id_match      # "NPC Circular 16-03" -> +1 on matching chunks

then applies authority weighting: DPA / IRR / NPC outrank BSP memos, which
outrank internal SOPs. The tier is surfaced in the UI so the compliance officer
knows what they are looking at.

The dense leg is optional. With no embedding model loaded the index still answers
from BM25 + section matching, which keeps the copilot demonstrable if a model
fails to load before the demo.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PROCESSED = REPO_ROOT / "corpus" / "processed"
CHUNKS_PATH = PROCESSED / "chunks.jsonl"

W_COSINE = 0.60
W_BM25 = 0.25
W_SECTION = 0.15

# Authority multipliers by document type. Tier 1 is the statute itself.
AUTHORITY_WEIGHT = {
    "statute": 1.00,
    "irr": 0.98,
    "circular": 0.96,
    "advisory": 0.94,
    "bsp_memo": 0.88,
    "morb": 0.88,
    "sop": 0.70,
}

# Legal tokens that must match lexically to score the section-ID bonus.
SECTION_TOKEN_RE = re.compile(
    r"\b(?:npc\s*(?:circular|advisory|memorandum|memo)?|circular|advisory|memorandum|"
    r"dsa|dpa|irr|bsp|morb|ra)\s*\.?\s*"
    r"((?:no\.?\s*)?\d{1,4}[-–][0-9]{2,4}|\d{2,4})\b",
    re.IGNORECASE,
)

# Domain vocabulary for the topical-grounding gate. Taglish included, because a
# bank officer asks "pwede ba ipasa ang CDR ... sa vendor sa Singapore".
#
# Deliberately excludes bare country words like "philippines" - "who is the
# president of the Philippines" is not a data-privacy question, and a corpus made
# entirely of legal text will happily retrieve something for it. The gate must be
# strict; a permissive fallback lets off-topic questions through.
DOMAIN_TERMS = (
    "data privacy", "privacy", "personal data", "personal information",
    "sensitive personal", "pii", "dpa", "npc", "compliance", "consent",
    "breach", "data subject", "retention", "disposal", "records", "outbound",
    "transfer", "vendor", "outsourc", "third part", "registr", "profiling",
    "automated decision", "artificial intelligence", " ai ", "dpia",
    "impact assessment", "dpo", "data protection officer", "legal basis",
    "lawful", "purpose limitation", "security", "penal", "fine",
    "circular", "advisory", "irr", "bsp", "ra 10173", "10173",
    "privacy.gov", "npc.gov", "egress", "redact", "anonymi",
    # Taglish vocabulary. A gate that only understands English legal register
    # would refuse the questions bank staff actually ask, which are in Taglish:
    # "May karapatang humingi ng data ng customer ko ang collection agency?"
    "karapatang", "customer", "collection", "data ng", "basehan",
    "ahente", "complaint", "reklamo", "itinatago", "itago", "pasok",
    "labas", "privacy officer", "compliance officer",
)


@dataclass
class RetrievedChunk:
    chunk: dict
    score: float
    cosine: float
    bm25: float
    section_match: float
    authority: float

    @property
    def citation(self) -> str:
        c = self.chunk
        doc = c["doc_id"]
        section = re.sub(r"\s+", " ", c["section"])[:60].strip()
        return f"[{doc} {section}]"

    def to_dict(self) -> dict:
        # The dense leg yields numpy float32 values, which the stdlib json encoder
        # rejects. Coerce at this boundary so every downstream consumer (FastAPI
        # response, audit ledger) receives plain Python numbers.
        return {
            "chunk_id": self.chunk["chunk_id"],
            "doc_id": self.chunk["doc_id"],
            "doc_title": self.chunk["doc_title"],
            "issuer": self.chunk["issuer"],
            "section": self.chunk["section"],
            "effective_date": self.chunk["effective_date"],
            "url": self.chunk["url"],
            "doc_type": self.chunk["doc_type"],
            "tags": self.chunk.get("tags", []),
            "score": float(self.score),
            "cosine": float(self.cosine),
            "bm25": float(self.bm25),
            "section_match": float(self.section_match),
            "authority": float(self.authority),
            "citation": self.citation,
            "text": self.chunk["text"],
        }


# Taglish interrogatives, particles and pronouns. A compliance officer asks
# "Kailangan ba mag-register ng AI credit scoring model ang banko namin?" - five of
# those twelve tokens carry no retrieval signal at all. Left in, they inflate the
# BM25 score of whichever long chunk happens to contain "ba"/"ng"/"ang" as
# standalone words, which is how a question about AI registration used to return
# the provision amending the Secrecy of Bank Deposits Act.
TAGLISH_STOPWORDS = frozenset(
    {
        # interrogatives / auxiliaries
        "ba", "bang", "po", "dapat", "dapat ba", "kailangan", "kailangan ba",
        "pwede", "puwede", "pwedeng", "maaari", "can", "could",
        "should", "would", "will", "shall", "may", "might", "must", "ko",
        "how", "when", "what", "why", "where", "which", "who", "whom",
        # particles / clitics
        "ang", "ng", "na", "pa", "mga", "yung", "nang", "may", "wala",
        "ako", "ikaw", "ito", "iyan", "iyon", "iyo", "atin", "natin",
        "ninyo", "namin", "nako", "natin", "silang",
        # discourse fillers that appear in real questions
        "about", "sabihin", "paki", "pakisabi", "sana", "please", "heto",
        "eto", "opw", "tru",
    }
)

# Conservative suffix stripper. Not linguistics - just enough to collapse the forms
# that actually appear across query and corpus ("register" / "registers" /
# "registered" / "registering" / "registration" all reduce to "regist"), so a
# question using one form can reach a passage using another.
_SUFFIXES = ("ations", "ation", "ions", "ion", "ings", "ing", "edly", "ed",
             "ers", "er", "ors", "or", "ies", "es", "s")
# "-ation"/"-ion" nouns come from a verb stem that itself ends in -er/-or, so the
# dangling r has to go too: registration -> registr -> regist, matching register.
_NOUN_SUFFIXES = ("ations", "ation", "ions", "ion")


def _stem(token: str) -> str:
    """Strip inflectional suffixes until stable, guarding short words."""
    if token.isdigit() or len(token) < 5:
        return token
    current = token
    for _ in range(3):  # register -> register(ed) -> regist
        for suf in _SUFFIXES:
            if not current.endswith(suf) or len(current) - len(suf) < 4:
                continue
            base = current[: -len(suf)]
            if suf == "ies":
                base += "y"
            if suf in _NOUN_SUFFIXES and base.endswith("r"):
                base = base[:-1]
            if base != current:
                current = base
            break
        else:
            break
    return current


def tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokens with Taglish stopwords removed and light stemming.

    Legal numbers survive because they are digit-bearing and ``isdigit``-guarded,
    so the section-ID signal is unaffected.
    """
    out: list[str] = []
    for raw in re.findall(r"[a-z0-9]+", text.lower()):
        if raw in TAGLISH_STOPWORDS:
            continue
        if raw.isdigit():
            out.append(raw)
            continue
        out.append(_stem(raw))
    return out


# Business Taglish and the statute speak different vocabularies. "Ipasa ang CDR
# ng customer ko sa vendor namin sa Singapore?" shares no content word with the
# provision that actually answers it - RA-10173 speaks of information
# "transferred to a third party for processing, whether domestically or
# internationally". Raw BM25 scores that question at exactly 0.000 and the copilot
# falls back to an unrelated provision, which is the single most common real
# question a bank compliance officer asks.
#
# These cues map a query onto the statutory phrasing. They are applied to the
# query only - never to the corpus - so they add recall without changing what the
# documents themselves say.
_OUTBOUND_CUES = (
    "vendor", "supplier", "third party", "third-party", "outsourc", "cloud",
    "ibang bansa", "ibang lugar", "abroad", "overseas", "outside the philippines",
    "third country", "cross-border", "cross border", "foreign", "offshore",
    "ipasa", "ipinapasa", "i-send", "isend", "padala", "ibigay", "transfer",
    "i-disclose", "idisisclose", "baho",
)
_OUTBOUND_TERMS = (
    "third", "party", "transferred", "transfer", "recipient", "contractor",
    "processing", "internationally", "cross", "border", "foreign", "disclosed",
)

_DATA_HANDLING_CUES = ("breach", "leak", "nag-leak", "compromised", "hacked",
                       "data subject", "mga datos", "personal data")
_DATA_HANDLING_TERMS = ("breach", "compromised", "unauthorized", "affected",
                        "notification", "notify", "incident")


def expand_query(query: str) -> list[str]:
    """Query tokens plus statutory synonyms implied by the phrasing."""
    tokens = tokenize(query)
    low = query.lower()
    if any(cue in low for cue in _OUTBOUND_CUES):
        tokens += [_stem(t) for t in _OUTBOUND_TERMS]
    if any(cue in low for cue in _DATA_HANDLING_CUES):
        tokens += [_stem(t) for t in _DATA_HANDLING_TERMS]
    return tokens


def extract_section_tokens(text: str) -> set[str]:
    """Pull normalised legal identifiers like '16-03', '2022-04', '10173'."""
    out: set[str] = set()
    for m in SECTION_TOKEN_RE.finditer(text):
        num = re.sub(r"[^0-9\-]", "", m.group(1))
        if num:
            out.add(num.lstrip("0") or num)
    for m in re.finditer(r"\b(\d{4,5})\b", text):  # bare statute numbers
        out.add(m.group(1))
    return out


class HybridIndex:
    """Loads chunks once; answers queries. Dense leg is optional."""

    def __init__(self) -> None:
        self.chunks: list[dict] = []
        self._bm25 = None
        self._embedder = None
        self._embeddings = None
        self._chunk_tokens: list[list[str]] = []
        self._load()

    def _load(self) -> None:
        if not CHUNKS_PATH.exists():
            raise FileNotFoundError(
                f"{CHUNKS_PATH} not found - run corpus/fetch_corpus.py then chunk_corpus.py"
            )
        with CHUNKS_PATH.open(encoding="utf-8") as fh:
            self.chunks = [json.loads(line) for line in fh if line.strip()]
        self._chunk_tokens = [tokenize(c["text"]) for c in self.chunks]
        self._build_bm25()
        print(f"[index] {len(self.chunks)} chunks loaded (BM25 ready)")

    def _build_bm25(self) -> None:
        from rank_bm25 import BM25Okapi

        corpus = self._chunk_tokens or [[]]
        self._bm25 = BM25Okapi(corpus)

    # -- dense leg ---------------------------------------------------------

    def enable_dense(self) -> bool:
        """Load the int8 ONNX embedding model + precomputed chunk matrix."""
        try:
            import numpy as np
            import onnxruntime as ort
            from transformers import AutoTokenizer

            from services.copilot.embeddings import Embedder

            embedder = Embedder()
            if not embedder.available:
                print("[index] dense leg unavailable:", embedder.reason)
                return False

            emb_path = PROCESSED / "embeddings.npy"
            if emb_path.exists():
                self._embeddings = np.load(emb_path)
                print(f"[index] dense leg on: cached {self._embeddings.shape}")
            else:
                print("[index] encoding corpus with e5-small...")
                matrix = embedder.encode_chunks([c["text"] for c in self.chunks])
                np.save(emb_path, matrix)
                self._embeddings = matrix
                print(f"[index] cached embeddings {matrix.shape}")

            self._embedder = embedder
            return True
        except Exception as exc:  # noqa: BLE001
            print(f"[index] dense leg failed to load: {type(exc).__name__}: {exc}")
            return False

    @property
    def dense_ready(self) -> bool:
        return self._embedder is not None and self._embeddings is not None

    def has_topical_grounding(self, query: str, hits: list) -> bool:
        """True when the query is actually about Philippine data privacy.

        Measured behaviour: with the dense leg on, the embedding model's
        similarity floor puts every query - including "Who won the 2025 FIFA
        World Cup?" - at roughly 0.66-0.75, and the top-vs-median spread overlaps
        between real and off-topic questions. Retrieval scores alone therefore
        cannot separate them, so the gate is lexical and STRICT: the question must
        contain genuine domain vocabulary.

        The absence of a score-based fallback is intentional. A corpus composed
        entirely of legal text will always retrieve something for anything;
        relying on retrieval confidence to detect out-of-domain questions is what
        made an early version answer the FIFA question.
        """
        q = query.lower()
        return any(term in q for term in DOMAIN_TERMS)

    # -- retrieval ---------------------------------------------------------

    def search(self, query: str, top_k: int = 6) -> list[RetrievedChunk]:
        if not self.chunks:
            return []

        bm25_scores = self._bm25.get_scores(expand_query(query))
        max_bm25 = float(max(bm25_scores)) or 1.0

        query_tokens = extract_section_tokens(query)
        q_lower = query.lower()

        cosines: list[float] = [0.0] * len(self.chunks)
        if self.dense_ready:
            import numpy as np

            qv = self._embedder.encode_queries([query])[0]
            matrix = self._embeddings
            # e5 vectors are unit-normalised, so dot product is cosine.
            cosines = list(matrix @ qv)

        # When the dense leg is absent the cosine term is identically zero. Scoring
        # a fixed 0 for it would cap every chunk at 0.40 and make the refusal
        # threshold unreachable, so the weights are renormalised over the signals
        # actually available in this process.
        w_cos, w_bm, w_sec = W_COSINE, W_BM25, W_SECTION
        if not self.dense_ready:
            total_w = w_bm + w_sec
            w_bm, w_sec = w_bm / total_w, w_sec / total_w
            w_cos = 0.0

        results: list[RetrievedChunk] = []
        for i, chunk in enumerate(self.chunks):
            bm25_norm = float(bm25_scores[i]) / max_bm25

            section_match = 0.0
            if query_tokens:
                ctoks = extract_section_tokens(f"{chunk['doc_id']} {chunk['section']}")
                if query_tokens & ctoks:
                    section_match = 1.0
                elif any(t in q_lower for t in query_tokens):
                    section_match = 0.5

            authority = AUTHORITY_WEIGHT.get(chunk.get("doc_type", "sop"), 0.7)

            base = (
                w_cos * max(cosines[i], 0.0)
                + w_bm * bm25_norm
                + w_sec * section_match
            )
            results.append(
                RetrievedChunk(
                    chunk=chunk,
                    score=base * authority,
                    cosine=float(cosines[i]),
                    bm25=bm25_norm,
                    section_match=section_match,
                    authority=authority,
                )
            )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def stats(self) -> dict:
        return {
            "chunks": len(self.chunks),
            "documents": len({c["doc_id"] for c in self.chunks}),
            "dense_ready": self.dense_ready,
            "total_chars": sum(len(c["text"]) for c in self.chunks),
        }