// Does the deployed page actually work? Run against a local preview before
// shipping and against the live URL after.
//
//   npm run preview
//   node scripts/verify-deploy.mjs http://localhost:4173/
//   node scripts/verify-deploy.mjs https://adamsohn.com/reasoning-grid/
//
// EVERY CHECK HERE MUST BE ABLE TO FAIL. The first version of this script had
// one that could not, and it is worth writing down because the mistake is easy
// to make twice. It read each figure box's height at `domcontentloaded`, called
// that "reserved", read the same box again after load, called that "actual",
// and compared them. Module scripts are deferred, so they run BEFORE
// DOMContentLoaded fires: both readings were the same post-hydration DOM, the
// delta was exactly 0 for all nine figures at all three widths, and deleting
// the entire stylesheet the check exists to guard still printed "ok". Two
// independent reviews found it, and only by trying to make it fail.
//
// So: reserved comes from the CSSOM, the figure is measured with the
// reservation forced off, and the two are compared across many widths.
import { chromium } from '@playwright/test';

const TARGET = process.argv[2] || 'http://localhost:4173/';

// A sentence from near the START of the essay and one from near the END. One
// canary only proves the prerender emitted something: the first version's
// canary sat at character 881 of 13,005, so a bug that truncated the other 93%
// would have passed. The tail canary plus the length floor is what actually
// says "the whole essay is here".
const CANARY_HEAD = 'Speed of iteration beats';
const CANARY_TAIL = 'A check only helps when it could have failed differently';
const MIN_BODY_CHARS = 11000;

// A literal, updated on purpose when a figure is added or removed. `> 0` passed
// happily when a figure was deleted along with its section.
const FIGURE_COUNT = 9;

const CLS_BUDGET = 0.1;

// Reserved minus intrinsic, in px. The two directions are different failures
// and get different budgets.
//
// UNDER is a box shorter than its figure, which moves the page. Zero tolerance:
// measure-figures.mjs biases every reserved height upward by FIT_PAD precisely
// so this can never happen, and if it does the fit is stale.
//
// OVER is cream under a figure. It never shifts anything, so the budget is
// loose: FIT_PAD is 24 of it by design, and the fit's error between the widths
// it sampled adds up to about 36 more (worst measured, dogfight at 445px). This
// number exists to catch a figure that shrank a lot without the sweep being
// rerun, not to police a few pixels of air.
const OVER_TOL = 72;
const UNDER_TOL = 0;

// Three widths for the browser checks, and a sweep for the box check. The sweep
// matters because 390 and 1440 are both sample points in measure-figures.mjs,
// where the fit is exact by construction. Testing only there tests nothing
// about the fit between samples, which is most of the range a reader uses.
const VIEWPORTS = [
  [390, 844, 'phone'],
  [768, 1024, 'tablet'],
  [1440, 900, 'desktop'],
];
const SWEEP = [
  280, 305, 330, 355, 380, 405, 445, 470, 500, 525, 570, 610, 660, 690, 730,
  775, 800, 850, 880, 930, 980, 1100, 1250, 1330, 1500, 1700, 1920, 2560,
];

let failures = 0;
const bad = (m) => {
  failures++;
  console.log(`  FAIL  ${m}`);
};
const ok = (m) => console.log(`  ok    ${m}`);

console.log(`\n=== ${TARGET} ===\n`);

// ---- 1. the HTML itself, no browser involved ---------------------------
const res = await fetch(TARGET);
const html = await res.text();
const visible = html
  .split('<div id="app">')[1]
  ?.replace(/<[^>]+>/g, ' ')
  .replace(/\s+/g, ' ')
  .trim() ?? '';

