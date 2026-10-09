# Architecture

KALIX is one process, three engines, and no network. This document explains how those parts fit
together and why.

---

## Process topology

```
                 ┌───────────────────────────────────────────┐
                 │  Browser (any modern browser)              │
                 │  http://127.0.0.1:8765                    │
                 └────────────────────┬──────────────────────┘
                                      │ HTTP over loopback only
                 ┌────────────────────▼──────────────────────┐
                 │  KALIX Local Core  (FastAPI / uvicorn)     │
                 │                                           │
                 │  ┌─────────────┐  ┌────────────────────┐  │
                 │  │ /api/pii/*  │  │ /api/copilot/ask  │  │
                 │  │ Egress Guard│  │ DPA Copilot       │  │
                 │  └──────┬──────┘  └─────────┬──────────┘  │
                 │         │                   │             │
                 │  ┌──────▼───────────────────▼──────────┐  │
                 │  │  engines (in-process, no sockets)    │  │
                 │  │  • PII ensemble (regex+Luhn+NER)    │  │
                 │  │  • retrieval (dense + BM25 + section)│ │
                 │  │  • generation (local llama.cpp)     │  │
                 │  └──────────────────────────────────────┘  │
                 │                                           │
                 │  ┌──────────────────────────────────────┐  │
                 │  │  audit ledger (SHA-256 hash chain)    │  │
                 │  │  /api/airgap  (real socket probe)     │  │
                 │  └──────────────────────────────────────┘  │
                 └───────────────────────────────────────────┘
                                      │
                        no outbound socket, ever
```

The browser is a client, not a dependency. Everything is loopback. `assert_loopback()` runs at import
time, so the process **cannot** start on a routable address.

---

## Module map

| Path | Responsibility |
|---|---|
| `services/core/app.py` | FastAPI app, routes, lifespan, static UI serving |
| `services/core/airgap.py` | Loopback assertion + live outbound probe |
| `services/core/ledger.py` | Append-only SHA-256 hash-chained audit ledger |
| `services/core/llm.py` | Optional client for a local llama.cpp server |
| `services/pii/recognizers.py` | Stage 1: deterministic PH recognizers, Luhn, normalisation |
| `services/pii/ner.py` | Stage 2: GLiNER zero-shot contextual NER (optional) |
| `services/pii/engine.py` | Stages 3–5: ensemble, redaction, verification pass, verdict |
| `services/copilot/retrieval.py` | Hybrid index, authority weighting, topical grounding |
| `services/copilot/embeddings.py` | multilingual-e5-small int8 ONNX embedder |
| `services/copilot/copilot.py` | Grounded answers, citation enforcement, refusal |
| `corpus/` | Mirror-aware fetcher, structure-aware chunker |
| `eval/` | Datasets + scoreboard generator |

---

## Data flow — Egress Guard

```
POST /api/pii/redact { text }
  │
  ├─ 1. normalise      Taglish digit forms unified
  │                    "09 17 123 4567" ≡ "+63 917 123 4567"
  │
  ├─ 2. mask tokens    Existing [TAG-HASH] tokens blanked, offsets preserved
  │                    (prevents the verifier rediscovering its own output)
  │
  ├─ 3. Stage 1        Deterministic recognisers, ordered by precision.
  │                    Higher-precision formats claim spans first, so
  │                    "12-345-6789" is an SSS and not also a TIN.
  │                    Checksums (Luhn) decide PAN confidence.
  │
  ├─ 4. Stage 2        GLiNER zero-shot NER, 19 PH labels (optional)
  │
  ├─ 5. Stage 3        ensemble = 0.45·regex + 0.35·gliner + 0.20·context
  │                    overlapping spans resolved by confidence
  │
  ├─ 6. Stage 4        redact → RE-DETECT over the output → repeat ≤3×
  │                    residual after 3 passes ⇒ BLOCK_ESCALATE
  │
  ├─ 7. Stage 5        verdict + advisory note
  │
  └─ 8. ledger         hash + counts + verdict (never the text)
```

**Why the verification pass exists:** a redactor you have not verified is a liability. Re-running
detection over the *output* is what lets "0.00% residual leakage" be a measurement rather than a
hope.

**Why PERSON is not redacted:** Philippine names ("de la Cruz", "Santos") are everywhere. Treating
them as a redaction trigger turns every message to mush. PERSON is surfaced as a **risk signal**
only.

---

## Data flow — DPA Copilot

```
POST /api/copilot/ask { text }
  │
  ├─ retrieve         score = w_cos·cosine + w_bm·BM25 + w_sec·section_match
  │                   × authority_weight(doc_type)
  │                   weights renormalise when the dense leg is absent,
  │                   so scoring stays calibrated in either mode
  │
  ├─ ground gate      reject out-of-domain questions BEFORE answering,
  │                   so refusal happens for the right reason
  │
  ├─ threshold        below REFUSAL_THRESHOLD ⇒ refuse in Taglish,
  │                   report what was found and what is missing
  │
  ├─ extract          rank sentences; operative-fact and quantified
  │                   sentences ("within 72 hours") outrank keyword overlap
  │
  ├─ generate         LLM optional. Constrained to quote cited spans.
  │                   Output without a citation tag is REJECTED.
  │
  └─ footer           advisory notice + corpus as-of date
```

**Why extractive-first:** the entire body of Philippine privacy law is a few hundred pages. Grounding
beats fine-tuning, which would change what the model *says* rather than what it *knows* — and would
make a fabricated circular number more likely, not less.

---

## Authority weighting

Retrieval multiplies the blended score by a per-document-type weight:

| Document type | Weight | Rationale |
|---|---|---|
| statute (RA 10173) | 1.00 | The law itself |
| irr | 0.98 | Binding rules under the statute |
| circular | 0.96 | NPC binding issuances |
| advisory | 0.94 | NPC guidance |
| bsp_memo | 0.88 | Supervisory expectation |
| sop | 0.70 | Internal, weakest |

The tier is surfaced in the UI so the officer always knows what authority they are reading.

---

## Failure semantics

Every optional dependency fails **safe**, and `/api/health` reports the truth:

| Failure | Behaviour |
|---|---|
| Dense model absent | BM25 + section matching; weights renormalise so the refusal threshold stays meaningful |
| LLM absent | Extractive answers from cited spans — no invention is possible |
| GLiNER absent | Regex + Luhn ensemble; verification pass still runs |
| Corpus absent | `/api/copilot/ask` returns HTTP 503 with the exact commands to build it |
| Retrieval thin | **Refusal**, not a guess |
| Residual PII after redaction | **BLOCK_ESCALATE**, never release |

The governing principle is **fail closed**. For a compliance tool a wrong answer is worse than no
answer, so every uncertain path refuses and says so.

---

## Concurrency and state

- The FastAPI process is single-process. The audit ledger serialises appends with a lock.
- Model and index objects are loaded once at startup (lifespan) and shared read-only.
- ONNX Runtime uses 4 intra-op threads; GLiNER and llama.cpp are separate processes.
- No shared mutable state exists between requests other than the append-only ledger.

---

## Security properties

| Property | Enforcement |
|---|---|
| Loopback-only binding | `assert_loopback()` at import |
| No telemetry | No analytics, crash reporting, or update pings anywhere |
| Ledger holds no PII | Only hashes, counts, verdicts, latency |
| Tamper evidence | SHA-256 chain; `verify()` reports the first broken seq |
| Weight integrity | SHA-256 recorded at download |
| Pseudonym irreversibility | HMAC-SHA256, client-held key |

See [`THREAT_MODEL.md`](THREAT_MODEL.md) for the full trust analysis and known limits.