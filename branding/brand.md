# Isla AI brand kit — "lagoon and abyss"

**Name.** Isla AI.
**Tagline.** *Walang datos na lumalabas.* — "No data ever leaves."

The mark is **one island inside a ring of open water.** The island is the
customer's data and the bank's obligations. The water is everything that would
normally carry it out — a cloud inference endpoint, a SaaS DPA scanner, a
vendor contract. The ring is a boundary with no crossing in it.

This is a better fit than a shield. A shield is a defensive posture that
presupposes a breach is coming. An island is a *placement*: the data is simply
not somewhere that can reach anything. The product does not defend the
perimeter, it never puts the data near one.

---

## Palette

Sampled from the mark itself, not invented. `scripts/process_isla_logo.py`
prints the dominant colours it finds in the artwork on every run:

```
#107080  52.6%      #106090  22.2%      #207080   7.8%
```

| Role | Hex | Use |
|---|---|---|
| **Lagoon** | `#107080` | The brand. Mark, CTAs, active tab, brand rules. |
| Lagoon Bright | `#2fbecc` | Focus rings and hover edges — anything that must hold on a dark surface |
| Lagoon Deep | `#106090` | Second brand stop; the cool end of the mark's gradient |
| **Abyss** | `#010f14` | Page base |
| Abyss Raised | `#04242b` | Panels, sidebar, the top of the page gradient |
| **Sand** | `#f6efe3` | Light surfaces, and the warm counterweight on a light page |
| **Coral** | `#ff5f3d` | The one warm accent. Action only. |

### Why teal, and not the red it replaced

This is a correctness decision, not a taste one.

`BLOCK` has to be red. It is the one status a privacy officer must never
misread as "fine to send," and it is the only solid fill in the product. The
previous identity made crimson the brand — so the product's alarm colour sat at
its centre, and a red brand mark read, to a compliance officer, as urgency
everywhere including where there was none.

Teal and coral-red are far apart on the wheel, and on the lightness axis too.
The brand now occupies the cool end of the spectrum and every warm red in the
interface means something specific.

### Semantic status layer

**Status is carried on four independent channels, never hue alone** (WCAG 2.2
SC 1.4.1, use of colour):

1. **Hue** — the colour below.
2. **Form** — a status surface is a *filled, bordered panel*, never a bare text tint.
3. **Icon** — a distinct glyph per state. `neutral` is `CircleDashed`, not `HelpCircle`.
4. **Label** — every state ships a written verdict string.

The <StatusBadge> primitive is the single place this is implemented. Screen code
must not hand-roll status colours. Remove all colour and the states are still
distinguishable — that is the test, and `status-badge.test.tsx` is what runs it.

| State | Hue | Fill | Icon | Written label |
|---|---|---|---|---|
| SAFE_TO_SEND | `#2fbf87` | translucent green | check in circle | "SAFE TO SEND" |
| REDACT_THEN_SEND | `#f0a92b` | translucent amber | exclamation in circle | "REDACT THEN SEND" |
| BLOCK_ESCALATE | `#ff2d40` | **solid** red wash + 3px left rule | circle-slash | "BLOCK & ESCALATE" |
| Copilot refusal | `#a78bfa` | translucent violet | `CircleDashed` | refusal prose |
| Citation chip | `#a78bfa` | translucent violet, 1px border | — | `[DOC §N]` |

**Never recolour a status.** If a status needs a new colour it is a new
semantic, and it needs a new icon and a new label too.

> These four hues are deliberately **not** brand colours. They are the tested
> semantic layer and they were not touched by the rebrand.

---

## Typography

| Use | Face | Weight | Fallback |
|---|---|---|---|
| Display, wordmark | **Outfit** | 200–800 | Segoe UI Variable Display, Segoe UI, system-ui |
| UI and body | **Plus Jakarta Sans** | 200–800 | Segoe UI Variable Text, Segoe UI, system-ui |
| Data, hashes, citations | **JetBrains Mono** | 100–800 | SF Mono, Cascadia Mono, Consolas |

All three are **SIL Open Font License 1.1** and all three are **self-hosted,
latin-subset, variable woff2 — 89 kB for the set** (`apps/web/public/fonts/`,
fetched by `scripts/fetch_fonts.py`).

**Why not a CDN.** Both web surfaces run `Content-Security-Policy:
default-src 'none'`. A Google Fonts request would be blocked outright — and
attempting it would contradict the product's entire claim, which is that
nothing is fetched externally. If the typeface may not come from a CDN, the
font has to come from the machine.

