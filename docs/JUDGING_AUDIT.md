# Judging audit — Isla AI

**AppBuilders PH Hackathon 2026 · Local AI track · Finance vertical**

This is an adversarial reading of our own submission against the five published
criteria, written to be useful rather than flattering. For each criterion: the
strongest case we can make, the strongest objection a sceptical judge would
raise, and an honest verdict. Where we are exposed, it says so.

Score bands are our estimate against other submissions we would expect at this
track, not a prediction of the result.

---

## Summary

| Weight | Criterion | Verdict | Where it is strongest | Where it is weakest |
|---|---|---|---|---|
| 25% | Problem & Usefulness | **Strong, with one real exposure** | Narrow, named, regulation-backed user | "Would the general public benefit?" — they would not, and we cannot pretend otherwise |
| 25% | Local AI Implementation | **Vulnerable** | Local inference is *architecturally* necessary | Our own ablation says the local AI is roughly tied with a lexical baseline |
| 20% | Technical Execution | **Strong** | 355 Python + 108 UI tests, honest claims, bugs published | Corpus is 12 documents but BSP and SEC are unreachable; small-sample metrics |
| 15% | Innovation | **Strong** | Refusing to be wrong; correct-refusal and named coverage gaps as a feature | Verifying your own redactor is good practice, not a novel idea |
| 15% | Product & Demo Quality | **Medium-strong** | Real console, zero fake buttons | Demo video still pending — that is 15% with a hole in it |

**The single biggest risk in this submission is the Local AI criterion, and it is
not where we expected.** Section 2 below explains it in full. It is worth more
than any rebrand, and it cannot be fixed by marketing.

---

## 1. Problem & Usefulness — 25%

*Does the project solve a genuine problem? · Is the target user clear? · Is
there a realistic use case? · Would the general public actually benefit?*

**Strongest case.** The user is named to the job title: a Philippine bank's data
privacy officer. The problem is not invented — it is 2023 NPC Advisory 2024-04
plus BSP circulars, obligations that already bind every bank in the country. And
the strongest evidence is that the seven legal instruments the product cites are
the *same* seven instruments those banks are bound by. The problem statement and
the solution are drawn from one source of truth.

**Strongest objection.** The rubric's fourth bullet is *"Would the general
public actually benefit?"* and the honest answer is **no**. A data privacy
officer at a Philippine bank is a population of perhaps low hundreds. Nothing
here helps a student, a small business owner, or anyone outside a regulated
enterprise. We have optimised for depth at the cost of breadth, and the rubric
asks for breadth in this criterion specifically.

We should not dress this up. The defensible position is narrower: the rubric
lists four bullets and we answer three of them decisively and the fourth not at
all. A judge weighting that bullet heavily will mark us down, and that is a
correct mark-down.

**Where we are weak beyond the general-public question.**

- The pain is *real but slow*. A DPO meets this problem in a quarterly audit
  cycle, not in a daily fire. "Realistic use case" is a yes; "urgent" is not.
- We have **no user research**. No interview with a DPO, no observation. The
  problem is derived from regulations, and regulations describe obligations
  rather than daily behaviour. A judge who asks "how do you know they want this?"
  currently has no evidence beyond our own reading.

**Honest verdict.** Strong on three of four bullets, absent on the fourth. If the
general-public bullet is worth a third of this criterion, we score roughly two
thirds of the maximum here. That is still a good score, but it is not a
maximum, and the fix is research we no longer have time to do.

**What we can still do before submission:** put the enterprise-only scope *on
the front page* rather than hoping nobody asks. `docs/SUBMISSION.md` should say
out loud: *this is deliberately not a consumer product, and here is why the
concentrated ICP is the right call.* Owning the decision reads very differently
from being caught by it.

---

## 2. Local AI Implementation — 25% — **highest risk**

*Is local inference fundamental to the product? · Does running locally provide a
meaningful advantage? · **Would the product lose significant functionality if its
local AI component were removed?** · Does it show the advantages of privacy,
latency, offline availability, cost, or hardware utilization?*

**This is where a rigorous judge can hurt us, and the evidence is ours.**

`eval/RESULTS_ABLATION.md` measures the product with and without the local neural
retrieval leg. The result: published retrieval metrics are **unchanged**.
Paraphrase MRR 0.671 with the neural leg, 0.654 without. Level questions 0.733
with, 0.767 without — marginally *worse* with it.

That is the third bullet of the rubric, and on the narrow reading of "the neural
embedding model" the honest answer is **no, the product would not lose much**.

