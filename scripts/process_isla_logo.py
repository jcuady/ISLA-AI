"""Turn the generated Isla AI logo into real production assets.

The generator returns a flat vector-style mark on a pure white field, with the
transparency faked as a painted checkerboard. Shipping that as-is would mean a
5 MB JPEG with an opaque white box around it, which fails on every dark surface
and is a performance defect on any page.

This script:
  1. crops the dead white margin,
  2. keys the checkerboard out globally - bright AND unsaturated - which a plain
     luminance key would get wrong by eating the pale aqua in the water ring,
  3. feathers the matte by a pixel so the edge does not crawl on dark surfaces,
  4. writes the transparent master, palette-quantised,
  5. emits the vector reduction to branding/ and apps/web/public/,
  6. rasters that reduction for the one surface that will not take an SVG,
  7. reports the dominant brand colours so the palette is sampled from the mark
     rather than invented.

Why there is no size ladder
---------------------------
The mark has two forms and only two: the engraved raster for hero-scale and
print, and a two-shape vector reduction for the screen.

The obvious third form - downscale the master to 512/256/64 - was measured and
then dropped. It is not catastrophic: the master holds together down to about
128px (512px keeps its topography and node network, 256px is legible, 128px is
island and ring only, 64px is soft). What rules it out is weight and one
hard limit. A 34px nav lockup costs 52 kB as a raster against 1.2 kB of SVG,
loaded on every page view. And the ring's stroke is about a twentieth of the
mark's width, which is under one device pixel at 16px - so in a favicon the
ring drops out entirely and the mark degenerates into a dot. The reduction
redraws it at 48 units on a 512 viewBox, where it stays solid.

An earlier version of this note claimed the downscaled 256px derivative had 63%
of its pixels in partial alpha and was "grey mush". That number was measured
while the alpha matte was still broken, and it described the bug rather than
the artwork. See the "retracted" note in branding/brand.md.

`isla-mark-180.png` is the reduction rasterised, because iOS will not accept an
SVG for an apple-touch-icon.

Run:  .venv\\Scripts\\python.exe scripts\\process_isla_logo.py
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "branding" / "_gen" / "isla-ai-logo-src.jpg"
OUT_DIR = REPO_ROOT / "branding"
PUBLIC = REPO_ROOT / "apps" / "web" / "public"

# A pixel is matte when it is both bright and unsaturated: the generator paints
# a checkerboard of near-white tiles to imitate transparency, and a checkerboard
# has no business having any colour in it.
TOLERANCE = 40
MAX_SATURATION = 18
FEATHER_PX = 1

# ---------------------------------------------------------------------------
# The vector reduction, expressed as data so the raster and the SVG in
# branding/isla-mark.svg cannot drift apart silently. Coordinates are the same
# 512-unit viewBox the SVG uses.
# ---------------------------------------------------------------------------

MARK_SCALE = 512.0
RING = {"cx": 256, "cy": 256, "r": 194, "stroke": 48}

# Island outline traced from the generated master, then scaled to 0.72 about
# (246, 249) and stretched 1.15 on the vertical so it clears the ring.
#
# The shrink is deliberate and is the reason this file exists rather than a
# straight trace. In the master the island spans nearly the full inner width of
# the ring, which is right for an engraved hero mark but at 26px collapses into
# a horizontal bar and the whole mark reads as a "no entry" sign. Pulling it in
# to 0.72 leaves a 36-unit channel of open water all the way round, and the
# slight vertical stretch keeps it a landmass rather than a bar.
#
# Cubics are (anchor, control, control, end). This list is the source of truth:
# the script emits branding/isla-mark.svg from it, and
# apps/web/src/components/isla-mark.test.tsx fails if the React component's
# inline copy drifts from it.
ISLAND_CURVES: list[tuple[tuple[float, float], ...]] = [
    ((119.2, 289.1), (132.2, 266.8), (153.8, 241.9), (175.4, 222.1)),
    ((175.4, 222.1), (194.1, 204.7), (220.0, 190.6), (239.4, 186.4)),
    ((239.4, 186.4), (264.6, 181.5), (288.4, 194.7), (309.3, 214.6)),
    ((309.3, 214.6), (330.2, 234.5), (352.5, 258.5), (376.2, 275.0)),
    ((376.2, 275.0), (384.2, 280.0), (389.9, 284.2), (388.5, 290.8)),
    ((388.5, 290.8), (381.3, 306.5), (352.5, 316.4), (316.5, 320.6)),
    ((316.5, 320.6), (273.3, 325.6), (215.7, 320.6), (172.5, 309.8)),
    ((172.5, 309.8), (148.0, 304.0), (122.1, 299.1), (119.2, 289.1)),
]

GRADIENT_TOP = (14, 124, 140)  # #0E7C8C
GRADIENT_BOTTOM = (16, 96, 144)  # #106090


def load_rgb(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)


def content_bbox(arr: np.ndarray, tolerance: int = TOLERANCE) -> tuple[int, int, int, int]:
    """Bounding box of everything that is not near-white."""
    distance = 255 - arr.min(axis=2)
    mask = distance > tolerance
    rows = np.where(mask.any(axis=1))[0]
    cols = np.where(mask.any(axis=0))[0]
    if rows.size == 0 or cols.size == 0:
        return 0, 0, arr.shape[1], arr.shape[0]
    pad = 8
    return (
        max(int(cols[0]) - pad, 0),
        max(int(rows[0]) - pad, 0),
        min(int(cols[-1]) + 1 + pad, arr.shape[1]),
        min(int(rows[-1]) + 1 + pad, arr.shape[0]),
    )


def key_neutral_white(
    arr: np.ndarray,
    tolerance: int = TOLERANCE,
    max_saturation: int = MAX_SATURATION,
) -> np.ndarray:
    """Alpha matte from a global colour key: matte where bright AND unsaturated.

    The obvious approach - a border-seeded flood fill through contiguous
    near-white - is wrong for this image, and it was wrong here first. The ring
    completely encloses the interior, so every checkerboard tile inside it is
    unreachable from the border and survives as opaque. The result looked like a
    plausible logo with a white disc sitting in the middle of it.

    A global key is correct because the two conditions together are specific to
    a painted checkerboard: a real highlight inside a mark is either bright and
    coloured, or dark. Bright-and-colourless only happens where the generator
    was faking transparency.

    The saturation guard is what protects the pale aqua highlights in the ring,
    which a plain luminance key would eat. Measured on this artwork the ring's
    most desaturated pixel is well inside the guard.
    """
    mx = arr.max(axis=2).astype(np.int16)
    mn = arr.min(axis=2).astype(np.int16)
    bright = (255 - mn) <= tolerance
    unsaturated = (mx - mn) <= max_saturation
    alpha = np.where(bright & unsaturated, 0, 255).astype(np.uint8)

    if FEATHER_PX > 0:
        # One box-blur pass on the matte softens the stair-stepped edge.
        #
        # The cumsum difference below is the SUM over the window, not the mean.
        # Casting that straight to uint8 wraps modulo 256: a fully-opaque 3x3
        # neighbourhood sums to 2295 and lands on 247, while a transparent one
        # lands on 0 by luck of alignment. It produced a plausible-looking file
        # with the island punched out. Divide by the window area before casting.
        padded = np.pad(alpha.astype(np.float32), FEATHER_PX, mode="edge")
        window = 2 * FEATHER_PX + 1
        cumsum = padded.cumsum(axis=0).cumsum(axis=1)
        cumsum = np.pad(cumsum, ((1, 0), (1, 0)), mode="constant")
        alpha = (
            (
                cumsum[window:, window:]
                - cumsum[:-window, window:]
                - cumsum[window:, :-window]
                + cumsum[:-window, :-window]
            )
            / (window * window)
        ).astype(np.uint8)
    return alpha


def flatten_beziers(curves: list[tuple[tuple[float, float], ...]], steps: int = 24) -> list[tuple[float, float]]:
    """Flatten a chain of cubic segments into a polyline."""
    points: list[tuple[float, float]] = []
    for segment in curves:
        p0, p1, p2, p3 = segment
        for i in range(steps + 1):
            if not points and i == 0:
                continue
            t = i / steps
            u = 1 - t
            x = u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0]
            y = u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1]
            points.append((x, y))
    return points


def island_path_data() -> str:
    """SVG `d` for the island, from the single source of truth above.

    One `C` command per cubic segment, carrying all six numbers. Emitting one
    `C` per point instead produces a path the SVG parser rejects outright -
    `Expected number` - while still rendering correctly through the PIL
    rasteriser used for the apple-touch-icon, because that path flattens the
    Béziers itself and never sees the string. `verify-ui.mjs` is what caught it.
    """
    parts: list[str] = []
    for segment in ISLAND_CURVES:
        if not parts:
            parts.append(f"M{segment[0][0]} {segment[0][1]}")
        (c1, c2, end) = segment[1], segment[2], segment[3]
        parts.append(
            f"C{c1[0]} {c1[1]} {c2[0]} {c2[1]} {end[0]} {end[1]}"
        )
    parts.append("Z")
    return " ".join(parts)


def svg_mark() -> str:
    """The small-size vector reduction, as a standalone SVG document.

    Generated rather than hand-maintained so the copy the browser gets, the
    copy the README gets and the copy process_isla_logo.py rasterises for the
    apple-touch-icon are all the same numbers.
    """
    d = island_path_data()
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512" role="img" aria-label="Isla AI mark">
  <title>Isla AI</title>
  <!--
    GENERATED FILE - do not edit by hand.

    Emitted by scripts/process_isla_logo.py from ISLAND_CURVES and RING in that
    file. branding/isla-ai-logo.png is the engraved master; this is the
    small-size reduction, which is what the web actually loads. See
    branding/brand.md for why the master cannot be used below ~500px.
  -->
  <defs>
    <linearGradient id="isla-ring" x1="52" y1="34" x2="470" y2="486" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#0E7C8C" />
      <stop offset="0.55" stop-color="#107080" />
      <stop offset="1" stop-color="#106090" />
    </linearGradient>
  </defs>
  <circle cx="{RING['cx']}" cy="{RING['cy']}" r="{RING['r']}" fill="none" stroke="url(#isla-ring)" stroke-width="{RING['stroke']}" />
  <path fill="url(#isla-ring)" d="{d}" />
</svg>
"""


