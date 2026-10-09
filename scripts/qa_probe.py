"""Adversarial QA probe for the Isla AI API.

Not a security scanner. This drives the live server the way a hostile client
would and reports what actually happened, so the answer is observed rather
than assumed.

    python scripts/qa_probe.py [base_url]
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765").rstrip("/")

# Payloads chosen per vulnerability class, not at random.
SQLI = "'; DROP TABLE audit_ledger; --"
NOSQL = '{"$ne": null}'
XSS = '<script>alert(document.domain)</script>'
XXE = '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY x SYSTEM "file:///etc/passwd">]>&x;'
TRAVERSAL = "../../../../etc/passwd"
CRLF = "value\r\nX-Injected: 1"
FORMAT = "{0.__class__.__mro__}"
NULLBYTE = "abc\x00def"
HOMOGLYPH = "аdmin"          # Cyrillic a
ZWJ = "admin‍"                # zero-width joiner

ADVERSARIAL = {
    "sql_injection": SQLI,
    "nosql_injection": NOSQL,
    "xss": XSS,
    "xxe": XXE,
    "format_string": FORMAT,
    "null_byte": NULLBYTE,
    "homoglyph": HOMOGLYPH,
    "zero_width": ZWJ,
    "crlf_injection": CRLF,
    "path_traversal": TRAVERSAL,
    "very_long": "A" * 100_000,
    "control_chars": "\x00\x01\x02\x7f",
    "rtl_override": "admin‮gnitset",
    "json_bomb": '{"text": ' + '[' * 200 + ']' * 200 + '}',
}

POST_ROUTES = ["/api/pii/scan", "/api/pii/redact", "/api/copilot/ask", "/api/risk/assess"]

results: list[tuple[str, str, int, str]] = []


def call(method: str, path: str, body: bytes | None = None, ctype="application/json"):
    url = BASE + path
    data = body
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = ctype
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.status, r.read()[:400], dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:400], dict(e.headers)
    except Exception as e:  # noqa: BLE001
        return 0, repr(e).encode()[:400], {}


def note(group: str, label: str, status: int, detail: str) -> None:
    results.append((group, label, status, detail))


print(f"probing {BASE}\n")

# ── 1. Adversarial payloads on every POST route ──────────────────────────────
for route in POST_ROUTES:
    for name, payload in ADVERSARIAL.items():
        code, body, hdrs = call("POST", route, json.dumps({"text": payload}).encode())
        ctype = hdrs.get("Content-Type", hdrs.get("content-type", ""))
        flag = ""
        if code == 0:
            flag = "  <-- CONNECTION FAILED"
        elif code == 500:
            flag = "  <-- SERVER ERROR"
        elif code == 200 and (b"Traceback" in body or b'File "' in body):
            flag = "  <-- STACK TRACE LEAKED"
        # Echoing the submitted text back inside a JSON body is correct API
        # behaviour, not an XSS hole: the response is application/json, the
        # browser does not render it, and the React console has no
        # dangerouslySetInnerHTML or innerHTML anywhere. What actually matters is
        # whether the response could be rendered as a document, so assert on the
        # content type rather than on the substring being present.
        elif code == 200 and b"<script>alert" in body and "json" not in ctype.lower():
            flag = "  <-- HTML-RENDERABLE REFLECTION"
        note(route, name, code, flag or body[:110].decode("utf-8", "replace"))

# ── 2. Malformed request shapes ─────────────────────────────────────────────
BAD_SHAPES = {
    "missing_text": b"{}",
    "text_null": b'{"text": null}',
    "text_int": b'{"text": 12345}',
    "text_list": b'{"text": ["a","b"]}',
    "text_obj": b'{"text": {"a":1}}',
    "text_bool": b'{"text": true}',
    "empty_body": b"",
    "not_json": b"this is not json",
    "wrong_key": b'{"scenario": "hello"}',
    "extra_keys": b'{"text":"hi","__proto__":{"admin":true}}',
    "truncated_json": b'{"text": "unterminated',
}
for route in POST_ROUTES:
    for name, payload in BAD_SHAPES.items():
        code, body, _ = call("POST", route, payload)
        flag = ""
        if code == 500:
            flag = "  <-- SERVER ERROR"
        elif code == 200 and (b"Traceback" in body or b"File \"" in body):
            flag = "  <-- STACK TRACE LEAKED"
        elif code not in (200, 400, 422):
            flag = "  <-- UNEXPECTED"
        note(route, name, code, flag or body[:110].decode("utf-8", "replace"))

# ── 3. Path traversal and routing on the catch-all ─────────────────────────
PATHS = [
    "/../app.py", "/..%2f..%2fapp.py", "/%2e%2e/%2e%2e/app.py",
    "/../../.env", "/../../requirements.txt", "/../../.git/config",
    "/../../../Windows/System32/drivers/etc/hosts",
    "/static/../../app.py", "/fonts/../../../app.py",
    "/app/", "/app/../landing.html", "//app", "/app%00.html",
    "/nonexistent-page", "/api/", "/api/nope",
]
for path in PATHS:
    code, body, _ = call("GET", path)
    flag = ""
    if code == 200 and (b"app = FastAPI" in body or b"BEGIN CERTIFICATE" in body
                        or b"[project]" in body):
        flag = "  <-- SOURCE FILE LEAKED"
    elif code == 200 and b"passwd" in body:
        flag = "  <-- SYSTEM FILE LEAKED"
    elif code == 200 and b"ISLA AI" in body and b"<html" in body:
        flag = "  (served a page)"
    note("routing", path[:46], code, flag or body[:90].decode("utf-8", "replace"))

# ── 4. Method confusion ────────────────────────────────────────────────────
for method, path in [("POST", "/api/health"), ("DELETE", "/api/audit"),
                     ("PUT", "/api/pii/scan"), ("GET", "/api/pii/scan"),
                     ("PATCH", "/")]:
    code, body, _ = call(method, path, b"{}" if method in ("POST", "PUT", "PATCH") else None)
    flag = "  <-- SHOULD NOT SUCCEED" if code == 200 else ""
    note("method", f"{method} {path}", code, flag or body[:80].decode("utf-8", "replace"))

# ── 5. Security headers on every surface ───────────────────────────────────
print("=" * 78)
for path in ["/", "/app", "/api/health", "/api/risk/indicators"]:
    _, _, hdrs = call("GET", path)
    lowered = {k.lower(): v for k, v in hdrs.items()}
    missing = [h for h in ("content-security-policy", "x-content-type-options",
                           "x-frame-options", "referrer-policy",
                           "permissions-policy") if h not in lowered]
    note("headers", path, 0, f"missing={missing or 'none'}")

# ── 6. CORS behaviour (must not be wildcard) ───────────────────────────────
req = urllib.request.Request(BASE + "/api/health", method="OPTIONS",
                             headers={"Origin": "https://evil.example"})
try:
    with urllib.request.urlopen(req, timeout=20) as r:
        cors = {k.lower(): v for k, v in r.headers.items()}.get("access-control-allow-origin", "(absent)")
        note("cors", "evil.example", r.status, f"ACAO={cors}")
except urllib.error.HTTPError as e:
    cors = {k.lower(): v for k, v in e.headers.items()}.get("access-control-allow-origin", "(absent)")
    note("cors", "evil.example", e.code, f"ACAO={cors}")

# ── Report ─────────────────────────────────────────────────────────────────
print(f"{'GROUP':<22}{'CASE':<48}{'CODE':<6}NOTE")
print("-" * 78)
for group, label, code, detail in results:
    print(f"{group:<22}{label[:46]:<48}{code:<6}{detail[:70]}")

problems = [r for r in results if "  <--" in r[3]]
print("\n" + "=" * 78)
print(f"probes: {len(results)}   flagged: {len(problems)}")
for group, label, code, detail in problems:
    print(f"  FLAG  {group} {label}: {detail.strip()}")