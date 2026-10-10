# Isla AI — 60-second demo script

**Total: 60 seconds.** This is a cut-down of [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md), not a
second version of it. The five-minute script spends 30 seconds on the air-gap unplug and
another 30 on the problem statement. In 60 seconds both are dead weight: the unplug is the
single riskiest thing you could do in front of a judge (Wi-Fi toggles are slow and fail),
and the problem is one sentence you can say while you are already moving.

**What was cut and why:**

| Cut | Why |
|---|---|
| Unplug the network live | 10–20s of waiting, and it fails on machines you do not control. The socket probe is still real — show it if asked. |
| Landing page scroll | Nothing in 60s is worth more than the beats below. |
| Ledger walkthrough | Answer it verbally in 8 seconds if asked. |
| Typing anything | **Never type in a demo.** Every input is pre-filled below. |

**Rule for the whole minute: the demo is three clicks. Everything else is you talking.**

---

## Before you present (run this now)

```powershell
.venv\Scripts\python.exe scripts\preflight.py
```

Do not present until it prints `PRE-FLIGHT PASSED — 49/49 checks.`

Then set up **three browser tabs, in this order**, so no click is ever live:

| Tab | URL | State to leave it in |
|---|---|---|
| 1 | <http://127.0.0.1:8765/app?view=egress> | Untouched — the high-risk sample loads itself on mount |
| 2 | <http://127.0.0.1:8765/app?view=risk> | Untouched |
| 3 | <http://127.0.0.1:8765/app?view=copilot> | Untouched — three suggestion chips are visible |

Zoom to 110%. Close every other window. Terminal open in the background, not foreground.

---

## The exact text — DPA Copilot and Egress Guard

**You do not type anything during the demo.** Both screens arrive pre-filled, and this section is
here so that if a tab is ever empty you know precisely what to restore. Every string below is
copied from the running product, not written from memory.

### Egress Guard — what is already in the box

Loaded automatically on mount. Do not retype it. This is the exact text:

```
From: Collections Team <collections@usapalmabank.com.ph>
Subject: Urgent - overdue notice for DELOS SANTOS, Maria Concepcion

Magandang araw po,

Nag-apply po ng overdue notice si Maria Concepcion de los Santos.
SSS 12-345-6789, TIN 456-789-012.
Registered mobile 0917 123 4567, GCash number +639171234568.
Credit card ending 4539578763621486, CVV 123, exp 09/28.
Account number: 0056-12345678. Monthly salary PHP 42,500.
Remittance via Cebuana Lhuillier ref #CEB-88213-4455.

Pakisuri na po bago mag-escalate. Salamat!
```

Three one-click alternatives sit underneath it, in this order. Each loads **and scans
immediately**, so a single click is enough:

| Button | Loads | Verdict it lands on |
|---|---|---|
| **Collections email** | the text above | `BLOCK & ESCALATE` |
| **Payment note** | `Magbayad si Maria ng PHP 42,500 sa account 0056-12345678 sangguniang 2024-03-15. Reference INV-2024-00123456, batch 20240315.` | `REDACT, THEN SEND` — one account number replaced |
| **Operations text** | `Please process invoice INV-2024-00123456 for batch 20240315. Kindly confirm receipt within five business days.` | `SAFE TO SEND` — no regulated PII at all |

If the textarea is empty on stage, click **Collections email**. That is the recovery move — one
click, no typing, and it restores the exact state the script describes.

### DPA Copilot — what each chip asks

Three suggestion chips, left to right. Each fills the composer with the exact question below and
sends it. **Chip 1 is the one to demo**; chips 2 and 3 are backups.

| Chip (as written on screen) | Exact question it sends |
|---|---|
| **Breach reporting clock** | `Ilang oras dapat ko i-report ang data breach?` |
| **Outsourcing to a vendor** | `Pwede ba ipasa ang CDR ng customer ko sa vendor namin sa Singapore?` |
| **Rules for automated decisions** | `Can our call center use AI to score our agents?` |

If every chip is somehow unavailable, type this — it is the same question chip 1 sends:

```
Ilang oras dapat ko i-report ang data breach?
```

The answer is **72 hours**, cited to `NPC-CIRC-16-03 Section 23` and `IRR-RA10173 Section 41`.

---

## [0:00–0:06] THE HOOK — do not touch the mouse

Start on Tab 1, already on screen.

> "Philippine banks are already barred from sending customer data to a cloud AI vendor. This
> is the copilot they can still use — and it runs on this laptop, not in a data centre."

**Six seconds. Do not scroll, do not click. Let the sentence land.**

---

## [0:06–0:20] EGRESS GUARD — one click

**Do:** click **Scan & redact**.

> "A collections officer is about to paste this into ChatGPT. Isla AI finds ten things in it: the
> sender's email, an SSS number, a TIN, two mobile numbers, a full card number, a CVV, a bank
> account, a salary figure and a remittance reference. It replaces every one with a keyed
> pseudonym, and then runs its own detector over its own output."

