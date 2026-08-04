// Chaos test for the opener's interactive state.
//
//   npm run dev                 # in another terminal
//   node scripts/chaos.mjs [rounds] [url]
//
// The figure, the two moment rows and the guided cue share one cursor and one
// lock between them, and the reader is free to hit any of it in any order at
// any moment, including mid-animation. That is more orderings than anyone can
// hold in their head, so this clicks at random and checks the invariants that
// have to survive every one of them.
//
// It asserts PROPERTIES, not a script. A test that walks the happy path proves
// the happy path works, which was never the thing in doubt.

import { chromium } from '@playwright/test';

const ROUNDS = Number(process.argv[2] ?? 60);
const URL = process.argv[3] ?? 'http://localhost:5176/';

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 1000 } });

// A page error is a failure on its own. Chaos that throws has already lost,
// whatever the DOM looks like afterwards.
const errors = [];
page.on('pageerror', (e) => errors.push(String(e)));
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });

await page.goto(URL, { waitUntil: 'networkidle' });
await page.waitForTimeout(600);

/** Everything a reader can hit in this section. */
async function targets() {
  const all = [];
  const push = async (loc, kind) => {
    const n = await loc.count();
    for (let i = 0; i < n; i++) all.push({ loc: loc.nth(i), kind });
  };
  await push(page.locator('.moments button'), 'moment');
  await push(page.locator('.tour-start button'), 'start');
  await push(page.locator('.synced .tabs button'), 'tab');
  await push(page.locator('.synced .play'), 'play');
  await push(page.locator('.synced .flame-rect'), 'flame');
  return all;
}

const failures = [];
function check(cond, label, detail = '') {
  if (!cond) failures.push(`${label}${detail ? ` (${detail})` : ''}`);
}

/**
 * The invariants. Every one of these is a rule the interface states somewhere,
 * so a violation is a contradiction rather than a matter of taste.
 */
async function invariants(where) {
  const state = await page.evaluate(() => {
    const cues = [...document.querySelectorAll('.cue')];
    const momentBtns = [...document.querySelectorAll('.moments button')];
    const startBtn = document.querySelector('.tour-start button');
    const cueOwners = cues.map((c) => {
      const btn = c.parentElement?.querySelector('button');
      return { disabled: btn ? btn.disabled : null, text: btn?.innerText ?? null };
    });
    return {
      cueCount: cues.length,
      cueOwners,
      current: momentBtns.filter((b) => b.getAttribute('aria-current') === 'true').length,
      anyDisabled: momentBtns.some((b) => b.disabled) || !!startBtn?.disabled,
      allDisabled: momentBtns.every((b) => b.disabled) && !!startBtn?.disabled,
      cuePointerEvents: cues.map((c) => getComputedStyle(c).pointerEvents),
    };
  });

  check(state.cueCount <= 1, `${where}: more than one cue on the page`, `${state.cueCount}`);
  check(state.current <= 1, `${where}: more than one current moment`, `${state.current}`);
  for (const o of state.cueOwners) {
    check(o.disabled !== true, `${where}: cue points at a disabled control`, o.text ?? '');
  }
  for (const pe of state.cuePointerEvents) {
    check(pe === 'none', `${where}: cue can swallow clicks`, pe);
  }
  // Disabling is all-or-nothing. A half-disabled row means the lock leaked into
  // some controls and not others.
  check(
    !state.anyDisabled || state.allDisabled,
    `${where}: only some controls are disabled`,
  );
  return state;
}

await invariants('start');

// Deterministic pseudo-random, so a failure can be reproduced by rerunning.
let seed = 20260803;
const rand = () => ((seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff);

for (let i = 0; i < ROUNDS; i++) {
  const all = await targets();
  const pick = all[Math.floor(rand() * all.length)];
  try {
    // force, because half the point is clicking things mid-animation. timeout
    // short, because a control that never becomes clickable is itself the bug
    // and should not hang the run.
    await pick.loc.click({ force: true, timeout: 900 });
  } catch {
    // A refused click is fine. A stuck page is caught by the settle check.
  }
  // Land inside the animation window sometimes and after it other times.
  await page.waitForTimeout(rand() < 0.5 ? 120 : 1300);
  await invariants(`round ${i + 1} after ${pick.kind}`);
}

// THE ONE THAT MATTERS MOST. After the noise stops, everything must come back.
// A leaked lock leaves the whole section dead with no way out but a reload.
await page.waitForTimeout(2500);
const final = await invariants('settled');
check(!final.anyDisabled, 'settled: controls still disabled after everything stopped');

check(errors.length === 0, 'page threw', errors.slice(0, 3).join(' | '));

await browser.close();

if (failures.length) {
  console.error(`FAIL after ${ROUNDS} rounds\n  ` + failures.join('\n  '));
  process.exit(1);
}
console.log(`ok: ${ROUNDS} random rounds, all invariants held`);
