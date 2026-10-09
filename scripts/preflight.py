r"""Pre-demo self-check.

Run this immediately before presenting. Every item is an automated assertion -
if this script passes, the demo should run start to finish with no surprises.

    .venv\Scripts\python.exe scripts\preflight.py
"""

from __future__ import annotations

import re
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

BASE = "http://127.0.0.1:8765"
checks: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    checks.append((name, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))


def get(path: str, timeout: float = 30):
    with urllib.request.urlopen(f"{BASE}{path}", timeout=timeout) as r:  # noqa: S310
        import json

        return json.loads(r.read())


def post(path: str, body: dict, timeout: float = 90):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=__import__("json").dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
        import json

        return json.loads(r.read())


print("Isla AI pre-flight\n" + "=" * 66)

# --- artifacts --------------------------------------------------------------
print("\n[artifacts]")
check("corpus chunks", (REPO_ROOT / "corpus" / "processed" / "chunks.jsonl").exists())
check("built UI", (REPO_ROOT / "apps" / "web" / "dist" / "index.html").exists())
check("landing page", (REPO_ROOT / "apps" / "web" / "dist" / "landing.html").exists())
check("brand assets", (REPO_ROOT / "branding" / "isla-mark.svg").exists())
check("model weights", (REPO_ROOT / "models" / "weights").exists())
check("fetch manifest", (REPO_ROOT / "corpus" / "raw" / "fetch_manifest.json").exists())

# --- banned name ------------------------------------------------------------
print("\n[identity]")
# The retired product name is assembled from fragments so that this scanner does
# not match itself; every other file in the repo must be clean.
RETIRED_NAME = "ban" + "tay"
SELF = Path(__file__).resolve()
offenders = []
for p in REPO_ROOT.rglob("*"):
    if not p.is_file() or any(x in p.parts for x in (".venv", "node_modules", "weights", "llamacpp", ".git")):
        continue
    if p.suffix.lower() not in {".py", ".md", ".tsx", ".ts", ".json", ".css", ".yaml", ".yml"}:
        continue
    if p.resolve() == SELF:
        continue
    try:
        if RETIRED_NAME in p.read_text(encoding="utf-8", errors="ignore").lower():
            offenders.append(str(p.relative_to(REPO_ROOT)))
    except OSError:
        continue
check("no retired-name references", not offenders, ", ".join(offenders[:3]))

# --- hackathon rules: disclosure completeness --------------------------------
# The host requires "models, APIs, frameworks, and major tools disclosed". That is
# checkable: every model in the registry must actually appear in the disclosure,
# and the rules/criteria must be transcribed somewhere a judge can audit.
print("\n[hackathon rules]")
DISCLOSURE_DOCS = [
    "docs/DISCLOSURES.md",
    "docs/SUBMISSION.md",
    "docs/HACKATHON_RULES.md",
    "docs/CORPUS_SOURCES.md",
    "docs/LICENSING.md",
]
missing_docs = [d for d in DISCLOSURE_DOCS if not (REPO_ROOT / d).exists()]
check("required disclosure docs present", not missing_docs, ", ".join(missing_docs))

try:
    registry = (REPO_ROOT / "models" / "registry.yaml").read_text(encoding="utf-8")
    disclosures = (REPO_ROOT / "docs" / "DISCLOSURES.md").read_text(encoding="utf-8").lower()
    # registry.yaml is a Markdown table despite the extension; the first cell of
    # each row is the model key.
    keys = set(re.findall(r"^\|\s*`([a-z0-9][a-z0-9._-]*)`\s*\|", registry, re.MULTILINE))
    undisclosed = sorted(k for k in keys if k.split("-")[0] not in disclosures)
    check(
        "every registry model appears in DISCLOSURES",
        bool(keys) and not undisclosed,
        ", ".join(undisclosed[:3]) or f"{len(keys)} models checked",
    )
except OSError as exc:  # noqa: BLE001
    check("model registry readable", False, str(exc))

reqs = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
CLOUD_SDKS = ("openai", "anthropic", "google-generativeai", "cohere", "replicate", "groq")
installed_cloud = [s for s in CLOUD_SDKS if any(l.strip().startswith(s) for l in reqs.splitlines())]
check("no cloud AI SDK installed", not installed_cloud, ", ".join(installed_cloud))

# --- unit tests -------------------------------------------------------------
print("\n[tests]")
import subprocess  # noqa: PLC0415

r = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no"],
    cwd=REPO_ROOT, capture_output=True, text=True, timeout=900,
)
tail = [ln for ln in r.stdout.strip().splitlines() if ln.strip()][-1:]
check("pytest", r.returncode == 0, tail[0] if tail else "")

# --- live server ------------------------------------------------------------
print("\n[live server]")
try:
    health = get("/api/health", timeout=60)
    check("server reachable", True)
    check("loopback only", health["bind"]["loopback_only"] is True)
    corpus = health.get("corpus") or {}
    check("corpus loaded", (corpus.get("chunks") or 0) > 150, f"{corpus.get('chunks')} chunks")
    check("dense retrieval", bool(corpus.get("dense_ready")))
except Exception as exc:  # noqa: BLE001
    check("server reachable", False, f"{type(exc).__name__}: {exc}")
    raise SystemExit(1) from exc

# --- egress guard -----------------------------------------------------------
print("\n[egress guard]")
sample = get("/api/sample")["sample"]
t0 = time.perf_counter()
r1 = post("/api/pii/redact", {"text": sample})
ms = (time.perf_counter() - t0) * 1000
check("verdict is BLOCK", r1["verdict"] == "BLOCK_ESCALATE", r1["verdict_label"])
check("verified clean", r1["verified_clean"] is True)
check("residual 0.00%", r1["residual_leakage"] == 0.0)
for leak in ("12-345-6789", "456-789-012", "4539578763621486", "0056-12345678"):
    check(f"redacted: {leak}", leak not in r1["redacted"])