We have disclosed this (`docs/DISCLOSURES.md`, the README, the landing page). We
believe disclosure is strictly better than being caught by a judge who runs the
ablation. But disclosure is not the same as a good answer.

**What we should argue, and whether the argument holds.**

| Claim | Holds? |
|---|---|
| "Local inference is architecturally necessary: a cloud model cannot answer *is this sensitive personal information?* without the PII being sent first." | **Yes — this is genuinely airtight.** It is not a performance claim, it is a logical one. |
| "Local latency: 0.2 ms PII p50, 8 ms copilot p50." | **True but weak.** The judges' own rubric offers latency as one of several advantages; our numbers are good, not distinctive. |
| "Local cost: no per-call fee." | **True, and the strongest economic argument** for a high-frequency, low-value-per-call workload like a paste scan. |
| "Offline availability in air-gapped bank estates." | **True and decisive for this ICP.** |
| "Hardware utilization: local ONNX on CPU." | **True.** |
| "The neural leg carries retrieval quality." | **No. We measured it. It does not.** |

So four of five arguments hold, and the fifth is the one the rubric singles out
with bold. The honest position is that **local AI is fundamental to the
*architecture and the threat model* while being close to neutral for *measured
quality*.** That is a real and defensible thing to be, provided we say it
plainly instead of implying the neural leg is doing heavy lifting.

**The mitigating fact, stated honestly.** The reason macro-F1 is 1.0000 and
citation accuracy is 100% is that the PII engine is deterministic regex + Luhn +
normalisation, and answers are *extracted* from cited spans rather than
generated. So the local AI leg's removal costs us little on these metrics — but
the product would fail entirely if a cloud API were substituted for the local
path, because the substitution requires transmitting the regulated data. The
ablation removes the *embedding model*; it does not remove *locality*. Those are
different experiments, and conflating them would be dishonest.

**Honest verdict.** If a judge reads the rubric literally and runs the ablation,
this criterion scores below maximum. If a judge reads "is local inference
fundamental to the product" — the first and most important bullet — we score
well. Our score here is far more sensitive to judge interpretation than any
other criterion.

**What we can still do:** make sure `eval/RESULTS_ABLATION.md` is one click from
the README, so the disclosure reads as confidence rather than as an apology. And
say the distinction above — embedding model vs locality — explicitly, because
we have earned it and it is the correct framing.

---

## 3. Technical Execution — 20%

*Does the product actually work? · How well are the models integrated? · How
technically sophisticated is the implementation? · Is it reliable enough for a
live demonstration?*

**Strongest case.** 129 Python tests + 99 UI tests, all passing. `tsc --noEmit`
clean. Zero npm vulnerabilities. Every published metric regenerates from
committed datasets by running committed code, in CI, on every push. Both web
surfaces ship `default-src 'none'` and CI asserts zero external requests. The
air-gap claim is enforced by an AST scan of every runtime module, not by a
promise. The CSP inline-script hash is verified in two places that must agree,
and CI fails if either goes stale.

**This criterion is where the honesty work converts directly into points.** A
submission that publishes its own near-misses — the CLS-pooling bug that made
the dense leg *worse* than baseline, the ledger flooded with 4,300 health-check
entries a day, the false "no socket" claim — reads as engineering maturity to
any judge who knows what they are looking at. We found those bugs ourselves and
wrote them down. That is the whole argument.

**Strongest objection.** Scale and rigour of evaluation:

- The corpus is **12 documents / 348 chunks.** Eleven are Philippine legal
  instruments; the twelfth is Isla AI's own compiled front-line guide, which is
  labelled tier 3 and ranked below every statute. **BSP and SEC are absent
  entirely**: both sites refuse this network and neither has a usable Wayback
  capture, and the retrievable RA 9160 is an abridged 2001 text that omits the
  covered/suspicious transaction reporting provisions. The product names those
  gaps on every risk assessment rather than filling them. Macro-F1 1.0000 on a dataset we
  wrote ourselves looks, to a careful judge, more like a ceiling than a result.
  The PII test set is synthetic. We have not measured recall against
  independently labelled real banking data, and that is the single largest
  methodological gap in the submission.
- **GLiNER has never run.** Every published PII number was measured with it
  absent, so one of the three "neural components" is untested.
- The Qwen2.5-3B generation path is wired but **has never produced a published
  answer.** Two of our three claimed local AI components are therefore
  unexercised.

