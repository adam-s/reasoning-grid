<script lang="ts">
  /**
   * How three models spend their thinking on the same task.
   *
   * ## Why this figure is here
   *
   * The rest of this page is one model, Qwen3-4B, and it measures WHERE a model
   * stops being right. It cannot say anything about how two models differ in
   * the way they think, because it only ever looks at one. This does, using
   * labels that were already published rather than anything collected here.
   *
   * Eight traces, 903 segments, Claude Haiku, Opus and Sonnet on long
   * multiplication and modular exponentiation. Same nine categories carrychain's
   * first labelling scheme was adapted from. The categories describe all three
   * models and every segment lands in one. The proportions do not agree at all.
   *
   * ## Dots, not stacked bars, and categories, not phases
   *
   * TWO DESIGN CHOICES, ONE ARGUMENT EACH.
   *
   * Not phases: `.agents/reference/flame-rubric-carrychain.md` maps `STRATEGY`
   * (this scheme's `DECOMPOSITION`) to BOTH Orient and Decide, because the model
   * states a plan and commits in one breath. A phase chart has to double-count
   * the largest category or place it by fiat, and since `DECOMPOSITION` is 31%
   * of Sonnet that choice would decide the whole result. A mapping that is not a
   * function is the defect the v2 rebuild exists to remove, so it is not
   * reintroduced here with a new dataset.
   *
   * Not stacked: stacking asks "what is this model made of", which puts the
   * comparison between models on shifting baselines -- only the leftmost band
   * starts from a common edge. The question here is the opposite one, how far
   * apart the models sit on each category, so every row gets a common axis and
   * the spread is a length the eye can measure directly.
   *
   * ## The data lives somewhere else on purpose
   *
   * `probe/build_thinking_mix.py` reads the published file in
   * agent-capability-threshold and records the commit it read, so the caption's
   * link resolves to the exact bytes behind these dots rather than to whatever
   * that repo's main branch says later.
   */
  import { THINKING_MIX as MIX } from '../../data/thinking-mix';
  import { observeWidth } from '../observeWidth.svelte';

  /* One hue per model. Three is few enough that hue alone carries it, and the
     row labels stay legible without a colour key on every dot. */
  const HUE: Record<string, string> = {
    haiku: 'var(--model-b)',
    opus: 'var(--fit)',
    sonnet: 'var(--model-a)',
  };

  /**
   * ---- ONE SCALE FOR THE TYPE AND THE ROOM IT NEEDS -----------------------
   *
   * Same treatment, and the same reason, as BoundaryWedge: the svg is
   * `width: 100%` over a fixed viewBox, so at a 430px viewport this 698-unit
   * box renders the category labels at 7.7px, the ticks at 6.5px and the model
   * key at 7.1px. `u` is one rendered CSS pixel in viewBox units, and the
   * gutters take it too -- the left gutter holds the longest category name, so
   * growing that name without growing the gutter pushes it off the edge.
   *
   * At u = 1 every number here is what it was, so the desktop figure does not
   * move. See the long note in BoundaryWedge for why it clamps in only one
   * direction.
   */
  let host: HTMLElement | null = $state(null);
  let u = $state(1);

  /** Fixed: `u` is measured against the viewBox, so it cannot depend on u. */
  const W = 698;
  const ROW = 30;
  const PAD = $derived({ l: 132 * u, r: 96 * u, t: 26 * u, b: 62 * u });
  const PW = $derived(W - PAD.l - PAD.r);
  const H = $derived(PAD.t + MIX.order.length * ROW + PAD.b);

  observeWidth(() => host, (px) => {
    u = Math.min(1.9, Math.max(1, W / px));
  });

  /* Both footers hang off the plot's bottom edge rather than off `H`, so the
     axis title and the key cannot land in the same band when the row count
     changes. They collided the first time this rendered. */
  const FOOT = $derived(PAD.t + MIX.order.length * ROW);

  type Row = {
    key: string;
    label: string;
    pts: { model: string; share: number }[];
    spread: number;
  };

  const rows: Row[] = MIX.order.map((key) => {
    const pts = MIX.models.map((m) => ({
      model: m.model,
      share: (m.counts[key] ?? 0) / m.segments,
    }));
    const shares = pts.map((p) => p.share);
    return {
      key,
      label: MIX.labels[key],
      pts,
      spread: Math.max(...shares) - Math.min(...shares),
    };
  });

  /** Round the axis out to a clean tick above the largest share. */
  const MAX = Math.ceil(Math.max(...rows.flatMap((r) => r.pts.map((p) => p.share))) * 20) / 20;
  const sx = (v: number) => PAD.l + (v / MAX) * PW;
  const sy = (i: number) => PAD.t + i * ROW + ROW / 2;

  const TICKS = Array.from({ length: Math.round(MAX / 0.1) + 1 }, (_, i) => i * 0.1);
  const pct = (v: number) => `${Math.round(v * 100)}%`;

  /* The row the figure is for. Named from the data rather than hardcoded, so a
     rebuild that changes which category spreads widest changes the callout. */
  const widest = rows.reduce((a, b) => (b.spread > a.spread ? b : a));
  const ratio = (() => {
    const s = widest.pts.map((p) => p.share).filter((v) => v > 0);
    return (Math.max(...s) / Math.min(...s)).toFixed(0);
  })();
