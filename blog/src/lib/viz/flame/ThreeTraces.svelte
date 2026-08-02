<script lang="ts">
  /**
   * Three traces from the same model at neighbouring difficulty, one per
   * outcome. The figure the OODA argument rests on.
   *
   * The comparison only works because difficulty is held roughly still —
   * N = 56, 65 and 77 — and the model is the same in all three. What differs is
   * how each one checked its own work, which is what the colours encode.
   *
   * There was a summary strip here: one stacked bar per trace showing its
   * category mix. It was cut. It restated the flame charts directly above it in
   * the same colours at lower resolution, so a reader who had understood the
   * charts learned nothing and a reader who had not was given a second thing to
   * decode. The one number it carried that the charts do not — crosscheck
   * against recheck — is a sentence, and now lives in the prose as one.
   */
  import CarryFlamePanel from './CarryFlamePanel.svelte';
  import CategoryLegend from './CategoryLegend.svelte';
  import { CARRY_SCHEME } from '../../design/scheme';
  import { CARRY_TRACES } from '../../data/carrychain-traces';

  let hiddenCategories = $state<Set<string>>(new Set());

  function toggle(cat: string) {
    const next = new Set(hiddenCategories);
    next.has(cat) ? next.delete(cat) : next.add(cat);
    hiddenCategories = next;
  }

  // Leaves only; containers span their children and would be counted twice.
  const allLeaves = $derived(CARRY_TRACES.flatMap((t) => t.rows.filter((r) => !r.container)));
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
    Position is share of each trace, not time. Click a marker, or any bar, for what it says.
  </p>

  {#each CARRY_TRACES as trace (trace.key)}
    <CarryFlamePanel {trace} {hiddenCategories} />
  {/each}
</div>

<style>
  .figure { margin: var(--space-md) 0 var(--space-lg); }

  .axis-note {
    margin: 2px 0 var(--space-md);
    font-size: var(--text-xs);
    line-height: 1.5;
    color: var(--ink-faint);
  }
</style>
