"""Turn the generated logo into real, brand-exact transparent assets.

The image generator paints a checkerboard to imitate transparency rather than
producing an alpha channel, and its crimson drifts from the palette. This script
rekeys both:

  1. Alpha is derived from saturation - the shield is strongly saturated, the
     checkerboard is neutral grey, so the boundary falls out cleanly and the
     padlock knocked out of the shield becomes genuinely transparent.
  2. Hue is locked to the brand crimson #ef233c while the generator's subtle
     luminance shading is preserved, so the mark reads as one flat brand colour
     rather than a generic red.

Outputs a 4096 master and a 2048 web asset, both with straight (unpremultiplied)
alpha.

    .venv\\Scripts\\python.exe scripts\\process_logo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

REPO_ROOT = Path(__file__).resolve().parent.parent
BRANDING = REPO_ROOT / "branding"

SOURCE = BRANDING / "kalix-mark-noir-b.jpg"
MASTER = BRANDING / "kalix-mark-noir.png"
WEB = BRANDING / "kalix-mark-noir-2048.png"

BRAND_RGB = np.array([0xEF, 0x23, 0x3C], dtype=np.float64)  # #ef233c

# Saturation window. Checkerboard sits below LOW; the shield body sits above HIGH.
LOW, HIGH = 0.10, 0.30


def saturation(rgb: np.ndarray) -> np.ndarray:
    """HSV-style saturation in [0, 1] from a float RGB array."""
    mx = rgb.max(axis=-1)
    mn = rgb.min(axis=-1)
    denom = np.where(mx == 0, 1.0, mx)
    return (mx - mn) / denom


def luminance(rgb: np.ndarray) -> np.ndarray:
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def main() -> int:
    if not SOURCE.exists():
        print(f"missing {SOURCE}")
        return 1

    img = Image.open(SOURCE).convert("RGB")
    rgb = np.asarray(img, dtype=np.float64)

    sat = saturation(rgb)
    alpha = np.clip((sat - LOW) / (HIGH - LOW), 0.0, 1.0)

    # A touch of blur removes JPEG ringing from the key edge without visibly
    # softening the mark at 4096px.
    a8 = (alpha * 255.0).astype(np.uint8)
    a8 = np.asarray(
        Image.fromarray(a8, mode="L").filter(ImageFilter.GaussianBlur(radius=1.2)),
        dtype=np.float64,
    ) / 255.0
    a8 = np.clip((a8 - 0.35) / 0.5, 0.0, 1.0)  # crisp the ramp back up

    # Lock hue to the brand crimson, keep the generator's luminance shading.
    lum = luminance(rgb)
    brand_lum = float(luminance(BRAND_RGB))
    ratio = np.clip(lum / max(brand_lum, 1e-6), 0.0, 1.35)[:, :, None]
    recoloured = np.clip(BRAND_RGB[None, None, :] * ratio, 0, 255)

    # Semi-transparent pixels take the brand colour outright; blending in the
    # neutral checkerboard there would leave a grey halo on a dark page.
    edge = (a8 > 0.0) & (a8 < 0.97)
    recoloured[edge] = BRAND_RGB[None, None, :]

    out = np.dstack([recoloured, a8[:, :, None] * 255.0]).astype(np.uint8)

    # Crop to the mark plus clear space of half the shield width (brand rule).
    ys, xs = np.where(a8 > 0.02)
    if len(xs) == 0:
        print("key failed: nothing above the saturation threshold")
        return 1
    pad = int((xs.max() - xs.min()) * 0.12)
    box = (
        max(0, int(xs.min()) - pad),
        max(0, int(ys.min()) - pad),
        min(out.shape[1], int(xs.max()) + pad + 1),
        min(out.shape[0], int(ys.max()) + pad + 1),
    )
    cropped = Image.fromarray(out, mode="RGBA").crop(box)

    coverage = float((np.asarray(cropped.split()[-1], dtype=np.float64) > 128).mean())
    cropped.save(MASTER)
    cropped.resize((2048, 2048), Image.LANCZOS).save(WEB)

    print(f"mark:      {cropped.size[0]}x{cropped.size[1]}  -> {MASTER.name}")
    print(f"web asset: 2048x2048        -> {WEB.name}")
    print(f"opaque coverage: {coverage * 100:.1f}% of the cropped canvas")
    print(f"brand colour locked to #{int(BRAND_RGB[0]):02X}{int(BRAND_RGB[1]):02X}"
          f"{int(BRAND_RGB[2]):02X}")
    return 0


if __name__ == "__main__":
    sys.exit(main())