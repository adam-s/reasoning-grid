<script lang="ts">
  /**
   * Three traces from the same model at neighbouring difficulty, one per
   * outcome. The figure the OODA argument rests on.
   *
   * The comparison only works because difficulty is held roughly still —
   * N = 56, 65 and 77 — and the model is the same in all three. What differs is
   * how each one checked its own work, which is what the colours encode.
   *
   * The summary strip goes BELOW the charts. The flame graphs are the evidence
   * and the strip is the reading; putting the reading first would tell the
   * reader what to see before showing it to them.
   */
  import CarryFlamePanel from './CarryFlamePanel.svelte';
  import CategoryLegend from './CategoryLegend.svelte';
  import { CARRY_SCHEME, metaFor } from '../../design/scheme';
  import { CARRY_TRACES } from '../../data/carrychain-traces';

  let hiddenCategories = $state<Set<string>>(new Set());

  function toggle(cat: string) {
    const next = new Set(hiddenCategories);
    next.has(cat) ? next.delete(cat) : next.add(cat);
    hiddenCategories = next;
  }

  // Leaves only; containers span their children and would be counted twice.
  const allLeaves = $derived(CARRY_TRACES.flatMap((t) => t.rows.filter((r) => !r.container)));

  type Mix = { key: string; verdict: string; parts: { cat: string; frac: number }[]; check: string };

  const mixes = $derived<Mix[]>(
    CARRY_TRACES.map((t) => {
      const leaves = t.rows.filter((r) => !r.container);
      const by = new Map<string, number>();
      for (const r of leaves) by.set(r.category, (by.get(r.category) ?? 0) + r.width);
      const total = [...by.values()].reduce((a, b) => a + b, 0) || 1;
      const cross = leaves.filter((r) => r.category === 'CROSSCHECK').length;
      const re = leaves.filter((r) => r.category === 'RECHECK').length;
      return {
        key: t.key,
        verdict: t.verdict,
        check: `${cross} : ${re}`,
        parts: CARRY_SCHEME.order
          .filter((c) => (by.get(c) ?? 0) > 0)
          .map((c) => ({ cat: c, frac: (by.get(c) as number) / total })),
      };
    }),
  );
</script>

<div class="figure">
  <CategoryLegend
    {hiddenCategories}
    onToggle={toggle}
    rows={allLeaves}
    scheme={CARRY_SCHEME}
    showShare={false}
  />

  <p class="axis-note">
    Position is share of the trace, not time — the three differ in length, and the
    token counts are in each header. Click a numbered marker for the moment it names,
    or any bar for its text. Drag to zoom.
  </p>

  {#each CARRY_TRACES as trace (trace.key)}
    <CarryFlamePanel {trace} {hiddenCategories} />
  {/each}

  <div class="mix">
    <h4>How each one spent its checking</h4>
    {#each mixes as m (m.key)}
      <div class="mix-row">
        <span class="mix-name">{m.verdict}</span>
        <span class="mix-bar">
          {#each m.parts as p (p.cat)}
            <span
              style:width="{p.frac * 100}%"
              style:background={metaFor(CARRY_SCHEME, p.cat).color}
              title="{metaFor(CARRY_SCHEME, p.cat).label} · {(p.frac * 100).toFixed(0)}%"
            ></span>
          {/each}
        </span>
        <span class="mix-ratio mono" title="crosscheck : recheck, in segments">{m.check}</span>
      </div>
    {/each}
    <p class="mix-note">
      Right-hand column is <strong>crosscheck : recheck</strong>, counted in segments. The run
      that got it right is the one that checked itself with methods that could fail
      differently from the arithmetic under test. The run that got it wrong checked
      more, not less.
    </p>
  </div>
</div>

<style>
  .figure { margin: var(--space-md) 0 var(--space-lg); }

  .axis-note {
    margin: 2px 0 var(--space-md);
    font-size: var(--text-xs);
    line-height: 1.5;
    color: var(--ink-faint);
  }

  .mix {
    margin-top: var(--space-md);
    padding-top: var(--space-md);
    border-top: 1px solid var(--line);
  }
  .mix h4 {
    margin: 0 0 10px;
    font-family: var(--font-sans);
    font-size: var(--text-xs);
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--ink-faint);
  }
  .mix-row {
    display: grid;
    grid-template-columns: 8.5rem 1fr 3.2rem;
    align-items: center;
    gap: 10px;
    margin-bottom: 5px;
  }
  .mix-name {
    font-size: var(--text-sm);
    color: var(--ink-dim);
    text-align: right;
  }
  .mix-bar {
    display: flex;
    height: 11px;
    border-radius: 2px;
    overflow: hidden;
    background: var(--panel-2);
  }
  .mix-bar span { min-width: 1px; }
  .mix-ratio {
    font-size: 0.7rem;
    color: var(--ink-dim);
    font-variant-numeric: tabular-nums;
    text-align: right;
  }
  .mix-note {
    margin: 10px 0 0;
    font-size: var(--text-xs);
    line-height: 1.55;
    color: var(--ink-faint);
  }

  @media (max-width: 560px) {
    .mix-row { grid-template-columns: 1fr 3.4rem; }
    .mix-name {
      grid-column: 1 / -1;
      text-align: left;
      font-size: var(--text-xs);
      margin-bottom: 1px;
    }
  }
</style>
