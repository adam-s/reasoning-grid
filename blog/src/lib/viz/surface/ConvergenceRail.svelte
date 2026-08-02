<script lang="ts">
  /**
   * Sparklines down the dead space beside the surface, scrubbing in step with it.
   *
   * The surface answers "what shape is it"; these answer "how much of any one
   * number do we actually have". Each line is a single cell's running pass rate
   * against trial index, with a dot at the trial the scrubber is on. They share
   * the surface's `t`, so a cell freezing on the terrain and its sparkline
   * stopping are the same event seen twice.
   *
   * Which cells is decided by the data, not by hand: split the rate range into
   * six bands and take the best-measured cell in each. Picking purely by trial
   * count instead returns six cells between 81% and 98%, because that is where
   * the long runs actually went — the sweep was meant to spend them near 50% and
   * spent them on cells already known to be around 80%. A rail that showed only
   * those would inherit the mistake and hide it. Stratifying spans 97% down to
   * 14%, and the trial counts beside each line show the misallocation instead of
   * burying it: 29 trials at the top of the range and 14 at the bottom.
   *
   * Rows rank by their rate AT THE CURRENT TRIAL, not by where they end up, so
   * the number beside each line always agrees with its position in the column.
   * They therefore overtake each other as the scrub runs, which is the honest
   * picture — early on these cells are genuinely not in their final order. The
   * reorder is animated so a row can be followed through it.
   *
   * SVG, not canvas: five polylines of at most 55 points each, and the repo's
   * dataviz note is right that SVG wins at this size on theming and crispness.
   */
  import { flip } from 'svelte/animate';
  import { MediaQuery } from 'svelte/reactivity';
  import { SURFACE } from '../../data/surface';

  const reduced = new MediaQuery('(prefers-reduced-motion: reduce)');

  type Props = { t: number; max: number };
  let { t, max }: Props = $props();

  const W = 128;
  const H = 26;

  type Line = { cell: string; n: number; run: number[]; note: string };

  const lines = $derived.by((): Line[] => {
    const all = Object.entries(SURFACE.cells).map(([cell, o]) => {
      const n = o.length;
      const run: number[] = [];
      let k = 0;
      for (let i = 0; i < n; i++) {
        k += o[i];
        run.push(k / (i + 1));
      }
      return { cell, n, run, p: run[n - 1] ?? 0 };
    });
    const capped = all.map(({ cell, n, run }) => {
      const k = Math.min(n, max);
      const r = run.slice(0, k);
      return { cell, n: k, run: r, p: r[k - 1] ?? 0 };
    });
    const BANDS = 6;
    const out: Line[] = [];
    for (let b = BANDS - 1; b >= 0; b--) {
      const lo = b / BANDS;
      const hi = (b + 1) / BANDS;
      const band = capped.filter((c) => c.p >= lo && (c.p < hi || (b === BANDS - 1 && c.p <= 1)));
      if (!band.length) continue;
      const best = band.reduce((x, c) => (c.n > x.n ? c : x));
      out.push({ cell: best.cell, n: best.n, run: best.run, note: `${best.n} trials` });
    }
    return out;
  });

  /** Ranked by the rate at `t`, so the column is always in the order it shows. */
  const ranked = $derived(
    [...lines].sort((a, b) => {
      const av = a.run[Math.min(t, a.n) - 1] ?? -1;
      const bv = b.run[Math.min(t, b.n) - 1] ?? -1;
      return bv - av;
    }),
  );

  // x spans the scrub, so a dot here sits where the slider does.
  const span = $derived(Math.max(2, max));

  const path = (run: number[], upto: number) => {
    const m = Math.min(upto, run.length);
    if (m < 1) return '';
    return run
      .slice(0, m)
      .map((p, i) => {
        const x = (i / (span - 1)) * W;
        return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${(H - p * H).toFixed(1)}`;
      })
      .join(' ');
  };

  const dot = (run: number[], upto: number) => {
    const i = Math.min(upto, run.length) - 1;
    if (i < 0) return null;
    return {
      x: (i / (span - 1)) * W,
      y: H - run[i] * H,
      p: run[i],
      done: upto > run.length,
    };
  };
</script>

<div class="rail" aria-label="Running pass rate for five cells, at the same trial count as the surface">
  <div class="cap">one cell at a time</div>
  {#each ranked as l (l.cell)}
    {@const d = dot(l.run, t)}
    <div class="row" class:done={d?.done} animate:flip={{ duration: reduced.current ? 0 : 260 }}>
      <div class="lab">
        <span class="cell mono">{l.cell}</span>
        <span class="val mono">{d ? `${Math.round(d.p * 100)}%` : '—'}</span>
      </div>
      <svg viewBox="-2 -3 {W + 12} {H + 6}" width={W + 12} height={H + 6} role="presentation">
        <!-- how much of this cell there is to see, so a short line reads as
             "nobody measured further", not "it ended" -->
        <line class="track" x1="0" y1={H + 1} x2={((l.n - 1) / (span - 1)) * W} y2={H + 1} />
        <path class="run" d={path(l.run, t)} />
        {#if d}
          <circle class="head" cx={d.x} cy={d.y} r="2.4" />
        {/if}
      </svg>
      <span class="note">{d?.done ? `all ${l.n} in` : l.note}</span>
    </div>
  {/each}
</div>

<style>
  .rail {
    display: flex;
    flex-direction: column;
    gap: 9px;
    padding: 8px 9px 9px;
    border-radius: var(--radius-sm);
    background: color-mix(in srgb, var(--panel) 82%, transparent);
    backdrop-filter: blur(2px);
    pointer-events: none;
    user-select: none;
  }
  .cap {
    font-family: var(--font-sans);
    font-size: 0.62rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--ink-faint);
  }
  .row { transition: opacity 200ms ease; }
  .row.done { opacity: 0.45; }

  .lab {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    font-size: 0.62rem;
  }
  .cell { color: var(--ink-dim); }
  .val { color: var(--ink); font-variant-numeric: tabular-nums; }

  svg { display: block; overflow: visible; }
  .track { stroke: var(--line-strong); stroke-width: 1.5; stroke-linecap: round; }
  .run { fill: none; stroke: var(--accent); stroke-width: 1.4; stroke-linejoin: round; }
  .head { fill: var(--accent); }

  .note {
    display: block;
    font-family: var(--font-sans);
    font-size: 0.58rem;
    color: var(--ink-faint);
  }

  @media (prefers-reduced-motion: reduce) {
    .row { transition: none; }
  }
</style>
