# Submission checklist — AppBuilders PH 2026, Local AI track (Finance)

**Deadline: 10:00 AM, 10 October 2026. No extensions.**

The host's rules and judging criteria, transcribed verbatim with a compliance
matrix, are in [`HACKATHON_RULES.md`](HACKATHON_RULES.md). This file answers the
submission form.

Run the pre-flight check as close to the slot as possible:

```powershell
.venv\Scripts\python.exe scripts\preflight.py
```

It prints `PRE-FLIGHT PASSED — 39/39 checks` or the demo should not start.

---

## The project

| Item | Status |
|---|---|
| **Project name** | **KALIX** — *Walang datos na lumalabas.* |
| **Short description** | On-device AI privacy-compliance copilot for Philippine banks. Detects and redacts PH banking PII before staff paste it into external AI, and answers Data Privacy Act questions offline with citations. |
| **Team members** | Malcolm Joaquin Cuady — Developer · Author. Mark Quiazon — Project Manager. Boundless IT Solutions (BITS). |
| **Public GitHub repository** | <https://github.com/jcuady/Kalix-AI---App-Builders-PH-HACKATHON> |

## The proof

| Item | Status |
|---|---|
| **Demo video** | Pending — recorded against `docs/DEMO_SCRIPT.md` after pre-flight passes |
| **X / LinkedIn video URL** | Pending |
| **What runs locally** | Egress Guard · DPA Copilot · audit ledger · HMAC pseudonyms · air-gap socket probe · both web surfaces · 168-test suite (73 Python + 95 UI) · the whole evaluation harness. Every published number was produced locally. |
| **What requires internet** | **Build time only**: model weight download (Qwen2.5-3B GGUF, multilingual-e5 ONNX, optional GLiNER) and corpus fetch from public NPC / lawphil mirrors. **Runtime: nothing.** No customer data leaves the machine and no cloud service is called; the only outbound traffic is the air-gap probe's own empty TCP handshake. Both web surfaces ship `default-src 'none'`. |

## The disclosures

| Item | Where |
|---|---|
| **Models used** | `multilingual-e5-small` int8 ONNX (113 MB, MIT) · `Qwen2.5-3B-Instruct` Q4_K_M (2.0 GB, Apache-2.0, *optional*) · `gliner_multi_pii-v1` (1.1 GB, Apache-2.0, *optional*). All fetched at install time, never committed. → [`DISCLOSURES.md`](DISCLOSURES.md) §1 |
| **Technologies and frameworks** | Python 3.12 · FastAPI · Uvicorn · Pydantic v2 · React 18 · TypeScript 5.6 · **Vite 8** · Tailwind CSS v4 · Radix UI · lucide-react · Vitest 4 · llama.cpp (Vulkan) · ONNX Runtime · Transformers · PyTorch CPU · rank-bm25 · pytest · Playwright · GitHub Actions → [`DISCLOSURES.md`](DISCLOSURES.md) §3 |
| **APIs and cloud services** | **No cloud AI API is used at runtime.** None. Hugging Face Hub and lawphil/eLibrary are build-time only. No telemetry, no analytics, no error reporting. → [`DISCLOSURES.md`](DISCLOSURES.md) §2 |
| **Existing code and assets** | Third-party model weights and llama.cpp binaries (pinned `b11515`), fetched not committed. Legal documents are public primary sources, unmodified, with URLs + SHA-256 in [`CORPUS_SOURCES.md`](CORPUS_SOURCES.md). Evaluation datasets are synthetic — no real customer records. Everything else was written for this project; the logo and brand identity are original. → [`DISCLOSURES.md`](DISCLOSURES.md) §4 |
| **AI development tools** | **MiniMax Code (`mavis` agent)** — primary development assistant, ran the build end to end. AI image generation for the shield mark (rekeyed and recoloured by script; vector master hand-authored). Archify for the architecture diagram. → [`DISCLOSURES.md`](DISCLOSURES.md) §5 |

## Every submission must answer

### Why does this product benefit from running AI locally?

Full answer in the [README](../README.md#why-does-this-product-benefit-from-running-ai-locally).
In short:

1. **Using a cloud model to find PII requires first sending the PII.** Asking an external model
   "is this sensitive personal information?" is itself a disclosure to a third party in a foreign
   jurisdiction — the act is the breach it is meant to prevent.
2. **Target environments have no network by design.** Air-gapped core-banking and ISO 27001-sealed
   networks exist precisely because the response window is hours long. The control must work with
   the cable out, not degrade when it is pulled. KALIX is demonstrated that way.
3. **Per-paste economics fail at API pricing.** 0.2 ms p50 with no per-call cost is arithmetic we
   already own.
4. **Regulators are already asking.** NPC Advisory 2024-04 applies the DPA to AI processing personal
   data. Banks can now produce that proof locally, as a hash chain that never stores customer text.
5. **Confidentiality is auditable or it is not.** "Read our DPA" is a claim; "no module on the
   request path opens a network connection, the CSP forbids off-origin fetches, and both are
   asserted in CI" is a test. We do not claim KALIX opens no socket at all — the air-gap probe
   deliberately opens empty TCP handshakes so the badge can be falsified live.

---

## Ready — nothing to do

| Item | State |
|---|---|
| Working product, landing page + 3-screen console | <http://127.0.0.1:8765> → console at `/app` |
| Egress Guard (P1) | macro-F1 **1.0000**, residual **0.00%** |
| DPA Copilot (P2) | citation accuracy **100%**, correct-refusal **100%** |
| Local AI, no cloud fallback | probed, not asserted |
| Real published scoreboard | all gates PASS — [`../eval/RESULTS.md`](../eval/RESULTS.md) |
| Honest disclosures | [`DISCLOSURES.md`](DISCLOSURES.md), incl. the metric that missed |
| Architecture diagram | Archify-validated |
| Logo and brand kit | [`../branding/brand.md`](../branding/brand.md) |
| README, threat model, licensing, roadmap | [`../README.md`](../README.md) · [`THREAT_MODEL.md`](THREAT_MODEL.md) · [`LICENSING.md`](LICENSING.md) · [`ROADMAP.md`](ROADMAP.md) |
| CI reproducing every number | [`.github/workflows/verify.yml`](../.github/workflows/verify.yml) |
| Pre-flight self-check | `scripts/preflight.py` — 39 assertions |

## Blocked on a human — cannot be automated

- [ ] **Demo video** recorded and uploaded
- [ ] **X / LinkedIn URL** added to this file, the README, and the submission form
- [ ] Final read of the README for anything overstated

## Optional, if time allows

- **Qwen2.5-3B** — Hugging Face throttles this host to ~0.33 MB/s, so the 2.0 GB
  GGUF takes roughly 100 minutes. The downloader is now resumable, so an
  interrupted transfer continues instead of restarting. The product is fully
  functional without it and **every published number was measured without it**.
- **GLiNER NER** — same throttling. Every published PII number was measured with
  GLiNER **absent**.

> Correction to an earlier note in this file: a previous revision reported the
> download as "stalled at 2,007 of 2,105 MB". That figure was the **preallocated
> sparse file size**, not downloaded content. Actual content was 545 MB (25.9%).