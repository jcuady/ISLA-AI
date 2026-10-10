"""Walk the four demo moves end to end against the running server.

Used to verify the demo script still matches what the product actually does.
"""

from __future__ import annotations

import json
import sys
import urllib.request

B = "http://127.0.0.1:8765"


def get(path: str):
    with urllib.request.urlopen(f"{B}{path}", timeout=20) as r:
        return json.loads(r.read())


def post(path: str, body: dict):
    req = urllib.request.Request(
        f"{B}{path}", json.dumps(body).encode(), {"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


# Fail with an instruction, not a traceback. This script is the browser-less
# demo path handed to another agent, so "the server is not running" is the one
# message it must never hide behind a socket stack.
try:
    health = get("/api/health")
except Exception as exc:  # noqa: BLE001
    print(f"Cannot reach {B} ({type(exc).__name__}).")
    print("Start the server first:")
    print(r'  Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList ' +
          r'"-m","uvicorn","services.core.app:app","--host","127.0.0.1","--port","8765" '
          r"-WorkingDirectory (Get-Location) -WindowStyle Hidden")
    print("Then wait for /api/health to return 200 (6-20s first start, ~45s if the")
    print("corpus changed and the embedding matrix must be rebuilt).")
    sys.exit(1)

print(f"--- health --- chunks={health['corpus']['chunks']} "
      f"dense={health['corpus']['dense_ready']} "
      f"embeddings={health['models']['embeddings']['available']}")
if not health["corpus"]["dense_ready"]:
    print("  WARNING dense retrieval is OFF - every published figure is invalid.")


print("--- routes ---")
for route in ("/", "/app", "/console", "/console?view=egress"):
    try:
        with urllib.request.urlopen(f"{B}{route}", timeout=10) as r:
            print(f"  {route:24} {r.status}")
    except Exception as exc:  # noqa: BLE001
        print(f"  {route:24} ERR {exc}")

print("\n--- DEMO 1: Egress Guard on the built-in sample ---")
sample = get("/api/sample")["sample"]
res = post("/api/pii/redact", {"text": sample})
print(f"  verdict : {res['verdict']} | {res['verdict_label']}")
print(
    f"  passes  : {res['passes']} | residual {res['residual_leakage'] * 100:.2f}% "
    f"| latency {res['latency_ms']:.2f} ms"
)
print(f"  entities: {res['entity_counts']}")

print("\n--- DEMO 2: Copilot, the 72-hour question ---")
ans = post("/api/copilot/ask", {"text": "Ilang oras dapat ko i-report ang data breach?"})
print(
    f"  refused {ans['refused']} | conf {ans['confidence']} "
    f"| llm_used {ans['llm_used']} | {ans['latency_ms']:.0f} ms"
)
print(f"  answer  : {ans['answer'][:160]}")
for c in ans["citations"]:
    print(f"  cite    : {c['label']}  ({c['doc_id']} {c['section']})")

print("\n--- DEMO 3: out-of-domain refusal ---")
ref = post("/api/copilot/ask", {"text": "Who won the 2025 FIFA World Cup?"})
print(f"  refused {ref['refused']} | citations {len(ref['citations'])}")

print("\n--- DEMO 4: Audit Ledger ---")
led = get("/api/audit?limit=3")
print(f"  chain valid : {led['verification']['valid']} | entries {led['verification']['entries']}")
print(f"  events      : {led['stats']['by_event']}")
print(f"  raw PII     : {led['stats'].get('contains_raw_pii')}")

print("\n--- air-gap probe ---")
gap = get("/api/airgap")
print(f"  air_gapped={gap['air_gapped']} outbound_blocked={gap['outbound_blocked']} "
      f"elapsed={gap['elapsed_ms']} ms")