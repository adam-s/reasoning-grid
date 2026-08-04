/**
 * Sabre win rate against the MiG pilot's per-cycle loop tax, over a sample of
 * merges. Prints a table; writes nothing.
 *
 *     node --experimental-strip-types scripts/dogfight-curve.mjs
 *
 * This used to generate `src/lib/data/dogfight-curve.ts`, which the figure drew
 * beside the fight. The figure no longer shows that curve, so the module it fed
 * is gone and this script is now a REPRODUCTION CHECK rather than a build step:
 * the one number the component still inherits from it is `TAX`, fixed at the
 * even-odds crossing. Nothing on the page demonstrates that crossing any more,
 * which is exactly why the means of re-deriving it should not have been deleted
 * along with the chart.
 *
 * A single fight settles nothing — a turning fight is chaotic and one
 * trajectory flips sign at random across the tax. That is what the ensemble is
 * for, and why the count is 120 rather than 1.
 */
import { ensemble, SABRE, MIG } from '../src/lib/viz/opener/dogfight.ts';

const N = 120;
const SEED = 12345;
const TAXES = Array.from({ length: 21 }, (_, i) => i * 0.005);

const t0 = Date.now();
const points = ensemble(TAXES, N, SEED);
const secs = ((Date.now() - t0) / 1000).toFixed(1);

console.log(`${points.length} tax values x ${N} merges (seed ${SEED}) in ${secs}s`);
console.log(`F-86 loop ${SABRE.loop0}s fixed; ${MIG.name} starts equal and grows by tax each cycle.\n`);
console.log('  tax     F-86 wins    rate   Wilson 95%');
for (const p of points) {
  console.log(
    `  ${p.tax.toFixed(3)}   ${String(p.wins).padStart(3)}/${p.n}     ` +
      `${(p.rate * 100).toFixed(0).padStart(3)}%   ` +
      `[${(p.lo * 100).toFixed(0)}, ${(p.hi * 100).toFixed(0)}]`,
  );
}
const cross = points.find((p) => p.rate >= 0.5);
console.log(
  cross
    ? `\ncrosses even odds at tax ${cross.tax.toFixed(3)} — this is the value TAX is pinned to`
    : '\nnever reaches even odds',
);
