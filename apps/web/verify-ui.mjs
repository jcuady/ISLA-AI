/**
 * Visual + console verification for the KALIX surfaces.
 *
 * A dedicated script rather than the shared MCP browser: this runs in an
 * isolated context, is re-runnable, and cannot be hijacked by another session.
 *
 *   node apps/web/verify-ui.mjs [baseUrl]
 */
import { chromium } from 'playwright';
import { mkdirSync, readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const BASE = process.argv[2] || 'http://127.0.0.1:8765';
// --csp-only runs the static policy assertion and exits, so CI can enforce the
// hash without standing up the whole server.
const CSP_ONLY = process.argv.includes('--csp-only');
// Anchored to this file, not the cwd, so the output path is stable no matter
// where the script is invoked from.
const HERE = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(HERE, '.verify');
mkdirSync(OUT, { recursive: true });

/**
 * The landing page ships a CSP that permits its inline reveal script only by
 * hash. If that script is edited without updating the hash, the page silently
 * loses every revealed section — so assert the hash here rather than trusting
 * a human to remember.
 */
function checkCspHash() {
  const html = readFileSync(resolve(HERE, 'public', 'landing.html'), 'utf8');
  const script = html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
  if (!script) {
    console.log('FAIL  csp: no inline <script> found in landing.html');
    return 1;
  }
  const actual = `sha256-${createHash('sha256').update(script, 'utf8').digest('base64')}`;

  const meta = html.match(/script-src '([^']+)'/)?.[1];
  const py = readFileSync(resolve(HERE, '..', '..', 'services', 'core', 'app.py'), 'utf8');
  const header = py.match(/script-src 'self' '(sha256-[^']+)'/)?.[1];

  if (meta !== actual) {
    console.log(`FAIL  csp: landing.html meta hash is stale.`);
    console.log(`        expected ${actual}\n        found    ${meta}`);
    return 1;
  }
  if (header !== actual) {
    console.log(`FAIL  csp: app.py header hash is stale.`);
    console.log(`        expected ${actual}\n        found    ${header}`);
    return 1;
  }
  console.log(`PASS  csp      (inline script hash matches both policies)`);
  return 0;
}

const VIEWPORTS = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'mobile', width: 390, height: 844 },
];

const PAGES = [
  { name: 'landing', path: '/' },
  { name: 'console', path: '/app' },
];

let failures = checkCspHash();

if (CSP_ONLY) {
  console.log(failures ? '\nFAILED' : '\nCSP policy assertions passed.');
  process.exit(failures ? 1 : 0);
}

const browser = await chromium.launch();

for (const vp of VIEWPORTS) {
  const ctx = await browser.newContext({
    viewport: { width: vp.width, height: vp.height },
    deviceScaleFactor: 2,
  });

  for (const p of PAGES) {
    const page = await ctx.newPage();
    const consoleErrors = [];
    const pageErrors = [];
    const external = [];

    page.on('console', (m) => {
      if (m.type() === 'error') consoleErrors.push(m.text());
    });
    page.on('pageerror', (e) => pageErrors.push(String(e)));
    // The air-gap claim: nothing may be fetched off-origin.
    page.on('request', (r) => {
      const u = r.url();
      if (!u.startsWith(BASE) && !u.startsWith('data:') && !u.startsWith('blob:')) {
        external.push(u);
      }
    });

    const res = await page.goto(BASE + p.path, { waitUntil: 'networkidle', timeout: 45000 });
    await page.waitForTimeout(600);

    // Scroll the whole page so IntersectionObserver reveals fire before a
    // fullPage capture, then return to the top.
    await page.evaluate(async () => {
      const step = window.innerHeight * 0.75;
      for (let y = 0; y < document.body.scrollHeight; y += step) {
        window.scrollTo(0, y);
        await new Promise((r) => setTimeout(r, 90));
      }
      window.scrollTo(0, 0);
    });
    await page.waitForTimeout(900);

    // Anything still invisible after a full scroll is a real bug, not a
    // screenshot artefact.
    const stillHidden = await page.evaluate(() =>
      [...document.querySelectorAll('.reveal')]
        .filter((el) => parseFloat(getComputedStyle(el).opacity) < 0.9)
        .map((el) => el.className)
        .slice(0, 5)
    );

    const status = res?.status() ?? 0;
    const overflow = await page.evaluate(() => {
      const de = document.documentElement;
      return de.scrollWidth - de.clientWidth;
    });

    await page.screenshot({
      path: `${OUT}/${p.name}-${vp.name}.png`,
      fullPage: vp.name === 'desktop',
    });

    const bad = [];
    if (status !== 200) bad.push(`HTTP ${status}`);
    if (consoleErrors.length) bad.push(`${consoleErrors.length} console error(s): ${consoleErrors[0]}`);
    if (pageErrors.length) bad.push(`page error: ${pageErrors[0]}`);
    if (external.length) bad.push(`EXTERNAL REQUEST (breaks air-gap): ${external[0]}`);
    if (overflow > 1) bad.push(`horizontal overflow ${overflow}px`);
    if (stillHidden.length) bad.push(`${stillHidden.length} section(s) never revealed: ${stillHidden[0]}`);

    if (bad.length) {
      failures += 1;
      console.log(`FAIL  ${p.name}/${vp.name}: ${bad.join(' | ')}`);
      consoleErrors.slice(0, 5).forEach((e) => console.log(`        console: ${e}`));
      external.slice(0, 5).forEach((e) => console.log(`        external: ${e}`));
    } else {
      console.log(`PASS  ${p.name}/${vp.name}  (HTTP ${status}, 0 console errors, 0 external requests, 0 overflow)`);
    }
    await page.close();
  }
  await ctx.close();
}

await browser.close();
console.log(failures ? `\n${failures} surface(s) FAILED` : '\nAll surfaces clean.');
process.exit(failures ? 1 : 0);