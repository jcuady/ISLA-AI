# Isla AI — 60-second demo film

A 60.00s 1920×1080 product film. Every frame showing the product is the **real
application performing real actions** against the real API — captured with
Playwright, never mocked, never rendered.

Regenerate end to end:

```powershell
# the app must be running
.venv\Scripts\python.exe scripts\preflight.py

node apps\web\video\record.mjs   # record the shots (~90s)
node apps\web\video\build.mjs     # composite, mix audio, encode
```

## How the 60 seconds is spent

| In | Out | Length | Source |
|---|---|---|---|
| 0.0s | 5.0s | 5.0s | **MiniMax-H3** generated hero |
| 5.0s | 12.0s | 7.0s | CSS motion graphic — the problem |
| 12.0s | 26.0s | 14.0s | **real product** — Egress Guard |
| 26.0s | 39.0s | 13.0s | **real product** — Fraud & AML |
| 39.0s | 49.0s | 10.0s | **real product** — DPA Copilot |
| 49.0s | 56.0s | 7.0s | CSS motion graphic — measured figures |
| 56.0s | 60.0s | 4.0s | **MiniMax-H3** generated close |

Audio is a separate graph: ten TTS lines at fixed offsets, over a generated
music bed ducked by `sidechaincompress` so the level follows the narration
rather than hand-tuned gains.

## Two rules this build enforces

**The generated clips never touch the product.** MiniMax-H3 is used only for
abstract brand atmosphere. A generated frame of a fake dashboard would be the
single most damaging thing in the repo for a project whose entire claim is that
it never invents a legal citation.

**Every click is verified before the frame is kept.** `clickOk()` clicks, then
polls the rendered panel text until the expected result is actually on screen,
and throws otherwise. Without it this build produced three perfectly
plausible-looking shots of the product sitting in its empty state — a failed
click raises no exception in Playwright, it just quietly does nothing.

## Traps worth keeping

- `brand.css` must **never** be injected into the running app. It defines
  `.grid` as a decorative background, and Tailwind's layout utility is also
  `.grid`; injecting it absolutely positioned every grid container and left an
  invisible full-screen layer swallowing the clicks. Only `OVERLAY_CSS` in
  `record.mjs` goes over product footage, and everything in it is namespaced
  `ovl`.
- `Scan & redact` is `disabled={!text.trim()}`. The sample loads asynchronously
  after mount, so clicking before it lands is a silent no-op. `waitForSample()`
  blocks on real textarea content first.
- Assertions must run against `main`'s `innerText`, and `innerText` applies
  `text-transform` — a label styled uppercase arrives as `"ENTITIES"`. Every
  expectation is case-insensitive.
- `page.waitForSelector()` takes a selector string and throws immediately on a
  bare RegExp. Poll `innerText` instead.