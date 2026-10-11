/**
 * Isla AI — 60-second demo film.
 *
 * Every product shot is the real application performing real actions against
 * the real API. Nothing is mocked, and no frame of product UI is synthesised.
 * The motion-graphic layers are CSS injected into the live page, so they
 * animate over genuine footage rather than replacing it.
 *
 * Scenes run in wall-clock time because Playwright records in real time; the
 * shot list below is the edit. Durations total exactly 60.0s.
 *
 *   node apps/web/video/record.mjs
 */
import { chromium } from 'playwright';
import { readFileSync, mkdirSync, rmSync, readdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const SHOTS = resolve(HERE, 'shots');
const BASE = 'http://127.0.0.1:8765';
const W = 1920;
const H = 1080;

const css = readFileSync(resolve(HERE, 'brand.css'), 'utf8');
const wait = (page, ms) => page.waitForTimeout(ms);

/** Build a motion-graphic frame (grid + glows) with `inner` as the content. */
const stage = (inner, extra = '') => `<!doctype html><html><head><meta charset="utf-8">
<style>${css}${extra}</style></head><body>
<div class="stage">
  <div class="grid"></div>
  <div class="glow glow--a"></div>
  <div class="glow glow--b"></div>
  ${inner}
</div></body></html>`;

/** Inject the overlay chrome over live product footage. */
/**
 * Overlay styles for real product footage — and ONLY these.
 *
 * brand.css must never be injected into the running app. It defines `.grid`
 * as a decorative background, and Tailwind's layout utility is also `.grid`:
 * injecting it made every grid container position:absolute inset:0, which
 * destroyed the layout and left an invisible full-screen layer swallowing the
 * clicks. Three shots recorded the product sitting in its empty state and
 * looked, on a quick skim, completely fine.
 *
 * The rule for this file: anything drawn over the product is namespaced under
 * `ovl` and nothing else.
 */
const OVERLAY_CSS = `
.ovl { position: fixed; inset: 0; pointer-events: none; z-index: 2147483000; }
.ovl__bar { position: absolute; top: 0; left: 0; height: 5px; width: 0;
  background: linear-gradient(90deg, #16A3B8, #2FBECC); }
/* Both the tag and the callout are offset past the console's 280px sidebar and
   below its header. Left at x=64 they sat on top of the sidebar's corpus and
   network readouts, which is unreadable and looks like a bug. */
.ovl__tag { position: absolute; top: 96px; left: 328px;
  font-family: "JetBrains Mono", Consolas, monospace; font-size: 20px;
  letter-spacing: 0.3em; text-transform: uppercase; color: #2FBECC;
  opacity: 0; transition: opacity 0.45s cubic-bezier(.16,1,.3,1);
  text-shadow: 0 2px 18px rgba(1,15,20,.95); }
.ovl__note { position: absolute; bottom: 70px; left: 320px; right: 80px;
  display: flex; align-items: baseline; gap: 22px; opacity: 0;
  transform: translateY(26px); padding: 18px 28px 20px;
  border-left: 3px solid #2FBECC; border-radius: 4px;
  background: linear-gradient(90deg, rgba(1,15,20,.94), rgba(1,15,20,.72) 62%, rgba(1,15,20,0));
  transition: opacity .55s cubic-bezier(.16,1,.3,1), transform .55s cubic-bezier(.16,1,.3,1); }
.ovl__note.on { opacity: 1; transform: none; }
.ovl__note b { font-size: 52px; font-weight: 800; letter-spacing: -0.025em;
  color: #fff; white-space: nowrap; }
.ovl__note span { font-size: 30px; font-weight: 600; color: #fff; }
.ovl__note i { font-style: normal; font-family: "JetBrains Mono", Consolas, monospace;
  font-size: 21px; letter-spacing: 0.16em; color: #7C979F; text-transform: uppercase;
  margin-left: auto; white-space: nowrap; }
.ovl__note b.stop { color: #ff6b7d; }
.ovl__note b.warn { color: #f0a92b; }
.ovl__note b.good { color: #2fbf87; }
.ovl__note b.accent { color: #2FBECC; }
`;

/** Inject the overlay chrome over live product footage. */
async function mountOverlay(page, tag) {
  await page.addStyleTag({ content: OVERLAY_CSS });
  await page.evaluate((label) => {
    const el = document.createElement('div');
    el.className = 'ovl';
    el.innerHTML = `
      <div class="ovl__bar"></div>
      <div class="ovl__tag">${label}</div>
      <div class="ovl__note"><b></b><span></span><i></i></div>`;
    document.body.appendChild(el);
    window.__ovl = {
      bar: el.querySelector('.ovl__bar'),
      tag: el.querySelector('.ovl__tag'),
      note: el.querySelector('.ovl__note'),
      b: el.querySelector('.ovl__note b'),
      s: el.querySelector('.ovl__note span'),
      i: el.querySelector('.ovl__note i'),
    };
    setTimeout(() => { window.__ovl.tag.style.opacity = '1'; }, 120);
  }, tag);
}

/** Show a callout over the footage. */
const say = (page, big, text, kicker, tone = '') =>
  page.evaluate(([b, s, k, t]) => {
    const o = window.__ovl;
    o.b.textContent = b;
    o.s.textContent = s;
    o.i.textContent = k;
    o.b.className = t;
    o.note.classList.add('on');
  }, [big, text, kicker, tone]);

const hush = (page) => page.evaluate(() => window.__ovl.note.classList.remove('on'));

/**
 * Click and then PROVE it landed.
 *
 * The console's left sidebar sits above the content column, so a plain click
 * can be intercepted and Playwright will retry it for thirty seconds without
 * ever pressing the thing. One copilot shot recorded 32.8s of nothing because
 * of exactly that. `force` avoids the interception, and the expectation turns a
 * silent failure into a thrown error - a video that quietly fails to click
 * would show a product doing something it never did.
 */
/**
 * Poll the rendered panel text until `expect` matches.
 *
 * Deliberately not page.getByText(): that resolves against the DOM, where a
 * hidden element can hold the text and make `state: 'visible'` time out even
 * though the screen plainly shows it. This reads what a viewer would read.
 *
 * Note innerText applies text-transform, so a CSS-uppercased label arrives as
 * "ENTITIES", not "Entities" - every expectation here is case-insensitive.
 */
async function waitText(page, expect, timeout = 12000) {
  const deadline = Date.now() + timeout;
  let last = '';
  let reads = 0;
  while (Date.now() < deadline) {
    const seen = await page.locator('main').innerText().catch((e) => `<<${e.name}>>`);
    last = seen;
    reads += 1;
    if (expect.test(seen)) return true;
    await page.waitForTimeout(250);
  }
  console.log(`      [debug] no match for ${expect}; last ${last.length} chars`);
  return false;
}

async function clickOk(page, locator, expect, label) {
  await locator.click({ force: true });
  if (expect && !(await waitText(page, expect))) {
    throw new Error(`${label}: clicked, but ${expect} never appeared on screen`);
  }
}

/**
 * The Egress Guard loads its sample asynchronously after mount, and
 * "Scan & redact" is disabled while the textarea is empty. Clicking before the
 * sample lands is a silent no-op - React still runs the handler, which returns
 * early on empty input - so the recording would show a guard that never scanned
 * anything. Wait for real content before pressing anything.
 */
async function waitForSample(page) {
  const box = page.locator('textarea').first();
  await box.waitFor({ state: 'visible', timeout: 15000 });
  const deadline = Date.now() + 15000;
  while (Date.now() < deadline) {
    const v = await box.inputValue().catch(() => '');
    if (v.trim().length > 40) return v.length;
    await page.waitForTimeout(200);
  }
  throw new Error('egress: the demo sample never loaded into the textarea');
}

/** Progress bar across the shot, matching the scene duration. */
const progress = (page, ms) => page.evaluate((d) => {
  const t0 = performance.now();
  (function tick() {
    const p = Math.min(1, (performance.now() - t0) / d);
    window.__ovl.bar.style.width = (p * 100).toFixed(2) + '%';
    if (p < 1) requestAnimationFrame(tick);
  })();
}, ms);

// ── the edit ────────────────────────────────────────────────────────────────

const SCENES = [
  {
    name: '01-title',
    ms: 5000,
    async run(page) {
      await page.setContent(stage(`
        <div class="stack">
          <div class="eyebrow">AppBuilders PH 2026 · Local AI · Finance</div>
          <div class="h1"><span class="line"><span>ISLA</span></span>
                         <span class="line"><span class="accent">AI</span></span></div>
          <div class="rule"></div>
          <div class="fade fade--1" style="font-family:var(--font-mono);font-size:26px;letter-spacing:.24em;color:var(--text-3)">IN-SITU LOCAL AI</div>
        </div>`));
      await wait(page, 3400);
      await page.setContent(stage(`
        <div class="stack">
          <div class="fade" style="font-size:52px;font-weight:600">Walang datos na lumalabas.</div>
          <div class="fade fade--1" style="font-size:30px;color:var(--text-2)">No data leaves.</div>
        </div>`));
      await wait(page, 1600);
    },
  },

  {
    name: '02-problem',
    ms: 7000,
    async run(page) {
      await page.setContent(stage(`
        <div class="stack--left" style="display:flex;flex-direction:column;gap:30px">
          <div class="eyebrow">The problem</div>
          <div class="h2" style="max-width:1300px">
            <span class="line"><span>Banks here cannot send</span></span>
            <span class="line"><span>customer data to a</span></span>
            <span class="line"><span class="stop">cloud AI vendor.</span></span>
          </div>
          <div class="rule"></div>
          <div class="fade fade--2" style="font-size:38px;color:var(--text-2);max-width:1180px;line-height:1.35">
            Their staff still need the answer in seconds.
          </div>
        </div>`));
      await wait(page, 4200);
      await page.evaluate(() => {
        document.querySelectorAll('.line > span').forEach((s) => (s.style.animation = 'none'));
        document.querySelectorAll('.line').forEach((s) => (s.querySelector('span').style.transform = 'translateY(110%)'));
      });
      await wait(page, 700);
      await page.evaluate(() => {
        document.querySelectorAll('.line').forEach((s, i) => {
          const t = s.querySelector('span');
          t.style.transition = 'transform .9s cubic-bezier(.16,1,.3,1)';
          t.style.transform = 'translateY(0)';
          t.style.transitionDelay = i * 0.12 + 's';
        });
        const f = document.querySelector('.fade--2');
        if (f) { f.style.opacity = '1'; f.style.transition = 'opacity .9s ease'; }
      });
      await wait(page, 2100);
    },
  },

  {
    name: '03-egress',
    ms: 14000,
    async run(page) {
      await page.goto(`${BASE}/app?view=egress`, { waitUntil: 'networkidle' });
      await mountOverlay(page, '01 · Egress guard');
      progress(page, 14000);
      console.log('    egress sample loaded:', await waitForSample(page), 'chars');
      await wait(page, 1200);

      await clickOk(page, page.getByRole('button', { name: /Scan & redact/i }).first(),
                    /entities\s+10/i, 'egress scan');
      await wait(page, 2600);

      await say(page, '10', 'entities found and replaced', 'pass 1 of 2', '');
      await wait(page, 3300);
      await say(page, '2', 'passes over its own output', 'self-verification', '');
      await wait(page, 3200);
      await hush(page);
      await wait(page, 700);
      await say(page, 'BLOCK', '& escalate — not a warning', 'card + CVV + account', 'stop');
      await wait(page, 2500);
    },
  },

  {
    name: '04-risk',
    ms: 13000,
    async run(page) {
      await page.goto(`${BASE}/app?view=risk`, { waitUntil: 'networkidle' });
      await mountOverlay(page, '02 · Fraud & AML');
      progress(page, 13000);
      await wait(page, 2000);

      await clickOk(page, page.getByRole('button', { name: /A caller claiming to be from the bank/i }).first(),
                    null, 'risk starter chip');
      await wait(page, 800);
      await clickOk(page, page.getByRole('button', { name: /Screen scenario/i }).first(),
                        /Decline and do not record/i, 'risk screen');
      await wait(page, 2800);

      await say(page, 'CRITICAL', 'card credential solicited by phone', 'customer exposed', 'stop');
      await wait(page, 3400);
      await hush(page);
      await wait(page, 900);

      // Scroll to the panel that admits what is missing.
      await page.evaluate(() => {
        const t = [...document.querySelectorAll('*')].find((n) =>
          /Not covered by this build/i.test(n.textContent || '') && n.children.length < 40);
        if (t) t.scrollIntoView({ block: 'center' });
      });
      await wait(page, 2200);
      await say(page, 'BSP · SEC · AMLC', 'not in the corpus — and it says so', 'named gap', 'warn');
      await wait(page, 2600);
    },
  },

  {
    name: '05-copilot',
    ms: 10000,
    async run(page) {
      await page.goto(`${BASE}/app?view=copilot`, { waitUntil: 'networkidle' });
      await mountOverlay(page, '03 · DPA copilot');
      progress(page, 10000);
      await wait(page, 2000);

      await clickOk(page, page.getByRole('button', { name: /Breach reporting clock/i }).first(),
                    /72 hours|seventy-two/i, 'copilot ask');
      await wait(page, 1800);

      await say(page, '72 hours', 'quoted from the NPC circular', 'NPC-CIRC-16-03 §23', 'good');
      await wait(page, 3600);
      await hush(page);
      await wait(page, 1400);
    },
  },

  {
    name: '06-numbers',
    ms: 7000,
    async run(page) {
      await page.setContent(stage(`
        <div class="stack">
          <div class="eyebrow">Measured, not estimated</div>
          <div class="tiles">
            <div class="tile"><em>PII macro-F1</em><strong class="good">1.0000</strong></div>
            <div class="tile"><em>Residual leak</em><strong class="good">0.00%</strong></div>
            <div class="tile"><em>Citation accuracy</em><strong>100%</strong></div>
            <div class="tile"><em>Fraud recall</em><strong class="accent">94.4%</strong></div>
          </div>
          <div class="fade fade--2" style="font-family:var(--font-mono);font-size:24px;letter-spacing:.2em;color:var(--text-3)">
            501 TESTS · CORPUS 348 CHUNKS · 11 PHILIPPINE INSTRUMENTS
          </div>
        </div>`));
      await wait(page, 7000);
    },
  },

  {
    name: '07-close',
    ms: 4000,
    async run(page) {
      await page.setContent(stage(`
        <div class="stack">
          <div class="h2"><span class="line"><span>On-device. Cited.</span></span>
                             <span class="line"><span class="accent">Refuses to guess.</span></span></div>
          <div class="rule"></div>
          <div class="fade fade--2" style="font-family:var(--font-mono);font-size:30px;letter-spacing:.16em;color:var(--text-2)">
            github.com/jcuady/ISLA-AI
          </div>
        </div>`));
      await wait(page, 4000);
    },
  },
];

// ── record ──────────────────────────────────────────────────────────────────

const total = SCENES.reduce((n, s) => n + s.ms, 0);
console.log(`Shot list: ${SCENES.length} scenes, ${(total / 1000).toFixed(1)}s total`);

rmSync(SHOTS, { recursive: true, force: true });
mkdirSync(SHOTS, { recursive: true });

const browser = await chromium.launch();

for (const [i, scene] of SCENES.entries()) {
  const dir = resolve(SHOTS, scene.name);
  const ctx = await browser.newContext({
    viewport: { width: W, height: H },
    deviceScaleFactor: 1,
    recordVideo: { dir, size: { width: W, height: H } },
  });
  const page = await ctx.newPage();
  const t0 = Date.now();
  try {
    await scene.run(page);
  } catch (err) {
    console.error(`  [${scene.name}] FAILED: ${err.message}`);
  }
  const took = Date.now() - t0;
  await ctx.close();
  const out = readdirSync(dir).find((f) => f.endsWith('.webm'));
  console.log(`  ${String(i + 1).padStart(2)}/${SCENES.length}  ${scene.name.padEnd(12)} ` +
              `${(scene.ms / 1000).toFixed(1)}s target · ${(took / 1000).toFixed(1)}s shot · ${out ?? 'NO FILE'}`);
}

await browser.close();
console.log(`\nSegments in ${SHOTS}`);