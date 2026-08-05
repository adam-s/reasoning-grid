// Measure every figure's rendered height across widths, and write the CSS that
// holds its box open before it mounts.
//
//   node scripts/measure-figures.mjs [url]        # writes src/lib/viz/figure-heights.css
//   node scripts/measure-figures.mjs [url] --check # exits 1 if the file is stale
//
// Why a script and not a hand-written stylesheet: these figures do not share
// breakpoints and do not scale by aspect ratio. The opener is 510px tall on a
// phone and 517px on a desktop three times as wide. The trace figure is 891px
// tall on a phone and 542px on a tablet, so it gets SHORTER as the screen
// widens. Any single rule is wrong somewhere, and the only way to know the
// right numbers is to render the page and read them off.
//
// Rerun this whenever a figure's layout changes. `--check` in CI catches the
// case where someone changes a figure and forgets.
import { chromium } from '@playwright/test';
import { readFileSync, writeFileSync } from 'node:fs';

const TARGET = process.argv[2] || 'http://localhost:5177/';
const CHECK = process.argv.includes('--check');
const OUT = new URL('../src/lib/viz/figure-heights.css', import.meta.url);

// The site's own breakpoints are scattered (560, 600, 620, 640, 700, 720, 760,
// 900), so sweep either side of each one rather than on a regular grid. A
// regular sweep straddles a breakpoint and averages across it.
const WIDTHS = [
  320, 360, 390, 430, 480, 540, 559, 561, 599, 601, 619, 621, 639, 641,
  699, 701, 719, 721, 759, 761, 820, 899, 901, 1024, 1200, 1440,
];

// Two heights this close are the same height. Below this, rounding and font
// metrics move a box a pixel or two between widths and every measurement
// becomes its own media query.
const TOL = 8;

// A height change this big between two widths is a reflow, not a slope, and
// the sweep goes looking for exactly where it happens.
const JUMP = 40;

const b = await chromium.launch();
const page = await b.newPage({ viewport: { width: 1440, height: 1000 } });
// Measure the figure, not the box that is already holding a height for it.
// figure-heights.css applies whether or not the figure has mounted, so without
// this the script would re-measure its own last answer and the numbers could
// only ever ratchet upward.
await page.addInitScript(() => {
  document.addEventListener('DOMContentLoaded', () => {
    const s = document.createElement('style');
    s.textContent = '[data-fig] { min-height: 0 !important; }';
    document.head.append(s);
  });
});
await page.goto(TARGET, { waitUntil: 'networkidle' });

/** @type {Map<number, Record<string, number>>} width -> figure -> height */
const at = new Map();

async function measure(w) {
  if (at.has(w)) return at.get(w);
  await page.setViewportSize({ width: w, height: 1000 });
  // Everything has to have been on screen once: figures that mount on
  // intersection report height 0 until they do.
  await page.evaluate(async () => {
    const H = document.documentElement.scrollHeight;
    for (let y = 0; y < H; y += 600) {
      window.scrollTo(0, y);
      await new Promise((r) => setTimeout(r, 30));
    }
    window.scrollTo(0, 0);
  });
  await page.waitForTimeout(400);
  const boxes = await page.evaluate(() =>
    Object.fromEntries(
      [...document.querySelectorAll('[data-fig]')].map((el) => [
        el.getAttribute('data-fig'),
        Math.round(el.getBoundingClientRect().height),
      ]),
    ),
  );
  at.set(w, boxes);
  return boxes;
}

for (const w of WIDTHS) await measure(w);

/**
 * Find every reflow to the pixel.
 *
 * The scattered `max-width` rules in the stylesheets are not the whole story:
 * the opener figure picks its column count in JS from the measured width
 * (IterationRings, R_OUT), so it steps at a width no stylesheet mentions. Any
 * pair of samples with a jump between them gets bisected until the two sides of
 * the step are one pixel apart, wherever the step came from.
 */
for (let pass = 0; pass < 40; pass++) {
  const ws = [...at.keys()].sort((x, y) => x - y);
  let found = null;
  for (let i = 0; i < ws.length - 1; i++) {
    const [w0, w1] = [ws[i], ws[i + 1]];
    if (w1 - w0 <= 1) continue;
    const [a, c] = [at.get(w0), at.get(w1)];
    const worst = Math.max(...Object.keys(a).map((k) => Math.abs(c[k] - a[k])));
    if (worst > JUMP) {
      found = [w0, w1, worst];
      break;
    }
  }
  if (!found) break;
  const [w0, w1, worst] = found;
  const mid = Math.floor((w0 + w1) / 2);
  await measure(mid);
  console.error(`  bisect ${w0}-${w1} (${worst}px jump) -> probed ${mid}`);
}

/** @type {Record<string, Array<{w: number, h: number}>>} */
const series = {};
for (const w of [...at.keys()].sort((x, y) => x - y)) {
  for (const [name, h] of Object.entries(at.get(w))) (series[name] ??= []).push({ w, h });
}
await b.close();

for (const w of [...at.keys()].sort((x, y) => x - y)) {
  const row = at.get(w);
  console.error(
    `  ${String(w).padStart(4)}px  ${Object.entries(row).map(([k, v]) => `${k}:${v}`).join('  ')}`,
  );
}

const names = Object.keys(series).sort();
if (!names.length) {
  console.error('No [data-fig] elements found. Is the dev server running that URL?');
  process.exit(1);
}

