<script lang="ts">
  /**
   * Sparklines down the dead space beside the surface, scrubbing in step with it.
   *
   * The surface answers "what shape is it"; these answer "how much of any one
   * number do we actually have". Each line is a cell's running pass rate against
   * trial index, with a dot at the trial the scrubber is on.
   *
   * Eight cells, one per band of the rate range, each the best-measured cell in
   * its band. Picking the best-measured cells outright instead returns eight
   * sitting between 74% and 98%, because that is where the long runs went — the
   * sweep meant to spend them near 50%. The trial count beside each label shows
   * it: 29 at the top of the range, 14 at the bottom. Eight bands is what the
   * height allows and every one of them has a cell in it.
   *
   * Rows rank by their rate AT THE CURRENT TRIAL, so the number always agrees
   * with the position. They overtake each other as the scrub runs, which is the
   * honest picture — early on these cells are not in their final order.
   */
  import { flip } from 'svelte/animate';
  import { MediaQuery } from 'svelte/reactivity';
  import { SURFACE } from '../../data/surface';

  const reduced = new MediaQuery('(prefers-reduced-motion: reduce)');

  type Props = { t: number; max: number };
  let { t, max }: Props = $props();

  const W = 128;
  const H = 22;

  type Line = { cell: string; n: number; run: number[] };

  const lines = $derived.by((): Line[] => {
    const all = Object.entries(SURFACE.cells).map(([cell, o]) => {
      const n = Math.min(o.length, max);
      const run: number[] = [];
      let k = 0;
      for (let i = 0; i < n; i++) {
        k += o[i];
        run.push(k / (i + 1));
      }
      return { cell, n, run, p: run[n - 1] ?? 0 };
    });
    const BANDS = 8;
    const out: Line[] = [];
    for (let b = BANDS - 1; b >= 0; b--) {
      const hi = b === BANDS - 1 ? 1.01 : (b + 1) / BANDS;
      const band = all.filter((c) => c.p >= b / BANDS && c.p < hi);
      if (band.length) {
        const best = band.reduce((x, c) => (c.n > x.n ? c : x));
        out.push({ cell: best.cell, n: best.n, run: best.run });
      }
    }
    return out;
  });

  const at = (l: Line, upto: number) => l.run[Math.min(upto, l.n) - 1] ?? -1;
  const ranked = $derived([...lines].sort((a, b) => at(b, t) - at(a, t)));

  const x = (i: number) => (i / (Math.max(2, max) - 1)) * W;

  const path = (l: Line, upto: number) => {
    const m = Math.min(upto, l.n);
    return m < 1
      ? ''
      : l.run
          .slice(0, m)
          .map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${(H - p * H).toFixed(1)}`)
          .join(' ');
  };
</script>

<div class="rail" aria-label="Running pass rate for {ranked.length} cells, at the same trial count as the surface">
  {#each ranked as l (l.cell)}
    {@const i = Math.min(t, l.n) - 1}
    <div class="row" animate:flip={{ duration: reduced.current ? 0 : 260 }}>
      <div class="lab mono">
        <span class="cell">{l.cell}</span>
        <span class="n">{l.n}</span>
        <span class="val">{i >= 0 ? `${Math.round(l.run[i] * 100)}%` : '—'}</span>
      </div>
      <svg viewBox="-2 -3 {W + 10} {H + 6}" width={W + 10} height={H + 6} role="presentation">
        <path d={path(l, t)} />
        {#if i >= 0}<circle cx={x(i)} cy={H - l.run[i] * H} r="2.4" />{/if}
      </svg>
    </div>
  {/each}
</div>

<style>
  .rail {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 8px 10px;
    border-radius: var(--radius-sm);
    background: color-mix(in srgb, var(--panel) 84%, transparent);
    pointer-events: none;
    user-select: none;
  }

  .lab {
    display: flex;
    align-items: baseline;
    gap: 6px;
    font-size: 0.64rem;
    font-variant-numeric: tabular-nums;
  }
  .cell { color: var(--ink); }
  .n { color: var(--ink-faint); }
  .val { margin-left: auto; color: var(--ink); }

  svg { display: block; overflow: visible; }
  path { fill: none; stroke: var(--accent); stroke-width: 1.6; stroke-linejoin: round; }
  circle { fill: var(--accent); }
</style>
