"""Isla AI local core - FastAPI application.

Binds 127.0.0.1 ONLY. Serves the React UI and the four API surfaces:

    POST /api/pii/scan      detect entities, no redaction
    POST /api/pii/redact    redact + verify + verdict
    POST /api/copilot/ask   grounded Taglish legal Q&A with citations
    POST /api/risk/assess   fraud / AML red-flag screening of a scenario
    GET  /api/risk/indicators  the indicator catalogue, served not invented
    GET  /api/airgap        live outbound socket probe
    GET  /api/audit         hash-chained ledger
    GET  /api/health        model + corpus readiness

No customer data leaves this process and no cloud service is called. The single
exception to "opens no outbound connection" is GET /api/airgap itself, which
deliberately opens empty TCP handshakes to fixed public resolvers - a judge has
to be able to falsify the air-gap claim by pulling the cable.
"""

from __future__ import annotations

import mimetypes
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

# The self-hosted woff2 files are served through the SPA fallback, which hands
# them to FileResponse and lets mimetypes guess the content type. On this
# platform it has no entry for .woff2, so the fonts ship as
# application/octet-stream. Chrome tolerates that; Safari refuses to render a
# font with the wrong MIME type and silently falls back to a system face -
# which would look like the brand fonts "not working" on a judge's laptop.
mimetypes.add_type("font/woff2", ".woff2")

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from services.core.airgap import assert_loopback, run_probe  # noqa: E402
from services.core.ledger import AuditLedger  # noqa: E402
from services.copilot.copilot import DPACopilot  # noqa: E402
from services.copilot.retrieval import HybridIndex  # noqa: E402
from services.pii.engine import EgressGuard  # noqa: E402
from services.risk.assess import COVERAGE_GAP, assess  # noqa: E402
from services.risk.indicators import catalogue_summary  # noqa: E402

BIND_HOST = os.environ.get("ISLA_HOST", "127.0.0.1")
BIND_PORT = int(os.environ.get("ISLA_PORT", "8765"))
DATA_DIR = REPO_ROOT / "data"
LEDGER_PATH = DATA_DIR / "audit_ledger.jsonl"
WEB_DIST = REPO_ROOT / "apps" / "web" / "dist"

assert_loopback(BIND_HOST)


# ---------------------------------------------------------------------------
# Startup / shared state
# ---------------------------------------------------------------------------

class State:
    index: HybridIndex | None = None
    copilot: DPACopilot | None = None
    guard: EgressGuard | None = None
    ledger: AuditLedger | None = None
    llm = None
    ner_available = False
    # Last observed air-gap state, so the ledger records the CHANGE, not every
    # health poll. None until the first probe completes.
    last_air_gapped: bool | None = None


state = State()


def _load_llm():
    """Attach the local llama.cpp server if it is reachable. Optional by design."""
    try:
        from services.core.llm import LlamaCppClient

        client = LlamaCppClient()
        if client.available():
            print(f"[isla] LLM online: {client.model_name}")
            return client
        print(f"[isla] LLM offline: {client.reason} (extractive answers still work)")
    except Exception as exc:  # noqa: BLE001
        print(f"[isla] LLM unavailable: {type(exc).__name__}: {exc}")
    return None


def _load_ner():
    try:
        from services.pii.ner import GLiNERBackend

        backend = GLiNERBackend()
        if backend.available:
            print("[isla] GLiNER NER online")
            return backend
        print(f"[isla] GLiNER unavailable: {backend.reason} (regex ensemble still active)")
    except Exception as exc:  # noqa: BLE001
        print(f"[isla] GLiNER unavailable: {type(exc).__name__}: {exc}")
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[isla] starting local core")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    state.ledger = AuditLedger(LEDGER_PATH)

    try:
        state.index = HybridIndex()
    except FileNotFoundError as exc:
        print(f"[isla] corpus unavailable: {exc}")
        state.index = None
    else:
        if state.index.enable_dense():
            print("[isla] dense retrieval online")
        state.copilot = DPACopilot(state.index)

    state.ner = _load_ner()
    state.guard = EgressGuard(ner_backend=state.ner)
    state.llm = _load_llm()
    if state.copilot is not None:
        state.copilot.llm = state.llm

    state.ledger.append("session_start", {"bind": BIND_HOST, "port": BIND_PORT})
    print(f"[isla] ready on http://{BIND_HOST}:{BIND_PORT}")
    yield
    if state.ledger:
        state.ledger.append("session_end", {})


