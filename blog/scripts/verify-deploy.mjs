// Does the deployed page actually work? Run against a local preview before
// shipping and against the live URL after.
//
//   node scripts/verify-deploy.mjs http://localhost:4173/
//   node scripts/verify-deploy.mjs https://adamsohn.com/reasoning-grid/
//
// Four things, in the order they can fail:
//
//   1. PROSE WITHOUT JS. Fetch the HTML and look for the essay in it. This is
//      the whole reason the page is prerendered, and it is the failure that
//      hides best: with JavaScript on, a page that prerendered nothing looks
//      perfect.
//   2. HYDRATION. Svelte only warns about a server/client mismatch in a dev
//      build, so the check here is behavioural: the figures have to actually
//      arrive, and the console has to stay clean.
//   3. LAYOUT SHIFT. The reserved figure boxes exist to stop the prose jumping
//      when nine figures mount. Measured with the real CLS observer, at three
//      widths, because the boxes are width-dependent.
//   4. RESERVED VS ACTUAL. Per figure, the height the box held open against the
//      height the figure turned out to be. CLS can pass on average while one
//      figure is badly wrong, and this says which one.
import { chromium } from '@playwright/test';

const TARGET = process.argv[2] || 'http://localhost:4173/';
const CANARY = 'Speed of iteration beats';
const WIDTHS = [
  [390, 844, 'phone'],
  [768, 1024, 'tablet'],
  [1440, 900, 'desktop'],
];

// Google's "good" CLS. Not a style preference: above this the page is judged to
// move under the reader.
const CLS_BUDGET = 0.1;
// A figure box off by more than this is worth naming even when CLS passes.
const BOX_TOL = 24;

let failures = 0;
const bad = (msg) => {
  failures++;
  console.log(`  FAIL  ${msg}`);
};
const ok = (msg) => console.log(`  ok    ${msg}`);

console.log(`\n=== ${TARGET} ===\n`);

// ---- 1. the HTML itself, no browser involved ---------------------------
const res = await fetch(TARGET);
const html = await res.text();
console.log(`html            ${res.status}  ${(html.length / 1024).toFixed(1)}KB`);
if (!res.ok) bad(`fetch returned ${res.status}`);
if (html.includes(CANARY)) ok(`prose is in the HTML (found ${JSON.stringify(CANARY)})`);
else bad(`prose is NOT in the HTML — the page did not prerender, or a stale build is live`);
if (/<div id="app"><\/div>/.test(html)) bad('app div is empty — prerender output was not written');

const figsInHtml = [...html.matchAll(/data-fig="([a-z-]+)"/g)].map((m) => m[1]);
if (figsInHtml.length) ok(`${figsInHtml.length} figure boxes reserved: ${figsInHtml.join(', ')}`);
else bad('no figure boxes in the HTML — every figure will shift the page when it mounts');

// ---- 2-4. the browser ---------------------------------------------------
const b = await chromium.launch();

for (const [w, h, label] of WIDTHS) {
  const page = await b.newPage({ viewport: { width: w, height: h } });
  const errors = [];
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push(m.text());
  });
  page.on('pageerror', (e) => errors.push(String(e)));

  // Start the CLS observer before anything renders, and keep every entry: a
  // shift that happens during hydration is exactly what this is looking for.
  await page.addInitScript(() => {
    window.__cls = 0;
    window.__shifts = [];
    new PerformanceObserver((l) => {
      for (const e of l.getEntries()) {
        if (e.hadRecentInput) continue;
        window.__cls += e.value;
        if (e.value > 0.001) window.__shifts.push(+e.value.toFixed(4));
      }
    }).observe({ type: 'layout-shift', buffered: true });
  });

  // The boxes are measured before hydration replaces them, so grab them as
  // early as the document allows.
  await page.goto(TARGET, { waitUntil: 'domcontentloaded' });
  const reserved = await page.evaluate(() =>
    Object.fromEntries(
      [...document.querySelectorAll('[data-fig]')].map((el) => [
        el.getAttribute('data-fig'),
        Math.round(el.getBoundingClientRect().height),
      ]),
    ),
  );

  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1500);

  const { cls, shifts, actual, pending } = await page.evaluate(() => ({
    cls: window.__cls,
    shifts: window.__shifts,
    pending: document.querySelectorAll('[data-fig].pending').length,
    actual: Object.fromEntries(
      [...document.querySelectorAll('[data-fig]')].map((el) => [
        el.getAttribute('data-fig'),
        Math.round(el.getBoundingClientRect().height),
      ]),
    ),
  }));

  console.log(`\n--- ${label} (${w}px) ---`);

  if (pending === 0) ok('every figure mounted');
  else bad(`${pending} figure(s) never mounted — still .pending after load`);

  if (errors.length === 0) ok('no console errors');
  else bad(`${errors.length} console error(s): ${[...new Set(errors)].slice(0, 3).join(' ;; ')}`);

  if (cls <= CLS_BUDGET) ok(`CLS ${cls.toFixed(4)} (budget ${CLS_BUDGET})`);
  else bad(`CLS ${cls.toFixed(4)} over budget ${CLS_BUDGET}; shifts ${shifts.slice(0, 6).join(', ')}`);

  const off = Object.keys(reserved)
    .map((k) => ({ k, r: reserved[k], a: actual[k] ?? 0, d: (actual[k] ?? 0) - reserved[k] }))
    .filter((x) => Math.abs(x.d) > BOX_TOL)
    .sort((x, y) => Math.abs(y.d) - Math.abs(x.d));
  if (!off.length) ok(`every reserved box within ${BOX_TOL}px of its figure`);
  else
    for (const x of off)
      bad(`${x.k}: reserved ${x.r}px, figure is ${x.a}px (${x.d > 0 ? '+' : ''}${x.d}px)`);

  await page.close();
}

await b.close();
console.log(`\n${failures === 0 ? 'PASS' : `FAIL — ${failures} problem(s)`}\n`);
process.exit(failures === 0 ? 0 : 1);
