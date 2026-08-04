// The favicon is the hero figure at 32px: concentric rings in the four OODA
// phase colours.
//   node scripts/build-favicon.mjs
//
// GENERATED, NOT DRAWN, because the colours belong to design/ooda.ts and a
// hand-written hex in an svg is a copy that drifts the first time the scheme
// moves. Rerun this after any change there.
//
// Six rings, not twenty. The real figure draws one band per iteration and at
// 32px that is a grey smear, so this keeps the thing that reads at tab size --
// concentric, four colours, a pale core -- and drops the count.
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));

// ooda.ts is TypeScript, so the hexes are read out of the source rather than
// imported. One regex per phase, and it throws if the shape changes.
const src = readFileSync(join(here, '../src/lib/design/ooda.ts'), 'utf8');

const phase = (name) => {
  const m = src.match(new RegExp(`${name}:\\s*\\{[^}]*?color:\\s*'(#[0-9a-fA-F]{6})'`, 's'));
  if (!m) throw new Error(`no colour found for ${name} in design/ooda.ts`);
  return m[1];
};

const OBSERVE = phase('OBSERVE');
const ORIENT = phase('ORIENT');
const DECIDE = phase('DECIDE');
const ACT = phase('ACT');

// NO BACKGROUND RECT. A tab strip is not always the page's cream: browsers
// render favicons on their own chrome, dark mode included, and a baked-in
// light square shows up as a bright tile around the mark. Transparent lets the
// rings sit on whatever is behind them.
const CORE = '#e8e4dc'; // --line, the pale hub the figure draws

// Outermost first, cycling the phases the way a run does.
const RINGS = [
  [15.0, ACT],
  [12.7, OBSERVE],
  [10.4, DECIDE],
  [8.1, ORIENT],
  [5.8, ACT],
  [3.5, OBSERVE],
];

const circles = RINGS.map(
  ([r, c]) => `<circle cx="16" cy="16" r="${r}" fill="none" stroke="${c}" stroke-width="1.7"/>`,
).join('');

const svg =
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">` +
  circles +
  `<circle cx="16" cy="16" r="1.9" fill="${CORE}"/>` +
  `</svg>`;

const out = join(here, '../public/favicon.svg');
writeFileSync(out, svg + '\n');
console.log(`wrote ${out}`);
console.log(`  observe ${OBSERVE}  orient ${ORIENT}  decide ${DECIDE}  act ${ACT}`);
