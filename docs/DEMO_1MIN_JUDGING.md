# Isla AI — 60-second demo, mapped to the judging criteria

**Read this on stage instead of [`DEMO_60S.md`](DEMO_SCRIPT.md).** That file is
the long version; this one is what you actually say, ordered so every weighted
criterion gets its moment before the clock runs out.

**Three clicks. Zero typing. 171 spoken words** (counted, not estimated). At
a confident 170 wpm that is exactly 60 seconds; at a calmer 150 it runs about
68 — which is what the marked cut in the Fraud beat is for. Memorise the
sentences, not the timings.

---

## Which beat earns which criterion

| Criterion | Weight | Beat | The line that scores it |
|---|---|---|---|
| **Problem & Usefulness** | 25% | Hook | "pasting customer data into ChatGPT — exactly what's barred" |
| **Local AI Implementation** | 25% | Egress | "checking if data is sensitive means sending it" |
| **Technical Execution** | 20% | Egress | "runs its own detector over its own output" |
| **Innovation** | 15% | Gap panel | "names the gap instead of inventing a circular" |
| **Product & Demo Quality** | 15% | Copilot | "Every answer is a retrieved span, never written from memory" |

The two 25% criteria are front-loaded on purpose. If you only get two things
across, they are the problem and the reason local is not a preference.

---

## Setup — before you present

```powershell
.venv\Scripts\python.exe scripts\preflight.py
```

Do not start until it prints `PRE-FLIGHT PASSED — 49/49 checks.`

Three tabs, already loaded, zoom 110%, every other window closed:

| Tab | URL | Leave it on |
|---|---|---|
| 1 | `http://127.0.0.1:8765/app?view=egress` | untouched |
| 2 | `http://127.0.0.1:8765/app?view=risk` | untouched |
| 3 | `http://127.0.0.1:8765/app?view=copilot` | untouched |

---

## [0:00–0:09] HOOK — Tab 1, do not touch the mouse

> "Philippine bank staff need the privacy rule in seconds. Their only fast
> option today is pasting customer data into ChatGPT — exactly what's barred.
> Isla AI answers on the bank's own hardware."

**Problem & Usefulness.** *Target user, realistic case, and the public benefit
all land in three sentences.* Do not scroll, do not click. Let it sit.

---

## [0:09–0:28] EGRESS GUARD — one click

**Click: `Scan & redact`.**

> "Ten pieces of personal data. Isla AI replaces every one, then runs its own
> detector over its own output. Card, CVV and account together — it refuses to
> send. Block, not a warning."
>
> "A cloud tool can't do that last step. Checking if data is sensitive means
> sending it."

**Local AI Implementation + Technical Execution.** The second sentence is the
whole 25% criterion. It is not a speed claim and not a privacy claim — it is a
logical one: you cannot test whether data is sensitive without first
transmitting it, and transmitting it is the act being prevented.

**Point at the four metrics: 10 entities · 2 passes · 0.00% residual ·
single-digit ms.** Read them off the screen. Never recite a latency number
from memory.

---

## [0:28–0:45] FRAUD & AML — Tab 2, the beat that wins it

**Click the chip reading `"A caller claiming to be from the bank asked th…"`**
(it is truncated on screen), then click **`Screen scenario`**.

> "A caller asked the customer to read their CVV. Critical — and it names who's
> exposed: bank and customer."
>
> "And here's what most compliance AI hides: BSP and SEC aren't in our corpus,
> so it names the gap instead of inventing a circular."
>
> "Visibly incomplete is worth something. Confidently wrong is worse than
> nothing."

**Innovation.** Scroll down to the **"Not covered by this build"** panel before
the second line. Pause one beat after the last sentence.

**If you are running late, cut this** → the three lines above.

---

## [0:45–0:55] COPILOT — Tab 3

**Click: `Breach reporting clock`.**

> "Same question in Taglish. Seventy-two hours — quoted from the NPC's
> circular, section attached. Every answer is a retrieved span, never written
> from memory."

**Product & Demo Quality.** Point at the citation chip.

---

## [0:55–1:00] CLOSE

> "Redaction, fraud screening, cited answers, tamper-evident proof. One
> machine, no cloud. Everything regenerates from the repo."

**Stop talking. Do not fill the silence.** Silence reads as confidence.

---

## What to type — nothing, unless something breaks

Both screens arrive pre-filled. This is only for recovery.

**Egress Guard** is preloaded with a collections email holding an SSS, a TIN,
two mobile numbers, a full card number, a CVV, a bank account, a salary figure
and a remittance reference. If the box is ever empty, **click `Collections
email`** — it loads and scans in one click. That is the recovery move; it never
needs typing.

**Copilot** chips, left to right:

| Chip | Exact question it sends |
|---|---|
| **Breach reporting clock** ← demo this | `Ilang oras dapat ko i-report ang data breach?` |
| Outsourcing to a vendor | `Pwede ba ipasa ang CDR ng customer ko sa vendor namin sa Singapore?` |
| Rules for automated decisions | `Can our call center use AI to score our agents?` |

If every chip is unavailable, type that first question — it is the same one.

---

## If a judge asks, answer in one sentence

**"Why does it have to run locally?"** → To test whether data is sensitive you
first have to see it, and sending it is the exact act we're preventing.

**"What does the local model actually do?"** → Retrieval embeddings, on-device.
The LLM is optional and off — every number we publish was measured without it.

**"How good is it?"** → PII detection 1.0000 macro-F1, 0.00% residual
leakage, citations 100%, fraud recall 94.4%. On small labelled sets we wrote
ourselves — that's the honest limit.

**"What can't it do?"** → BSP and SEC circulars, and AMLC deadlines — those
sites refuse this machine, and RA 9160's public copy is abridged. It names each
gap on every relevant answer.

**"Will it replace our cloud AI?"** → No. Cloud AI is banned for this data.
This is what you're allowed to use.

---

## Do not say

- ❌ "100% accurate." → "1.0000 macro-F1 on our labelled set."
- ❌ "No network calls at all." → Our own air-gap probe deliberately opens one.
  Say that first if asked.
- ❌ "It knows Philippine banking law." → Eleven instruments. BSP and SEC are
  absent and it says so.
- ❌ Anything about certifications. Nothing here has been audited against
  anything.

---

## Rehearsal

Run `node apps\web\rehearse-60s.mjs` — 27 checks, machine-verified against the
running product, including every string quoted above.

Then rehearse **three times by hand, timed, with the mouse.** If you cannot do
it in 60 seconds one-handed, cut the Fraud & AML beat — the other three still
tell the whole story.