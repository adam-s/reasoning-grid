<script lang="ts">
  // Scaffold marker. Delete as each viz lands.
  type Props = { name: string; ports: string };
  let { name, ports }: Props = $props();
</script>

<div class="ph">
  <span class="mono tag">{name}</span>
  <span class="mono src">ports {ports}</span>
</div>

<style>
  .ph {
    border: 1px dashed var(--line-strong);
    background: var(--panel);
    border-radius: 3px;
    padding: var(--space-xl) var(--space-md);
    display: flex; flex-direction: column; gap: 6px; align-items: center;
    color: var(--ink-faint);
  }
  .tag { font-size: 0.9rem; color: var(--ink-dim); }
  .src { font-size: 0.72rem; }
</style>