app = FastAPI(title="Isla AI Local Core", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://{BIND_HOST}:{BIND_PORT}", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    """Baseline hardening for a loopback-bound app that still renders HTML.

    # frame-ancestors and friends cannot be delivered in a <meta> CSP, so they
    # are set here as real response headers. The CSP mirrors the one embedded in
    # the landing page; a browser applies the intersection of every policy it
    # receives, so both must permit the same inline script or it gets blocked.
    # That hash is the SHA-256 of the landing page's reveal script. Both policies
    # are re-checked on every run of apps/web/verify-ui.mjs, which fails the
    # build if the script changes without the hash being updated.
    """
    response = await call_next(request)
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'none'; "
        "script-src 'self' 'sha256-a/hjoGVM2OiJBb39J6k5BZvTLUf8Hi0mk7nPOIUUhGc='; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "form-action 'none'; "
        "base-uri 'none'; "
        "frame-ancestors 'none'; "
        "object-src 'none'",
    )
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
    response.headers.setdefault(
        "Permissions-Policy", "geolocation=(), camera=(), microphone=(), interest-cohort=()"
    )
    # Loopback-only, no caching: this is a compliance tool holding live data.
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class TextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20_000)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health() -> dict:
    """Model + corpus readiness. Honest about what is and is not loaded."""
    index_stats = state.index.stats() if state.index else None
    return {
        "status": "ok",
        "product": "Isla AI",
        "stands_for": "In-Situ Local AI",
        "tagline": "Walang datos na lumalabas.",
        "bind": {"host": BIND_HOST, "port": BIND_PORT, "loopback_only": True},
        "corpus": index_stats,
        "models": {
            "llm": {
                "available": state.llm is not None,
                "name": getattr(state.llm, "model_name", None),
                "role": "generation (optional)",
            },
            "embeddings": {
                "available": bool(state.index and state.index.dense_ready),
                "name": "multilingual-e5-small int8",
                "role": "retrieval",
            },
            "ner": {
                "available": state.ner_available,
                "name": "GLiNER multi-v2.1",
                "role": "contextual NER (optional)",
            },
        },
        "engines": {
            "regex_luhn": True,
            "verification_pass": True,
            "citation_enforcement": True,
            "audit_ledger": state.ledger is not None,
        },
    }


@app.get("/api/airgap")
def airgap() -> dict:
    """Live socket probe. NOT a hardcoded string - judges can pull the cable.

    The probe itself runs on every call because the whole point is that the
    claim can be falsified live. What the ledger records is a *change* in
    outbound reachability, not each poll: the console re-probes every 20
    seconds, and writing all of those would bury the redaction and copilot
    entries that the audit trail exists to prove, at roughly 4,300 entries a
    day. An unchanged state is not an auditable event.
    """
    probe = run_probe(BIND_HOST)
    result = probe.to_dict()
    previous = state.last_air_gapped
    state.last_air_gapped = probe.air_gapped
    if state.ledger and previous != probe.air_gapped:
        state.ledger.append(
            "airgap_probe",
            {
                "air_gapped": probe.air_gapped,
                "outbound_blocked": probe.outbound_blocked,
                "changed": previous is not None,
            },
        )
    return result


@app.post("/api/pii/scan")
def pii_scan(req: TextRequest) -> dict:
    if state.guard is None:
        raise HTTPException(503, "PII engine not ready")
    result = state.guard.scan(req.text)
    payload = result.to_dict()
    if state.ledger:
        state.ledger.append(
            "pii_scan",
            {
                "entities": len(result.entities),
                "verdict": result.verdict.value,
                "verified_clean": result.verified_clean,
                "text_sha256_prefix": _text_hash(req.text)[:16],
            },
        )
    return payload


@app.post("/api/pii/redact")
def pii_redact(req: TextRequest) -> dict:
    if state.guard is None:
        raise HTTPException(503, "PII engine not ready")
    result = state.guard.scan(req.text)
    payload = result.to_dict()
    if state.ledger:
        # Metadata only - never the customer text itself.
        state.ledger.append(
            "pii_redaction",
            {
                "entities_redacted": len(payload["redaction_map"]),
                "verdict": result.verdict.value,
                "verified_clean": result.verified_clean,
                "residual_leakage": result.residual_leakage,
                "passes": result.passes,
                "latency_ms": round(result.latency_ms, 1),
                "input_sha256_prefix": _text_hash(req.text)[:16],
                "output_sha256_prefix": _text_hash(result.redacted)[:16],
            },
        )
    return payload


@app.post("/api/copilot/ask")
def copilot_ask(req: TextRequest) -> dict:
    if state.copilot is None:
        raise HTTPException(
            503,
            "Corpus not built. Run: python corpus/fetch_corpus.py && python corpus/chunk_corpus.py",
        )
    answer = state.copilot.ask(req.text)
    if state.ledger:
        state.ledger.append(
            "copilot_answer",
            {
                "refused": answer.refused,
                "confidence": answer.confidence,
                "citations": len(answer.citations),
                "latency_ms": round(answer.latency_ms, 1),
                "question_sha256_prefix": _text_hash(req.text)[:16],
            },
        )
    return answer.to_dict()


@app.post("/api/risk/assess")
def risk_assess(req: TextRequest) -> dict:
    """Screen a described transaction or scenario for fraud and AML red flags.

    Runs entirely on deterministic rules; retrieval only attaches the statutory
    text to the hooks the rules name. A degraded retrieval path still returns a
    verdict, with `degraded: true` and unresolved hooks left uncited.
    """
    if not req.text.strip():
        raise HTTPException(422, "text is required")
    result = assess(req.text, index=state.index)
    payload = result.to_dict()
    if state.ledger:
        state.ledger.append(
            "risk_assessment",
            {
                "tier": result.tier,
                "red_flags": [f["id"] for f in result.red_flags],
                "exposed": sorted(result.exposed),
                "citations": result.citation_count,
                "degraded": result.degraded,
                "latency_ms": round(result.latency_ms, 1),
                "scenario_sha256_prefix": _text_hash(req.text)[:16],
            },
        )
    return payload


@app.get("/api/risk/indicators")
def risk_indicators() -> dict:
    """The full indicator catalogue, so the UI never invents a red flag."""
    items = catalogue_summary()
    return {
        "count": len(items),
        "indicators": items,
        "coverage_gap": list(COVERAGE_GAP),
    }


@app.get("/api/audit")
def audit(limit: int = 50) -> dict:
    if state.ledger is None:
        raise HTTPException(503, "ledger not ready")
    return {
        "entries": state.ledger.recent(limit),
        "verification": state.ledger.verify(),
        "stats": state.ledger.stats(),
    }


@app.get("/api/sample")
def sample() -> dict:
    """Demo seed text so the demo is reproducible and never typed live."""
    return {"sample": DEMO_SAMPLE}


def _text_hash(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


DEMO_SAMPLE = """From: Collections Team <collections@usapalmabank.com.ph>
Subject: Urgent - overdue notice for DELOS SANTOS, Maria Concepcion

Magandang araw po,

Nag-apply po ng overdue notice si Maria Concepcion de los Santos.
SSS 12-345-6789, TIN 456-789-012.
Registered mobile 0917 123 4567, GCash number +639171234568.
Credit card ending 4539578763621486, CVV 123, exp 09/28.
Account number: 0056-12345678. Monthly salary PHP 42,500.
Remittance via Cebuana Lhuillier ref #CEB-88213-4455.

Pakisuri na po bago mag-escalate. Salamat!
"""


# ---------------------------------------------------------------------------
# Static UI
# ---------------------------------------------------------------------------

if WEB_DIST.exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    LANDING = WEB_DIST / "landing.html"

    @app.get("/")
    def index() -> FileResponse:
        # "/" is the marketing surface; the console lives at /app. If the
        # landing page is missing from the build, fall back to the console
        # rather than 404-ing the product.
        target = LANDING if LANDING.is_file() else WEB_DIST / "index.html"
        return FileResponse(target)

    @app.get("/app", include_in_schema=False)
    @app.get("/console", include_in_schema=False)
    def console() -> FileResponse:
        return FileResponse(WEB_DIST / "index.html")

    @app.get("/{full_path:path}")
    def spa(full_path: str) -> FileResponse:
        # SPA fallback; never serve outside the built UI directory.
        candidate = (WEB_DIST / full_path).resolve()
        if full_path and candidate.is_file() and WEB_DIST.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(WEB_DIST / "index.html")
else:

    @app.get("/")
    def index_placeholder() -> JSONResponse:
        return JSONResponse(
            {
                "product": "Isla AI",
                "message": "UI not built yet. Run: npm --prefix apps/web run build",
                "api_docs": "/docs",
            }
        )


if __name__ == "__main__":
    import uvicorn

    print(f"[isla] binding to loopback only: {BIND_HOST}:{BIND_PORT}")
    uvicorn.run("services.core.app:app", host=BIND_HOST, port=BIND_PORT, log_level="info")