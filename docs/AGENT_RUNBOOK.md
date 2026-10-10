# Isla AI — Agent Runbook

**Read this before touching anything.** This file is written for an AI agent
picking up the repository cold. It assumes you have the repo, a Windows
machine, and no prior context.

- **Repo:** <https://github.com/jcuady/ISLA-AI> · local root contains
  `README.md`, `docs/`, `services/`, `apps/web/`, `corpus/`, `eval/`, `tests/`
- **Submission deadline: 10:00 AM, 10 October 2026 (Philippine time).**
- **Demo script:** [`DEMO_60S.md`](DEMO_60S.md) — three clicks, zero typing.

---

## 0. The five rules that matter most

These are not style preferences. Violating them produces work that looks fine
and is wrong.

1. **Never move a gate to fit a result.** If a threshold fails, the code or the
   claim is wrong — fix the cause. Moving the number is how a project becomes
   a lie, and it is the one thing that cannot be undone before judging.
2. **Never fabricate Philippine law.** Where a rule cannot be fetched, the
   product names the gap. `LegalHook(GAP)` and `tests/test_fraud_corpus.py`
   enforce this. BSP, SEC and AMLC are *absent on purpose*.
3. **Never report a number you did not measure on the current machine.** If the
   embedding model is missing, retrieval degrades and every published figure is
   invalid (see §3).
4. **Tests must never touch the production audit ledger.** `tests/conftest.py`
   redirects it via `ISLA_LEDGER_PATH`. Do not "simplify" that away.
5. **When a check reports a defect in code you are confident is correct, suspect
   the check first.** Two real QA checks were wrong and were corrected — the
   product was not. Then verify the correction is real, not convenient.

---

## 1. Environment gotchas (Windows PowerShell 5.1)

These cost real time if you hit them cold.

| Trap | Do this |
|---|---|
| Console mojibake on Python output | `$env:PYTHONIOENCODING="utf-8"` before **every** Python call |
| No heredocs — `<<'EOF'` is a parse error | Write a temp `.py` file with the file tool, run it, then `rm -- "path"` |
| `Set-Content -Encoding utf8` writes a **BOM** | Use `[System.IO.File]::WriteAllText($p, $t, (New-Object System.Text.UTF8Encoding($false)))` — and `[System.IO.File]` needs an **absolute** path |
| File deletion | One top-level `rm -- "a" "b"`. Never `Remove-Item`, never bare `del` |
| Background server tasks get killed | `Start-Process ... -WindowStyle Hidden` survives; a managed background task does **not** |
| `python -c` with quotes | PowerShell mangles `\"` inside `-c`. Use a temp `.py` file for anything non-trivial |

---

## 2. Run it

### 2a. Warm machine (the dev laptop)

```powershell
cd <repo root>
npm --prefix apps\web run build          # REQUIRED — see §3
Start-Process -FilePath ".venv\Scripts\python.exe" `
  -ArgumentList "-m","uvicorn","services.core.app:app","--host","127.0.0.1","--port","8765" `
  -WorkingDirectory "<repo root>" -WindowStyle Hidden
```

First start takes **6–20 s**; the first start after a corpus change takes
**~45 s** because it re-encodes the embedding matrix. Poll
`http://127.0.0.1:8765/api/health` until it returns `200`.

Never start it in the foreground expecting it to return.

### 2b. Fresh clone

