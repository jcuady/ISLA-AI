# KALIX brand kit — "red noir"

**Name.** KALIX, derived from *kalasag* (shield).
**Tagline.** *Walang datos na lumalabas.* — "No data ever leaves."

The mark is a **shield enclosing a closed padlock**, cut as negative space. The shield is
protection; the lock is the compliance control. Together they state the product's whole argument
in one shape: the data stays behind the shield because it is physically, not just
administratively, prevented from leaving.

The padlock is *masked out of* the shield rather than drawn on top of it. That is what lets the
mark sit on any background — light, dark, or over the noir grid — without the lock needing its
own fill. It also survives being scaled to a 16 px favicon.

---

## Palette

| Role | Hex | Use |
|---|---|---|
| **Signal Crimson** | `#ef233c` | The brand. Mark, CTAs, active tab, focus ring, brand rules. |
| Crimson Hot | `#ff3b52` | Hover, gradient top-stop, active press |
| Crimson Deep | `#c4102a` | Gradient bottom-stop, pressed states |
| Noir Void | `#000000` | Page base |
| Noir Ink | `#12050a` | Raised surfaces, the crimson-tinted top of the page gradient |
| Paper | `#ffffff` | Primary type, knockout fill inside the mark |

### Semantic status layer

**The brand accent is red, so "BLOCK" can no longer be the only red thing in the product.** The
previous identity reserved red exclusively for BLOCK; adopting red noir retires that rule. Status
is therefore carried by **three independent channels**, never hue alone (WCAG 2.2 SC 1.4.1, use of
colour):

1. **Hue** — the colour below.
2. **Form** — a status surface is a *filled, bordered panel*, never a bare text tint.
3. **Label** — every state ships a distinct **icon** *and* a written verdict string.

Remove all colour and the three states are still distinguishable. That is the test.

| State | Hue | Fill | Icon | Written label |
|---|---|---|---|---|
| SAFE_TO_SEND | `#2fbf87` | translucent green | check in circle | "SAFE TO SEND" |
| REDACT_THEN_SEND | `#f0a92b` | translucent amber | exclamation in circle | "REDACT THEN SEND" |
| BLOCK_ESCALATE | `#ff2d40` | **solid** red wash + 3px left rule | circle-slash | "BLOCK & ESCALATE" |
| Copilot refusal | `#a78bfa` | translucent violet | — | refusal prose |
| Citation chip | `#a78bfa` | translucent violet, 1px border | — | `[DOC §N]` |

**Never recolour a status.** If a status needs a new colour it is a new semantic, and it needs a
new icon and a new label too.

---

## Typography

| Use | Face | Fallback |
|---|---|---|
| Display, wordmark | Manrope | Segoe UI Variable Display, Segoe UI, system-ui |
| UI and body | Inter | Segoe UI Variable Text, Segoe UI, system-ui |
| Code, hashes, citations | JetBrains Mono | SF Mono, Cascadia Mono, Consolas |

**No webfonts are fetched.** Both web surfaces run with `default-src 'none'`, so a Google Fonts
request would be blocked outright — and would break the air-gap claim. The stacks above degrade to
first-class system faces rather than degrading to Times.

---

## Clear space and sizing

**Clear space:** at least **half the shield's width** on all four sides. Nothing enters that zone.

| Use | Minimum size |
|---|---|
| Favicon / app icon | 16 px |
| UI chrome | 24 px |
| Document header | 48 px |
| Full lockup | 96 px |

At 16 px the shackle and body compress; the mark still reads as a shield containing a lock.

---

## Variants

| File | Use |
|---|---|
| `kalix-mark.svg` | **Vector master. Source of truth.** Favicon, UI, print, anything that scales. |
| `kalix-mark-noir.png` | 2238×2689 transparent raster, generated then rekeyed by `scripts/process_logo.py` |
| `kalix-mark-noir-2048.png` | 2048×2048 web asset |
| `wordmark.svg` | Shield + KALIX lockup on noir |

Prefer the SVG in the product. A 2.9 MB PNG in a hero is a performance defect, and the SVG is
infinitely scalable — which is what "ultra HD" actually requires.

### How these were produced

**Disclosed, because the competition requires it and because you should be able to check my work.**

The shield silhouette was generated with an AI image model (`connector__matrix__generate_image`,
4K). That model cannot emit an alpha channel — it painted a *checkerboard* to imitate transparency.
`scripts/process_logo.py` rekeys it for real: alpha is derived from pixel saturation (the shield is
saturated, the checkerboard is neutral), and hue is locked to `#ef233c` while the generator's
luminance shading is preserved. Re-run it and you get byte-identical logic.

The model also left a faint vertical seam and a gradient that drifted off-palette, which is why the
**SVG master is hand-authored** and the raster is kept only as a reference. Both are in the repo.

---

## Misuse

Do not:

- Recolour the mark outside the palette.
- Rotate, skew, or stretch the shield. It is vertically symmetrical by construction.
- Add bevels, glows, or drop shadows to the mark.
- Draw the padlock as a separate element on top of the shield — it is negative space.
- Re-typeset the wordmark in a different face, or alter its letter-spacing.
- Use a status colour for anything other than its status.

---

## Voice

KALIX states what it did and what it did not do.

- **Fails closed and says so.** When evidence is thin it refuses, in Taglish, and names what it
  found and what is missing.
- **Never claims a measurement it has not taken.** The network chip reports an observed socket
  probe, not a hardcoded string. `eval/RESULTS.md` is generated by running the code.
- **Publishes its own weak numbers.** Source attribution sits at 80% against our own 90% bar and is
  printed as the weakest metric on the landing page. A red number we explain is worth more than a
  green one nobody checks.
- **Advisory, never authoritative.** Every answer carries its citation and the footer that it is not
  a substitute for legal advice.
- **Plain, bilingual, warm.** Taglish is the working language of Philippine bank branches; the
  product speaks it rather than translating out of it.

---

## Why the name

*Kalasag* is the Tagalog word for **shield**. KALIX takes that idea and makes it an AI compliance
control: the shield does not guard a perimeter that can be breached by an employee pasting a
customer record into a chat window. It computes the answer **inside the perimeter**, where the data
already is, and therefore cannot leak on the way out.

That is the product in one word.