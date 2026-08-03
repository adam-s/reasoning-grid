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
    LAMBDA_SCHEME,
    type CategoryScheme,
    type AnyFlameRow,
  } from '../../design/scheme';

  type Props = {
    rows?: readonly AnyFlameRow[];
    scheme?: CategoryScheme;
    /** List every category in the scheme, not only the ones this trace used. */
    showEmpty?: boolean;
  };

  let { rows = [], scheme = LAMBDA_SCHEME, showEmpty = false }: Props = $props();

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

<ul class="legend">
  {#each present as cat (cat)}
    {@const meta = metaFor(scheme, cat)}
    <li class="item">
      <span class="rule" style:background={meta.color} aria-hidden="true"></span>
      <span class="label">{meta.label}</span>
    </li>
  {/each}
</ul>

<style>
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 2px 14px;
    margin: 0;
    padding: var(--space-sm) 0 2px;
    list-style: none;
  }
  .item {
    display: inline-flex;
    align-items: baseline;
    gap: 6px;
    font-family: var(--font-sans);
    font-size: var(--text-xs);
    color: var(--ink);
  }
  /* A rule reads as a share of a length; a square reads as a bullet. */
  .rule {
    width: 12px;
    height: 3px;
    border-radius: 1px;
    flex-shrink: 0;
    align-self: center;
  }
  .label {
    white-space: nowrap;
  }
</style>
