// Which code is scheduling requestAnimationFrame while the page sits idle?
//   node scripts/raf-blame.mjs [url] [width]
import { chromium } from '@playwright/test';
const URL = process.argv[2] || 'http://localhost:5175/';
const W = +(process.argv[3] || 1440);

const b = await chromium.launch();
const ctx = await b.newContext({ viewport: { width: W, height: 900 } });
await ctx.addInitScript(() => {
  window.__raf = new Map();
  window.__on = false;
  const r = window.requestAnimationFrame.bind(window);
  window.requestAnimationFrame = (cb) => {
    if (window.__on) {
      const s = (new Error().stack || '').split('\n').slice(2, 4).join(' <- ')
        .replace(/https?:\/\/[^/]+/g, '').replace(/\s+at\s+/g, ' ').trim();
      window.__raf.set(s, (window.__raf.get(s) || 0) + 1);
    }
    return r(cb);
  };
});
const page = await ctx.newPage();
await page.goto(URL, { waitUntil: 'networkidle' });
await page.waitForTimeout(1500);

for (const phase of ['idle at top', 'idle at bottom']) {
  if (phase === 'idle at bottom') {
    await page.evaluate(async () => {
      const H = document.documentElement.scrollHeight;
      for (let y = 0; y < H; y += 500) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 50)); }
    });
    await page.waitForTimeout(800);
  }
  await page.evaluate(() => { window.__raf.clear(); window.__on = true; });
  await page.waitForTimeout(3000);
  const rows = await page.evaluate(() => { window.__on = false; return [...window.__raf].sort((a, b) => b[1] - a[1]); });
  const total = rows.reduce((s, [, n]) => s + n, 0);
  console.log(`\n--- ${phase} @${W}px --- ${(total / 3).toFixed(0)} rAF/sec over 3s, ${rows.length} distinct sites`);
  for (const [site, n] of rows.slice(0, 12)) console.log(`  ${String(Math.round(n / 3)).padStart(4)}/s  ${site}`);
}
await b.close();
