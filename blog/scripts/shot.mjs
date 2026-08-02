// Screenshot one section at a given viewport, for reviewing a figure without a browser.
//   node scripts/shot.mjs <out.png> [width] [section text]
import { chromium } from '@playwright/test';
const [out, w = '1280', needle = 'Three ways to finish'] = process.argv.slice(2);
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: +w, height: 1400 }, deviceScaleFactor: 2 });
await p.goto('http://localhost:5175/', { waitUntil: 'networkidle' });
await p.waitForTimeout(600);
await p.locator('section', { hasText: needle }).first().screenshot({ path: out });
console.log('wrote', out, `@${w}px`);
await b.close();
