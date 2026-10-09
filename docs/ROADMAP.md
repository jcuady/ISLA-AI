# Isla AI roadmap

## What shipped, and what did not

The build ran against a hard constraint that the original blueprint did not account for: the
development machine has **no NVIDIA GPU and 15.2 GB of RAM**, and submission was ~18 hours away. The
blueprint assumed 24–30 hours on a GPU laptop.

The blueprint's own cut list was followed — it said never to cut the PII Engine or the Copilot,
because together they are 50% of the score.

| Blueprint phase | Status | Note |
|---|---|---|
| P0 Skeleton | ✅ Shipped | Adapted: Python 3.12 (3.14 has no ML wheels), llama.cpp `b11515` Vulkan build |
| P1 PII Engine | ✅ Shipped | Regex + Luhn + ensemble + verification pass. **All eval gates pass.** |
| P2 Copilot | ✅ Shipped | 223 citable chunks, hybrid retrieval, citation enforcement, refusal |
| P3 Breach Triage | ⛔ **Cut** | 72h/2h clocks and form generation. Highest demo theatre, but it would have come at the cost of the core. |
| P4 UX | ✅ Adapted | FastAPI + React on loopback instead of Tauri — no Rust or MSVC on this machine |
| P5 AI Systems Register | ⛔ **Cut** | Blueprint's designated first cut. |
| P6 Eval + docs | ✅ Shipped | 40-case PII dataset, RAG eval, published scoreboard |
| P7 Rehearse | ✅ Shipped | `docs/DEMO_SCRIPT.md` |

### What was cut, honestly

**Breach Triage (P3)** and the **AI Systems Register (P5)** are not in the build. The blueprint's
rule was to cut Register before Triage; with ~18 hours on CPU-only hardware, both went. The corpus
still contains NPC Circular 16-03 with the 72-hour rule, so the *information* is present even though
the interactive clocks are not.

This is a deliberate scope decision, not an omission. For a hackathon, one thing that works
completely beats four that work partially.

---

## Deviations from the blueprint, and why

### Python 3.12 instead of 3.14

The machine ships Python 3.14. PyPI has **zero wheels** for `transformers`, `gliner`,
`presidio-analyzer`, `sentence-transformers`, `optimum` or `llama-cpp-python` on `cp314`. Isla AI
provisions 3.12 via `uv` and `scripts/bootstrap.ps1` does it automatically.

### FastAPI + React instead of Tauri

No Rust toolchain, no MSVC C++, no Windows SDK. Installing a full C++ build environment would have
consumed hours for a native window frame. Serving the UI over loopback turned out to be *stronger* for
the pitch: a browser pointed at `127.0.0.1` makes the air-gap claim self-evident.

### multilingual-e5-small instead of bge-m3

bge-m3 is 568 M parameters (~2.3 GB) with no int8 ONNX export — unaffordable with ~1 GB free RAM.
`multilingual-e5-small` int8 is **113 MB** and genuinely cross-lingual, which is what a Taglish
query against an English legal corpus needs. It is 20× lighter.

### Qwen2.5-3B instead of 7B as the demo default

With no NVIDIA GPU, a 7B Q4_K_M runs on CPU with ~1 GB free RAM. In a live demo, a slow or
OOM-ing model is worse than a smaller one that answers instantly. The 7B and 14B tiers remain
documented for T2/T3 hardware.

### Corpus mirrors

`privacy.gov.ph` and `bsp.gov.ph` return HTTP 403 from this network. The fetcher resolves through
the Wayback Machine and lawphil. It also **content-validates** every document, because an early
fetch silently captured five identical copies of an index page instead of the actual circulars.
See [`CORPUS_SOURCES.md`](CORPUS_SOURCES.md).

---

## Next steps, in priority order

### P0 — production hardening (before any real bank data)

1. **Set `ISLA_PSEUDONYM_KEY`** from an OS keystore. The demo fallback is deterministic and must
   not see live data.
2. **Enforce SHA-256 verification at load**, not just at download.
3. **Longer pseudonym digests.** The 4-hex suffix is a demo-grade truncation and is not
   collision-resistant at scale.
4. **Key rotation**, which currently breaks joins across the boundary by design.

### P1 — the two cut features

5. **Breach Triage** — the corpus already carries NPC Circular 16-03; the rule engine for the 72h
   and BSP 2-hour clocks is deterministic by design and does not need a model.
6. **AI Systems Register** — generate NPC Circular 2022-04 registration entries and the NPC Advisory
   2024-04 governance checklist. This is the feature that produces a *regulator-facing artefact*,
   which is what makes the product purchasable rather than merely clever.

### P2 — quality

7. **LoRA tone tuning** on Qwen2.5-3B, generating training data *locally* from the corpus and
   filtering it with the RAG verifier. Never fine-tune on legal facts — that raises hallucination risk.
8. **Expand the eval set** from 40 cases toward the blueprint's 300, especially adversarial inputs
   (prompt-injection attempts asking for raw account numbers).
9. **Taglish evaluation set** to measure retrieval quality properly rather than by anecdote.

### P3 — reach

10. **Browser extension** for paste interception at the source, rather than relying on the user to
    paste into Isla AI first.
11. **Tauri shell** once a Rust toolchain is available, for the native-window experience.
12. **OCR and vision** — Qwen2-VL / PaddleOCR for scanned IDs and statements.

---

## What would change the architecture

- **A real GPU.** Moves the default model to 7B/14B and makes GLiNER cheap enough to run on every
  request rather than only on the long tail.
- **A larger corpus.** Beyond RA 10173 and NPC issuances — BSP circulars, MORB, sectoral rules. The
  retrieval architecture already handles this; only the fetcher needs new sources.
- **Multi-tenancy.** A bank with many branches would need per-branch key separation and a
  partitioned ledger. The current ledger is single-tenant by design.