/**
 * Collapse a width->height series into as few straight segments as will still
 * pass within TOL of every measured point.
 *
 * A flat `min-height` per band is not good enough here. Almost every figure on
 * this page grows continuously with the viewport — the allocation grid runs
 * 543px at 320 wide up to 928px at 759 — so a single number per band is right
 * at the edges and tens of pixels wrong in the middle, which is exactly the
 * shift this whole exercise exists to prevent. A segment is emitted as
 * `calc(Apx + Bvw)`, which is the line through its two endpoints, so the
 * reserved height is exact at both ends and interpolates between them.
 *
 * Greedy: extend the current segment while the line from its start to the
 * candidate end stays within TOL of every point it spans. A real breakpoint
 * shows up as a jump no line can cover, and the segment closes there.
 */
function segments(points) {
  const out = [];
  let i = 0;
  while (i < points.length - 1) {
    let j = i + 1;
    // Push j out as far as a straight line from i still explains everything.
    while (j + 1 < points.length && fits(points, i, j + 1)) j++;
    out.push({ from: points[i].w, to: points[j].w, h0: points[i].h, h1: points[j].h });
    i = j;
  }
  if (!out.length) {
    const only = points[0];
    out.push({ from: only.w, to: only.w, h0: only.h, h1: only.h });
  }
  return out;
}

/**
 * Cut the series where this figure actually steps.
 *
 * Two conditions, and both are needed. The samples must be a couple of pixels
 * apart, which marks them as the deliberate probes either side of a breakpoint
 * rather than points on a slope -- fitting a line across a 2px gap gives a
 * slope like -16500vw, numerically right over the two pixels it covers and
 * nonsense as a rule. And the height must actually jump.
 *
 * The height test is what makes this per figure. The sweep probes either side
 * of every breakpoint ANY figure has, and bisection adds more, so a figure that
 * does not care about a given width still has a sample pair sitting there.
 * Splitting on the width gap alone published those as steps: allocation ended
 * up with 711px at 542 and 696px at 543, a 15px disagreement one pixel apart
 * that is measurement noise across a re-layout, not a breakpoint. A reader
 * resizing through 542 would have watched the box twitch for no reason.
 */
function split(points) {
  const groups = [[points[0]]];
  for (let i = 1; i < points.length; i++) {
    const closeInWidth = points[i].w - points[i - 1].w <= 4;
    const jumps = Math.abs(points[i].h - points[i - 1].h) > TOL;
    if (closeInWidth && jumps) groups.push([points[i]]);
    else groups[groups.length - 1].push(points[i]);
  }
  return groups;
}

function fits(points, i, j) {
  const { w: w0, h: h0 } = points[i];
  const { w: w1, h: h1 } = points[j];
  const slope = (h1 - h0) / (w1 - w0);
  for (let k = i + 1; k < j; k++) {
    const predicted = h0 + slope * (points[k].w - w0);
    if (Math.abs(predicted - points[k].h) > TOL) return false;
  }
  return true;
}

/** The line through two measured points, as a CSS length. */
function line(seg) {
  // A group of one: the far side of a reflow that bisection pinned to a single
  // pixel. It holds until the next rule takes over, so it is a flat height.
  if (seg.to === seg.from) return `${seg.h0}px`;
  const slope = (seg.h1 - seg.h0) / (seg.to - seg.from);
  if (Math.abs(slope) < 0.002) return `${Math.max(seg.h0, seg.h1)}px`;
  const intercept = seg.h0 - slope * seg.from;
  // 100vw is the viewport width, so a slope per px becomes a coefficient on vw.
  return `calc(${intercept.toFixed(1)}px + ${(slope * 100).toFixed(3)}vw)`;
}

const lines = [
  '/* GENERATED by scripts/measure-figures.mjs -- do not edit by hand.',
  ' *',
  ' * The height each figure box holds open before its figure mounts, measured',
  ' * off the real page at 26 widths. Rerun the script after any change to a',
  ' * figure\'s layout; `--check` fails if these numbers no longer match.',
  ' *',
  ' * The height applies whether or not the figure has mounted. Releasing it on',
  ' * mount collapsed the box for the frame between the figure rendering and its',
  ' * canvas sizing itself, which cost 0.23 of CLS on a phone -- the exact shift',
  ' * the reservation exists to prevent. It is a min-height, so a figure that',
  ' * grows past it is unaffected.',
  ' */',
  '',
];

for (const name of names) {
  const pts = series[name];
  const segs = split(pts).flatMap(segments);
  lines.push(
    `/* ${name}: ${pts[0].h}px at ${pts[0].w} wide, ${pts[pts.length - 1].h}px at ${pts[pts.length - 1].w}, ` +
      `${segs.length} rule${segs.length === 1 ? '' : 's'} */`,
  );
  // A rule that restates the one before it is noise. The sweep probes either
  // side of every breakpoint ANY figure has, so a figure that does not care
  // about a given breakpoint still gets a sample pair there. Left alone that
  // emitted `min-height: 229px` eighteen times for grid-key, and gave
  // allocation two rules a pixel apart that disagreed by 15px -- measurement
  // noise across a re-layout, published as if it were a breakpoint.
  let last = null;
  segs.forEach((seg, i) => {
    const value = line(seg);
    if (value === last) return;
    last = value;
    const sel = `[data-fig='${name}'] { min-height: ${value}; }`;
    // Below the first sample the first rule's line still applies; above the
    // last, the last one holds. Neither end extrapolates far enough at any real
    // viewport width to need a clamp.
    lines.push(i === 0 ? sel : `@media (min-width: ${seg.from}px) { ${sel} }`);
  });
  lines.push('');
}

const css = lines.join('\n');
const prev = (() => {
  try {
    return readFileSync(OUT, 'utf8');
  } catch {
    return null;
  }
})();

if (CHECK) {
  if (prev !== css) {
    console.error('figure-heights.css is stale. Run: node scripts/measure-figures.mjs');
    process.exit(1);
  }
  console.error('figure-heights.css is current.');
} else {
  writeFileSync(OUT, css);
  console.error(`\nwrote ${OUT.pathname} (${names.length} figures)`);
}
