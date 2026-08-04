// CDP performance + leak probe.
//   node perf.mjs [url] [width] [height]
// Instruments rAF/timers/listeners in-page, drives every control, and reports
// what is still running when nobody is touching the page.
import { chromium } from '@playwright/test';

const URL = process.argv[2] || 'http://localhost:5175/';
const W = +(process.argv[3] || 1440);
const H = +(process.argv[4] || 900);

const INSTRUMENT = () => {
  const I = {
    rafLive: new Map(), rafCalls: 0, rafStacks: new Map(),
    intervals: new Map(), timeouts: new Map(),
    listeners: new Map(),
    longtasks: [], frameGaps: [], errors: [],
  };
  window.__inst = I;
  const top = (e) => (e.stack || '').split('\n').slice(2, 5).join(' | ').replace(/https?:\/\/[^/]+/g, '');

  const rRAF = window.requestAnimationFrame.bind(window);
  const rCAF = window.cancelAnimationFrame.bind(window);
  window.requestAnimationFrame = (cb) => {
    const s = top(new Error());
    const id = rRAF((t) => { I.rafLive.delete(id); try { cb(t); } catch (e) { I.errors.push(String(e)); throw e; } });
    I.rafLive.set(id, s); I.rafCalls++;
    I.rafStacks.set(s, (I.rafStacks.get(s) || 0) + 1);
    return id;
  };
  window.cancelAnimationFrame = (id) => { I.rafLive.delete(id); return rCAF(id); };

  const rSI = window.setInterval.bind(window), rCI = window.clearInterval.bind(window);
  window.setInterval = (fn, ms, ...a) => { const id = rSI(fn, ms, ...a); I.intervals.set(id, top(new Error())); return id; };
  window.clearInterval = (id) => { I.intervals.delete(id); return rCI(id); };

  const rST = window.setTimeout.bind(window), rCT = window.clearTimeout.bind(window);
  window.setTimeout = (fn, ms, ...a) => {
    const s = top(new Error());
    const id = rST((...b) => { I.timeouts.delete(id); return typeof fn === 'function' ? fn(...b) : fn; }, ms, ...a);
    I.timeouts.set(id, s); return id;
  };
  window.clearTimeout = (id) => { I.timeouts.delete(id); return rCT(id); };

  for (const T of [window.EventTarget]) {
    const rAdd = T.prototype.addEventListener, rRem = T.prototype.removeEventListener;
    T.prototype.addEventListener = function (type, fn, opt) {
      const tag = (this === window ? 'window' : this === document ? 'document'
        : this.tagName ? this.tagName.toLowerCase() : String(this && this.constructor && this.constructor.name));
      const k = tag + ':' + type;
      I.listeners.set(k, (I.listeners.get(k) || 0) + 1);
      return rAdd.call(this, type, fn, opt);
    };
    T.prototype.removeEventListener = function (type, fn, opt) {
      const tag = (this === window ? 'window' : this === document ? 'document'
        : this.tagName ? this.tagName.toLowerCase() : String(this && this.constructor && this.constructor.name));
      const k = tag + ':' + type;
      I.listeners.set(k, (I.listeners.get(k) || 0) - 1);
      return rRem.call(this, type, fn, opt);
    };
  }

  new PerformanceObserver((l) => { for (const e of l.getEntries()) I.longtasks.push(Math.round(e.duration)); })
    .observe({ entryTypes: ['longtask'] });

  let last = performance.now();
  const tick = (t) => { const d = t - last; if (d > 34) I.frameGaps.push(Math.round(d)); last = t; rRAF(tick); };
  rRAF(tick);

  window.addEventListener('error', (e) => I.errors.push('error: ' + e.message));
  window.addEventListener('unhandledrejection', (e) => I.errors.push('rejection: ' + String(e.reason)));
};

const snap = (label) => async (page) => {
  const r = await page.evaluate(() => {
    const I = window.__inst;
    return {
      rafCalls: I.rafCalls, rafLive: I.rafLive.size,
      intervals: [...I.intervals.values()],
      listeners: Object.fromEntries([...I.listeners].filter(([, v]) => v !== 0)),
      longtasks: I.longtasks.slice(), errors: I.errors.slice(),
      gaps: I.frameGaps.length,
      nodes: document.querySelectorAll('*').length,
      docW: document.documentElement.scrollWidth, winW: window.innerWidth,
    };
  });
  return { label, ...r };
};

const b = await chromium.launch();
// Touch is emulated below 900px so the `pointer: coarse` rules that size the
// controls actually apply. Without it every control reports its mouse size and
// the touch-target check is measuring the wrong page.
const ctx = await b.newContext({ viewport: { width: W, height: H }, hasTouch: W < 900 });
await ctx.addInitScript(INSTRUMENT);
const page = await ctx.newPage();
const cdp = await ctx.newCDPSession(page);
await cdp.send('Performance.enable');
const metrics = async () => Object.fromEntries((await cdp.send('Performance.getMetrics')).metrics.map(m => [m.name, m.value]));

await page.goto(URL, { waitUntil: 'networkidle' });
await page.waitForTimeout(1000);

console.log(`\n=== ${W}x${H} ${URL} ===`);
const s0 = await snap('load')(page);
console.log(`load            rafCalls ${s0.rafCalls}  live ${s0.rafLive}  nodes ${s0.nodes}  docW ${s0.docW}/${s0.winW}`);