`scripts/bootstrap.ps1` provisions a clean machine end to end and is
idempotent:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1
```

**Python 3.12 is required.** 3.14 has no wheels for `transformers`, `gliner`,
`optimum` or `llama-cpp-python`.

### 2c. Model weights — the step people miss

`models/weights/` is **gitignored**. A fresh clone has no models. Without the
embedding model the product still runs, but retrieval falls back to BM25 only
and **every published number becomes invalid**.

```powershell
# Just the 113 MB critical model — the one you need for the demo
.venv\Scripts\python.exe models\download_models.py --only multilingual-e5-small-int8
```

Optional, large, and **not needed for the demo**: `qwen2.5-3b-instruct-q4_k_m`
(2.0 GB) and `gliner-multi-v2.1` (1.1 GB). Use `--skip-optional` to skip both.

Known: the huggingface.co single-stream path can stall. The fetcher uses
ranged parallel connections; check the progress **log line**, not the `.part`
file size — it preallocates the full length.

---

## 3. Two things that will silently break a run

**`apps/web/dist/` is gitignored.** The Python job in CI never builds it. If you
run the test suite on a fresh checkout without `npm run build`, the routing and
delivery tests skip — this is deliberate and asserted, not a silent pass.
Always build before the full suite.

**The corpus is committed; the raw sources are not.** `corpus/processed/
chunks.jsonl` (348 chunks, 12 documents) is tracked so the demo works with no
network. `corpus/raw/*.pdf` is gitignored. To rebuild the corpus you need the
raw files back: `corpus/fetch_corpus.py` (needs internet). Never edit
`chunks.jsonl` by hand — fix `corpus/chunk_corpus.py` and rebuild.

---

## 4. Verify — every gate, with the exact line to look for

Run from the repo root. All of these must pass before a demo.

```powershell
$env:PYTHONIOENCODING="utf-8"
npm --prefix apps\web run build
.venv\Scripts\python.exe -m pytest tests\ -q        # 393 passed
cd apps\web; npx vitest run; npx tsc --noEmit; cd ..\..
.venv\Scripts\python.exe eval\run_eval.py
.venv\Scripts\python.exe eval\risk_eval.py
.venv\Scripts\python.exe scripts\qa_probe.py
.venv\Scripts\python.exe scripts\use_case_walk.py
.venv\Scripts\python.exe scripts\preflight.py
node apps\web\verify-ui.mjs
node apps\web\qa-frontend.mjs
node apps\web\rehearse-60s.mjs
.venv\Scripts\python.exe scripts\demo_walkthrough.py   # needs the server up
```

| Gate | Expected |
|---|---|
| `pytest` | `393 passed` |
| `vitest` | `Tests 108 passed (108)` — **501 total** (393 Python + 108 UI) |
| `tsc --noEmit` | silent |
| `run_eval` | `PII macro-F1 1.0000` · `residual 0.0000` · all 4 gates `PASS` |
| `risk_eval` | `P 0.850 R 0.944 F1 0.895` · `tier 1.000` · all 5 gates `PASS` |
| `qa_probe` | `probes: 126   flagged: 0` |
| `use_case_walk` | `use cases: 59   passed: 59   failed: 0` |
| `preflight` | `PRE-FLIGHT PASSED — 49/49 checks. Ready to demo.` |
| `verify-ui` | `All surfaces clean.` (also asserts the CSP inline-script hash) |
| `qa-frontend` | `front-end checks: 34   passed: 34   failed: 0` |
| `rehearse-60s` | `rehearsal: 27   passed: 27   failed: 0` |

**Published figures that must not regress:** PII macro-F1 1.0000 · high-risk
R/P 1.0000 · residual 0.00% · citation 100% · refusal 100% · fraud P 0.850 /
R 0.944 / F1 0.895 · tier 1.000 · routine FPR 0/3 · latency p50 0.2 / 11 / 4 ms ·
corpus 348 chunks / 12 documents / 11 instruments · preflight 49/49.

Latency jitters by ±1–2 ms between runs. `eval/RESULTS.md` is the authority and
is regenerated by `run_eval.py`; if a doc disagrees with it, the doc is wrong.

---

## 5. Demo

### 5a. If you are driving the browser

Follow [`DEMO_60S.md`](DEMO_60S.md) exactly. It is three clicks and zero typing,
and `rehearse-60s.mjs` machine-checks every string it quotes. Do not improvise
the numbers — read them off the screen.

### 5b. If you are an agent with no browser

`scripts/demo_walkthrough.py` walks all four moves against the live API. Copy
from its output; do not write the payloads from memory.

The API contract, stated once so you stop guessing:

```python
# The request key is "text". Sending "question" returns 422.
post("/api/pii/redact",   {"text": "..."})   # -> verdict, entities, passes, residual_leakage
post("/api/copilot/ask",  {"text": "..."})   # -> answer, citations, refused
post("/api/risk/assess",  {"text": "..."})   # -> tier, exposed, red_flags, required_actions
```

- Risk returns **`red_flags`**, *not* `indicators`.
- Egress verdict is `BLOCK_ESCALATE`; the UI renders it `BLOCK & ESCALATE`.
- `citation_count` may legitimately be `0` on a risk flag whose `legal_hook`
  is a GAP — that is the product being honest, not a bug.

---

## 6. Invariants — do not break these

- **The copilot is extractive.** Answers are retrieved spans, never generated.
  `llm=False` in a fresh run is *correct*, not a broken install.
- **A citation appears only when retrieval returned a span from that document
  containing the anchor phrase.** Near matches carry `anchor_in_text: false`.
- **The risk engine is a deterministic rule table, not a model call**, so an
  officer can reproduce the reason months later.
- **The audit ledger is hash-chained and stores counts and verdicts, never
  customer text.** It is cross-process safe via a sidecar lock — do not
  reintroduce an in-process-only lock.
- **Both web surfaces ship `Content-Security-Policy: default-src 'none'`.** The
  landing page's only inline script is allowed by SHA-256. If you edit it,
  update the hash in **both** `landing.html` and `services/core/app.py`, or
  `verify-ui.mjs` fails and the page silently loses every reveal.
- **Both web surfaces must make zero off-origin requests.** `verify-ui.mjs`
  enforces this — it is the air-gap claim.

---

## 7. Git and GitHub

```powershell
$env:GIT_TERMINAL_PROMPT="0"
git gc -q
git push origin main
```

PowerShell surfaces git's stderr progress as an error even on success — **check
for the `main -> main` line** before concluding the push failed. Omitting
`git gc` can produce an HTTP 408 on this remote.

`gh` is a broken npm shim here and no API token is present. The repository
description and its 19 topics must be pasted via the GitHub web UI; the exact
copy is in [`SUBMISSION.md`](SUBMISSION.md).

---

## 8. Still blocked on a human — not on you

These cannot be done by an agent. If you are asked for them, say so.

1. **Demo video** (~1 min) — script is ready and rehearsed in `DEMO_60S.md`.
2. **X / LinkedIn post** with the video URL, tagging **@cognition** and **Devin**.
3. **Repo description + 19 topics** via the GitHub web UI.

Until 1 and 2 exist, the landing page's Project facts panel honestly reads
*"being recorded"* and *"to be posted"*. Replace those two lines with real
values only once they are true.

### Known, disclosed product gaps

- BSP, SEC and AMLC circulars are **not** in the corpus — those sites refuse
  this network and Wayback has no usable capture. The product names this gap on
  every relevant answer.
- RA 9160's public copy is abridged, so no reporting deadline can be quoted. A
  test asserts the absence rather than leaving it to chance.
- Qwen2.5-3B and GLiNER were never exercised; every published number was
  measured without them.