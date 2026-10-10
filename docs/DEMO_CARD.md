# THE CARD — Isla AI 60-second demo

> **Print this one page. It is the whole demo.**
>
> ### You type NOTHING. Three clicks. That is the trick.

---

## 1 · Before you start (do this 5 minutes before)

```powershell
.venv\Scripts\python.exe scripts\preflight.py
```

Wait for: **`PRE-FLIGHT PASSED — 49/49 checks.`**

Open these three tabs, leave them alone, zoom 110%, close everything else:

| Tab | Address |
|---|---|
| 1 | `http://127.0.0.1:8765/app?view=egress` |
| 2 | `http://127.0.0.1:8765/app?view=risk` |
| 3 | `http://127.0.0.1:8765/app?view=copilot` |

---

## 2 · The 60 seconds — what to say

### [0:00] Tab 1. Say, don't click yet:

> "Philippine bank staff need the privacy rule in seconds. Their only fast
> option today is pasting customer data into ChatGPT — exactly what's barred.
> Isla AI answers on the bank's own hardware."

### [0:09] Click **Scan & redact**. Say:

> "Ten pieces of personal data. Isla AI replaces every one, then runs its own
> detector over its own output. Card, CVV and account together — it refuses to
> send. Block, not a warning."
>
> "A cloud tool can't do that last step. Checking if data is sensitive means
> sending it."

*Point at the metrics:* **10 entities · 2 passes · 0.00% · single-digit ms**

### [0:28] Tab 2. Click **"A caller claiming to be from the bank asked th…"**,
then click **Screen scenario**. Say:

> "A caller asked the customer to read their CVV. Critical — and it names who's
> exposed: bank and customer."
>
> "And here's what most compliance AI hides: BSP and SEC aren't in our corpus,
> so it names the gap instead of inventing a circular."
>
> "Visibly incomplete is worth something. Confidently wrong is worse than
> nothing."

*Scroll down to the **"Not covered by this build"** panel.*

**⏱ Running late? Cut this whole beat.** The other two still tell the story.

### [0:45] Tab 3. Click **Breach reporting clock**. Say:

> "Same question in Taglish. Seventy-two hours — quoted from the NPC's
> circular, section attached. Every answer is a retrieved span, never written
> from memory."

### [0:55] Stop talking.

> "Redaction, fraud screening, cited answers, tamper-evident proof. One
> machine, no cloud. Everything regenerates from the repo."

**Then say nothing. Silence reads as confidence.**

---

## 3 · EGRESS GUARD — what to do

**Normally:** click **`Scan & redact`**. Nothing else.

**If the box is empty** (tab lost its state) → click the **`Collections email`**
button. One click, loads and scans instantly. **Never type.**

### If you genuinely must type this

Paste or type exactly this — it was tested and produces the **identical**
result: 10 entities, 2 passes, 0.00% residual, `BLOCK & ESCALATE`.

```
From: collections@usapalmabank.com.ph
SSS 12-345-6789, TIN 456-789-012. Mobile 0917 123 4567, GCash +639171234568.
Card 4539578763621486, CVV 123. Account 0056-12345678. Salary PHP 42,500.
Remittance via Cebuana Lhuillier ref #CEB-88213-4455.
```

> ⚠️ **Leave out either the email or the remittance reference and you drop to
> 8 entities / 1 pass.** Then say *"eight pieces of personal data"* and do
> **not** say "two passes". The script line is written for ten.

---

## 4 · DPA COPILOT — what to do

**Normally:** click the chip **`Breach reporting clock`**. Nothing else.

If you must type, this is the exact question that chip sends:

```
Ilang oras dapat ko i-report ang data breach?
```

The other two chips, if you need them:

| Chip | Question it sends |
|---|---|
| Outsourcing to a vendor | `Pwede ba ipasa ang CDR ng customer ko sa vendor namin sa Singapore?` |
| Rules for automated decisions | `Can our call center use AI to score our agents?` |

**Expected answer: 72 hours**, cited to `NPC-CIRC-16-03 Section 23`.

---

## 5 · FRAUD & AML — what to do

Click the middle chip (**"A caller claiming to be from the bank asked th…"**)
→ click **`Screen scenario`**.

The chips are truncated on screen. That is normal. The middle one is the CVV
scenario.

---

## 6 · If something breaks

| What you see | Do this | Never do this |
|---|---|---|
| Egress box empty | Click **`Collections email`** | Don't retype the long email |
| No verdict appeared | Wait 1 s, then click **Scan & redact** | Don't click twice |
| Copilot looks empty | Click **`Breach reporting clock`** | Don't debug on stage |
| Anything else | Go to Tab 3, finish the close | Don't narrate the problem |

**If you cannot recover in 5 seconds, jump to Tab 3 and close.** The 72-hour
answer is the most reliable thing you own.

---

## 7 · Numbers — say these, nothing else

| ✅ Say | ❌ Never say |
|---|---|
| "1.0000 macro-F1 on our labelled set" | "100% accurate" |
| "94.4% fraud indicator recall" | "catches every scam" |
| "Eleven Philippine instruments" | "it knows Philippine banking law" |
| "BSP and SEC aren't in our corpus" | silence about the gap |
| "The LLM is optional and was off" | "the AI wrote this answer" |

**Every answer is a retrieved span** — never "written from memory". That is the
whole product.

---

## 8 · The one thing to remember if everything goes wrong

> **"The code is in the repo — every number in it regenerates on CI."**