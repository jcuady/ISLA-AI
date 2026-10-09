# Isla AI corpus sources

Every document in the corpus is a **public government publication**. Nothing is proprietary and
nothing required clearance. This file records exactly what was fetched, from where, and how its
authenticity was verified.

---

## Documents (7 required, all verified)

| Document | Issuer | Type | Chunks | Fetched via |
|---|---|---|---|---|
| **RA 10173** — Data Privacy Act of 2012 | Congress | statute | 44 | `lawphil.net` (direct) |
| **IRR of RA 10173** (as amended) | National Privacy Commission | irr | 80 | `privacy.gov.ph` PDF (direct) |
| **NPC Advisory No. 2024-04** — Guidelines on AI and Sensitive Personal Data | NPC | advisory | 8 | Wayback mirror |
| **NPC Circular No. 16-03** — Personal Data Breach Management | NPC | circular | 29 | `privacy.gov.ph` PDF |
| **NPC Circular No. 2022-04** — DPS Registration / DPO / ADS | NPC | circular | 38 | `privacy.gov.ph` PDF |
| **NPC Circular No. 2022-01** — Guidelines on Administrative Fines | NPC | circular | 11 | `privacy.gov.ph` PDF |
| **NPC Circular No. 2023-04** — Guidelines on Consent | NPC | circular | 28 | `privacy.gov.ph` PDF |

**Total: 223 citable chunks, ~283,500 characters of real legal text.**

Per-document provenance, SHA-256, and fetch status are recorded in
[`corpus/raw/fetch_manifest.json`](../corpus/raw/fetch_manifest.json).

---

## Mirror problem and how it was solved

`privacy.gov.ph` and `bsp.gov.ph` both return **HTTP 403** from many networks (verified during
development, with and without a browser User-Agent). The corpus fetcher therefore tries a mirror
chain:

1. **origin** — the canonical URL
2. **wayback** — `https://web.archive.org/web/2024id_/<url>` (raw, un-rewritten snapshot)
3. **lawphil** — public statute mirror

### Content validation (this mattered)

An early fetch appeared to succeed — 7/7 documents, no errors — but **five "documents" were byte-for-byte
identical (238,542 bytes)**: they were the *index listing page*, not the circulars. A green status
message had hidden a completely wrong corpus.

`corpus/fetch_corpus.py` now refuses to save a document unless it passes validation:

| Check | Purpose |
|---|---|
| ≥ 2000 characters of extracted text | Rejects stubs and error pages |
| Not ≥ 8 occurrences of "Advisory No." | Rejects index/listing pages |
| Mentions its own subject | An "NPC Circular 16-03" must contain "personal data breach" |

This is why the corpus is trustworthy: it is verified by content, not by HTTP status code.

### Documents that could not be retrieved

| Document | Outcome |
|---|---|
| **NPC Circular 2016-03** (Guidelines on Outbound Data Transfer) | **Not retrievable** — not listed on the advisories index, no usable Wayback capture. The "vendor in Singapore" question is therefore answered from **DPA §26** and the IRR's outsourcing/processor rules, which *are* in the corpus. |
| **BSP Memorandum M-2024-019** | **Not retrievable** — `bsp.gov.ph` 403s and the Wayback capture 404s. Cited in documentation as supervisory context only; the copilot does not depend on it. |

Both are listed as **optional** sources in the fetcher, so their absence does not fail the build. This
is disclosed rather than papered over.

---

## Citation metadata

An answer a compliance officer cannot defend to an examiner is worse than no answer, so **every
chunk carries its full citation**:

```python
chunk_id        # "NPC-CIRC-16-03-SECTION-17-127"
text            # the span
doc_id          # "NPC-CIRC-16-03"
doc_title       # "NPC Circular No. 16-03 - Personal Data Breach Management"
issuer          # "National Privacy Commission"
section         # "SECTION 17. Notification of the Commission..."
effective_date  # "2016-12-15"
url             # canonical source URL
doc_type        # statute | irr | circular | advisory | bsp_memo | morb
authority_tier  # 1 = statute/NPC, 2 = BSP, 3 = internal
```

Retrieval applies **authority weighting**: DPA / IRR / NPC outrank BSP memoranda, which outrank
internal SOPs. The tier is surfaced in the UI so the officer knows what they are looking at.

---

## Verification

Rebuild and verify the corpus at any time:

```powershell
.venv\Scripts\python.exe corpus\fetch_corpus.py     # refetch + content-validate
.venv\Scripts\python.exe corpus\chunk_corpus.py     # rebuild chunks.jsonl
```

Section-header parsing was corrected during development after it was found to label each chunk with
the *following* section's header — which would have made **every citation off by one**. The fix is
covered by `tests/`.

Two further header guards were added after the front-line guide was authored. A line that mentions
"Section" more than once is a cross-reference, not a heading, and a line whose first word after the
number is a finite verb is a sentence, not a title. Without them, body text that happened to wrap
onto a line beginning "Section 12. RA 10173 Section 11(f) requires…" was labelled as the heading
for everything after it — a citation to nothing at all.

The corpus can be rebuilt with no network at all, which matters for a product whose central claim is
that it runs air-gapped:

```powershell
.venv\Scripts\python.exe corpus\fetch_corpus.py --offline   # adopt what is already in corpus/raw
.venv\Scripts\python.exe corpus\chunk_corpus.py               # rebuild chunks.jsonl
```

---

## The eighth document: ISLA-GUIDE-CS

Seven of the eight documents in the corpus are Philippine legal instruments fetched from public
mirrors. The eighth, `corpus/raw/ISLA-GUIDE-CS.md`, is **authored by Isla AI** and is not a legal
source. It exists because the corpus had no answer to the most common question a bank front-line
officer asks — "can I ask the customer for the CVV?" — and because the Act's own vocabulary
("adequate and not excessive", "strict confidentiality") does not appear in the question.

It is kept honest by construction:

| Control | Where |
|---|---|
| `doc_type` is `sector_guidance`, not `circular` or `sop` | `corpus/fetch_corpus.py` |
| `authority_tier` 3, and retrieval weight 0.55 — below every statute, circular and advisory | `AUTHORITY_WEIGHT` in `services/copilot/retrieval.py` |
| Issuer reads "Isla AI (compiled aid; not a legal source)" on every citation chip | `fetch_corpus.py` |
| URL is `isla-ai://corpus/ISLA-GUIDE-CS`, never a `privacy.gov.ph` link | `fetch_corpus.py` |
| Every rule it states is split into "DPA basis" (citable, indexed) and "Binding rule" (PCI DSS / BSP, **not** indexed) | the document itself |
| It declines to name BSP circular numbers rather than guess at them | `tests/test_frontline_copilot.py` |

The operational go/no-go that decides whether staff may solicit a card secret lives in PCI DSS and
Bangko Sentral regulations, neither of which is indexed. When a front-line question depends on it,
the copilot cites the DPA provisions it *can* verify and appends a `SCOPE NOTE` saying so, rather
than refusing the whole question or inventing the rule.

---

## Citation verification notes

Legal citations in this project are reproduced from the source documents themselves. The 72-hour
breach-notification rule is quoted verbatim from NPC Circular 16-03 and is present in the indexed
corpus text — which is exactly the kind of thing a reviewer can confirm by running
`python eval/run_eval.py`.

**Isla AI is not a legal authority and not legal advice.** For a binding interpretation, consult the
source circular and a qualified Philippine privacy counsel.