console.log(`html            ${res.status}  ${(html.length / 1024).toFixed(1)}KB  ${visible.length} visible chars`);
if (!res.ok) bad(`fetch returned ${res.status}`);
if (html.includes(CANARY_HEAD)) ok('prose from the opening is in the HTML');
else bad('the opening prose is NOT in the HTML — the page did not prerender, or a stale build is live');
if (html.includes(CANARY_TAIL)) ok('prose from the closing is in the HTML');
else bad('the closing prose is missing — the prerender truncated the essay');
if (visible.length >= MIN_BODY_CHARS) ok(`${visible.length} visible characters (floor ${MIN_BODY_CHARS})`);
else bad(`only ${visible.length} visible characters, floor is ${MIN_BODY_CHARS}`);

const figsInHtml = [...html.matchAll(/data-fig="([^"]+)"/g)].map((m) => m[1]);
if (figsInHtml.length === FIGURE_COUNT) ok(`${FIGURE_COUNT} figure boxes reserved: ${figsInHtml.join(', ')}`);
else bad(`${figsInHtml.length} figure boxes, expected exactly ${FIGURE_COUNT}: ${figsInHtml.join(', ') || 'none'}`);

// ---- 2. the link preview, which fails where nobody can see it -----------
//
// index.html says these break silently if the deploy subpath moves: the page
// still works, and only the card in somebody else's Slack goes blank. Nothing
// checked them until a review pointed out that deploying to a new subpath would
// pass every other assertion in this file.
const meta = (prop) =>
  html.match(new RegExp(`<meta\\s+property="${prop}"\\s+content="([^"]+)"`))?.[1] ?? null;
const base = new URL(TARGET);
const expectedPrefix = `${base.origin}${base.pathname}`;
// These tags are absolute by necessity, so against a local preview they name
// the production URL and can only ever mismatch. Say so and move on rather than
// training everyone to ignore two red lines on every local run.
const LOCAL = ['localhost', '127.0.0.1'].includes(base.hostname);
for (const prop of LOCAL ? [] : ['og:url', 'og:image']) {
  const value = meta(prop);
  if (!value) bad(`${prop} is missing`);
  else if (!value.startsWith(expectedPrefix)) bad(`${prop} is ${value}, which does not sit under ${expectedPrefix}`);
  else ok(`${prop} points inside the deployed path`);
}
if (LOCAL) console.log(`  --    og: tags name the production URL, not checked against a local preview`);
const ogImage = meta('og:image');
if (!LOCAL && ogImage?.startsWith(expectedPrefix)) {
  const head = await fetch(ogImage, { method: 'HEAD' }).catch(() => null);
  if (head?.ok) ok(`og:image fetches (${head.status})`);
  else bad(`og:image does not fetch: ${head ? head.status : 'request failed'}`);
}

// ---- 3. the URL without its trailing slash ------------------------------
//
// `base: './'` resolves assets against the URL's directory, so /reasoning-grid
// resolves ./assets/x.js to /assets/x.js and 404s the bundle and the
// stylesheet. Now that the prose is prerendered the page still paints, as an
// unstyled wall of serif text, which reads as "up" to anything automated.
// Checked in a browser rather than with fetch, because the fix is a redirect
// the page performs itself. CloudFront answers the bare URL with 200 and the
// prerendered essay, so a status code says nothing: the question is whether a
// reader who lands there ends up on a working page.
const BARE = base.pathname !== '/' && base.pathname.endsWith('/')
  ? `${base.origin}${base.pathname.replace(/\/$/, '')}`
  : null;

const browser = await chromium.launch();