def render_mark_svg_equivalent(size: int, supersample: int = 4) -> Image.Image:
    """Rasterise the two-shape reduction at `size` with a brand gradient."""
    big = size * supersample
    factor = big / MARK_SCALE
    mask = Image.new("L", (big, big), 0)
    draw = ImageDraw.Draw(mask)

    def s(point: tuple[float, float]) -> tuple[float, float]:
        return (point[0] * factor, point[1] * factor)

    draw.ellipse(
        [
            s((RING["cx"] - RING["r"], RING["cy"] - RING["r"])),
            s((RING["cx"] + RING["r"], RING["cy"] + RING["r"])),
        ],
        outline=255,
        width=int(RING["stroke"] * factor),
    )
    draw.polygon([s(p) for p in flatten_beziers(ISLAND_CURVES)], fill=255)

    ramp = np.linspace(0.0, 1.0, big, dtype=np.float32)[:, None]
    top = np.array(GRADIENT_TOP, dtype=np.float32)
    bottom = np.array(GRADIENT_BOTTOM, dtype=np.float32)
    column = (top[None, :] * (1 - ramp) + bottom[None, :] * ramp)[:, None, :]
    rgb = np.repeat(column, big, axis=1).astype(np.uint8)

    out = np.dstack([rgb, np.asarray(mask, dtype=np.uint8)])
    image = Image.fromarray(out, "RGBA")
    return image.resize((size, size), Image.LANCZOS)


