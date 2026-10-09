"""End-to-end walk of every demo use case against the running server.

`scripts/qa_probe.py` asks what an attacker would. This asks what a judge will.
Each case below is one beat in docs/DEMO_SCRIPT.md, asserted against the live
API rather than against a mock, so a regression here is a broken demo.

    python scripts/use_case_walk.py [base_url]
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765").rstrip("/")

GREEN, RED, DIM, RESET = "\033[32m", "\033[31m", "\033[2m", "\033[0m"


def post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"__status": e.code, "__body": e.read()[:300].decode("utf-8", "replace")}


def get(path: str) -> dict:
    with urllib.request.urlopen(BASE + path, timeout=60) as r:
        return json.loads(r.read())


results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    mark = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
    print(f"  {mark}  {name}" + (f"  {DIM}{detail}{RESET}" if detail else ""))


# ── 1. Egress Guard ─────────────────────────────────────────────────────────
print("\n[1] Egress Guard — redact a staff member's paste")
r = post("/api/pii/scan", {"text":
    "Client Maria Santos, SSS 12-3456789-0, card 4539 1488 0343 6467, "
    "email maria.santos@gmail.com, mobile 0917 555 0142. Sends CDR to vendor."})
check("responds", "__status" not in r, f"status={r.get('__status')}")
# An SSS is a high-risk government identifier, so the engine escalates rather
# than redacting-and-sending. Both branches are asserted below: this one, and
# the plain redaction case. Getting this wrong in either direction would be a
# real safety defect.
check("SSS present -> BLOCK_ESCALATE", r.get("verdict") == "BLOCK_ESCALATE",
      r.get("verdict", ""))
check("escalation explains itself",
      any("SSS" in n or "government identifier" in n for n in r.get("notes", [])),
      "; ".join(r.get("notes", []))[:80])
check("verified clean", r.get("verified_clean") is True)
check("residual leakage is 0", r.get("residual_leakage") == 0.0, str(r.get("residual_leakage")))
check("PAN redacted", "4539 1488 0343 6467" not in r.get("redacted", ""), r.get("redacted", "")[:70])
check("SSS redacted", "12-3456789-0" not in r.get("redacted", ""))
check("email redacted", "maria.santos@gmail.com" not in r.get("redacted", ""))
check("mobile redacted", "0917 555 0142" not in r.get("redacted", ""))

print("\n[1b] Egress Guard — ordinary PII redacts and sends")
r = post("/api/pii/scan", {"text":
    "Card 4539 1488 0343 6467, email maria.santos@gmail.com, "
    "mobile 0917 555 0142. Sending to the vendor."})
check("responds", "__status" not in r)
check("no SSS/TIN -> REDACT_THEN_SEND", r.get("verdict") == "REDACT_THEN_SEND",
      r.get("verdict", ""))
check("still verified clean", r.get("verified_clean") is True)

# ── 2. DPA Copilot — Taglish question ───────────────────────────────────────
print("\n[2] DPA Copilot — answer a Taglish breach question")
r = post("/api/copilot/ask", {"text": "Ilang oras dapat ko i-report ang data breach?"})
check("responds", "__status" not in r, f"status={r.get('__status')}")
check("not refused", r.get("refused") is False)
check("answer mentions 72 hours", "72" in r.get("answer", "") or "seventy-two" in r.get("answer", "").lower())
check("at least one citation", len(r.get("citations", [])) >= 1, f"{len(r.get('citations', []))} citations")
check("every citation has a section",
      all(c.get("section") for c in r.get("citations", [])), "")
check("every citation has an issuer",
      all(c.get("issuer") for c in r.get("citations", [])), "")
check("no LLM was called", r.get("llm_used") is False)

# ── 3. Copilot — correct refusal out of domain ──────────────────────────────
print("\n[3] DPA Copilot — refuse an out-of-domain question")
r = post("/api/copilot/ask", {"text": "Who won the 2025 FIFA World Cup?"})
check("responds", "__status" not in r)
check("refused", r.get("refused") is True)
check("refusal cites nothing", len(r.get("citations", [])) == 0,
      f"{len(r.get('citations', []))} citations on a refusal")

# ── 4. The front-line question that started all this ────────────────────────
print("\n[4] DPA Copilot — front-line: may staff ask a customer for the PIN/CVV?")
r = post("/api/copilot/ask", {"text":
    "Pwede ba humingi ng CVV o PIN sa customer ko? Naka-send kami ng OTP sa kausap."})
check("responds", "__status" not in r)
check("not refused", r.get("refused") is False)
check("cites RA 10173 or its IRR",
      any(c.get("doc_id") in ("RA-10173", "IRR-RA10173") for c in r.get("citations", [])),
      ", ".join(c.get("doc_id", "") for c in r.get("citations", [])))
check("names the scope limit (PCI/BSP outside corpus)",
      "PCI" in r.get("answer", "") or "BSP" in r.get("answer", "")
      or any("scope" in (n or "").lower() for n in r.get("notes", [])),
      r.get("notes", []))

# ── 5. Fraud & AML — critical, credential solicitation ──────────────────────
print("\n[5] Fraud & AML — call-centre agent solicits a card PIN")
r = post("/api/risk/assess", {"text":
    "A call center agent asked the customer for the credit card PIN and CVV."})
check("responds", "__status" not in r, f"status={r.get('__status')}")
check("tier is critical", r.get("tier") == "critical", r.get("tier", ""))
check("both parties exposed",
      set(r.get("exposed", [])) == {"bank", "customer"}, str(r.get("exposed")))
check("credential_solicitation fired",
      any(f["id"] == "credential_solicitation" for f in r.get("red_flags", [])))
check("evidence is quoted back",
      any(f.get("evidence") for f in r.get("red_flags", [])))
check("names a required action", len(r.get("required_actions", [])) >= 1)
check("coverage gap is disclosed", len(r.get("coverage_gap", [])) >= 1,
      f"{len(r.get('coverage_gap', []))} gaps")
check("never cites a GAP hook as law",
      all(not (f.get("legal_hook", {}).get("is_gap") and f.get("citation"))
          for f in r.get("red_flags", [])))
check("footer disclaims legal advice",
      "not legal advice" in r.get("footer", "").lower())

# ── 6. Fraud & AML — structuring, with a real citation ──────────────────────
print("\n[6] Fraud & AML — structuring below a reporting threshold")
r = post("/api/risk/assess", {"text":
    "A customer deposits nine separate cash deposits of PHP 49,000 each in one "
    "day across three branches, then withdraws most of it the next morning."})
check("responds", "__status" not in r)
check("tier is high or critical", r.get("tier") in ("high", "critical"), r.get("tier", ""))
check("structuring fired",
      any(f["id"] == "structuring" for f in r.get("red_flags", [])))
check("at least one citation resolved", r.get("citation_count", 0) >= 1,
      f"{r.get('citation_count')} citations")
check("bank is exposed", "bank" in r.get("exposed", []), str(r.get("exposed")))

# ── 7. Fraud & AML — routine banking must not cry wolf ──────────────────────
print("\n[7] Fraud & AML — routine banking raises nothing")
r = post("/api/risk/assess", {"text":
    "A customer withdraws PHP 25,000 from an ATM in Makati during business hours "
    "and then makes a PHP 24,000 purchase at a grocery store."})
check("responds", "__status" not in r)
check("no red flags", len(r.get("red_flags", [])) == 0,
      f"{len(r.get('red_flags', []))} flags")
check("tier is the lowest",
      r.get("tier") in ("none", "minimal", "low"), r.get("tier", ""))

# ── 8. Audit ledger ─────────────────────────────────────────────────────────
print("\n[8] Audit ledger — chain intact, no customer text")
r = get("/api/audit")
entries = r.get("entries", r if isinstance(r, list) else [])
check("responds with entries", len(entries) > 0, f"{len(entries)} entries")

# Strip the hash fields before searching. Every entry carries a SHA-256 prev/entry
# hash, and a 4-digit sequence like "6488" appears inside a random 64-char hex
# string often enough that a naive substring search reports a PII leak that is
# not there. This exact false positive fired during this audit. Search the
# human-meaningful fields only.
HASH_FIELDS = {"prev_hash", "entry_hash"}


def strip_hashes(obj):
    if isinstance(obj, dict):
        return {k: strip_hashes(v) for k, v in obj.items() if k not in HASH_FIELDS}
    if isinstance(obj, list):
        return [strip_hashes(v) for v in obj]
    if isinstance(obj, str) and re.fullmatch(r"[0-9a-f]{16,}", obj):
        return "<hash>"
    return obj


blob = json.dumps(strip_hashes(r)).lower()
# Search for the actual identifiers the walk just sent, not short digit runs.
LEAKS = ["maria", "santos", "4539 1488", "45391488", "12-3456789", "maria.santos",
         "0917 555 0142", "cvv"]
for leak in LEAKS:
    check(f"ledger holds no '{leak}'", leak not in blob)

# The ledger must still prove what it says it proves.
check("ledger keeps a scenario fingerprint",
      any(isinstance(s, dict) and "scenario_sha256_prefix" in s
          for s in (e.get("summary", {}) for e in entries if isinstance(e, dict))),
      "stores a hash prefix, not the text")

# ── 9. Health + air-gap ─────────────────────────────────────────────────────
print("\n[9] Health and air-gap claims")
h = get("/api/health")
check("status ok", h.get("status") == "ok")
check("loopback only", h.get("bind", {}).get("loopback_only") is True)
check("corpus is populated", h.get("corpus", {}).get("chunks", 0) > 0,
      f"{h.get('corpus', {}).get('chunks')} chunks / {h.get('corpus', {}).get('documents')} docs")
check("embeddings available", h.get("models", {}).get("embeddings", {}).get("available") is True)
check("no cloud AI SDK installed",
      h.get("models", {}).get("llm", {}).get("available") in (False, None))
a = get("/api/airgap")
check("air-gap probe returns a verdict", "reachable" in json.dumps(a).lower()
      or "socket" in json.dumps(a).lower() or "external" in json.dumps(a).lower())

# ── report ──────────────────────────────────────────────────────────────────
passed = sum(1 for _, ok, _ in results if ok)
failed = [r for r in results if not r[1]]
print(f"\n{'=' * 70}")
print(f"use cases: {len(results)}   passed: {passed}   failed: {len(failed)}")
for name, _, detail in failed:
    print(f"  FAILED  {name}  {detail}")
sys.exit(1 if failed else 0)