// Rehearsal check: follow docs/DEMO_60S.md exactly as written and confirm every
// step produces the state the script claims. Run with the server up.
//
//   node apps/web/rehearse-60s.mjs

import { chromium } from 'playwright';

const BASE = 'http://127.0.0.1:8765';
const results = [];
const check = (name, ok, detail = '') => {
  results.push({ name, ok, detail });
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  ${detail}` : ''}`);
};

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();
const errors = [];
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });

// ── TAB 1 · Egress Guard (0:06-0:20) ──────────────────────────────────────
console.log('\n[Tab 1] Egress Guard');
await page.goto(`${BASE}/app?view=egress`, { waitUntil: 'networkidle' });
await page.waitForTimeout(1500);
const sample = await page.locator('textarea').first().inputValue();
check('deep link ?view=egress works', sample.length > 40, `${sample.length} chars preloaded`);
check('preloaded sample holds an SSS', /12-345-6789/.test(sample), '');

// The script tells the presenter exactly what is already in the box and tells
// them which button to press if it is ever empty. Pin both, so a drift in the
// fixture cannot leave a wrong string sitting in a document people read on
// stage. Compared against the block quoted in docs/DEMO_60S.md.
const DOCUMENTED_SAMPLE = [
  'From: Collections Team <collections@usapalmabank.com.ph>',
  'Subject: Urgent - overdue notice for DELOS SANTOS, Maria Concepcion',
  '',
  'Magandang araw po,',
  '',
  'Nag-apply po ng overdue notice si Maria Concepcion de los Santos.',
  'SSS 12-345-6789, TIN 456-789-012.',
  'Registered mobile 0917 123 4567, GCash number +639171234568.',
  'Credit card ending 4539578763621486, CVV 123, exp 09/28.',
  'Account number: 0056-12345678. Monthly salary PHP 42,500.',
  'Remittance via Cebuana Lhuillier ref #CEB-88213-4455.',
  '',
  'Pakisuri na po bago mag-escalate. Salamat!',
  '',
].join('\n');
check('preloaded text is exactly what the script documents',
  sample === DOCUMENTED_SAMPLE,
  sample === DOCUMENTED_SAMPLE ? '' : 'DEMO_60S.md quotes a different sample');

for (const label of ['Collections email', 'Payment note', 'Operations text']) {
  check(`recovery button "${label}" exists`,
    (await page.getByRole('button', { name: label, exact: true }).count()) === 1, '');
}
const scanBtn = page.getByRole('button', { name: /Scan & redact/i }).first();
check('button is labelled "Scan & redact"', (await scanBtn.count()) === 1,
  (await scanBtn.count()) === 1 ? '' : 'label differs from the script');
await scanBtn.click();
await page.waitForTimeout(2500);
const egText = await page.locator('main').innerText();
// The escalation reason matters: this sample holds a card PAN, a CVV and an
// account number together, so it takes the *payment-credential compromise*
// branch, not the SSS/TIN branch. Saying the wrong reason on stage is worse
// than saying nothing, so the rehearsal pins the actual string.
check('verdict renders as BLOCK & ESCALATE', /BLOCK\s*&\s*ESCALATE/i.test(egText), '');
check('escalates for card PAN + CVV + account together',
  /payment-credential compromise/i.test(egText), '');
check('shows the verification pass', /verif/i.test(egText), '');

// The spoken line names the ten things found. If the fixture or the detector
// changes, that sentence becomes a lie told on stage, so check the categories
// the script actually says out loud against what is on screen.
const KINDS = ['EMAIL', 'SSS', 'TIN', 'GCASH', 'PAN', 'CVV', 'ACCT', 'AMOUNT', 'REMIT'];
const missing = KINDS.filter((k) => !new RegExp(`\\[${k}-[0-9A-F]{4}\\]`).test(egText));
check('every kind named in the script is in the redacted output',
  missing.length === 0, missing.length ? `missing ${missing.join(', ')}` : '');
check('detected count is the ten the script claims', /Detected\s*\(\s*10\s*\)/i.test(egText), '');