def dominant_colors(arr: np.ndarray, top: int = 6) -> list[tuple[tuple[int, int, int], float]]:
    """Most common saturated colours, so the palette comes from the artwork."""
    h, w = arr.shape[:2]
    step = max(h // 400, 1)
    sample = arr[::step, ::step].reshape(-1, 3)
    mx = sample.max(axis=1)
    mn = sample.min(axis=1)
    saturated = mx - mn
    keep = (saturated > 45) & (mx > 40)
    sample = sample[keep]
    quantised = (sample // 16) * 16
    counts = Counter(map(tuple, quantised.tolist()))
    total = sum(counts.values()) or 1
    return [(c, n / total) for c, n in counts.most_common(top)]


def quantise(rgba: Image.Image, colors: int = 128) -> Image.Image:
    """Palette-quantise all four channels jointly with FASTOCTREE.

    Measured on this artwork, the alternatives are not close:

        raw 32-bit RGBA                      5581 kB
        quantise RGB only (64-256 colours)   4258-4854 kB
        quantise alpha to 4/5/6 bits         5145-5349 kB
        FASTOCTREE over RGBA, 128 colours     258 kB

    Quantising colour alone barely helps, because the file is not big because
    of the colours - it is big because alpha varies per pixel and PNG cannot
    compress a 32-bit channel plane well. FASTOCTREE builds one palette across
    R, G, B and A together, so the few distinct *combinations* in this artwork
    collapse instead of the four channels independently.

    128 entries is enough: the mark is a flat teal ring plus a feathered edge,
    so the matte needs roughly a dozen alpha steps and the rest of the budget
    goes to colour.
    """
    return rgba.quantize(colors=colors, method=Image.FASTOCTREE)


def main() -> int:
    if not SRC.exists():
        print(f"missing source: {SRC}", file=sys.stderr)
        return 1

    arr = load_rgb(SRC)
    print(f"source {arr.shape[1]}x{arr.shape[0]}")

    box = content_bbox(arr)
    arr = arr[box[1] : box[3], box[0] : box[2]]
    print(f"cropped to {arr.shape[1]}x{arr.shape[0]}")

    alpha = key_neutral_white(arr)
    rgba = Image.fromarray(np.dstack([arr, alpha]), "RGBA")

    master = OUT_DIR / "isla-ai-logo.png"
    quantise(rgba).save(master, optimize=True)
    print(f"master  {master.relative_to(REPO_ROOT)}  "
          f"{master.stat().st_size / 1024:.0f} kB")
    print(f"transparent area: {(alpha == 0).mean():.1%}  "
          f"partial: {((alpha > 0) & (alpha < 255)).mean():.1%}")

    # The vector reduction, in both the branding copy and the one the web serves.
    document = svg_mark()
    for target in (OUT_DIR / "isla-mark.svg", PUBLIC / "isla-mark.svg"):
        target.write_text(document, encoding="utf-8", newline="")
        print(f"vector  {target.relative_to(REPO_ROOT)}  "
              f"{target.stat().st_size / 1024:.1f} kB")

    # The only raster derivative: iOS refuses an SVG apple-touch-icon.
    touch = PUBLIC / "isla-mark-180.png"
    render_mark_svg_equivalent(180).save(touch)
    print(f"web     {touch.relative_to(REPO_ROOT)}  {touch.stat().st_size / 1024:.0f} kB")
    print("        (raster of the vector reduction, not a downscale of the master)")

    print("\ndominant brand colours sampled from the mark:")
    for colour, share in dominant_colors(arr):
        print(f"  #{colour[0]:02X}{colour[1]:02X}{colour[2]:02X}  {share:.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