**Read the four metrics off the screen — 10 entities, 2 passes, 0.00% residual, single-digit
milliseconds. Do not recite them from memory: latency varies per run, and contradicting your own
screen on stage costs you the credibility the number was there to buy.**

> "It didn't just redact. Card number, CVV and account number in the same message is a complete
> payment-credential compromise, so it refuses to send. Not a warning — a block."

**This is a real distinction and worth saying slowly:** a tool that only redacts would have
let this through.

---

## [0:20–0:42] FRAUD & AML — the beat that wins it

**Do:** switch to Tab 2. Click the chip reading **"A caller claiming to be from the bank asked
th…"** (the chips are truncated on screen; it is the middle one), then click **Screen
scenario**.

**Wait for the verdict. It takes under 10 ms — the wait is the UI updating, not the engine.**

> "A call centre agent asked a customer to read their CVV out loud. The answer comes back
> **CRITICAL**, and it names who's exposed — the bank *and* the customer."

**Move the cursor to the evidence quote.**

> "It quotes the exact words that triggered it, and it tells the officer what to do: decline,
> and escalate today, because that credential is now burned."

**Now scroll down to the "Not covered by this build" panel. This is the whole pitch.**

> "And here is what most compliance AI would hide. BSP, SEC, AMLC and PCI DSS aren't in our
> corpus — this machine can't reach those sites. So it names the gap instead of inventing a
> circular number. A copilot that's visibly incomplete is worth something. One that's
> confidently wrong is worse than no copilot at all."

**Pause for exactly one beat after that last sentence. Then stop.**

---

## [0:42–0:55] THE COPILOT — proves it is a tool, not a stunt

**Do:** switch to Tab 3. Click the chip **"Breach reporting clock"**. It sends
`Ilang oras dapat ko i-report ang data breach?` — Taglish, the way a branch actually asks.

> "Same question in Taglish, the way a branch actually asks it. Seventy-two hours — quoted
> from the NPC's own circular, with the section attached."

**Point at the citation chip.**

> "Every answer is a verbatim span from a retrieved section. It never writes a legal claim
> from memory."

---

## [0:55–1:00] THE CLOSE

> "Redaction, fraud screening, cited answers and tamper-evident proof — one machine, no cloud.
> Everything you've seen is reproducible from the repo. Thank you."

**Stop talking. Do not add a sentence. Do not fill silence.**

---

## If something breaks

The single most common failure is a tab that lost its pre-filled state. Recover by name, do
not debug.

| Symptom | Say | Do |
|---|---|---|
| Input box is empty | "Here's the one we always use." | Click any sample chip |
| Verdict never appears | "Let me show you the one I'm confident in." | Switch to Tab 3, click a chip |
| Tab 2 is slow | "The engine is under ten milliseconds; that's the UI." | Move to the copilot beat early |
| Anything else | **"The code is in the repo — every number in it regenerates on CI."** | Switch to Tab 3 and finish |

**Never debug on stage.** If you cannot recover in 5 seconds, jump to the copilot beat and
close. The 72-hour answer is the most reliable thing you own.

---

## If a judge asks

**"Does it need the internet?"** No. Everything you saw ran on this machine. The one outbound
packet is our own air-gap probe opening an empty TCP handshake so the badge can be falsified
live — I can show you it.

**"How good is it really?"** Don't oversell. PII detection is 1.0000 macro-F1 with 0.00%
residual leakage, citation accuracy 100%, fraud indicator recall 94.4% at 100% tier accuracy.
Those are on small labelled sets we wrote ourselves — that's the honest limit.

**"Is the local AI doing the work?"** The honest answer, and give it unprompted: retrieval
quality is roughly tied with a lexical baseline — we measured it and published it. What local
inference buys is that the product can exist at all, because a cloud model can't answer *"is
this sensitive personal information?"* without first being sent the information.

**"What can't it do?"** BSP and SEC circulars, and AMLC reporting deadlines — those sites
refuse this machine, and RA 9160's public copy is abridged. It names each of those gaps on
every relevant answer.

---

## Do not say

- ❌ "100% accurate." → Say "1.0000 macro-F1 on our labelled set."
- ❌ "It replaces your cloud AI." → Say "It's what you can still use."
- ❌ "No network calls at all." → The air-gap probe deliberately opens one. Say so first.
- ❌ "It knows Philippine banking law." → It knows 11 instruments. BSP and SEC are absent and it says so.
- ❌ "It's HIPAA-grade." → Nothing has been audited against anything. Never claim certification.

---

## Rehearsal

Run it three times, timed, **with the mouse**. If you cannot do it in 60 seconds with one
hand on the mouse, cut the Egress Guard beat (Section 2) — the remaining two beats still
tell the whole story.