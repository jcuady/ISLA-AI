# Isla AI threat model

## Scope and assumptions

**Isla AI protects:** regulated Philippine personal data while it is being inspected, redacted, and
answered about — inside a bank's own network.

**Isla AI does NOT protect against:** physical access to the host, a compromised host OS, or an operator
who deliberately exfiltrates data. Those are baseline infrastructure concerns, not product features.
Encryption at rest is delegated to the platform (BitLocker on Windows, LUKS/dm-crypt on Linux) and the
operator owns the key.

### Trust boundaries

```
┌─ UNTRUSTED ──────────────────────────────────────────────────┐
│  Text pasted by a staff member (may contain live PII)        │
└───────────────────────────┬───────────────────────────────────┘
                            │ enters loopback only
┌─ SEMI-TRUSTED ────────────▼───────────────────────────────────┐
│  Browser (127.0.0.1:8765)  ← same machine, same operator     │
└───────────────────────────┬───────────────────────────────────┘
                            │
┌─ TRUSTED CORE ────────────▼───────────────────────────────────┐
│  FastAPI process · PII engine · retrieval · ledger            │
│  No data leaves; no cloud call on the request path                │
└──────────────────────────────────────────────────────────────┘
```

---

## Threats addressed

### T1 — Shadow-AI exfiltration

**Threat.** A staff member pastes a customer record into ChatGPT/Copilot/Gemini. The regulated data
leaves the organisation before anyone reviews it.

**Mitigation.** The Egress Guard detects and redacts before release, and the **verification pass**
re-runs the full detector over the *redacted output* — a redactor you have not verified is a
liability, and this pass is what allows the "0.00% residual leakage" claim to rest on measurement
rather than hope. Measured at **0.00%** over the 40-case published dataset.

**Residual risk.** A novel identifier format absent from the recogniser set could evade Stage 1. This
is why GLiNER context is a second, independent opinion and why the verdict escalates to
`BLOCK_ESCALATE` rather than silently releasing when anything is uncertain.

### T2 — Fabricated compliance advice

**Threat.** A hallucinated circular number or penalty. In a regulated context this is not a
nuisance; it is a misstatement to a regulator.

**Mitigation.** Three independent controls:

1. **Extractive-first generation** — answers quote retrieved spans verbatim; the model paraphrases
   within a chunk's scope rather than composing freely.
2. **Citation enforcement at the generation layer** — a legal claim with no resolvable chunk citation
   is suppressed *before it reaches the user*. Output with no `[DOC section]` tag is rejected.
3. **Refusal on thin evidence** — below the retrieval threshold Isla AI refuses in Taglish and reports
   what it did and did not find. Measured correct-refusal behaviour is in `eval/RESULTS.md`.

**Residual risk.** A cited span can still be *quoted* in a misleading way by an LLM. The verification
is that the span really is in the corpus; the interpretation remains the officer's to check.

### T3 — Audit trail that itself leaks

**Threat.** An audit log containing customer records becomes a second breach — and an examiner
requesting evidence would itself expose PII.

**Mitigation.** The ledger stores **hashes and metadata only**: entity counts, verdict, latency,
SHA-256 prefixes of input and output. Never the text. Entries are SHA-256 hash-chained, so altering
any historical record invalidates every subsequent hash and is detectable by one pass.

This is the artefact a bank can hand an NPC or BSP examiner **without disclosing a single customer
record** — a genuinely novel compliance property.

### T4 — Model tampering

**Threat.** A swapped or corrupted weight file.

**Mitigation.** `models/download_models.py` records SHA-256 per asset. Model files should be
re-verified before load in a production deployment (see roadmap). The manifest is version-controlled.

### T5 — Non-loopback exposure

**Threat.** Serving regulated inference on a routable interface.

**Mitigation.** `assert_loopback()` raises at import time; the process cannot start on `0.0.0.0`.

---

## Pseudonymisation keys

Redaction tokens are **irreversible HMAC-SHA256 pseudonyms**:

```
[PHONE-9C1E]  =  "[PHONE-" + HMAC-SHA256(key, original)[:4].upper() + "]"
```

- The same input always yields the same token, so **joins survive** — you can still correlate the same
  customer across records without revealing who they are.
- The key never leaves the client and is never transmitted.
- **The 4-hex-character digest is a truncation and is therefore not collision-resistant at scale.**
  That is a deliberate demo-grade trade-off; production should use a longer suffix. Documented here
  rather than hidden.

### Key handling

`ISLA_PSEUDONYM_KEY` supplies the key. **If unset, the code falls back to a deterministic per-machine
seed** so demo output is reproducible.

> **Production requirement:** the fallback must not be used on live customer data. Set
> `ISLA_PSEUDONYM_KEY` to a high-entropy secret held in the OS keystore, and rotate it on a defined
> schedule. Rotation breaks joins across the boundary — plan for that.

---

## Threats explicitly NOT addressed

| Threat | Why not | What the operator must do |
|---|---|---|
| Physical access / memory scraping | Out of scope for an app | Full-disk encryption, locked-down endpoint |
| Compromised host OS / malware | Out of scope | Standard endpoint hardening |
| Malicious insider with Isla AI access | Cannot be solved in software | OS-level access control, audit review |
| Breach of the corpus index at rest | Delegated to the platform | BitLocker / LUKS with operator-held key |
| A novel PII format nobody has seen yet | Fundamentally open | Treat verdicts as advisory; human review |

---

## Design principle

**Fail closed.** When the system is uncertain — residual detection after redaction, retrieval below
threshold, a model that fails to load — it says so and refuses, rather than degrading silently into
a confident-looking wrong answer. For a compliance tool, a wrong answer is worse than no answer.