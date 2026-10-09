# AppBuilders PH — Local AI Hackathon: rules, requirements, judging criteria

**Source.** Transcribed verbatim from <https://appbuildersph.com/hackathon/> — tabs
**Challenge**, **Rules**, and **Judging**. Captured 9 October 2026.

**Purpose.** This file is the single source of truth for *what the host requires*.
[`SUBMISSION.md`](SUBMISSION.md) answers the submission form; this file is the
compliance audit. Every row below carries the evidence that proves it, or says
plainly that it is not yet proven.

---

## 1. The challenge — what counts as Local AI

> Cloud services may be used, but meaningful AI functionality must run locally.

**Accepted as Local AI** (host's list): Local LLMs · Local vision models · Local
speech recognition · **Local embeddings and RAG** · Local AI agents · Local image
generation · Edge AI · Offline AI · **Privacy-preserving AI** · Hybrid local + cloud
systems · AI on PCs, laptops, phones, or edge hardware.

**Accepted product types:** Productivity · Developer tools · Accessibility ·
Education · **Finance** · Gaming · Disaster response · Healthcare · Creative tools
· Enterprise tools · Computer vision · Personal assistants · **Privacy tools** ·
Local agents.

> **KALIX sits in three of these lists at once:** Local AI (local embeddings and
> RAG), Finance, and Privacy tools. That is the intended intersection, not a
> stretch.

---

## 2. Rules

*Technical requirements every project has to meet.*

### Required

| # | Requirement (verbatim) |
|---|---|
| R1 | Substantially built during the hackathon |
| R2 | A meaningful part of AI inference executes locally |
| R3 | A working product, demonstrated |
| R4 | Models, APIs, frameworks, and major tools disclosed |
| R5 | Core Local AI functionality works without depending entirely on a cloud AI API |

### Allowed

| # | Explicitly permitted (verbatim) |
|---|---|
| A1 | Existing open-source models and libraries |
| A2 | AI-assisted development |
| A3 | Devin |
| A4 | Cloud APIs as secondary components |

**Example technologies named by the host** (none of these are required, they are
illustrations): Ollama · LM Studio · **llama.cpp** · MLX · **ONNX** · PyTorch ·
TensorFlow · WebGPU · Core ML · AMD ROCm · DirectML · Hugging Face.

> **Note on A2/A3.** AI-assisted development is *explicitly allowed*, and Devin is
> named by the host. Our use of MiniMax Code is disclosed in
> [`DISCLOSURES.md`](DISCLOSURES.md) §5 rather than left implicit — permitted is not
> the same as undisclosed.

---

## 3. Judging criteria

> Half the score is how useful your product is and how real your Local AI is.

| Weight | Criterion | The judge is asking |
|---|---|---|
| **25%** | **Problem & Usefulness** | Does the project solve a genuine problem? · Is the target user clear? · Is there a realistic use case? · Would the general public actually benefit? |
| **25%** | **Local AI Implementation** | Is local inference fundamental to the product? · Does running locally provide a meaningful advantage? · **Would the product lose significant functionality if its local AI component were removed?** · Does it show the advantages of privacy, latency, offline availability, cost, or hardware utilization? |
| **20%** | **Technical Execution** | Does the product actually work? · How well are the models integrated? · How technically sophisticated is the implementation? · Is it reliable enough for a live demonstration? |
| **15%** | **Innovation** | Is the solution meaningfully different? · Does the team approach the problem in an interesting way? · Does Local AI enable something new? |
| **15%** | **Product & Demo Quality** | Is the experience understandable? · Is the UX usable? · Can the team clearly communicate the value? · Is the live demonstration convincing? |

The weights confirm the host's framing: **Problem (25%) + Local AI (25%) = half
the score.**

---

## 4. Compliance matrix

Status vocabulary — **MET**: proven by a command in this repo, reproducible by a
judge. **MET (disclosed)**: true, and we volunteer the caveat. **PARTIAL**: true in
part; the gap is stated. **NOT MET**: does not hold.

### Required rules

| # | Requirement | Status | Evidence — how a judge verifies it |
|---|---|---|---|
| **R1** | Substantially built during the hackathon | **MET** | `git log --format='%ad' --date=iso` → both commits dated 2026-10-09, the event day. Precise framing: the repository was initialised *during* the event, which is why the history is 2 commits rather than 200. What the history does not show is the stronger evidence — every component (PII engine, hybrid retrieval, corpus pipeline, console, evaluation harness, CI) is original work described in the README, built on nothing but the standard library plus named open-source models.
| **R2** | A meaningful part of AI inference executes locally | **MET** | Three neural components run on-device, none in a cloud: `multilingual-e5-small` int8 **ONNX** encoder (112 MB, 223×384 embeddings, `dense_ready: true`), optional GLiNER NER, optional Qwen2.5-3B via **llama.cpp**. Proof: `GET /api/health` → `models.embeddings.available`; `python eval/run_eval.py` prints `dense leg on: cached (223, 384)`. See §5 for the honest limit of this claim. |
| **R3** | A working product, demonstrated | **MET** | `python scripts/preflight.py` → **39/39**, asserting every claim the demo makes against a live server. CI regenerates the scoreboard on every push (`.github/workflows/verify.yml`, 3 jobs). See [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md). |
| **R4** | Models, APIs, frameworks, and major tools disclosed | **MET** | README "Stack" table; [`DISCLOSURES.md`](DISCLOSURES.md) §5 lists AI-assisted development tooling; `models/registry.yaml` records every model, licence and role; `requirements.txt` and `apps/web/package.json` are the authoritative manifests. |
| **R5** | Core Local AI functionality works without depending entirely on a cloud AI API | **MET** | **No cloud AI API is installed, required, or reachable at runtime.** `tests/test_airgap_claims.py` asserts no cloud SDK appears in `requirements.txt`, and that no runtime module outside the air-gap probe and the loopback llama.cpp client holds a network primitive. Both web surfaces ship `Content-Security-Policy: default-src 'none'`; `node apps/web/verify-ui.mjs` asserts **0 external requests** on all 4 surfaces and fails CI otherwise. CI job 1 runs the PII eval with **zero pip installs**. The badge is a live socket probe, not a string — pull the cable and it flips. |

### Judging criteria

| Weight | Criterion | Status | Where the evidence lives |
|---|---|---|---|
| 25% | **Problem & Usefulness** | **MET** | Target user is named and narrow: a Philippine bank's data-privacy officer. The problem is a 2023 NPC Advisory + BSP circular obligation with no tooling. Not hypothetical — the rules those banks must follow are the same seven instruments KALIX cites. |
| 25% | **Local AI Implementation** | **MET** | On-device: ONNX embeddings (0.60 weight of the hybrid score), optional llama.cpp generation, deterministic PII engine, HMAC pseudonyms, ledger, both UIs. **Advantage demonstrated, not asserted:** measured 0.2 ms PII p50 and 8 ms copilot p50 on CPU — no network round-trip exists to be slow. The one part that degrades gracefully is disclosed in §5. |
| 20% | **Technical Execution** | **MET** | 73 Python + 95 UI tests, all passing. Type-clean (`tsc --noEmit`), 0 npm vulnerabilities, verified in a clean minimal env with no model weights. Published metrics regenerate from committed datasets. |
| 15% | **Innovation** | **MET** | The differentiator is **refusing to be wrong**: a 3-pass verification loop that re-runs the detector over KALIX's own redaction output and escalates on anything that survives, plus correct-refusal as a first-class outcome (100% measured). A hash-chained ledger that stores counts and verdicts but *never* customer text. |
| 15% | **Product & Demo Quality** | **MET** | ChatGPT-style console, fully wired to the live API, zero fake buttons, zero mock data. 4/4 surfaces verified for console errors, overflow and external requests. |

---

## 5. Honest limits — read this before judging

Stated here rather than buried, because a judge will find them anyway.

1. **The copilot degrades gracefully.** With no model weights at all it still scores
   100% citation accuracy at 2 ms p50 (`python eval/run_eval.py --sparse-only`, run
   in CI). That is excellent engineering, but it is also the answer to *"would the
   product lose significant functionality if its local AI component were removed?"*
   — **and the honest answer today is: no, not much.** The dense leg improves
   retrieval; it is not load-bearing for the headline number.
   The genuinely load-bearing local computation is the **PII engine**, which is
   deterministic rather than neural, and the **citation-enforcement pass**, which
   is what keeps answers on the statute.

2. **No generative model has ever produced a published answer.** Every number in
   the README was measured with the answer path *extractive* — quoted verbatim
   from cited spans. This is a deliberate design choice (it is why citation
   accuracy is 100% and not "mostly"), and the UI labels such answers
   `extractive` so nobody reads them as generated prose. It also means the
   llama.cpp path is built, wired and disclosed but was not exercised for any
   published metric.

3. **GLiNER NER has never run.** The contextual-NER stage is optional; every
   published PII number was measured with it absent. The engine is regex + Luhn +
   normalisation, which is why macro-F1 is 1.0000 — and also why it is not a
   neural component.

4. **First build needs the internet.** Model weights and the corpus are fetched
   from public mirrors. *Runtime* needs nothing.

5. **Demo video and social URL are still pending.** Marked "Pending" in
   [`SUBMISSION.md`](SUBMISSION.md). They are not fabricated.

---

## 6. Judge's 90-second path

```powershell
git clone https://github.com/jcuady/Kalix-AI---App-Builders-PH-HACKATHON.git
cd Kalix-AI---App-Builders-PH-HACKATHON

# 1. Does it work? (no models, no GPU, no network)
pip install -r requirements-verify.txt
python -m pytest tests/ -q
python eval/run_eval.py --sparse-only

# 2. Does the UI stay local? (0 external requests is asserted)
npm --prefix apps/web install
npm --prefix apps/web test
node apps/web/verify-ui.mjs

# 3. Full demo readiness (starts the server itself)
.venv\Scripts\python.exe scripts\preflight.py
```