> **Correction.** The console previously declared `Manrope` and `Inter` in its
> font tokens and loaded *neither* — no `@font-face`, no link. It had been
> silently falling back to Segoe UI the whole time, and looked fine because
> Segoe UI is a perfectly good system face. The tokens are now the families
> that are actually shipped.

---

## Clear space and sizing

**Clear space:** at least **one quarter of the ring's outer diameter** on all
four sides. Nothing enters that zone.

| Use | Minimum size | Which form |
|---|---|---|
| Favicon | 16 px | `favicon.svg` — mark on a solid plate |
| UI chrome | 24 px | vector reduction |
| Document header, social | 48 px | vector reduction |
| Hero, print, slide | 128 px+ | engraved master PNG |

### The two forms of the mark, and why there are two

| File | Form | Use |
|---|---|---|
| `branding/isla-ai-logo.png` | 2813×2812 transparent raster, 273 kB, **84.9%** fully transparent | Hero, print, slide. The engraved topography and the node network are what carry the brand at size. |
| `branding/isla-mark.svg` | Vector, 2 shapes, **1.2 kB** | **Everything on screen.** Favicon, console rail, nav, README. |
| `apps/web/public/isla-mark-180.png` | Raster of the vector reduction, 12 kB | The only place a raster is unavoidable: iOS will not accept an SVG apple-touch-icon. |
| `apps/web/public/favicon.svg` | Vector on a solid plate | 16px |

The master downscales better than you would expect from a 1px engraved hatch.
Measured on the committed file, with the downscaled pixels inspected at 1:1:

| Downscale | File size | Reads as |
|---|---|---|
| 512px | 179 kB | Topography and node network fully legible |
| 256px | 52 kB | Legible; the topography softens |
| 128px | ~13 kB | Island and ring hold; the hatching is gone |
| 64px | 6 kB | Soft. The island loses its edge and the ring thins to a hair |

So the master is usable from about 128px. The vector reduction is preferred
below that, and on screen generally, for three reasons that are not about
quality:

1. **Weight.** A nav lockup costs 52 kB as a 256px raster against 1.2 kB of
   SVG, on every page load, for a 34px image.
2. **The ring cannot survive 16px.** Its stroke is roughly a twentieth of the
   mark's width. That is under a device pixel at favicon size, so it drops out
   and the mark degenerates into a dot. The reduction redraws it at 48 units on
   a 512 viewBox, where it stays solid.
3. **`currentColor`.** The console mark has to inherit the console's foreground.
   An `<img>` cannot, so the component inlines the geometry regardless.

The reduction is a deliberate redrawing, not a trace: same construction (ring +
island), two solid shapes. The island is scaled to **0.72** so a clear channel of
open water surrounds it — at true scale the landmass nearly fills the ring and
the mark tightens into a disc. That is a legibility preference, not a repair.
The engraved node network is dropped because it is noise below about 200px.

> **Earlier claim, retracted.** An intermediate version of this document stated
> that downscaling pushed 63% of pixels into partial alpha and produced grey
> mush at 256px. That measurement was taken while the alpha matte was still
> broken, and it described the bug rather than the artwork. The table above is
> the honest one.

Geometry lives in exactly one place: `ISLAND_CURVES` and `RING` in
`scripts/process_isla_logo.py`. That script emits `isla-mark.svg`;
`isla-mark.test.tsx` asserts the copy inlined in the React component (which
needs `currentColor`, so it cannot be an `<img>`) still matches. A brand that
has quietly grown two logos is a failure mode worth a test.

### How these were produced

**Disclosed, because the competition rules require it and because you should be
able to check the work.**

The mark and the hero photograph were generated with an AI image model
(`connector__matrix__generate_image`, 4K) from the prompts recorded in
`branding/asset-manifest.json`. The model emits no alpha channel — it paints a
*checkerboard* to imitate transparency. `scripts/process_isla_logo.py` rekeys it
for real, and the raw 4K sources are gitignored while the processed masters are
tracked.

Two failures in that script were worth the debugging, and both are documented
in the source because both produce files that look fine:

- **The key was a border-seeded flood fill.** The ring completely encloses the
  interior, so no checkerboard tile inside it was reachable from the border and
  all of them survived as opaque. The output looked like a plausible logo with a
  white disc sitting in the middle of it. A *global* key — bright **and**
  unsaturated — is the correct rule here, and the saturation guard is what
  protects the pale aqua in the ring.
