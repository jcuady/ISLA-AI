# KALIX — 5-minute demo script

**Total: 5 minutes.** The demo must end with the network unplugged and every claim verified on
screen. Rehearse three times; time each run.

**Before you start (10 minutes prior):**

- [ ] Run the pre-flight self-check. It asserts every claim the demo makes — corpus loaded, dense
      retrieval up, redaction verified clean, the 72-hour answer citable, out-of-domain refusal
      working, ledger chain intact, 66 tests green. **Do not present until it prints
      `PRE-FLIGHT PASSED`.**

  ```powershell
  .venv\Scripts\python.exe scripts\preflight.py
  ```

- [ ] Models downloaded, corpus built, UI built, KALIX running.
- [ ] Close Chrome, Cursor, and other IDEs — this laptop has 15.2 GB RAM and every free megabyte
      matters during a live demo.
- [ ] Open <http://127.0.0.1:8765> — this now serves the **landing page**. The console is at
      <http://127.0.0.1:8765/app>. Open both in tabs so neither click is live.
- [ ] Terminal open with `eval/RESULTS.md` ready as a backup tab.

---

## [0:00–0:30] THE AIR-GAP OPEN

**Do:** Land on the landing page. Scroll once, slowly. Then point at the network chip in the
console header.

> "Everything you're about to see runs with no internet at all — because in banking, it has to."

**Do (optional, 10 seconds):** open devtools on the landing page and show the Network tab is empty.

> "There's no CDN, no webfont, no analytics on this page. Its Content-Security-Policy is
> `default-src 'none'` — the browser is *forbidden* from fetching anything off-origin. So when I
> tell you this is air-gapped, that's enforced by the page, not promised by me."

**Do:** Disable Wi-Fi (or pull the cable). Wait up to 20 seconds.

**Expected:** the chip flips from `NETWORK: CONNECTED` to `NETWORK: AIR-GAPPED` (green).

> "That chip is not a label I typed. It's an actual socket probe — it just tried to reach the
> internet and reported what it found. Pull the cable and the answer changes."

**If a judge wants proof:** open the terminal.

```powershell
Invoke-RestMethod http://127.0.0.1:8765/api/airgap | ConvertTo-Json -Depth 4
```

> "And it still works. Nothing you will see needs a network."

**Then:** click **Open the console** to reach `/app`.

---

## [0:30–1:15] THE PROBLEM

**Do:** Egress Guard tab. The sample bank email is already loaded.

> "This is an ordinary collections email from a Philippine bank. It contains an SSS, a TIN, a mobile
> number, a GCash number, a live card PAN, its CVV, a bank account number, a salary, and a remittance
> reference. Nine regulated identifiers — in thirty-one words."

> "Today, an employee pastes something like this into ChatGPT to summarise it. And we all know what
> happens next."

**Do:** Show the screen briefly, then move on. Don't linger on the problem.

> "IBM's 2025 breach report: twenty percent of organisations were breached through security incidents
> involving shadow AI. That adds two hundred thousand US dollars to the average breach. ASEAN is now
> at three point six seven million. And BSP Memorandum M-2024-019 says, in writing, to every
> supervised financial institution: handle PII properly."

---

## [1:15–2:00] THE FIX

**Do:** Click **Scan & redact**.

**Expected on screen:** entities highlighted, then the redacted pane, then a red verdict:

```
BLOCK & ESCALATE
0.00% residual leakage · verification CLEAN · ~5 ms
```

> "Ten entities, detected in milliseconds, entirely on this machine. Card PAN plus CVV plus an account
> identifier together — that's a complete payment credential bundle, so KALIX blocks rather than
> redacts and releases."

> "Notice the SSS — twelve-dash-three-four-five-dash-six-seven-eight-nine. That's a two-three-four
> layout, not the canonical three-two-four. And the GCash number is just a mobile number with no
> marker at all. Generic PII models miss both. That's the part we had to build for the Philippines
> specifically."

**Do — the crucial beat:** point at `0.00% residual`.

> "A redactor you haven't verified is a liability. So after redaction, KALIX re-runs the entire
> detector over its own output. If anything still trips, it escalates instead of releasing. That
> number is measured, not claimed — the evaluation is in the repo and anyone can re-run it."

---

## [2:00–3:00] THE LAW, OFFLINE

**Do:** Copilot tab. Click the pre-loaded question:
**"Ilang oras dapat ko i-report ang data breach?"**

**Expected:** a cited answer naming **72 hours**, sourced to NPC Circular 16-03.

> "Seventy-two hours. From NPC Circular sixteen-oh-three. And every claim carries its section, because
> a compliance officer has to be able to defend that answer to an examiner — an uncited answer is
> worse than no answer."

