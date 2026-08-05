// Does a figure still animate after a reload that lands scrolled down?
//
//   npm run preview
//   node scripts/check-reload-freeze.mjs [url]
//
// A regression check for one specific race, kept because it took a reproduction
// to find and would have been invisible to every other check here.
//
// The opener frames its animation on an IntersectionObserver so it does not
// burn a phone's battery off screen. Reload the page scrolled down and scroll
// back up, and the observer can deliver two records for that figure in ONE
// callback: 205px tall and off screen, then 508px and on screen once it has
// sized itself. onscreen.svelte.ts read entries[0], so the stale record won,
// `near` stayed false, and the rings sat frozen at two percent of their first
// lap. About one reload in three, and only with a slow CPU.
//
// The tell is requestAnimationFrame throughput, not a screenshot: a frozen
// figure looks like a figure that has not started yet. ~360/sec is four loops
// running, ~240 is one of them dead.
//
// Throttles the CPU 6x on purpose. At full speed the two records land in
// separate deliveries and nothing goes wrong.
import { chromium } from '@playwright/test';
const T = process.argv[2] || 'http://localhost:4173/';
const b = await chromium.launch();
let frozen = 0;
for (let attempt = 0; attempt < 14; attempt++) {
  const p = await b.newPage({ viewport:{width:1280,height:900} });
  const cdp = await p.context().newCDPSession(p);
  await cdp.send('Emulation.setCPUThrottlingRate', { rate: 6 });
  await p.addInitScript(() => {
    window.__io = [];
    const R = window.IntersectionObserver;
    window.IntersectionObserver = class extends R {
      constructor(cb, opts) {
        super((entries, obs) => {
          for (const e of entries) {
            const f = e.target.closest && e.target.closest('[data-fig]');
            if (f && f.getAttribute('data-fig') === 'rings') {
              window.__io.push({ t: Math.round(performance.now()), hit: e.isIntersecting, h: Math.round(e.boundingClientRect.height) });
            }
          }
          return cb(entries, obs);
        }, opts);
      }
    };
    window.__raf = 0;
    const r = window.requestAnimationFrame.bind(window);
    window.requestAnimationFrame = (cb) => { window.__raf++; return r(cb); };
  });
  await p.goto(T, { waitUntil:'networkidle' });
  const Y = 900 + (attempt % 5) * 350;
  await p.evaluate((yy) => window.scrollTo(0, yy), Y);
  await p.waitForTimeout(300);
  await p.reload({ waitUntil:'domcontentloaded' });
  await p.waitForTimeout(2500);
  for (let i = 0; i < 30; i++) { await p.mouse.wheel(0, -400); await p.waitForTimeout(40); }
  await p.waitForTimeout(1000);
  const before = await p.evaluate(()=>window.__raf);
  await p.waitForTimeout(800);
  const after = await p.evaluate(()=>window.__raf);
  const io = await p.evaluate(()=>window.__io);
  const a = await p.locator('[data-fig="rings"]').screenshot();
  await p.waitForTimeout(600);
  const c = await p.locator('[data-fig="rings"]').screenshot();
  const rate = Math.round((after - before) / 0.8);
  const moving = !a.equals(c);
  if (!moving) frozen++;
  console.log(`  reload at y=${String(Y).padStart(4)}  moving=${String(moving).padEnd(5)} rAF/s=${String(rate).padStart(3)}  deliveries=${io.length}`);
  await p.close();
}
await b.close();
console.log(frozen === 0
  ? `\nPASS  14 reloads, none froze`
  : `\nFAIL  ${frozen} of 14 reloads left the opener frozen`);
process.exit(frozen === 0 ? 0 : 1);