- **The edge feather summed instead of averaging.** A cumsum difference gives
  the sum over the window; cast straight to `uint8` it wraps modulo 256. A fully
  opaque 3×3 neighbourhood sums to 2295 and lands on 247, while a transparent one
  lands on 0 by luck of alignment. This punched the island out of the mark.

Compression, measured rather than guessed:

| Strategy | Size |
|---|---|
| raw 32-bit RGBA | 5581 kB |
| quantise RGB only (64–256 colours) | 4258–4854 kB |
| quantise alpha to 4/5/6 bits | 5145–5349 kB |
| **FASTOCTREE over RGBA, 128 colours** | **258–273 kB** |

Quantising colour alone barely helps, because the file is not big because of the
colours — it is big because alpha varies per pixel. FASTOCTREE builds one palette
across all four channels jointly, so the few distinct *combinations* in this
artwork collapse instead of the four channels independently.

---

## Misuse

Do not:

- Recolour the mark outside the lagoon ramp.
- Use the engraved master below ~128px. Use the vector reduction instead.
- Fill in the island so it touches the ring. The water is the point.
- Add bevels, glows, or drop shadows to the mark.
- Re-typeset the wordmark in a different face, or alter its letter-spacing.
- **Use a status colour for anything other than its status.**
- Load the typefaces from a CDN.

---

## Voice

Isla AI states what it did and what it did not do.

- **Fails closed and says so.** When evidence is thin it refuses, in Taglish, and
  names what it found and what is missing.
- **Never claims a measurement it has not taken.** The network chip reports an
  observed socket probe, not a hardcoded string. `eval/RESULTS.md` is generated
  by running the code.
- **Publishes its own weak numbers.** Source attribution sits at 80% against our
  own 90% bar and is printed as the weakest metric on the landing page. A red
  number we explain is worth more than a green one nobody checks.
- **Admits when a component did not earn its place.** `eval/RESULTS_ABLATION.md`
  reports that published retrieval metrics are unchanged with the neural leg
  removed. That is not hidden.
- **Advisory, never authoritative.** Every answer carries its citation and the
  footer that it is not a substitute for legal advice.
- **Plain, bilingual, warm.** Taglish is the working language of Philippine bank
  branches; the product speaks it rather than translating out of it.

---

## Why the name

*Isla* — Spanish, and everyday Filipino — is a small outlying island: land that
is surrounded by water rather than bounded by it. English *isle* says the same
thing, and the two words have always traded with each other in Philippine
English.

It is a better name for this product than a defensive one would be. A shield or
a vault describes what happens when something goes wrong. An island describes
where the data *is*: somewhere the data does not travel from. The metaphor also
carries the local-AI argument without a word of explanation, which is the
whole reason it was chosen.

And the metaphor is falsifiable. An island is isolated by geography, not by
policy — which is exactly why the product ships an air-gap probe, a ledger, and
a Content-Security-Policy that forbids off-origin requests. The name makes a
promise the code is built to let a judge break.

---

## What ISLA stands for

**ISLA — In-Situ Local AI.**

Always deployed with the expansion visible at least once nearby. A backronym that
has to be guessed teaches a judge nothing.

### Why not "Information Security Local AI"

That was the first candidate and it is a weaker expansion for three reasons worth
recording, because the reasons generalise:

1. **It miscategorises the product.** Information security is vulnerability
   management, identity, incident response and network defence. Isla AI does none
   of those. In a bank these sit with different people — the CISO rather than the
   data privacy officer — and the NPC obligations this product answers to sit with
   the DPO. An acronym that names the wrong department is a small credibility tax.
2. **It overclaims breadth.** "Information Security" is a category thousands of
   products claim. It carries no information.
3. **It undersells the mechanism.** What is actually distinctive is *where the
   computation happens*, not the subject domain.

### Why "In-Situ Local AI" instead

*In situ* is the term of art for data being in its place of origin, and it is
literally the product's argument: the inference runs on hardware where the record
already exists. It also bridges the two halves of the brand, which is what made it
worth choosing.

> The island is the metaphor. *In situ* is the engineering term for the same thing.

A judge who asks "would this lose functionality without local AI?" has the answer
in the four letters before they ask it.

**Deployment rule.** Wordmark always reads `ISLA AI`. The expansion appears once
in the first viewport, once in the footer, and once in the README header. It is
never set in place of the wordmark, because `ISLA` alone is the brand and
`In-Situ Local AI` is the explanation.

**Swapping it is a five-minute change.** The string appears in
`branding/brand.md`, `apps/web/public/landing.html` (three places),
`apps/web/index.html`, `README.md`, `docs/SUBMISSION.md`, and the `/api/health`
payload. No code depends on it.