// ── TAB 2 · Fraud & AML (0:20-0:42) ───────────────────────────────────────
console.log('\n[Tab 2] Fraud & AML');
await page.goto(`${BASE}/app?view=risk`, { waitUntil: 'networkidle' });
await page.waitForTimeout(600);
// The starter chips are truncated to 46 characters in the UI, so the accessible
// name is the truncated string, not the full scenario.
const cvvChip = page.getByRole('button', { name: /A caller claiming to be from the bank/i }).first();
check('CVV starter chip exists as rendered', (await cvvChip.count()) === 1,
  (await cvvChip.count()) === 1 ? '' : 'chip text differs from the script');
await cvvChip.click();
await page.waitForTimeout(300);
const screenBtn = page.getByRole('button', { name: /Screen scenario/i }).first();
check('button is labelled "Screen scenario"', (await screenBtn.count()) === 1);
await screenBtn.click();
await page.waitForTimeout(3500);
const riskText = await page.locator('main').innerText();
check('verdict is CRITICAL', /CRITICAL/i.test(riskText), '');
check('names bank AND customer exposed',
  /Exposed/i.test(riskText) && /bank/i.test(riskText) && /customer/i.test(riskText), '');
check('quotes the evidence', /“CVV”/.test(riskText), '');
check('names the required action', /Decline and do not record/i.test(riskText), '');
check('has the "Not covered by this build" panel',
  /Not covered by this build/i.test(riskText), '');
check('names BSP, SEC, AMLC and PCI',
  /BSP/.test(riskText) && /SEC/.test(riskText) && /AMLC/.test(riskText) && /PCI/.test(riskText), '');

// ── TAB 3 · Copilot (0:42-0:55) ───────────────────────────────────────────
console.log('\n[Tab 3] Copilot');
await page.goto(`${BASE}/app?view=copilot`, { waitUntil: 'networkidle' });
await page.waitForTimeout(600);
const clockChip = page.getByRole('button', { name: /Breach reporting clock/i }).first();
check('"Breach reporting clock" chip exists', (await clockChip.count()) === 1);
await clockChip.click();
await page.waitForTimeout(4000);

// docs/DEMO_60S.md tells the presenter the exact question this chip sends, and
// offers it as the thing to retype if the chips are unavailable. Pin it.
const QUESTION = 'Ilang oras dapat ko i-report ang data breach?';
check('chip sends exactly the question the script documents',
  (await page.locator('main').innerText()).includes(QUESTION), QUESTION);

// Read chip 1's answer now: the loop below navigates away to the backup chips,
// so anything asserted after it would be reading the wrong answer.
const cpText = await page.locator('main').innerText();
check('answers 72 hours', /72|seventy-two/i.test(cpText), '');
check('carries a citation chip',
  /NPC-CIRC|IRR-RA10173|RA-10173/.test(cpText), '');

// The other two chips are named as backups, with their exact wording. Their
// accessible name is the title AND the question - both are child spans - so
// this must be a substring match, not `exact`.
for (const [chip, q] of [
  ['Outsourcing to a vendor', 'Pwede ba ipasa ang CDR ng customer ko sa vendor namin sa Singapore?'],
  ['Rules for automated decisions', 'Can our call center use AI to score our agents?'],
]) {
  await page.goto(`${BASE}/app?view=copilot`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(500);
  await page.getByRole('button', { name: new RegExp(chip, 'i') }).first().click();
  await page.waitForTimeout(4000);
  check(`"${chip}" sends the documented question`,
    (await page.locator('main').innerText()).includes(q), '');
}
check('no console errors across the whole run', errors.length === 0, errors[0] || '');

await ctx.close();
await browser.close();

const failed = results.filter((r) => !r.ok);
console.log(`\n${'='.repeat(66)}`);
console.log(`rehearsal: ${results.length}   passed: ${results.length - failed.length}   failed: ${failed.length}`);
failed.forEach((f) => console.log(`  FAILED  ${f.name}  ${f.detail}`));
process.exit(failed.length ? 1 : 0);