<script lang="ts">
  /**
   * Three traces from the same model at neighbouring difficulty, one per
   * outcome. The figure the OODA argument rests on.
   *
   * The comparison only works because difficulty is held roughly still —
   * N = 56, 65 and 77 — and the model is the same in all three. What differs is
   * how each one checked its own work, which is what the colours encode.
   *
   * This renders through FlamePanel, the component the λ-bench post shipped.
   * There was briefly a CarryFlamePanel here that reimplemented it; it was
   * deleted. FlamePanel already had the minimap, the tooltip that dismisses on
   * scroll and outside pointerdown, scroll-position sync, adaptive chart height
   * and the touch-vs-hover split, all of which had been through production. The
   * rewrite had none of them and would have had to earn each one back. What was
   * genuinely new — numbered annotation markers, a percentage axis, a
   * replaceable header — went into FlamePanel as props that default to the λ
   * behaviour.
   */
  import FlamePanel from './FlamePanel.svelte';
  import CategoryLegend from './CategoryLegend.svelte';
  import { CARRY_SCHEME } from '../../design/scheme';
  import { OODA_SCHEME, CATEGORY_PHASE } from '../../design/ooda';
  import { CARRY_TRACES } from '../../data/carrychain-traces';

  // No minimaps. They were on for the 396-segment trace and off for the two
  // 64-segment ones, which made the three panels of a comparison look like
  // different kinds of chart. Turning it on everywhere would cost ~80px per
  // panel to overview charts that are two levels deep and already fully
  // visible. Zoom is still there: click a block, then Reset.

  // Two lenses on one set of events, not two figures. Switching recolours the
  // same bars, which is the point being made: the OODA view and the move view
  // describe identical spans and only one of them can tell the runs apart.
  let lens = $state<'move' | 'ooda'>('move');
  const scheme = $derived(lens === 'ooda' ? OODA_SCHEME : CARRY_SCHEME);

  const traces = $derived(
    lens === 'move'
      ? CARRY_TRACES
      : CARRY_TRACES.map((t) => ({
          ...t,
          rows: t.rows.map((r) => ({ ...r, category: CATEGORY_PHASE[r.category] ?? r.category })),
        })),
  );

  let hiddenCategories = $state<Set<string>>(new Set());

  // A category hidden under one lens has no counterpart under the other.
  $effect(() => {
    lens;
    hiddenCategories = new Set();
  });

  function toggle(cat: string) {
    const next = new Set(hiddenCategories);
    next.has(cat) ? next.delete(cat) : next.add(cat);
    hiddenCategories = next;
  }

  // Leaves only; containers span their children and would be counted twice.
  const allLeaves = $derived(traces.flatMap((t) => t.rows.filter((r) => !r.container)));

  const fmt = new Intl.NumberFormat('en-US');

  const tone = (outcome: string) =>
    outcome === 'converged_right' ? 'ok' : outcome === 'grind' ? 'wait' : 'err';
</script>

<div class="figure">
  <div class="lens" role="group" aria-label="Colour the same bars by">
    <button class:on={lens === 'move'} onclick={() => (lens = 'move')}>by move</button>
    <button class:on={lens === 'ooda'} onclick={() => (lens = 'ooda')}>by OODA phase</button>
  </div>

  <CategoryLegend
    {hiddenCategories}
    onToggle={toggle}
    rows={allLeaves}
    {scheme}
    showShare={false}
    showEmpty={lens === 'ooda'}
  />

  {#each traces as trace (trace.key)}
    {#snippet head()}
      <header class="head">
        <span class="badge" data-tone={tone(trace.outcome)}>{trace.verdict}</span>
        <span class="blurb">{trace.blurb}</span>
        <span class="stats mono">
          {trace.cell} · N={trace.n} · T={trace.temperature} · {fmt.format(trace.tokens)} tok
        </span>
      </header>
    {/snippet}

    <FlamePanel
      trace={{ ...trace, name: trace.verdict, stepCount: trace.segments }}
      {scheme}
      header={head}
      formatTick={(v) => `${Math.round((v / trace.chars) * 100)}%`}
      tickValues={(d) =>
        [0, 0.25, 0.5, 0.75, 1]
          .map((f) => f * trace.chars)
          .filter((v) => v >= d[0] - 1 && v <= d[1] + 1)}
      showLegend={false}
      showMinimap={false}
      showInspectorHint={false}
      showZoomHint={false}
      {hiddenCategories}
    />
  {/each}
</div>

<style>
  .figure { margin: var(--space-md) 0 var(--space-lg); }

  .lens {
    display: inline-flex;
    gap: 1px;
    padding: 1px;
    margin-bottom: 10px;
    border: 1px solid var(--line);
    border-radius: var(--radius-sm);
    background: var(--panel);
  }
  .lens button {
    padding: 3px 10px;
    border: 0;
    border-radius: 2px;
    background: transparent;
    cursor: pointer;
    font-family: var(--font-sans);
    font-size: var(--text-xs);
    color: var(--ink-faint);
    transition: background 130ms ease, color 130ms ease;
  }
  .lens button:hover { color: var(--ink); }
  .lens button.on { background: var(--ink); color: var(--bg); }


  .head {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 6px 10px;
    margin-bottom: 8px;
  }
  .badge {
    font-family: var(--font-sans);
    font-size: var(--text-xs);
    font-weight: 600;
    letter-spacing: 0.02em;
    padding: 2px 8px;
    border-radius: var(--radius-sm);
    border: 1px solid;
  }
  .badge[data-tone='ok'] { color: #2d7d6a; border-color: #2d7d6a55; background: #2d7d6a12; }
  .badge[data-tone='err'] { color: #bf4536; border-color: #bf453655; background: #bf453612; }
  .badge[data-tone='wait'] { color: #b07a1e; border-color: #b07a1e55; background: #b07a1e12; }

  .blurb {
    font-size: var(--text-sm);
    color: var(--ink-dim);
    flex: 1 1 12rem;
  }
  .stats {
    font-size: 0.68rem;
    color: var(--ink-faint);
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }

  @media (max-width: 620px) {
    .blurb, .stats { flex-basis: 100%; }
  }
</style>
