# Verifying the air-gap claim yourself

KALIX claims that no customer data leaves the machine and that no cloud service is called. It does
**not** claim it opens no socket — section 1 below explains why that would be a dishonest claim.
This document is how you check the real claim rather than take it on faith. Every step is a
falsifiable check, and one of them is a test that fails the build.

---

## 1. The badge is a real probe, not a string

The UI badge is driven by `GET /api/airgap`, which performs **actual TCP connection attempts** against
public addresses and reports what happened.

Open <http://127.0.0.1:8765> and look at the badge:

| Observed | Meaning |
|---|---|
| `NETWORK: CONNECTED` (amber) | An external host was reachable. KALIX still transmits nothing, but this machine is not air-gapped. |
| `NETWORK: AIR-GAPPED` (green) | No external host reachable **and** DNS does not resolve. |

The amber state is the **expected** result on a normal laptop, and KALIX reports it honestly rather
than claiming a green badge it has not earned.

### Watch it react

1. Note the badge (should read `NETWORK: CONNECTED`).
2. Disable Wi-Fi, or unplug the network cable.
3. Wait up to 20 seconds (the UI re-probes on a timer).
4. The badge flips to `NETWORK: AIR-GAPPED`.

Then re-enable the network and it flips back. A hardcoded string cannot do that.

---

## 2. Inspect the raw probe result

```powershell
Invoke-RestMethod http://127.0.0.1:8765/api/airgap | ConvertTo-Json -Depth 5
```

Sample output on a connected machine:

```json
{
  "air_gapped": false,
  "outbound_blocked": false,
  "resolver_available": true,
  "bind_host": "127.0.0.1",
  "probes": [
    { "target": "1.1.1.1:443",   "reachable": true,  "error": null },
    { "target": "8.8.8.8:443",   "reachable": true,  "error": null },
    { "target": "huggingface.co", "resolved": true, "error": null }
  ],
  "note": "An external host was reachable. KALIX itself still transmits nothing, but this machine is not air-gapped."
}
```

Every field is an observed result. There is no branch that returns `"air_gapped": true`
unconditionally.

---

## 3. Confirm the server is loopback-only

KALIX **refuses to start** on a routable address. `services/core/airgap.py`:

```python
LOOPBACK_ONLY = {"127.0.0.1", "localhost", "::1"}

def assert_loopback(bind_host: str) -> None:
    if bind_host not in LOOPBACK_ONLY:
        raise RuntimeError(...)
```

This runs at import time in `services/core/app.py`, so the process will not come up on `0.0.0.0`.

Verify it refuses:

```powershell
.venv\Scripts\python.exe -m uvicorn services.core.app:app --host 0.0.0.0 --port 8765
# RuntimeError: KALIX refuses to bind '0.0.0.0'. ...
```

Confirm nothing is listening externally while running:

```powershell
Get-NetTCPConnection -State Listen -LocalPort 8765 |
  Select-Object LocalAddress, LocalPort, State
# LocalAddress should be 127.0.0.1 only
```

---

## 4. Prove the product still works offline

This is the real test, and it is the one that matters for an air-gapped bank branch.

1. **Pre-cache everything while connected:** model weights, corpus, and the built UI.
2. **Disconnect** the network entirely (Wi-Fi off, cable out).
3. Start KALIX: `.venv\Scripts\python.exe -m uvicorn services.core.app:app --host 127.0.0.1 --port 8765`
4. Run the Egress Guard on the sample bank email.
5. Ask the Copilot: *"Ilang oras dapat ko i-report ang data breach?"*

Both must work identically. If either changes behaviour when the cable is out, the local claim is
false.

### Offline parity check

```powershell
# With the network connected
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8765/api/copilot/ask `
  -Body '{"text":"Ilang oras dapat ko i-report ang data breach?"}' -ContentType "application/json" |
  ConvertTo-Json -Depth 6 | Out-File connected.json

# ...disconnect the network, restart KALIX, repeat...

# The `answer`, `citations` and `verdict` fields must be byte-identical.
# Latency will differ slightly; that is expected and is not a parity failure.
```

---

## 5. Read the source

The strongest check is to read the code. Search the runtime for outbound calls:

```powershell
# Any HTTP client usage in the running services?
Select-String -Path services\**\*.py -Pattern 'requests\.|urlopen|httpx\.(get|post)|socket\.create_connection'
```

Expected and acceptable:

- `corpus/fetch_corpus.py` — **build-time only**, downloads public legal documents.
- `models/download_models.py` — **build-time only**, downloads model weights.
- `services/core/airgap.py` — the **probe itself**, which only opens a TCP connection to test
  reachability and transmits no payload.
- `services/core/llm.py` — talks to the **local** llama.cpp server on `127.0.0.1`.

There is no network call in the PII engine, the copilot, or the API request path.
`tests/test_airgap_claims.py` enforces this: it walks every module under `services/` with an AST
parser and fails if any of them other than `airgap.py` and `llm.py` gains a network primitive
(`socket`, `urlopen`, `requests`, `httpx`, …), and it separately asserts that no cloud AI SDK is
installed. If someone later adds a `requests.get()` to the copilot, the suite goes red.

---

## 6. What this does and does not prove

**Proves:** KALIX's core functions run without internet and emit no telemetry.

**Does not prove:** that a determined attacker with physical access to the machine cannot read memory
or disk. See [`THREAT_MODEL.md`](THREAT_MODEL.md) for the actual trust boundary — encryption at rest
and physical access control remain the operator's responsibility (BitLocker/LUKS).