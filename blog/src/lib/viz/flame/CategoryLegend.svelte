<script lang="ts">
  /**
   * A key: which colour means what. Nothing else.
   *
   * It used to carry a proportional share bar, a percentage against every
   * category, and a button per entry that hid that category from the chart.
   * All three are gone. The bar restated what the flame graph above it already
   * draws, at lower resolution and in a different order; the percentages
   * invited reading a share off the key rather than off the figure; and the
   * filtering was a control on a figure that is read, not operated.
   *
   * What went with them: `hiddenCategories` and `onToggle` here, `ownHidden`
   * and `toggleCategory` in FlamePanel, and the hidden-category branches in
   * FlameGraph's opacity. Dropping a feature is only a simplification if its
   * plumbing goes too.
   */
  import {
    metaFor,
    type CategoryScheme,
    type AnyFlameRow,
  } from '../../design/scheme';

  type Props = {
    rows?: readonly AnyFlameRow[];
    /** The category happening right now, if the caller is playing a trace
     *  back. Everything else dims, so the key doubles as a readout of what
     *  the run is doing at the playhead. null leaves every entry at full
     *  strength, which is what a static figure wants. */
    active?: string | null;
    scheme: CategoryScheme;
    /** List every category in the scheme, not only the ones this trace used. */
    showEmpty?: boolean;
  };

  let {
    rows = [], scheme, showEmpty = false, active = null,
  }: Props = $props();

  /**
   * Leaves only. Container rows span their children and carry the dominant
   * category among them, so counting containers would list a category that
   * never actually occurs as a step.
   */
  const leaves = $derived(
    rows.some((r) => r.muted !== undefined) ? rows.filter((r) => !r.muted) : rows,
  );

  /** Present categories only — an entry for one the trace never used is noise. */
  const present = $derived(
    showEmpty
      ? scheme.order
      : scheme.order.filter((c) => leaves.some((r) => r.category === c)),
  );
</script>

<!-- Two rows, always: the column count is half the entries, rounded up. A wrap
     that depends on the container width puts the break in a different place at
     every size, and a key is read as a block -- it should not reflow while the
     figure beside it stays put. -->
<ul class="legend" style:--cols={Math.ceil(present.length / 2)}>
  {#each present as cat (cat)}
    {@const meta = metaFor(scheme, cat)}
    <li class="item" class:on={active === cat} class:off={active !== null && active !== cat}>
      <span class="rule" style:background={meta.color} aria-hidden="true"></span>
      <span class="label">{meta.label}</span>
    </li>
  {/each}
</ul>

<style>
  .legend {
    display: grid;
    grid-template-columns: repeat(var(--cols, 4), max-content);
    gap: 8px 26px;
    margin: 0;
    padding: var(--space-sm) 0 4px;
    list-style: none;
  }
  .item {
    display: inline-flex;
    align-items: center;
    gap: 9px;
    font-family: var(--font-sans);
    font-size: 0.84rem;
    color: var(--ink);
  }
  /* A rule reads as a share of a length; a square reads as a bullet. */
  .rule {
    width: 20px;
    height: 4px;
    border-radius: 2px;
    flex-shrink: 0;
  }
  .label {
    white-space: nowrap;
  }

  /* Driven by the playhead, not by a pointer: the entry for the step under the
     cursor stays at full strength and the rest step back.
     
     OPACITY ONLY. Bolding the active label changed its width, which reflowed
     the whole grid every time the playhead crossed into another category --
     the legend visibly jumped, and it jumped most where the steps are shortest
     and the crossings fastest. Nothing here may change a metric: no weight, no
     size, no ring that adds to the box.
     
     Dimming the others rather than brightening one also keeps the swatches'
     colours true -- a saturated swatch would no longer be the colour it is
     labelling. And 0.45 rather than lower, because this is still a key: a
     reader glancing at it to find out what a colour means has to be able to
     read every entry, not only the one the run happens to be in. */
  .item { transition: opacity 200ms ease; }
  .item.off { opacity: 0.45; }

  @media (prefers-reduced-motion: reduce) {
    .item { transition: none; }
  }

  @media (max-width: 640px) {
    .legend {
      grid-template-columns: repeat(2, max-content);
      gap: 6px 20px;
    }
    .item { font-size: 0.78rem; }
  }
</style>