check("fast enough (<1500 ms)", ms < 1500, f"{ms:.0f} ms")

safe = post("/api/pii/redact", {"text": "Please process invoice INV-2024-00123456 for batch 20240315."})
check("no false positive on invoice", safe["verdict"] == "SAFE_TO_SEND", safe["verdict_label"])

# --- copilot ----------------------------------------------------------------
print("\n[DPA copilot]")
t0 = time.perf_counter()
r2 = post("/api/copilot/ask", {"text": "Ilang oras dapat ko i-report ang data breach?"})
ms = (time.perf_counter() - t0) * 1000
check("72-hour question answered", r2["refused"] is False)
check("states 72 hours", "72 hour" in r2["answer"].lower())
check("has citations", len(r2["citations"]) > 0, f"{len(r2['citations'])} cites")
check("fast enough (<5000 ms)", ms < 5000, f"{ms:.0f} ms")

r3 = post("/api/copilot/ask", {"text": "Who won the 2025 FIFA World Cup?"})
check("out-of-domain refuses", r3["refused"] is True)
check("no invented citations", len(r3["citations"]) == 0)

# --- transaction risk --------------------------------------------------------
# The demo shows this screen, and the claim it makes is unusual for a product
# of this kind: it names what it cannot verify. If that panel ever disappears
# the demo's best moment silently becomes the product's worst.
print("\n[transaction risk]")
t0 = time.perf_counter()
risky = post("/api/risk/assess", {
    "text": (
        "A student account received 480,000 in cash deposits from three "
        "different people over two days, and sent most of it by wire to a "
        "beneficiary abroad the same day."
    )
})
ms = (time.perf_counter() - t0) * 1000
check("mule scenario raises critical", risky["tier"] in ("high", "critical"), risky["tier"])
check("names who is exposed", set(risky["exposed"]) >= {"customer", "bank"},
      ", ".join(risky["exposed"]))
check("every red flag shows evidence", all(f["evidence"] for f in risky["red_flags"]),
      f"{len(risky['red_flags'])} flags")
check("required actions returned", len(risky["required_actions"]) > 0)
check("states the coverage gap", len(risky["coverage_gap"]) > 0,
      f"{len(risky['coverage_gap'])} items")
check("names BSP as missing", any("BSP" in g for g in risky["coverage_gap"]))
check("no hook cites an absent instrument",
      all(f["legal_hook"]["doc_id"] not in ("BSP", "SEC") for f in risky["red_flags"]))
check("fast enough (<2000 ms)", ms < 2000, f"{ms:.0f} ms")

benign = post("/api/risk/assess", {
    "text": "Customer withdrew PHP 5,000 from an ATM with a debit card."
})
check("routine banking raises nothing", not benign["red_flags"], benign["tier"])

cat = get("/api/risk/indicators")
check("indicator catalogue served", cat["count"] >= 12, f"{cat['count']} indicators")

# --- air-gap + ledger -------------------------------------------------------
print("\n[proof]")
probe = get("/api/airgap")
check("probe returns observed data", len(probe["probes"]) > 0, probe["note"][:60])
audit = get("/api/audit?limit=10")
check("ledger chain valid", audit["verification"]["valid"] is True,
      f"{audit['verification']['entries']} entries")
check("ledger holds no raw PII", audit["stats"]["contains_raw_pii"] is False)

# --- web surfaces ------------------------------------------------------------
# The demo opens on the landing page and clicks through to the console, so both
# must serve. The security headers are asserted because the air-gap claim is
# partly a claim about what the browser is allowed to fetch.
print("\n[web surfaces]")
try:
    with urllib.request.urlopen(f"{BASE}/", timeout=30) as r:  # noqa: S310
        root_html = r.read().decode("utf-8", "replace")
        root_headers = dict(r.headers)
    check("landing serves at /", True, f"{len(root_html) // 1024} kB")
    # Identify the marketing page structurally, not by copy. The console mounts
    # React into #root and ships no Open Graph tags; the landing does the
    # reverse. Matching on a phrase broke the moment the tagline was reworded,
    # which is a test that fails for a reason unrelated to what it checks.
    check(
        "landing is the marketing page",
        'id="root"' not in root_html and 'property="og:title"' in root_html,
        f"root-mount={'no' if 'id=\"root\"' not in root_html else 'YES'}, og={'yes' if 'og:title' in root_html else 'NO'}",
    )

    with urllib.request.urlopen(f"{BASE}/app", timeout=30) as r:  # noqa: S310
        app_html = r.read().decode("utf-8", "replace")
    check("console serves at /app", 'id="root"' in app_html)

    csp = next((v for k, v in root_headers.items() if k.lower() == "content-security-policy"), "")
    check("CSP forbids remote loads", "default-src 'none'" in csp)
    check("framing denied", "frame-ancestors 'none'" in csp)
    check("no-sniff header", any(k.lower() == "x-content-type-options" for k in root_headers))
except Exception as exc:  # noqa: BLE001
    check("web surfaces", False, f"{type(exc).__name__}: {exc}")

# --- summary ----------------------------------------------------------------
passed = sum(1 for _, ok, _ in checks if ok)
total = len(checks)
print("\n" + "=" * 66)
if passed == total:
    print(f"PRE-FLIGHT PASSED — {passed}/{total} checks. Ready to demo.")
    raise SystemExit(0)

print(f"PRE-FLIGHT FAILED — {passed}/{total} passed. Fix before presenting:")
for name, ok, detail in checks:
    if not ok:
        print(f"  - {name}  {detail}")
raise SystemExit(1)