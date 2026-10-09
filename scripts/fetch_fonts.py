"""Fetch the Isla AI typeface as self-hosted woff2 subsets.

Why self-hosted: the app ships `Content-Security-Policy: default-src 'none'`, so
there is no Google Fonts and no CDN at runtime - by design, because the product
claims nothing leaves the machine. A distinctive typeface is still worth having,
so the three families are downloaded once at build time, subset to latin, and
committed. `font-src 'self'` then permits exactly that and nothing else.

Fonts (all SIL Open Font License 1.1):
  Outfit              display - geometric, warm, modern
  Plus Jakarta Sans   text    - humanist, highly legible at small sizes
  JetBrains Mono      data    - latency figures and code

Run:  .venv\\Scripts\\python.exe scripts\\fetch_fonts.py
"""

from __future__ import annotations

import hashlib
import re
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = REPO_ROOT / "apps" / "web" / "public" / "fonts"
BRAND_DIR = REPO_ROOT / "branding" / "fonts"

# A modern UA is required or Google serves ttf instead of woff2.
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
CSS_URL = (
    "https://fonts.googleapis.com/css2"
    "?family=Outfit:wght@400;500;600;700;800"
    "&family=Plus+Jakarta+Sans:wght@400;500;600;700"
    "&family=JetBrains+Mono:wght@400;500;700"
    "&display=swap"
)

FAMILIES = {
    "Outfit": "outfit",
    "Plus Jakarta Sans": "plus-jakarta-sans",
    "JetBrains Mono": "jetbrains-mono",
}

# Only the latin block; the tagalog text we ship is plain ASCII.
KEEP_SUBSETS = {"latin"}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310
        return r.read().decode("utf-8")


def download(url: str, dest: Path) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:  # noqa: S310
        data = r.read()
    dest.write_bytes(data)
    return len(data)


def main() -> int:
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    BRAND_DIR.mkdir(parents=True, exist_ok=True)

    try:
        css = fetch(CSS_URL)
    except Exception as exc:  # noqa: BLE001
        print(f"could not fetch the font CSS: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    blocks = re.findall(r"/\*\s*([\w\-\[\]]+)\s*\*/\s*(@font-face\s*\{.*?\})", css, re.S)
    written: list[tuple[str, int]] = []

    for subset, block in blocks:
        if subset not in KEEP_SUBSETS:
            continue
        family = re.search(r"font-family:\s*'([^']+)'", block)
        weight = re.search(r"font-weight:\s*(\d+)", block)
        url = re.search(r"url\((https://[^)]+\.woff2)\)", block)
        if not (family and weight and url):
            continue

        raw_family = family.group(1)
        slug = FAMILIES.get(raw_family)
        if slug is None:
            continue

        name = f"{slug}-{weight.group(1)}.woff2"
        dest = FONT_DIR / name
        size = download(url.group(1), dest)
        written.append((name, size))

    if not written:
        print("no latin woff2 files were found in the response", file=sys.stderr)
        return 1

    total = 0
    unique = 0
    for slug in sorted(set(FAMILIES.values())):
        # The v2 API serves one variable woff2 per family and repeats it for every
        # requested weight. Keeping 12 copies of 3 files is 300 kB of dead weight
        # in the repository, so identical payloads collapse to one file and the
        # stylesheet declares a weight range instead.
        seen: dict[str, Path] = {}
        for name, size in written:
            if not name.startswith(slug + "-"):
                continue
            data = (FONT_DIR / name).read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if digest in seen:
                (FONT_DIR / name).unlink()
                continue
            canonical = FONT_DIR / f"{slug}.woff2"
            (FONT_DIR / name).rename(canonical)
            seen[digest] = canonical
        for canonical in seen.values():
            size = canonical.stat().st_size
            total += size
            unique += 1
            print(f"  {canonical.name:34} {size / 1024:6.1f} kB  (variable, weights 100-900)")
    print(f"{unique} files, {total / 1024:.0f} kB total -> {FONT_DIR.relative_to(REPO_ROOT)}")

    # Keep the licence text beside the brand assets, not only in the repo root.
    licence = BRAND_DIR / "OFL.txt"
    if not licence.exists():
        licence.write_text(
            "Outfit, Plus Jakarta Sans and JetBrains Mono are licensed under the\n"
            "SIL Open Font License 1.1. See https://openfontlicense.org/ for the\n"
            "full terms. Self-hosted subsets are committed to apps/web/public/fonts.\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())