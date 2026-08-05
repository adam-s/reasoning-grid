// Which element moved, and by how much? Name the source of every layout shift.
//
//   node scripts/cls-blame.mjs <url> [width]
//
// verify-deploy.mjs reports the CLS number; this says who caused it. Written
// while chasing a 0.23 shift that turned out to be IterationRings laying itself
// out at its hardcoded 880px guess for one frame before its ResizeObserver
// reported the real 374px. The blame line pointed straight at `ul.cards`
// jumping 300px, which no screenshot could have shown.
import { chromium } from '@playwright/test';
const T = process.argv[2], W = +(process.argv[3]||390);
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: W, height: 844 } });
await p.addInitScript(() => {
  window.__b = [];
  new PerformanceObserver((l) => {
    for (const e of l.getEntries()) {
      if (e.hadRecentInput) continue;
      window.__b.push({
        v: +e.value.toFixed(4),
        t: Math.round(e.startTime),
        src: [...(e.sources||[])].map(s => {
          const el = s.node;
          if (!el || !el.tagName) return '?';
          const fig = el.closest && el.closest('[data-fig]');
          return `${el.tagName.toLowerCase()}${el.className && typeof el.className==='string' ? '.'+el.className.trim().split(/\s+/)[0] : ''}` +
                 (fig ? ` [in ${fig.getAttribute('data-fig')}]` : '') +
                 ` ${Math.round(s.previousRect.top)}->${Math.round(s.currentRect.top)}`;
        }),
      });
    }
  }).observe({ type: 'layout-shift', buffered: true });
});
await p.goto(T, { waitUntil: 'networkidle' });
await p.waitForTimeout(2000);
const bl = await p.evaluate(() => window.__b);
for (const e of bl) console.log(`  ${String(e.v).padStart(7)}  @${String(e.t).padStart(5)}ms  ${e.src.join(' | ')}`);
console.log('total', bl.reduce((s,e)=>s+e.v,0).toFixed(4));
await b.close();
import { chromium } from '@playwright/test';
const T = process.argv[2], W = +(process.argv[3]||390);
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: W, height: 844 } });
await p.addInitScript(() => {
  window.__b = [];
  new PerformanceObserver((l) => {
    for (const e of l.getEntries()) {
      if (e.hadRecentInput) continue;
      window.__b.push({
        v: +e.value.toFixed(4),
        t: Math.round(e.startTime),
        src: [...(e.sources||[])].map(s => {
          const el = s.node;
          if (!el || !el.tagName) return '?';
          const fig = el.closest && el.closest('[data-fig]');
          return `${el.tagName.toLowerCase()}${el.className && typeof el.className==='string' ? '.'+el.className.trim().split(/\s+/)[0] : ''}` +
                 (fig ? ` [in ${fig.getAttribute('data-fig')}]` : '') +
                 ` ${Math.round(s.previousRect.top)}->${Math.round(s.currentRect.top)}`;
        }),
      });
    }
  }).observe({ type: 'layout-shift', buffered: true });
});
await p.goto(T, { waitUntil: 'networkidle' });
await p.waitForTimeout(2000);
const bl = await p.evaluate(() => window.__b);
for (const e of bl) console.log(`  ${String(e.v).padStart(7)}  @${String(e.t).padStart(5)}ms  ${e.src.join(' | ')}`);
console.log('total', bl.reduce((s,e)=>s+e.v,0).toFixed(4));
await b.close();
