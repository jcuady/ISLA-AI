"""Static-file delivery, which is half the demo surface and easy to get quietly wrong.

Both web surfaces are served by the same process. The landing page and the
console are plain files under `apps/web/dist`, handed out by the SPA fallback,
so every asset they reference passes through `mimetypes` guessing.

That guessing is where the fonts used to break. The self-hosted woff2 files
shipped as `application/octet-stream`, which Chrome tolerates and Safari does
not: it refuses to render a font whose MIME type is wrong and silently falls
back to a system face. On the development machine the brand type looked fine, so
the bug only appeared on someone else's laptop - which is to say, a judge's.

`font-src 'self'` is the CSP doing its job; these tests are what stop the
transport underneath it from being wrong.
"""

from __future__ import annotations

import mimetypes

import pytest

from services.core.app import app  # noqa: F401  (import registers the MIME type)


WEB_PUBLIC = "apps/web/public"
REQUIRED_ASSETS = [
    "landing.html",
    "favicon.svg",
    "isla-mark.svg",
    "isla-mark-180.png",
    "hero-island.jpg",
    "hero-tiny.jpg",
    "fonts/outfit.woff2",
    "fonts/plus-jakarta-sans.woff2",
    "fonts/jetbrains-mono.woff2",
]


def test_woff2_is_registered_with_the_right_media_type():
    """The one that bit us: mimetypes has no woff2 entry on this platform."""
    assert mimetypes.guess_type("outfit.woff2")[0] == "font/woff2"


@pytest.mark.parametrize(
    "suffix,expected",
    [
        (".svg", "image/svg+xml"),
        (".png", "image/png"),
        (".jpg", "image/jpeg"),
        (".woff2", "font/woff2"),
    ],
)
def test_every_web_asset_type_resolves(suffix: str, expected: str):
    assert mimetypes.guess_type(f"probe{suffix}")[0] == expected


@pytest.mark.parametrize("asset", REQUIRED_ASSETS)
def test_the_demo_assets_exist(asset: str):
    """A missing asset is a broken demo, not a build warning."""
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    assert (root / WEB_PUBLIC / asset).is_file(), f"{asset} is referenced by the UI but missing"


def test_landing_only_references_assets_that_exist():
    """Catches a renamed or deleted file that the page still points at."""
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    public = root / WEB_PUBLIC
    html = (public / "landing.html").read_text(encoding="utf-8")
    referenced = set(re.findall(r'(?:src|href)="(/[^"]+)"', html))
    for path in sorted(referenced):
        if path.startswith(("/api", "/app", "/console")):
            continue  # routes, not files
        assert (root / "apps/web/dist" / path.lstrip("/")).is_file() or (
            public / path.lstrip("/")
        ).is_file(), f"landing.html references {path}, which does not exist"
