<script lang="ts">
  /**
   * CategoryLegend — a key that is also a distribution.
   *
   * The original was a row of swatch-plus-label buttons: it told you which
   * colour meant what and nothing else. But the single most useful fact about a
   * reasoning trace is how the time divides — how much went on verification,
   * how much on correcting errors, how much on giving up — and that was
   * available for free from the same rows the chart already had.
   *
   * So the legend carries a proportional bar. Each segment's width is that
   * category's share of the trace, which makes the key double as a summary and
   * removes the need for a separate chart to say the same thing. Hiding a
   * category drops it out of the bar and the remainder renormalises, so
   * filtering reads as "of what is left, how does it divide".
   *
   * Deliberately not here: a count of segments. Share of *time* is what the
   * flame graph is measuring, and showing both invites the reader to compare
   * two numbers that answer different questions.
   */
  import type { AnyFlameRow, CategoryScheme } from '../../design/scheme';
  import { LAMBDA_SCHEME, metaFor } from '../../design/scheme';

  type Props = {
    hiddenCategories: ReadonlySet<string>;
    onToggle: (category: string) => void;
    rows?: ReadonlyArray<AnyFlameRow>;
    /** Which categories this legend keys. Defaults to the λ set. */
    scheme?: CategoryScheme;
    /** Show the proportional bar and the per-category percentages. Turn off
     *  when the rows pool several traces of different lengths, where a single
     *  bar reads as an average but is really dominated by the longest one. */
    showShare?: boolean;
  };

  let { hiddenCategories, onToggle, rows = [], scheme = LAMBDA_SCHEME, showShare = true }: Props =
    $props();

  let hovered = $state<string | null>(null);

  // Leaves only. Parent rows in this data are containers spanning their
  // children, so counting both would charge the same milliseconds twice.
  // When the data marks containers explicitly, believe it. The containment test
  // below assumes every row shares one coordinate space, which is false the
  // moment rows from several traces are pooled into one legend: each trace's
  // offsets start at zero, so a deeper row from trace B falls inside a leaf from
  // trace C by pure coincidence and the leaf is dropped. That silently lost the
  // only ERROR_CORRECTION row in the whole corpus.
  const leaves = $derived(
    rows.some((r) => r.muted !== undefined)
      ? rows.filter((r) => !r.muted)
      : rows.filter((r) => !rows.some((o) => o !== r && o.depth > r.depth && o.start >= r.start && o.start + o.width <= r.start + r.width))
  );

  const totals = $derived.by(() => {
    const t = new Map<string, number>();
    for (const r of leaves) t.set(r.category, (t.get(r.category) ?? 0) + r.width);
    return t;
  });

  const visibleTotal = $derived(
    scheme.order.reduce((s, c) => (hiddenCategories.has(c) ? s : s + (totals.get(c) ?? 0)), 0)
  );

  // Present categories only. An entry at 0% is noise in a legend.
  const present = $derived(scheme.order.filter((c) => (totals.get(c) ?? 0) > 0));

  function share(c: string): number {
    if (hiddenCategories.has(c) || visibleTotal <= 0) return 0;
    return (totals.get(c) ?? 0) / visibleTotal;
  }
</script>

<div class="legend" role="group" aria-label="Category filter">
  {#if showShare && present.length && visibleTotal > 0}
    <div class="bar" aria-hidden="true">
      {#each present as cat (cat)}
        {@const w = share(cat)}
        {#if w > 0}
          <span
            class="seg"
            class:dim={hovered !== null && hovered !== cat}
            style:width="{w * 100}%"
            style:background={metaFor(scheme, cat).color}
          >
            {#if w > 0.055}<span class="sym">{metaFor(scheme, cat).symbol}</span>{/if}
          </span>
        {/if}
      {/each}
    </div>
  {/if}

  <div class="items">
    {#each present as cat (cat)}
      {@const meta = metaFor(scheme, cat)}
      {@const isHidden = hiddenCategories.has(cat)}
      {@const pct = share(cat)}
      <button
        type="button"
        class="item"
        class:is-hidden={isHidden}
        class:dim={hovered !== null && hovered !== cat && !isHidden}
        onclick={() => onToggle(cat)}
        onmouseenter={() => (hovered = cat)}
        onmouseleave={() => (hovered = null)}
        onfocus={() => (hovered = cat)}
        onblur={() => (hovered = null)}
        aria-pressed={!isHidden}
        title={meta.description}
      >
        <span class="rule" style:background={meta.color} aria-hidden="true"></span>
        <span class="label">{meta.label}</span>
        {#if showShare}
          <span class="pct mono">{isHidden ? '—' : `${(pct * 100).toFixed(pct < 0.095 ? 1 : 0)}%`}</span>
        {/if}
      </button>
    {/each}
  </div>
</div>

<style>
  .legend {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: var(--space-sm) 0 2px;
  }

  /* the proportional bar */
  .bar {
    display: flex;
    height: 9px;
    border-radius: 2px;
    overflow: hidden;
    background: var(--panel-2);
  }
  .seg {
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 2px;
    transition: width 220ms cubic-bezier(0.4, 0, 0.2, 1), opacity 140ms ease;
  }
  .seg.dim { opacity: 0.3; }
  .sym {
    font-family: var(--font-mono);
    font-size: 7px;
    line-height: 1;
    color: rgba(255, 255, 255, 0.9);
    user-select: none;
  }

  /* the key */
  .items {
    display: flex;
    flex-wrap: wrap;
    gap: 2px 4px;
  }
  .item {
    display: inline-flex;
    align-items: baseline;
    gap: 6px;
    padding: 3px 7px 3px 6px;
    border: 1px solid transparent;
    border-radius: var(--radius-sm);
    background: transparent;
    cursor: pointer;
    font-family: var(--font-sans);
    font-size: var(--text-xs);
    color: var(--ink);
    transition: opacity 140ms ease, border-color 140ms ease, background 140ms ease;
  }
  .item:hover { background: var(--panel); border-color: var(--line); }
  .item.dim { opacity: 0.45; }
  .item.is-hidden { opacity: 0.4; }
  .item.is-hidden .label { text-decoration: line-through; text-decoration-thickness: 1px; }
  .item.is-hidden .rule { opacity: 0.3; }

  /* a rule reads as a share of a length; a square reads as a bullet */
  .rule {
    width: 12px;
    height: 3px;
    border-radius: 1px;
    flex-shrink: 0;
    align-self: center;
  }
  .label { white-space: nowrap; }
  .pct {
    font-size: 0.68rem;
    color: var(--ink-faint);
    font-variant-numeric: tabular-nums;
    min-width: 2.1em;
    text-align: right;
  }

  @media (prefers-reduced-motion: reduce) {
    .seg { transition: none; }
  }
</style>