**Honest verdict.** Strong on execution quality and verification discipline.
Weak on evaluation rigour and dataset independence. A judge who values "does it
actually work" will score us high; a judge who values "is the evaluation
trustworthy at scale" will mark the synthetic dataset.

---

## 4. Innovation — 15%

*Is the solution meaningfully different? · Does the team approach the problem in
an interesting way? · Does Local AI enable something new?*

**Strongest case.** The differentiator is **refusing to be wrong**, and it is
structural rather than cosmetic:

1. **A 3-pass verification loop.** After redaction, the full detector runs again
   over the product's *own output*, and anything that survives escalates. Most
   redaction tools trust their first pass; this one audits itself.
2. **Correct-refusal as a first-class outcome**, measured at 100%, rather than a
   fallback nobody scores. The copilot refuses in Taglish when the evidence is
   thin and names what is missing.
3. **A hash-chained ledger that stores counts and verdicts but never the
   customer's text** — provable compliance evidence that is itself safe to keep.
4. **The island as an architecture.** Data is placed, not guarded. Nothing
   defends the perimeter because nothing needs to.

**Strongest objection.** Self-verification of a redactor is good practice, not a
novel idea — it is closer to defence-in-depth than to innovation. And the
innovation is *architectural* (locality, verification loop, ledger) rather than
*model-innovative*. In a Local AI track where some submissions fine-tune or
distil, we shipped an ensemble of well-understood parts and called it a product.

**Honest verdict.** Above average, not exceptional. The idea is coherent and the
execution of it is unusually disciplined, but a judge looking for a technical
novelty will not find one here, and we should not dress up "we used BM25 plus
embeddings" as research. The genuine novelty claim is narrower: **a compliance
control whose primary output is a refusal, and which audits its own output
before releasing it.**

---

## 5. Product & Demo Quality — 15%

*Is the experience understandable? · Is the UX usable? · Can the team clearly
communicate the value? · Is the live demonstration convincing?*

**Strongest case.** A chat-driven console fully wired to the live API with zero
mock data and zero non-functional buttons, deep-linkable views, persistent
navigation, an honest health chip that reflects a real socket probe, a four-
channel status system (hue, form, icon, label) enforced by a single primitive,
self-hosted fonts under `default-src 'none'`, and four surfaces verified for
console errors, overflow and external requests on every run. `preflight.py`
asserts 39 claims against a live server.

**Strongest objection — and this one is a hole, not an argument.**

- **The demo video is not recorded.** The rubric asks whether the live
  demonstration is convincing, and a submission with a pending video is carrying
  15% of the score with something missing. Nothing we write in a Markdown file
  fixes that.
- **The social/X/LinkedIn URL is pending.**
- 348 chunks is a small corpus for a live Q&A demo. A judge asking an
  out-of-scope question gets a refusal — which is the designed behaviour and is
  *presented as correct*, but a judge who does not know that is seeing a product
  that doesn't know anything.

**Honest verdict.** The strongest of our five *as software*, and the weakest as
a *submission*, purely because two artefacts are unfinished. Fixing them is
worth more than anything else left on the list, and it is the only item here
that is purely a matter of execution rather than of argument.

---

## Ranked list of what to fix, by expected score impact

1. **Record the demo video and post the social URL.** Only item that is purely
   execution, and it unblocks a whole criterion.
2. **Land the Qwen2.5-3B weights and exercise the generation path at least
   once**, even if no published metric depends on it. "The local LLM path has
   never produced an answer" is a sentence we would rather not have to write.
3. **Run GLiNER once and report what it does and does not add.** Same reason.
4. **State the embedding-model-vs-locality distinction out loud** in the README's
   "why local" section, so the ablation reads as rigour rather than as a
   weakness we were caught publishing.
5. **Say "enterprise-only, deliberately" on the front page** instead of hoping
   the general-public bullet is not read literally.
6. Everything else — colours, fonts, naming, documentation — is done and should
   not consume another minute before the deadline.

---

## Claims we are not making

Repeated from `docs/DISCLOSURES.md` because an audit that omits them is not an
audit:

- Local does **not** mean better model quality. A 3B model is a 3B model.
- No cloud AI API is installed, required or reachable at runtime.
- The product **does** open one socket: the air-gap probe's empty TCP handshake
  to fixed public resolvers, which exists so the badge can be falsified.
- Correctness comes from **retrieval and verification, not scale**. The worst
  case is a wrong chunk rather than an invented statute.
- **First build requires internet** for model weights and the corpus. Runtime
  requires nothing.
- Built with AI-assisted development tooling, disclosed per the rules.
