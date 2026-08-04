// Does the page's data support what the page says about it?
//   node scripts/check-data.mjs [url]
// Imports each data module through the dev server (so Vite compiles the .ts for
// us) and recomputes every quantity a caption or a paragraph asserts.
import { chromium } from '@playwright/test';

const URL = process.argv[2] || 'http://localhost:5175/';
const b = await chromium.launch();
const page = await b.newPage();
await page.goto(URL, { waitUntil: 'networkidle' });

const out = await page.evaluate(async () => {
  const { WINNER } = await import('/src/lib/data/winner.ts');
  const { SURFACE } = await import('/src/lib/data/surface.ts');
  const { ALLOCATION } = await import('/src/lib/data/allocation.ts').catch(() => ({}));
  const { THINKING_MIX } = await import('/src/lib/data/thinking-mix.ts');
  const { OPENER } = await import('/src/lib/data/opener.ts');
  const { CARRY_TRACES } = await import('/src/lib/data/reasoning-grid-traces.ts');
  const { SCORES, SCORES_GROUP } = await import('/src/lib/data/sampling.ts');

  const r = {};

  // ---- WINNER, behind BoundaryWedge -------------------------------------
  const wKeys = Object.keys(WINNER.cells);
  const maxDim = Math.max(...wKeys.flatMap((k) => k.split('x').map(Number)));
  r.winner = {
    cells: wKeys.length,
    dim: WINNER.dim,
    maxDigitSeen: maxDim,
    has2x14: wKeys.includes('2x14'),
    has8x8: wKeys.includes('8x8'),
    qwenAt8x8: WINNER.cells['8x8']?.qwen ?? null,
    problems: WINNER.problems,
    findings: WINNER.findings,
    dotsDrawn: wKeys.length * 2,
  };
  // Both circles for a cell share cx (the total a+b); they hide each other
  // wherever the two rates are equal.
  const seen = new Set();
  let hidden = 0;
  for (const [k, c] of Object.entries(WINNER.cells)) {
    const [a, bb] = k.split('x').map(Number);
    for (const p of [c.qwen, c.phi]) {
      const key = `${a + bb}|${p}`;
      if (seen.has(key)) hidden++;
      else seen.add(key);
    }
  }
  r.winner.distinctDotPositions = seen.size;
  r.winner.dotsHiddenUnderOthers = hidden;

  // ---- SURFACE ----------------------------------------------------------
  const lens = Object.values(SURFACE.cells).map((o) => o.length);
  r.surface = {
    cells: Object.keys(SURFACE.cells).length,
    outcomesField: SURFACE.outcomes,
    outcomesCounted: lens.reduce((a, c) => a + c, 0),
    maxTrials: SURFACE.maxTrials,
    maxTrialsCounted: Math.max(...lens),
    cellsWithAtLeast29: lens.filter((n) => n >= 29).length,
    cellsWithMoreThan29: lens.filter((n) => n > 29).length,
    outcomesBeyond29: lens.reduce((a, n) => a + Math.max(0, n - 29), 0),
  };
  // What truncating at 29 does to the cells that have more.
  r.surface.truncated = Object.entries(SURFACE.cells)
    .filter(([, o]) => o.length > 29)
    .map(([k, o]) => {
      const rate = (arr) => arr.filter(Boolean).length / arr.length;
      return { cell: k, n: o.length, at29: +rate(o.slice(0, 29)).toFixed(4), atAll: +rate(o).toFixed(4) };
    });

  // ---- ALLOCATION -------------------------------------------------------
  if (ALLOCATION) {
    const aCells = ALLOCATION.cells ?? ALLOCATION;
    const list = Array.isArray(aCells) ? aCells : Object.values(aCells);
    r.allocation = {
      cells: list.length,
      totalRuns: list.reduce((a, c) => a + (c.runs ?? 0), 0),
      maxA: Math.max(...list.map((c) => c.a ?? 0)),
      maxB: Math.max(...list.map((c) => c.b ?? 0)),
    };
  }

  // ---- THINKING_MIX -----------------------------------------------------
  r.thinkingMix = {
    segmentsField: THINKING_MIX.segments,
    segmentsSummed: THINKING_MIX.models.reduce((a, m) => a + m.segments, 0),
    traces: THINKING_MIX.models.reduce((a, m) => a + m.traces, 0),
    models: THINKING_MIX.models.map((m) => m.model),
  };

  // ---- OPENER / IterationRings ------------------------------------------
  // Angular share equals character share by construction. Painted area does
  // not: the ribbon is a constant width at a radius that grows across the
  // spiral, so a character late in a run covers more ink than one early on.
  const { CATEGORY_PHASE } = await import('/src/lib/design/ooda.ts');
  const R_IN_FRAC = 0.11;
  r.rings = OPENER.map((t) => {
    const laps = [];
    let cur = [];
    for (const s of t.segments) {
      const ph = CATEGORY_PHASE[s.category] ?? 'UNPHASED';
      cur.push({ ph, chars: s.end - s.start });
      if (ph === 'ACT') { laps.push(cur); cur = []; }
    }
    if (cur.length) laps.push(cur);
    const total = laps.flat().reduce((a, s) => a + s.chars, 0) || 1;
    const L = laps.length;
    const rIn = R_IN_FRAC, rOut = 1;
    // radius grows linearly with cumulative angle across the whole spiral
    const radAt = (frac) => rIn + (rOut - rIn) * frac;
    const chars = {}, area = {};
    let c = 0;
    for (const s of laps.flat()) {
      const f0 = c / total, f1 = (c + s.chars) / total;
      // area of a constant-width ribbon over an angular sweep at radius r is
      // proportional to the integral of r dtheta, i.e. mean radius x sweep
      const sweep = f1 - f0;
      const meanR = (radAt(f0) + radAt(f1)) / 2;
      chars[s.ph] = (chars[s.ph] || 0) + s.chars;
      area[s.ph] = (area[s.ph] || 0) + sweep * meanR;
      c += s.chars;
    }
    const areaTot = Object.values(area).reduce((a, x) => a + x, 0) || 1;
    const share = {};
    for (const k of new Set([...Object.keys(chars), ...Object.keys(area)])) {
      share[k] = {
        chars: +((chars[k] || 0) / total * 100).toFixed(1),
        ink: +((area[k] || 0) / areaTot * 100).toFixed(1),
      };
    }
    return { key: t.key, verdict: t.verdict, cell: t.cell, laps: L, share };
  });

  // ---- CARRY_TRACES, the Locked claim in App.svelte ----------------------
  const traceList = Array.isArray(CARRY_TRACES) ? CARRY_TRACES : Object.values(CARRY_TRACES);
  const locked = traceList.find((t) => Array.isArray(t?.segments)
    && (/lock/i.test(t.verdict || '') || /lock/i.test(t.key || '')));
  if (locked) {
    const loop = locked.segments.filter((s) => s.category === 'LOOP').length;
    r.locked = {
      key: locked.key, cell: locked.cell,
      segments: locked.segments.length,
      loopSegments: loop,
      loopPct: +((loop / locked.segments.length) * 100).toFixed(1),
    };
  }

  // ---- SAMPLING, behind DistributionPanels ------------------------------
  r.sampling = {
    groups: SCORES.length,
    perGroup: SCORES_GROUP,
    total: SCORES.reduce((a, c) => a + c, 0),
  };

  r.carryShape = Array.isArray(CARRY_TRACES) ? 'array' : Object.keys(CARRY_TRACES).slice(0, 6);
  return r;
});

console.log(JSON.stringify(out, null, 2));
await b.close();
