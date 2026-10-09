// Front-end QA walk: drive every console view against the live API.
//
// verify-ui.mjs checks that surfaces *load* clean. This one actually uses
// them — it types into each input, submits, and asserts the response arrives.
// A screen that renders but does not work is the failure this catches, and it
// is invisible to a load-only check.
//
//   node apps/web/qa-frontend.mjs [baseUrl]

import { chromium } from 'playwright';

const BASE = (process.argv[2] || 'http://127.0.0.1:8765').replace(/\/$/, '');
const results = [];
const check = (name, ok, detail = '') => {
  results.push({ name, ok, detail });
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  ${detail}` : ''}`);
};

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();

const consoleErrors = [];
const externalRequests = [];
page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });
page.on('request', (r) => {
  const u = r.url();
  if (!u.startsWith(BASE) && !u.startsWith('data:') && !u.startsWith('blob:')) externalRequests.push(u);
});

// ── every view loads and renders something ────────────────────────────────
console.log('\n[A] Views render');
for (const view of ['copilot', 'egress', 'risk', 'ledger']) {
  consoleErrors.length = 0;
  await page.goto(`${BASE}/console?view=${view}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(400);
  const text = (await page.locator('main').innerText()).trim();
  check(`${view}: renders content`, text.length > 40, `${text.length} chars`);
  check(`${view}: no console errors`, consoleErrors.length === 0, consoleErrors[0] || '');
}

// ── copilot: ask a real question ───────────────────────────────────────────
console.log('\n[B] Copilot answers a question');
consoleErrors.length = 0;
await page.goto(`${BASE}/console?view=copilot`, { waitUntil: 'networkidle' });
const box = page.locator('textarea').first();
await box.fill('Ilang oras dapat ko i-report ang data breach?');
await box.press('Enter');
await page.waitForTimeout(3500);
const answer = await page.locator('main').innerText();
check('copilot: answer rendered', /72|seventy-two/i.test(answer), '');
check('copilot: shows a citation', /RA-10173|NPC-CIRC|IRR-RA10173/.test(answer), '');
check('copilot: no console errors', consoleErrors.length === 0, consoleErrors[0] || '');

// ── egress guard: scan real PII ────────────────────────────────────────────
console.log('\n[C] Egress Guard redacts real PII');
consoleErrors.length = 0;
await page.goto(`${BASE}/console?view=egress`, { waitUntil: 'networkidle' });
await page.waitForTimeout(300);
const area = page.locator('textarea').first();
await area.fill('Maria Santos, card 4539 1488 0343 6467, maria.santos@gmail.com, 0917 555 0142');
const scanBtn = page.getByRole('button', { name: /scan/i }).first();
if (await scanBtn.count()) {
  await scanBtn.click();
} else {
  await area.press('Enter');
}
await page.waitForTimeout(3000);
const egressText = await page.locator('main').innerText();
check('egress: card number no longer on screen',
  !egressText.includes('4539 1488 0343 6467'), '');
check('egress: shows a redaction or verdict',
  /PAN-|EMAIL-|PHONE-|REDACT|BLOCK/i.test(egressText), '');
check('egress: no console errors', consoleErrors.length === 0, consoleErrors[0] || '');

// ── fraud risk: assess a real scenario ────────────────────────────────────
console.log('\n[D] Fraud & AML screens a real scenario');
consoleErrors.length = 0;
await page.goto(`${BASE}/console?view=risk`, { waitUntil: 'networkidle' });
await page.waitForTimeout(300);
const riskArea = page.locator('textarea').first();
await riskArea.fill('A call center agent asked the customer for the credit card PIN and CVV.');
// The control is a multi-line textarea, so Enter inserts a newline rather than
// submitting. The submit button is the only trigger and it is labelled
// "Screen scenario"; matching on /assess/ silently skipped it and then pressed
// Enter, which proved nothing.
const assessBtn = page.getByRole('button', { name: /screen scenario/i }).first();
check('risk: submit button is reachable and labelled', (await assessBtn.count()) === 1);
await assessBtn.click();
await page.waitForTimeout(3500);
const riskText = await page.locator('main').innerText();
check('risk: shows a tier', /CRITICAL|HIGH|MEDIUM|LOW/i.test(riskText), '');
check('risk: shows who is exposed', /Exposed/i.test(riskText) && /bank/i.test(riskText) && /customer/i.test(riskText), '');
// The screen shows the indicator's human-readable label, not its internal id.
// "credential_solicitation" is engine vocabulary; a compliance officer is shown
// "A card credential or one-time code is being solicited". Assert the latter.
check('risk: explains the indicator in plain language',
  /card credential or one-time code/i.test(riskText), '');
check('risk: quotes the evidence that triggered it', /“CVV”|CVV/.test(riskText), '');
check('risk: shows a required action', /Decline and do not record/i.test(riskText), '');
check('risk: shows the coverage gap', /Not covered by this build/i.test(riskText), '');
check('risk: refuses to cite a rule it does not hold',
  /Not in corpus/i.test(riskText), '');
check('risk: disclaims legal advice', /not legal advice/i.test(riskText), '');
check('risk: no console errors', consoleErrors.length === 0, consoleErrors[0] || '');

// ── ledger ────────────────────────────────────────────────────────────────
console.log('\n[E] Ledger');
consoleErrors.length = 0;
await page.goto(`${BASE}/console?view=ledger`, { waitUntil: 'networkidle' });
await page.waitForTimeout(1200);
const ledgerText = await page.locator('main').innerText();
check('ledger: renders entries or an empty state', ledgerText.length > 30, '');
check('ledger: no raw card numbers', !/4539/.test(ledgerText), '');
check('ledger: no console errors', consoleErrors.length === 0, consoleErrors[0] || '');

// ── accessibility + hygiene ───────────────────────────────────────────────
console.log('\n[F] Accessibility and hygiene');
await page.goto(`${BASE}/console?view=copilot`, { waitUntil: 'networkidle' });
await page.waitForTimeout(300);

const headingCount = await page.locator('h1, h2').count();
check('has a heading', headingCount >= 1, `${headingCount} headings`);

const unlabelled = await page.evaluate(() =>
  [...document.querySelectorAll('input, textarea, select')]
    .filter((el) => {
      const id = el.id;
      const hasLabel = id && document.querySelector(`label[for="${id}"]`);
      return !hasLabel && !el.getAttribute('aria-label') && !el.getAttribute('aria-labelledby')
        && !el.closest('label');
    }).length);
check('every form control is labelled', unlabelled === 0, `${unlabelled} unlabelled`);

const imgsNoAlt = await page.evaluate(() =>
  [...document.querySelectorAll('img')].filter((i) => !i.hasAttribute('alt')).length);
check('every img has alt', imgsNoAlt === 0, `${imgsNoAlt} without`);

const btnNoName = await page.evaluate(() =>
  [...document.querySelectorAll('button')]
    .filter((b) => !(b.innerText || '').trim() && !b.getAttribute('aria-label')).length);
check('every button has a name', btnNoName === 0, `${btnNoName} unnamed`);

check('zero external requests', externalRequests.length === 0, externalRequests[0] || '');

// keyboard: tab must reach an interactive control and show focus
await page.keyboard.press('Tab');
await page.keyboard.press('Tab');
const focused = await page.evaluate(() => document.activeElement?.tagName || '');
check('keyboard focus moves', focused && focused !== 'BODY', `focus on ${focused}`);

const overflow = await page.evaluate(() =>
  document.documentElement.scrollWidth - document.documentElement.clientWidth);
check('no horizontal overflow', overflow <= 1, `${overflow}px`);

await ctx.close();
await browser.close();

const failed = results.filter((r) => !r.ok);
console.log(`\n${'='.repeat(70)}`);
console.log(`front-end checks: ${results.length}   passed: ${results.length - failed.length}   failed: ${failed.length}`);
failed.forEach((f) => console.log(`  FAILED  ${f.name}  ${f.detail}`));
process.exit(failed.length ? 1 : 0);