</script>

<figure bind:this={host} style:--u={u}>
  <svg
    viewBox="0 0 {W} {H}"
    role="img"
    aria-label="Share of labelled thinking segments per category for Claude
      Haiku, Opus and Sonnet on the same arithmetic tasks. The categories
      describe all three models, but the proportions differ, most widely on
      {widest.label}."
  >
    {#each TICKS as t}
      <line x1={sx(t)} y1={PAD.t} x2={sx(t)} y2={PAD.t + rows.length * ROW}
            class="grid" class:zero={t === 0} />
      <text x={sx(t)} y={PAD.t - 10 * u} class="tick mid">{pct(t)}</text>
    {/each}

    {#each rows as r, i}
      <text x={PAD.l - 12 * u} y={sy(i) + 4 * u} class="cat">{r.label}</text>

      <!-- The connector is the finding on every row: its length IS the
           disagreement between the models on that category. -->
      <line
        x1={sx(Math.min(...r.pts.map((p) => p.share)))}
        y1={sy(i)}
        x2={sx(Math.max(...r.pts.map((p) => p.share)))}
        y2={sy(i)}
        class="span"
        class:lead={r.key === widest.key}
      />

      {#each r.pts as p}
        <circle cx={sx(p.share)} cy={sy(i)} r="5" fill={HUE[p.model]} class="dot" />
      {/each}
    {/each}

    <text x={sx(widest.pts.reduce((a, b) => (b.share > a.share ? b : a)).share) + 14 * u}
          y={sy(MIX.order.indexOf(widest.key)) + 4 * u}
          class="callout">{ratio}× apart</text>

    <text x={PAD.l + PW / 2} y={FOOT + 24 * u} class="axis">share of labelled thinking segments</text>

    {#each MIX.models as m, i}
      <circle cx={PAD.l + i * 96 * u} cy={FOOT + 48 * u} r="5" fill={HUE[m.model]} />
      <text x={PAD.l + i * 96 * u + 11 * u} y={FOOT + 48 * u} class="key">{m.model}</text>
    {/each}
  </svg>

  <figcaption>
    Every one of {MIX.segments.toLocaleString()} segments across
    {MIX.models.reduce((n, m) => n + m.traces, 0)} traces lands in one of these
    categories, for all three models. The proportions are another matter, and
    {widest.label.toLowerCase()} runs {ratio} times wider in one model than
    another. Shown as categories rather than as Boyd's four phases because this
    scheme puts decomposition in two phases at once, so a phase chart would have
    to double-count its largest category. Labels are from
    <a href={MIX.source.url} target="_blank" rel="noopener">{MIX.source.path}</a>
    at commit {MIX.source.commit.slice(0, 7)}, not collected for this page.
  </figcaption>
</figure>

<style>
  figure { margin: 0; width: 100%; }
  svg { display: block; width: 100%; height: auto; overflow: visible; }

  .grid { stroke: var(--line); stroke-width: 1; }
  .grid.zero { stroke: var(--line-strong); }

  /* Quiet by default so the dots read first; the widest row is the one the
     caption names, so it gets ink rather than a separate annotation. */
  .span { stroke: var(--line-strong); stroke-width: 2; }
  .span.lead { stroke: var(--ink-dim); stroke-width: 3; }

  .dot { stroke: var(--bg); stroke-width: 1.5; }

  .cat {
    font-family: var(--font-sans);
    font-size: calc(13px * var(--u, 1));
    fill: var(--ink);
    text-anchor: end;
  }

  .callout {
    font-family: var(--font-sans);
    font-size: calc(12px * var(--u, 1));
    font-weight: var(--weight-medium);
    fill: var(--ink);
    dominant-baseline: middle;
  }

  .key {
    font-family: var(--font-sans);
    font-size: calc(12px * var(--u, 1));
    fill: var(--ink-dim);
    dominant-baseline: middle;
  }

  .tick {
    font-family: var(--font-mono);
    font-size: calc(11px * var(--u, 1));
    fill: var(--ink-faint);
  }
  .tick.mid { text-anchor: middle; }

  .axis {
    font-family: var(--font-sans);
    font-size: calc(12px * var(--u, 1));
    fill: var(--ink-dim);
    letter-spacing: 0.04em;
    text-anchor: middle;
  }

  figcaption {
    margin-top: var(--space-md);
    max-width: var(--maxw);
    font-family: var(--font-sans);
    font-size: var(--text-sm);
    line-height: var(--leading-snug);
    color: var(--ink-dim);
  }
</style>
