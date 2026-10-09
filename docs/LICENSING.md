# KALIX licensing

A regulated buyer cannot ship GPL-viral or research-only licences into production, so every
component was selected on three criteria: **runs on commodity hardware**, **commercial-use licence**,
and **performs on Taglish**.

No model weights are committed to this repository. `models/download_models.py` fetches pinned files
and records their SHA-256.

---

## Models

| Model | Version | Licence | Commercial use | Notes |
|---|---|---|---|---|
| **Qwen2.5-3B-Instruct** (Q4_K_M GGUF) | `Qwen/Qwen2.5-3B-Instruct-GGUF` | **Apache-2.0** | ✅ Yes | Demo default. Strong Taglish for its size. |
| Qwen2.5-7B-Instruct (Q4_K_M) | `Qwen/Qwen2.5-7B-Instruct-GGUF` | Apache-2.0 | ✅ Yes | Recommended T2 workstation tier |
| Qwen2.5-14B-Instruct (Q4_K_M) | `Qwen/Qwen2.5-14B-Instruct-GGUF` | Apache-2.0 | ✅ Yes | T3 analyst workstation |
| Phi-3.5-mini-instruct | `bartowski/Phi-3.5-mini-instruct-GGUF` | **MIT** | ✅ Yes | Low-spec T1 branch-box fallback |
| multilingual-e5-small | `intfloat/multilingual-e5-small` | **MIT** | ✅ Yes | Embeddings (int8 ONNX) |
| GLiNER multi-v2.1 | `urchade/gliner_multi-v2.1` | **Apache-2.0** | ✅ Yes | Zero-shot contextual NER |

> **Llama 3.1 was deliberately excluded.** Its community licence requires a separate authorisation
> request above 700M MAU and is flagged in our own build notes as needing legal review — not
> something to ship into a bank without that review.

### Quantisation

All shipped weights are `Q4_K_M`. `IQ4_XS` is used only if VRAM is desperate; `Q4_K_M` is the quality
sweet spot and worth the ~400 MB.

---

## Runtime and libraries

| Layer | Component | Licence | Commercial use |
|---|---|---|---|
| LLM runtime | **llama.cpp** (`ggml-org/llama.cpp`, tag `b11515`) | MIT | ✅ |
| ONNX inference | **onnxruntime** | MIT | ✅ |
| Embeddings/NER serving | **optimum**, **transformers** | Apache-2.0 | ✅ |
| Machine learning | **PyTorch** (CPU build) | BSD-3-Clause | ✅ |
| Vector search | **rank-bm25** | Apache-2.0 | ✅ |
| RAG index | **numpy** | BSD-3-Clause | ✅ |
| PDF extraction | **PyMuPDF** (AGPL-3.0 **or** commercial) | ⚠️ **Review** | **See note** |
| PDF extraction (alt) | **pypdf** (BSD-3-Clause) | BSD-3-Clause | ✅ |
| API | **FastAPI**, **Uvicorn**, **Pydantic** | MIT / BSD / MIT | ✅ |
| UI | **React**, **Vite**, **TypeScript** | MIT | ✅ |
| Testing | **pytest** | MIT | ✅ |

### ⚠️ PyMuPDF licence note

PyMuPDF is licensed **AGPL-3.0 or a commercial licence**. Using it inside a closed-source product
without a commercial licence would impose AGPL obligations.

**Mitigation:** PyMuPDF is used **only in the offline corpus build tool** (`corpus/fetch_corpus.py`,
`corpus/chunk_corpus.py`) — a build-time script that is not distributed to bank users. The **shipped
runtime does not import PyMuPDF**; it reads pre-built `chunks.jsonl`.

For distribution in any packaged form, either:
1. obtain a PyMuPDF commercial licence, or
2. swap to **`pypdf`** (BSD-3-Clause) — already available as an installed dependency, and the chunker
   has a single extraction call site to change.

This is flagged rather than silently shipped.

---

## Corpus

All source documents are **public government publications**:

| Document | Issuer | Status |
|---|---|---|
| RA 10173 — Data Privacy Act of 2012 | Congress of the Philippines | Public domain / official publication |
| IRR of RA 10173 (as amended) | National Privacy Commission | Public official publication |
| NPC Circular No. 16-03 | National Privacy Commission | Public official publication |
| NPC Circular No. 2022-01 | National Privacy Commission | Public official publication |
| NPC Circular No. 2022-04 | National Privacy Commission | Public official publication |
| NPC Circular No. 2023-04 | National Privacy Commission | Public official publication |
| NPC Advisory No. 2024-04 | National Privacy Commission | Public official publication |

Per-document provenance and SHA-256 are recorded in `corpus/raw/fetch_manifest.json`. Government
issuances are not third-party copyrighted works, but attribution is retained in every citation and
each source URL is preserved so any statement can be traced to the issuing authority.

---

## Evaluation data

`eval/datasets/` and the corpus index were **created for this project** from public documents and
synthetic examples modelled on realistic Philippine banking artefacts.

**No real customer data, real account numbers, or real personal records are included anywhere in this
repository.**

---

## KALIX code and brand

The KALIX source code, the shield logo, and the brand identity are original works created for this
project. The logo derives from *kalasag* (shield) and was designed specifically for this submission.