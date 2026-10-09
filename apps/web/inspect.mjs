// One-off design inspection: full-page captures of the landing page so the
// layout can actually be judged, not just asserted. Uses its own browser
// instance rather than the shared MCP browser so nothing can collide with
// another session.
import { chromium } from 'playwright';

const shots = [
  { name: 'landing-desktop', url: 'http://127.0.0.1:8765/', width: 1440, height: 900 },
  { name: 'landing-mobile', url: 'http://127.0.0.1:8765/', width: 390, height: 844 },
];

const browser = await chromium.launch();
for (const s of shots) {
  const ctx = await browser.newContext({
    viewport: { width: s.width, height: s.height },
    deviceScaleFactor: 1,
  });
  const page = await ctx.newPage();
  await page.goto(s.url, { waitUntil: 'networkidle' });
  // Scroll down in viewport-sized steps, the way a visitor does, so the
  // IntersectionObserver reveal actually fires before capture. Jumping
  // straight to the bottom skips every section in between.
  await page.evaluate(async () => {
    const step = window.innerHeight * 0.8;
    for (let y = 0; y < document.body.scrollHeight; y += step) {
      window.scrollTo(0, y);
      await new Promise((r) => setTimeout(r, 120));
    }
    window.scrollTo(0, document.body.scrollHeight);
    await new Promise((r) => setTimeout(r, 400));
    window.scrollTo(0, 0);
    await new Promise((r) => setTimeout(r, 500));
  });
  await page.waitForTimeout(700);
  await page.screenshot({ path: `shots/${s.name}.png`, fullPage: true });
  // Report anything still invisible: a blank region is the failure this
  // script exists to catch, so measure it rather than eyeballing it.
  const hidden = await page.evaluate(() =>
    [...document.querySelectorAll('.reveal')]
      .filter((el) => getComputedStyle(el).opacity !== '1')
      .map((el) => el.className + ' :: ' + (el.textContent || '').trim().slice(0, 40)),
  );
  console.log(`${s.name}: ${hidden.length} element(s) still transparent`);
  hidden.slice(0, 8).forEach((h) => console.log('   hidden: ' + h));
  await ctx.close();
}
await browser.close();