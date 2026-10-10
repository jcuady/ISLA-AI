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

import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PROCESSED = REPO_ROOT / "corpus" / "processed"
CHUNKS_PATH = PROCESSED / "chunks.jsonl"

W_COSINE = 0.60


def corpus_fingerprint(chunks: list[dict]) -> str:
    """A content hash of the corpus the embedding matrix was built from.

    The cache used to be validated on row count alone. That catches a corpus
    that grew or shrank, but it cannot see an edit that leaves the count
    untouched - and search() indexes cosines by chunk position, so a stale
    matrix silently scores every query against vectors encoded from text that
    is no longer in the corpus. Hashing the actual text closes that.

    Row order is part of the fingerprint for the same reason: position is the
    join key between a chunk and its vector.
    """
    h = hashlib.sha256()
    for c in chunks:
        h.update(c.get("chunk_id", "").encode("utf-8"))
        h.update(b"\x00")
        h.update(c.get("text", "").encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()
W_BM25 = 0.25
W_SECTION = 0.15

# Authority multipliers by document type. Tier 1 is the statute itself.
#
# sector_guidance is Isla AI's own compiled operational aid. It is deliberately
# below everything, including internal SOPs at 0.70: a question that a statute
# can answer must never be answered by the guide instead, and a judge should be
# able to see at a glance that the guide outranked nothing.
AUTHORITY_WEIGHT = {
    "statute": 1.00,
    "irr": 0.98,
    "circular": 0.96,
    "advisory": 0.94,
    "bsp_memo": 0.88,
    "morb": 0.88,
    "sop": 0.70,
    "sector_guidance": 0.55,
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
    # Front-line and customer-facing vocabulary. A call-centre agent asking
    # "pwede ba humingi ng CVV sa customer?" was refused as out-of-scope
    # because none of the above terms appeared in it. That was wrong: asking
    # for a card credential IS data-privacy processing, so the question is
    # squarely in domain even though it contains no legal vocabulary at all.
    "credit card", "debit card", "card number", "cardholder", "cvv", "cvc",
    "security code", "atm", "pin", "password", "otp", "one-time",
    "verification code", "agent", "call center", "call centre",
    "front line", "frontline", "teller", "recorded call", "recording",
    "transcript", "chat log", "screenshot", "employee", "staff",
    "disclose", "solicit", "soliciting", "over the phone", "caller",
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

# Front-line and customer-facing phrasing. The recurring bank question is not
# written in legal register: a call-centre agent asks "pwede ba humingi ng CVV
# sa customer?" and the statute never uses the words CVV, agent or customer.
# Raw BM25 scored that question at 0.000 against the provision that actually
# decides it - RA 10173 Section 11(d), which requires collection to be adequate
# and not excessive, and Section 20(e), which holds agents to strict
# confidentiality. So the phrasing is mapped onto the words the Act uses.
#
# ROLE and ACTION are deliberately separate lists. "Can our call center use AI
# to score our agents?" contains two role cues and no action, and it is an
# automated-decision question answered by NPC Advisory 2024-04. Expanding it
# toward confidentiality pulled it off that document and dropped source
# attribution from 80% to 60%. Roles describe WHO is asking, which says nothing
# about what the question is about; only actions do.
_FRONTLINE_ROLE_CUES = (
    "agent", "ahente", "teller", "call center", "call centre",
    "customer service", "customer-facing", "staff", "employee",
    "caller", "over the phone", "front line", "frontline", "front desk",
)
_FRONTLINE_ACTION_CUES = (
    "recorded call", "recording", "record the call", "call recording",
    "tape the call", "transcript", "chat log", "screenshot",
    "conversation with", "chat with the", "how long", "retention",
    "delete the recording", "disclose to the", "read out", "spell out",
    "write down", "take down", "note down",
    "humingi", "i-ask", "magtanong", "ibigay", "kayang",
    "ask the customer", "ask the client", "solicit",
)
_FRONTLINE_TERMS = (
    # DPA anchors that decide a front-line question.
    "sensitive", "personal", "information", "financial",
    "adequate", "excessive", "purpose", "declared", "legitimate",
    "strict", "confidentiality", "employees", "agents", "representatives",
    "security", "measures", "reasonable", "appropriate",
    "consent", "lawful", "unauthorized", "processing", "penalized",
    "breach", "notification", "data", "protection", "officer",
    "retention", "retained", "collected",
)

# Card and account credentials specifically. These map onto the two provisions
# that make soliciting a card secret a privacy matter rather than a style rule:
# RA 10173 Section 11(d) (adequate and not excessive) and Section 20(e)
# (employees, agents and representatives hold personal information under
# strict confidentiality).
_CARD_CREDENTIAL_CUES = (
    "cvv", "cvc", "cvv2", "cid", "security code", "card verification",
    "likod ng credit card", "back of the card", "back of their card",
    "cardholder data", "card number", "credit card", "debit card",
    " atm pin", "pin code", "personal identification number",
    "password", "login", "log-in", "one-time", "otp", "authenticator",
    "verification code",
)
_CARD_CREDENTIAL_TERMS = (
    "sensitive", "authentication", "personal", "information", "financial",
    "adequate", "excessive", "purpose", "collected",
    "strict", "confidentiality", "employees", "agents", "representatives",
    "security", "measures", "reasonable", "appropriate", "unlawful",
    "disclosure", "unauthorized", "processing", "penalized",
    "card", "verification", "value", "pin", "password", "credential",
    "login", "breach", "notification", "72", "hours",
)


# Classification questions ("is credit card information SPI?") are a different
# question from handling questions. The handling expansions pull Section 20
# hard, because Section 20 really is the strongest provision for "may I collect
# this". But a question about what a category of data IS is answered by the
# SPI definition in RA 10173 Section 3 and the SPI rules in Section 13.
_CLASSIFICATION_CUES = (
    "sensitive personal", "sensitive?", "considered sensitive", "classified",
    "is it spi", "spi?", " considered personal information", "is personal data",
    "does it count as", "fall under", "falls under", "covered by",
    "considered private", "private information",
)
_CLASSIFICATION_TERMS = (
    "sensitive", "personal", "information", "privileged",
    "prohibited", "consent", "authorization", "lawful", "processing",
    "financial", "definition", "means", "refers",
)


# Registration questions. "Kailangan ba mag-register ng AI credit scoring model
# ang banko namin?" was answered with NPC Advisory 2024-04 (what AI systems
# owe) instead of NPC Circular 2022-04 (how a processing system is registered),
# because "ai", "credit", "scoring" and "model" all pull the advisory and
# "register" alone is too rare to pull back. Registration is its own body of
# vocabulary with its own instrument.
_REGISTRATION_CUES = (
    "mag-register", "magregister", "registro", "register", "registration",
    "dps", "data processing system", "processing system", "seal of registration",
    "certificate of registration", "notified entity", "privacy.gov.ph/registration",
)
_REGISTRATION_TERMS = (
    "registration", "registry", "registered", "register", "certificate",
    "seal", "processing", "system", "systems", "notification", "notify",
    "circular", "dpo", "accountability", "penal",
)


def expand_query(query: str) -> list[str]:
    """Query tokens plus statutory synonyms implied by the phrasing."""
    tokens = tokenize(query)
    low = query.lower()
    if any(cue in low for cue in _OUTBOUND_CUES):
        tokens += [_stem(t) for t in _OUTBOUND_TERMS]
    if any(cue in low for cue in _DATA_HANDLING_CUES):
        tokens += [_stem(t) for t in _DATA_HANDLING_TERMS]
    if any(cue in low for cue in _FRONTLINE_ACTION_CUES):
        tokens += [_stem(t) for t in _FRONTLINE_TERMS]
    if any(cue in low for cue in _CARD_CREDENTIAL_CUES):
        tokens += [_stem(t) for t in _CARD_CREDENTIAL_TERMS]
    if any(cue in low for cue in _CLASSIFICATION_CUES):
        tokens += [_stem(t) for t in _CLASSIFICATION_TERMS]
    if any(cue in low for cue in _REGISTRATION_CUES):
        tokens += [_stem(t) for t in _REGISTRATION_TERMS]
    return tokens


# Questions that turn on an operational rule the corpus does not hold.
_SOLICITATION_CUES = (
    "humingi", "i-ask", "magtanong", "tinanong", "ask", "asking", "request",
    "solicit", "disclose", "kayang", "ibigay", "pwede", "can i", "can we",
    "can our", "should i", "should we", "allowed", "permit", "bakit", "why",
    "take down", "write down", "record", "hold on to",
    "read", "spell", "say aloud", "recite", "verify", "confirm",
)

# The one thing this system must never do is let a front-line "can I ask the
# customer for the CVV?" resolve into a confident yes or no that it has no
# authority for. The Data Privacy Act makes the situation a privacy matter and
# the corpus answers that part. Whether the bank's card programme permits the
# act is set by PCI DSS and Bangko Sentral regulations, which are not indexed.
# Rather than refuse (the previous behaviour, which read as "not my scope" and
# was useless to the person asking) or bluff, the copilot answers the part it
# can cite and then states the boundary out loud.
SCOPE_NOTE = (
    "SCOPE NOTE: everything quoted above comes from the instruments this "
    "system holds locally - the Data Privacy Act, its IRR, and the National "
    "Privacy Commission circulars. The operational go/no-go rule at the "
    "counter (whether staff may solicit a card verification value, PIN, "
    "password or one-time code, and how long a recording may be kept) is set "
    "by PCI DSS and by Bangko Sentral regulations, neither of which is in "
    "this corpus, so this answer does not decide that question. Confirm with "
    "your data protection officer and the bank's card security policy before "
    "you act on a customer."
)


def scope_note_for(query: str) -> str | None:
    """The operational-scope boundary, when the question depends on it.

    Fires on a credential or an interaction cue, never on a role alone. A
    role alone is not an operational question: "can our call center use AI to
    score our agents" mentions a call centre and has nothing to do with PCI DSS.
    """
    low = query.lower()
    credential = any(cue in low for cue in _CARD_CREDENTIAL_CUES)
    interaction = any(cue in low for cue in _FRONTLINE_ACTION_CUES)
    solicitation = any(cue in low for cue in _SOLICITATION_CUES)
    return SCOPE_NOTE if ((credential or interaction) and solicitation) else None


def extract_section_tokens(text: str) -> set[str]:
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

            from services.copilot import embeddings
            from services.copilot.embeddings import Embedder

            embedder = Embedder()
            if not embedder.available:
                print("[index] dense leg unavailable:", embedder.reason)
                return False

            emb_path = PROCESSED / f"embeddings.{embeddings.POOLING}.npy"
            fp_path = PROCESSED / f"embeddings.{embeddings.POOLING}.npy.fingerprint"
            fingerprint = corpus_fingerprint(self.chunks)
            cached = None
            if emb_path.exists():
                cached = np.load(emb_path)
                # A cached matrix from a different corpus build is not a stale
                # cache, it is a crash: search() indexes cosines by chunk
                # position, so a matrix with the wrong row count raises
                # IndexError deep inside the query path. The corpus grew from
                # 227 to 246 chunks when the operational guide was added, which
                # is exactly how that happened.
                if cached.shape[0] != len(self.chunks):
                    print(f"[index] cached embeddings {cached.shape[0]} rows != "
                          f"{len(self.chunks)} chunks; re-encoding")
                    cached = None
                # Row count alone cannot see an edit that leaves the chunk
                # count unchanged, so the content is hashed as well.
                elif not fp_path.exists() or fp_path.read_text(encoding="utf-8").strip() != fingerprint:
                    print("[index] cached embeddings predate the current chunk "
                          "text; re-encoding")
                    cached = None

            if cached is not None:
                self._embeddings = cached
                print(f"[index] dense leg on: cached {self._embeddings.shape} ({embeddings.POOLING})")
            else:
                print(f"[index] encoding corpus with e5-small ({embeddings.POOLING} pooling)...")
                matrix = embedder.encode_chunks([c["text"] for c in self.chunks])
                np.save(emb_path, matrix)
                fp_path.write_text(fingerprint, encoding="utf-8")
                self._embeddings = matrix
                print(f"[index] cached embeddings {matrix.shape} -> {emb_path.name}")

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