**Do:** Click **"Pwede ba ipasa ang CDR ng customer ko sa vendor namin sa Singapore?"**

> "Now in Taglish. Can we send the customer's CDR to our vendor in Singapore? This is the question
> most compliance officers cannot answer in under an hour. Ours answers in under a second — offline —
> from the statute, with citations."

**Do — the differentiator:** click **"Who won the 2025 FIFA World Cup?"**

**Expected:** a Taglish refusal.

> "Ask it something outside the corpus and it refuses. Correct refusal is a feature — it's the
> behaviour that stops a model inventing a circular number. In this industry a confident wrong answer
> is worse than no answer."

---

## [3:00–3:45] THE ARTEFACT THEY'LL PAY FOR

**Do:** Audit Ledger tab.

> "Every one of those actions wrote a hash-chained record. SHA-256, each entry linked to the last.
> Alter one entry and the whole chain after it breaks — anyone can verify it in one pass."

**Do:** Point at `RAW PII STORED: NONE`.

> "And here's the part a bank actually cares about. The ledger stores hashes and metadata — entity
> counts, verdicts, latency. Never the customer text. So when the NPC or BSP asks what your
> controls did on the fifteenth of March, you hand them cryptographic proof — without disclosing a
> single customer record. That property doesn't exist in a cloud tool. In a cloud tool, answering
> that question *is* the breach."

---

## [3:45–4:30] THE NUMBERS

**Do:** Open `eval/RESULTS.md` in the prepared tab.

> "The rubric asks whether it actually works. Here's the scoreboard, generated by running the code —
> anyone can reproduce it with one command."

> "Macro F1 of one point oh on a forty-case Philippine set. High-risk recall and precision at one
> point oh. Residual leakage zero. Zero negatives mis-redacted — which matters more than it sounds,
> because a redactor that mangles every invoice number is unusable."

**Be honest if a number is missed.** Say so plainly. It is worth more than a fabricated score.

### The weakest number, volunteered before they ask

Source attribution reads **80.00%** — four of five questions cite the right instrument, one does
not. Offer it yourself:

> "The weakest number on that board is source attribution, at four out of five. The one that fails
> asks whether a bank has to register an AI credit scoring model. We get it right to cite a real
> section — we never invent one — but we attribute it to the wrong instrument. The reason is
> boring and honest: the phrase 'credit scoring' appears nowhere in the seven legal documents we
> bundle, so the retrieval has nothing to match on. That's a corpus gap. We could have tuned the
> ranker until that one case went green, and then the other four numbers would mean nothing."

If pressed on how 80% was reached: `docs/DISCLOSURES.md` §7 lists every change, including that the
denominator grew from four to five.

---

## [4:30–5:00] THE CLOSE

> "Every Philippine bank is already an AI company under NPC Advisory 2024-04 — credit scoring, KYC,
> collections. Almost none can prove compliance for their own AI.
>
> We built the copilot that can. And it never leaves your building — not by policy, not by promise,
> but because it legally cannot. The data stays inside the shield, because the shield *is* the
> control.
>
> KALIX. Walang datos na lumalabas."

---

## Backup plan

| If this happens | Do this |
|---|---|
| Model didn't load | **Do not panic.** The copilot answers extractively from cited spans. Say: "This is actually the safer mode — every word is quoted from the corpus, so nothing can be invented." |
| Server crashed | `scripts\bootstrap.ps1` then relaunch. Keep the terminal visible. |
| Network badge shows CONNECTED | Say so honestly and explain the probe is real. Then pull the cable live. |
| Anything is slow | Pre-load every tab and sample before you start. Never type live. |
| Total failure | Play the recorded offline video. It exists for this reason. |

## The four questions you will be asked

**"Isn't this what OneTrust does?"**
They do governance *workflow*. They don't run inference — and their cloud AI offerings require
sending you the very data being governed. We produce the same artefacts locally. We compete on the
artefact being produced on your hardware, not on the workflow.

**"Why not just use the OpenAI API?"**
Three reasons. First, it's circular — to classify PII with a cloud model you must first transmit the
PII, which *is* the breach. Second, our users run air-gapped core-banking and ISO 27001-sealed
environments with two-hour incident windows where a network call is unavailable by policy. Third,
per-token economics: scanning every paste across a bank at volume is not affordable via API.

**"Is a 3B model good enough for legal reasoning?"**
Legal correctness comes from retrieval, not model scale — we constrain answers to cited spans. Where
scale matters we offer a 7B and 14B tier on hardware the bank already owns. I'd rather show you
Recall@5 and citation accuracy than argue about parameter counts.

**"How do we know it actually works?"**
`python eval/run_eval.py`. Forty labelled Philippine cases, a published dataset, every number
generated by running the code. And the offline-parity check: identical output with the cable out.