// ---- 4. reserved height against the figure's own height ----------------
//
// The check that used to be a tautology. `reserved` is read off the CSSOM
// before anything can have changed it; `intrinsic` is the figure measured with
// the reservation forced to zero, which is the same trick measure-figures.mjs
// uses so that it cannot re-measure its own last answer.
{
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  await page.goto(TARGET, { waitUntil: 'networkidle' });

  const worst = new Map();
  for (const w of SWEEP) {
    await page.setViewportSize({ width: w, height: 1000 });
    await page.evaluate(async () => {
      const H = document.documentElement.scrollHeight;
      for (let y = 0; y < H; y += 700) {
        window.scrollTo(0, y);
        await new Promise((r) => setTimeout(r, 20));
      }
      window.scrollTo(0, 0);
    });
    await page.waitForTimeout(220);

    const rows = await page.evaluate(() => {
      const els = [...document.querySelectorAll('[data-fig]')];
      const reserved = els.map((el) => parseFloat(getComputedStyle(el).minHeight) || 0);
      const style = document.createElement('style');
      style.textContent = '[data-fig] { min-height: 0 !important; }';
      document.head.append(style);
      // Force layout with the reservation off, then read the figure itself.
      const intrinsic = els.map((el) => el.getBoundingClientRect().height);
      style.remove();
      return els.map((el, i) => ({
        name: el.getAttribute('data-fig'),
        reserved: Math.round(reserved[i]),
        intrinsic: Math.round(intrinsic[i]),
      }));
    });

    for (const r of rows) {
      const d = r.reserved - r.intrinsic;
      const prev = worst.get(r.name);
      if (!prev || d < prev.under) worst.set(r.name, { ...prev, under: d, underAt: w });
      const cur = worst.get(r.name);
      if (cur.over === undefined || d > cur.over) worst.set(r.name, { ...cur, over: d, overAt: w });
    }
  }
  await page.close();

  console.log(`\n--- reserved vs figure, ${SWEEP.length} widths from ${SWEEP[0]} to ${SWEEP[SWEEP.length - 1]} ---`);
  for (const [name, w] of [...worst].sort((a, b) => a[1].under - b[1].under)) {
    if (w.under < -UNDER_TOL) bad(`${name}: box is ${-w.under}px SHORT of its figure at ${w.underAt}px wide, so the page shifts`);
    else if (w.over > OVER_TOL) bad(`${name}: box is ${w.over}px taller than its figure at ${w.overAt}px wide, over the ${OVER_TOL}px budget`);
    else ok(`${name}: ${w.under >= 0 ? '+' : ''}${w.under}px to +${w.over}px across the sweep`);
  }
}

// ---- 5. per viewport: it mounted, it drew, it did not move --------------
for (const [w, h, label] of VIEWPORTS) {
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  const errors = [];
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
  page.on('pageerror', (e) => errors.push(String(e)));

  await page.addInitScript(() => {
    window.__cls = 0;
    new PerformanceObserver((l) => {
      for (const e of l.getEntries()) if (!e.hadRecentInput) window.__cls += e.value;
    }).observe({ type: 'layout-shift', buffered: true });
  });

  await page.goto(TARGET, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);

  const { cls, pending, drew } = await page.evaluate(() => ({
    cls: window.__cls,
    pending: document.querySelectorAll('[data-fig].pending').length,
    // Mounting proves JavaScript ran. It does not prove anything was drawn: a
    // figure whose width observer never fires renders an empty box at exactly
    // the right height, with no error, no shift, and no .pending. Ask for a
    // canvas or an svg with real dimensions instead.
    drew: [...document.querySelectorAll('[data-fig]')]
      .filter((el) => {
        // Not just canvas or svg: the allocation grid is a table of coloured
        // divs, and asking only for a drawing surface reported it blank at
        // every width. Any figure that put real, sized content in its box
        // counts.
        const c = el.querySelector('canvas, svg');
        if (c) {
          const r = c.getBoundingClientRect();
          return r.width > 8 && r.height > 8;
        }
        return el.querySelectorAll('*').length > 8 && el.getBoundingClientRect().height > 40;
      })
      .map((el) => el.getAttribute('data-fig')),
  }));

  console.log(`\n--- ${label} (${w}px) ---`);
  if (pending === 0) ok('every figure mounted');
  else bad(`${pending} figure(s) never mounted`);

  const blank = figsInHtml.filter((n) => !drew.includes(n));
  if (blank.length === 0) ok('every figure drew something');
  else bad(`${blank.length} figure(s) mounted but drew nothing: ${blank.join(', ')}`);

  if (errors.length === 0) ok('no console errors');
  else bad(`${errors.length} console error(s): ${[...new Set(errors)].slice(0, 3).join(' ;; ')}`);

  if (cls <= CLS_BUDGET) ok(`CLS ${cls.toFixed(4)} (budget ${CLS_BUDGET})`);
  else bad(`CLS ${cls.toFixed(4)} over budget ${CLS_BUDGET}`);

  await page.close();
}

