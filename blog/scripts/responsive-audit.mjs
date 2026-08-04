// Where does the layout break, and by how much?
//   node scripts/responsive-audit.mjs [url]
// Reports per-viewport: horizontal overflow, any element wider than its parent,
// touch targets under 44px, text/figure collisions, and ResizeObserver churn.
import { chromium } from '@playwright/test';

const URL = process.argv[2] || 'http://localhost:5175/';
const VIEWPORTS = [
  [320, 568, 'iPhone SE'],
  [390, 844, 'iPhone 14'],
  [430, 932, 'iPhone Pro Max'],
  [768, 1024, 'iPad portrait'],
  [1024, 768, 'iPad landscape'],
  [1440, 900, 'desktop'],
];

const b = await chromium.launch();
for (const [w, h, label] of VIEWPORTS) {
  const ctx = await b.newContext({ viewport: { width: w, height: h }, hasTouch: w < 900 });
  await ctx.addInitScript(() => {
    window.__roHits = 0;
    const R = window.ResizeObserver;
    window.ResizeObserver = class extends R {
      constructor(cb) { super((...a) => { window.__roHits++; return cb(...a); }); }
    };
    window.__errs = [];
    window.addEventListener('error', (e) => window.__errs.push(e.message));
  });
  const page = await ctx.newPage();
  await page.goto(URL, { waitUntil: 'networkidle' });
  await page.evaluate(async () => {
    const H = document.documentElement.scrollHeight;
    for (let y = 0; y < H; y += 400) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 40)); }
    window.scrollTo(0, 0);
  });
  await page.waitForTimeout(600);

  const r = await page.evaluate(() => {
    const out = { over: [], small: [], figures: [], docW: document.documentElement.scrollWidth, winW: window.innerWidth };

    // anything sticking out past the viewport
    for (const el of document.querySelectorAll('body *')) {
      const b = el.getBoundingClientRect();
      if (b.width === 0 || b.height === 0) continue;
      if (b.right > window.innerWidth + 1 || b.left < -1) {
        const cs = getComputedStyle(el);
        // an element inside a scroll container is allowed to be wider
        let p = el.parentElement, scrolls = false;
        while (p && p !== document.body) {
          const pcs = getComputedStyle(p);
          if (/auto|scroll/.test(pcs.overflowX)) { scrolls = true; break; }
          p = p.parentElement;
        }
        if (scrolls) continue;
        out.over.push(`${el.tagName.toLowerCase()}${el.className && typeof el.className === 'string' ? '.' + el.className.split(' ')[0] : ''} ` +
          `[${Math.round(b.left)}..${Math.round(b.right)}] w=${Math.round(b.width)} pos=${cs.position}`);
      }
    }

    // touch targets
    for (const el of document.querySelectorAll('button, a, [role="button"], input, select')) {
      const b = el.getBoundingClientRect();
      if (b.width === 0 || b.height === 0) continue;
      if (b.height < 44 || b.width < 44) {
        out.small.push(`"${(el.textContent || el.getAttribute('aria-label') || el.tagName).trim().slice(0, 28)}" ${Math.round(b.width)}x${Math.round(b.height)}`);
      }
    }

    // Each figure vs the space it was given. A chart inside a horizontal scroll
    // container is ALLOWED to be wider than its box -- that is what the
    // container is for -- so only report the ones with nowhere to go.
    for (const el of document.querySelectorAll('svg, canvas')) {
      const b = el.getBoundingClientRect();
      const p = el.parentElement.getBoundingClientRect();
      if (b.width <= p.width + 1) continue;
      let a = el.parentElement, scrolls = false;
      while (a && a !== document.body) {
        if (/auto|scroll/.test(getComputedStyle(a).overflowX)) { scrolls = true; break; }
        a = a.parentElement;
      }
      if (scrolls) continue;
      out.figures.push(`${el.tagName.toLowerCase()} ${Math.round(b.width)} > parent ${Math.round(p.width)}`);
    }

    return { ...out, roHits: window.__roHits, errs: [...new Set(window.__errs)] };
  });

  const flag = (n) => (n ? '***' : '   ');
  console.log(`\n--- ${label} ${w}x${h} ---`);
  console.log(`  doc ${r.docW} / win ${r.winW}  ${r.docW > r.winW + 1 ? '*** HORIZONTAL OVERFLOW ***' : 'no overflow'}   RO callbacks: ${r.roHits}`);
  if (r.over.length) console.log(`  ${flag(1)} ${r.over.length} elements past the viewport edge:\n      ` + r.over.slice(0, 8).join('\n      '));
  if (r.figures.length) console.log(`  ${flag(1)} figure wider than its container:\n      ` + r.figures.slice(0, 8).join('\n      '));
  if (r.small.length) console.log(`  ${flag(1)} ${r.small.length} targets under 44px: ` + r.small.slice(0, 16).join(', '));
  if (r.errs.length) console.log(`  ${flag(1)} page errors: ` + r.errs.join(' ;; '));
  await ctx.close();
}
await b.close();
