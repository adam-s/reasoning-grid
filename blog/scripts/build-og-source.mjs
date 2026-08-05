// Regenerate the surface screenshot the social card is built from.
//
//   npm run preview
//   node scripts/build-og-source.mjs [url]
//   node scripts/build-og-card.mjs        # then rebuild the card itself
//
// Why this exists: `assets/og-source-surface.png` was a screenshot somebody
// took by hand and committed. That made it unregenerable, so when the
// convergence rail was recoloured from a flat navy to the surface's own ramp,
// the card kept advertising a figure the page no longer draws, and nothing
// could notice. The repo's rule is that a published artifact is produced by a
// committed script; this is the missing script.
//
// Run it against the PREVIEW, not the dev server. The card should show what
// ships.
import { chromium } from '@playwright/test';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const TARGET = process.argv[2] || 'http://localhost:4173/';
const OUT = join(dirname(fileURLToPath(import.meta.url)), '../assets/og-source-surface.png');

// The size the committed image already was, kept so `object-position` in
// build-og-card.mjs still crops to the same part of the figure.
const WIDTH = 943;
const HEIGHT = 569;

// Far enough into the scrub that the surface has its shape and the rail has
// spread across the ramp. At trial 1 every cell is 0% or 100% and the card
// would show a cliff.
const TRIAL = 20;

const b = await chromium.launch();
const page = await b.newPage({
  viewport: { width: WIDTH, height: HEIGHT + 400 },
  deviceScaleFactor: 2,
});
await page.goto(TARGET, { waitUntil: 'networkidle' });

const fig = page.locator('[data-fig="surface"]');
await fig.scrollIntoViewIfNeeded();
await page.waitForTimeout(600);

const slider = page.locator('input[type=range]').last();
await slider.evaluate((el, v) => {
  const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  set.call(el, String(v));
  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
}, TRIAL);
await page.waitForTimeout(900);

await fig.screenshot({ path: OUT });
await b.close();
console.log(`wrote ${OUT} at ${WIDTH}x${HEIGHT} @2x, trial ${TRIAL}`);
