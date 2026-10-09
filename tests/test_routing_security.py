"""The static catch-all is the product's only unauthenticated file surface.

Seam under test: `GET /{full_path:path}` in services/core/app.py, exercised
through the real FastAPI app so routing, containment and error handling are
all in the path a browser or a hostile client would actually take.

These tests exist because two real defects lived in nine lines of that handler,
and neither produced an error a human would have noticed during a demo:

  * An embedded null byte made pathlib raise ValueError from stat(), which
    escaped as an unhandled 500. A malformed path is not a server fault; it is
    a path that does not exist, and an attacker should not be able to turn a
    bad request into a server error at all.

  * Every unknown path answered 200 with the SPA shell, API paths included. A
    client that fat-fingered `/api/pii/scrn` got HTML and a success code
    instead of a 404, which silently hides the mistake from the caller and from
    anything watching for 4xx rates.

The SPA genuinely needs no blanket fallback: `/app` and `/console` are served
by their own routes and client navigation uses `?view=` on `/console`, so there
is no deep client path that has to resolve to the shell. The tests below pin
that down, including the routes that must keep working.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.core.app import app  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# apps/web/dist is a build artifact and is git-ignored, so a fresh CI checkout
# does not have it. These tests were written and passed against a built tree,
# then failed 11/27 on a clean `git archive HEAD` checkout in the Python-only
# CI job. Delivery assertions therefore declare their dependency instead of
# assuming a build happened; the security assertions below are unconditional
# precisely because they must hold whether or not the UI was built.
DIST_BUILT = (ROOT / "apps" / "web" / "dist" / "index.html").is_file()

requires_build = pytest.mark.skipif(
    not DIST_BUILT,
    reason="apps/web/dist is a git-ignored build artifact; delivery is covered by "
           "the web-build CI job and by scripts/preflight.py against a live server",
)


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


# ── the two defects ─────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "path",
    [
        "/%00",
        "/a%00b",
        "/fonts/outfit%00.woff2",
        "/%2500",           # double-encoded, decodes to the literal text %00
    ],
)
def test_null_byte_in_path_is_a_404_not_a_500(client: TestClient, path: str):
    """A hostile path must not be able to produce a server error.

    The percent-encoded form is the one that matters: that is what a browser
    sends, and it is what reaches the handler as a real null byte. A literal
    NUL is rejected by the HTTP client before it is ever transmitted, so it
    cannot be the regression this test guards.
    """
    r = client.get(path)
    assert r.status_code == 404, f"{path!r} returned {r.status_code}, expected 404"
    assert "Traceback" not in r.text


@pytest.mark.parametrize(
    "path",
    [
        "/api/nope",
        "/api/pii/scrn",          # a typo in a real endpoint
        "/api/risk/assess/extra",
        "/nonexistent-page",
        "/../app.py",
        "/%2e%2e/%2e%2e/app.py",
        "/../../.env",
        "/../../.git/config",
        "/static/../../app.py",
    ],
)
def test_unknown_path_is_a_404(client: TestClient, path: str):
    """Unknown paths 404. They must not answer 200 with the SPA shell, and an
    API path must not answer with HTML at all."""
    r = client.get(path)
    assert r.status_code == 404, f"{path!r} returned {r.status_code}, expected 404"


@requires_build
def test_dot_segments_normalise_rather_than_escape(client: TestClient):
    """`..` is collapsed by the router before the handler runs, so
    `/app/../landing.html` is simply `/landing.html` - a legitimate public
    asset. That is correct normalisation, not a traversal: the property that
    actually matters is that no path can reach a file *outside*
    apps/web/dist, which the next test pins directly.
    """
    r = client.get("/app/../landing.html")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "ISLA" in r.text.upper()


def test_no_source_or_secret_is_reachable_through_the_catch_all(client: TestClient):
    """Containment: nothing outside apps/web/dist may ever be served."""
    for path in ["/../app.py", "/../../requirements.txt", "/../../.git/config",
                 "/../../../Windows/System32/drivers/etc/hosts", "/..%2f..%2fapp.py"]:
        body = client.get(path).text
        for marker in ("app = FastAPI", "[project]", "BEGIN CERTIFICATE",
                       "root:x:", "fastapi>="):
            assert marker not in body, f"{path!r} leaked {marker!r}"


# ── the routes that must keep working ───────────────────────────────────────

@pytest.mark.parametrize("path", ["/app", "/console", "/"])
@requires_build
def test_real_pages_still_serve(client: TestClient, path: str):
    r = client.get(path)
    assert r.status_code == 200, f"{path} returned {r.status_code}"
    assert "<html" in r.text.lower()


@pytest.mark.parametrize(
    "asset",
    ["isla-mark.svg", "favicon.svg", "hero-island.jpg",
     "fonts/outfit.woff2", "fonts/plus-jakarta-sans.woff2", "fonts/jetbrains-mono.woff2"],
)
@requires_build
def test_real_assets_are_still_served(client: TestClient, asset: str):
    """The 404 must not swallow the demo. Assets live in dist and must resolve."""
    r = client.get(f"/{asset}")
    assert r.status_code == 200, f"/{asset} returned {r.status_code}"
    assert len(r.content) > 0


@requires_build
def test_asset_content_type_is_still_correct(client: TestClient):
    """The woff2 regression this module's sibling file guards, re-checked
    through the route rather than through mimetypes directly."""
    assert client.get("/fonts/outfit.woff2").headers["content-type"] == "font/woff2"
    assert client.get("/isla-mark.svg").headers["content-type"] == "image/svg+xml"


def test_a_post_to_a_get_only_route_is_still_405(client: TestClient):
    """Method checking must not be weakened by the catch-all being present."""
    assert client.post("/api/health").status_code == 405
    assert client.delete("/api/audit").status_code == 405


def test_missing_payload_is_a_clean_422(client: TestClient):
    """Error shape is part of the contract a client codes against."""
    r = client.post("/api/pii/scan", json={})
    assert r.status_code == 422
    assert r.headers["content-type"].startswith("application/json")
    assert "detail" in r.json()