// ---- 6. the page with JavaScript off -----------------------------------
//
// The reader this whole change was made for, and the one no other check here
// sees, because every other check runs a browser with scripting on.
{
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, javaScriptEnabled: false });
  const page = await ctx.newPage();
  await page.goto(TARGET, { waitUntil: 'load' });
  const r = await page.evaluate(() => ({
    docHeight: document.documentElement.scrollHeight,
    alts: document.querySelectorAll('[data-fig] .alt').length,
    // naturalWidth, not the count of <img> tags. A broken src still renders an
    // element, and a figure standing in for a figure is the one asset here
    // whose 404 nobody would ever see.
    stills: document.querySelectorAll('[data-fig] img.still').length,
    stillsLoaded: [...document.querySelectorAll('[data-fig] img.still')]
      .filter((i) => i.naturalWidth > 0).length,
    buttons: [...document.querySelectorAll('button')].length,
    // The box's own height is not the test: with the reservation released it
    // still stands as tall as the description inside it. Ask the CSSOM whether
    // anything is being held open.
    reserved: [...document.querySelectorAll('[data-fig]')]
      .filter((el) => (parseFloat(getComputedStyle(el).minHeight) || 0) > 0).length,
    text: document.body.innerText.length,
  }));
  console.log(`\n--- no JavaScript (390px) ---`);
  if (r.text > 8000) ok(`${r.text} characters of readable text`);
  else bad(`only ${r.text} characters readable without JavaScript`);
  if (r.alts === FIGURE_COUNT) ok(`all ${FIGURE_COUNT} figures carry a written description`);
  else bad(`${r.alts} of ${FIGURE_COUNT} figures have a description`);
  if (r.stills === FIGURE_COUNT) ok(`all ${FIGURE_COUNT} figures carry a picture`);
  else bad(`${r.stills} of ${FIGURE_COUNT} figures have a picture`);
  if (r.stillsLoaded === r.stills) ok(`all ${r.stills} pictures loaded`);
  else bad(`${r.stills - r.stillsLoaded} picture(s) failed to load — check the paths under ./figures/`);
  if (r.reserved === 0) ok('no figure holds empty space open');
  else bad(`${r.reserved} figure box(es) still reserve height for a figure that cannot arrive`);
  if (r.buttons === 0) ok('no controls offered that cannot work');
  else bad(`${r.buttons} button(s) rendered that do nothing without JavaScript`);
  await ctx.close();
}

// ---- 7. the URL without its trailing slash ------------------------------
if (BARE) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(BARE, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);
  const r = await page.evaluate(() => ({
    path: location.pathname,
    styled: getComputedStyle(document.body).backgroundColor,
    mounted: document.querySelectorAll('[data-fig].pending').length,
    figs: document.querySelectorAll('[data-fig]').length,
  }));
  console.log(`\n--- ${BARE} (no trailing slash) ---`);
  if (r.path.endsWith('/')) ok(`lands on ${r.path}`);
  else bad(`stays on ${r.path}, where every relative asset resolves to the site root`);
  if (r.figs > 0 && r.mounted === 0) ok('the page works from there');
  else bad(`${r.mounted} of ${r.figs} figures unmounted — the bundle did not load`);
  await page.close();
}

await browser.close();
console.log(`\n${failures === 0 ? 'PASS' : `FAIL — ${failures} problem(s)`}\n`);
process.exit(failures === 0 ? 0 : 1);