// --- idle burn: nothing touched, is anything still animating? ---
const a = await page.evaluate(() => window.__inst.rafCalls);
await page.waitForTimeout(2000);
const bq = await page.evaluate(() => window.__inst.rafCalls);
// A figure that loops while the reader is looking at it is a design choice,
// not a defect. The defect is a figure that loops while it is off screen, and
// the only way to tell them apart is to measure at the top and then again with
// every opener figure scrolled well away. Both numbers are printed.
console.log(`IDLE, ON SCREEN ${((bq - a) / 2).toFixed(1)} rAF/sec at the top of the page (looping figures are visible here)`);

// --- enumerate controls ---
const controls = await page.evaluate(() =>
  [...document.querySelectorAll('button')].map((el, i) => ({
    i, text: (el.textContent || '').trim().slice(0, 40),
    w: Math.round(el.getBoundingClientRect().width),
    h: Math.round(el.getBoundingClientRect().height),
  })));
console.log(`controls        ${controls.length} buttons`);
const small = controls.filter(c => c.h > 0 && c.h < 44);
if (small.length) console.log(`  TOUCH TARGETS <44px: ${small.map(c => `"${c.text}"(${c.w}x${c.h})`).join(', ')}`);

// --- scroll the whole page (fires observers, mounts everything) ---
await page.evaluate(async () => {
  const H = document.documentElement.scrollHeight;
  for (let y = 0; y < H; y += 400) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 60)); }
  window.scrollTo(0, 0);
});
await page.waitForTimeout(500);
const s1 = await snap('scrolled')(page);
console.log(`after scroll    rafCalls ${s1.rafCalls}  live ${s1.rafLive}  nodes ${s1.nodes}  longtasks ${s1.longtasks.length} (max ${Math.max(0, ...s1.longtasks)}ms)`);

// --- hammer every button: rapid double-clicks catch concurrent rAF loops ---
const m0 = await metrics();
for (const c of controls) {
  const el = page.locator('button').nth(c.i);
  try {
    if (!(await el.isVisible()) || await el.isDisabled()) continue;
    await el.scrollIntoViewIfNeeded();
    await el.click({ timeout: 2000, force: true });
    await page.waitForTimeout(80);
    await el.click({ timeout: 2000, force: true }).catch(() => {});   // re-entrant
    await el.click({ timeout: 2000, force: true }).catch(() => {});
    await page.waitForTimeout(120);
  } catch { /* disabled mid-animation is fine */ }
}
await page.waitForTimeout(1500);
const s2 = await snap('hammered')(page);
const m1 = await metrics();
console.log(`after hammer    rafCalls ${s2.rafCalls}  live ${s2.rafLive}  nodes ${s2.nodes}  longtasks ${s2.longtasks.length} (max ${Math.max(0, ...s2.longtasks)}ms)`);
console.log(`  slow frames >34ms: ${s2.gaps}`);
if (s2.rafLive > 3) console.log(`  *** ${s2.rafLive} rAF callbacks queued at rest — concurrent loops ***`);

// --- idle burn again, after interaction ---
const c1 = await page.evaluate(() => window.__inst.rafCalls);
await page.waitForTimeout(2000);
const c2 = await page.evaluate(() => window.__inst.rafCalls);
console.log(`IDLE, POST      ${((c2 - c1) / 2).toFixed(1)} rAF/sec once every animation has settled`);
// The one that matters. Scroll the openers out of range and wait: anything
// still scheduling frames here is painting something nobody can see.
await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
await page.waitForTimeout(1200);
const d1 = await page.evaluate(() => window.__inst.rafCalls);
await page.waitForTimeout(2000);
const d2 = await page.evaluate(() => window.__inst.rafCalls);
const offscreen = (d2 - d1) / 2;
console.log(`IDLE, OFF SCREEN ${offscreen.toFixed(1)} rAF/sec with the opener figures scrolled away  ${offscreen > 20 ? '*** STILL ANIMATING OUT OF SIGHT ***' : 'ok'}`);

// --- leaked timers / listeners ---
if (s2.intervals.length) console.log(`  *** ${s2.intervals.length} uncleared setInterval:`, s2.intervals.slice(0, 5));
const leaked = Object.entries(s2.listeners).filter(([k, v]) => v > 0 && /^(window|document)/.test(k));
if (leaked.length) console.log(`  window/document listeners never removed:`, Object.fromEntries(leaked));

// --- heap growth across repeated interaction ---
await cdp.send('HeapProfiler.enable');
await cdp.send('HeapProfiler.collectGarbage');
const h0 = (await metrics()).JSHeapUsedSize;
for (let round = 0; round < 3; round++) {
  for (const c of controls.slice(0, 8)) {
    const el = page.locator('button').nth(c.i);
    try { if (await el.isVisible() && !(await el.isDisabled())) { await el.click({ force: true, timeout: 1500 }); await page.waitForTimeout(150); } } catch {}
  }
}
await page.waitForTimeout(1000);
await cdp.send('HeapProfiler.collectGarbage');
const h1 = (await metrics()).JSHeapUsedSize;
console.log(`heap            ${(h0 / 1e6).toFixed(1)}MB -> ${(h1 / 1e6).toFixed(1)}MB after 3 rounds  (+${((h1 - h0) / 1e6).toFixed(1)}MB)`);
console.log(`listeners(cdp)  ${m0.JSEventListeners} -> ${m1.JSEventListeners}   nodes ${m0.Nodes} -> ${m1.Nodes}`);

const sf = await snap('final')(page);
if (sf.errors.length) console.log(`  *** PAGE ERRORS: ${[...new Set(sf.errors)].slice(0, 8).join(' ;; ')}`);
if (sf.docW > sf.winW + 1) console.log(`  *** HORIZONTAL OVERFLOW: doc ${sf.docW} > win ${sf.winW}`);

await b.close();
