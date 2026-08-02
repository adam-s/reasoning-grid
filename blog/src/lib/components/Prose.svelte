<script lang="ts">
  import type { Snippet } from 'svelte';
  type Props = { children: Snippet };
  let { children }: Props = $props();
</script>

<div class="prose">{@render children()}</div>

<style>
  .prose :global(p) { margin: 0 0 var(--space-md); }
  .prose :global(p:last-child) { margin-bottom: 0; }
  .prose :global(code) { font-family: var(--font-mono); font-size: 0.9em; }
</style>
