<script lang="ts">
  import type { Snippet } from 'svelte';
  type Props = { children: Snippet };
  let { children }: Props = $props();
</script>

<div class="prose">{@render children()}</div>

<style>
  .prose :global(p) { margin: 0 0 var(--space-md); }
  .prose :global(p:last-child) { margin-bottom: 0; }
  /* A subhead inside the reading column, tighter to the paragraph under it than
     to the one above, so it groups forward with the text it introduces rather
     than floating between blocks.

     The SIZE is the shared scale and is not re-picked here. This rule used to
     hard-code 1.15rem, which overrode the house `--text-xl` and left the subhead
     barely larger than the body text it was meant to head. Spacing is this
     component's business; type size is the site's. */
  .prose :global(h3) {
    margin: var(--space-xl) 0 var(--space-sm);
    font-size: var(--text-xl);
  }
  .prose :global(h3:first-child) { margin-top: 0; }
  .prose :global(code) { font-family: var(--font-mono); font-size: 0.9em; }

  /* Small tables inside the reading column. Numbers are monospaced and
     right-aligned with tabular figures so columns line up on the decimal and
     the eye can compare down a column instead of reading each cell. */
  .prose :global(table) {
    width: 100%;
    margin: var(--space-md) 0;
    border-collapse: collapse;
    font-family: var(--font-sans);
    font-size: var(--text-sm);
  }
  .prose :global(th),
  .prose :global(td) {
    padding: 5px 10px;
    border-bottom: 1px solid var(--line);
    text-align: right;
  }
  .prose :global(th:first-child),
  .prose :global(td:first-child) { text-align: left; }
  .prose :global(th) {
    border-bottom-color: var(--line-strong);
    font-weight: var(--weight-medium);
    color: var(--ink-dim);
    font-size: var(--text-xs);
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }
  .prose :global(td) { font-variant-numeric: tabular-nums; }
  .prose :global(td:not(:first-child)) { font-family: var(--font-mono); }
  /* The row a table exists to point at. Background rather than weight, because
     bolding a numeral changes its width even with tabular figures on. */
  .prose :global(tr.peak td) { background: var(--panel); color: var(--ink); }
</style>
