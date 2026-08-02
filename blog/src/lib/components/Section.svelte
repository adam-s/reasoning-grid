<script lang="ts">
  import type { Snippet } from 'svelte';
  /**
   * `width` picks what the section body is allowed to occupy.
   *   'measure' (default) — 640px, the reading column
   *   'figure'            — 880px, a chart that needs room
   *   'page'              — the full 1100px shell
   * The header always stays at the measure, so a wide figure never drags its
   * own title out to the edge with it.
   */
  type Props = {
    eyebrow?: string;
    title?: string;
    id?: string;
    width?: 'measure' | 'figure' | 'page';
    children: Snippet;
  };
  let { eyebrow, title, id, width = 'measure', children }: Props = $props();
</script>

<section {id} class={width}>
  {#if eyebrow || title}
    <header>
      {#if eyebrow}<div class="eyebrow mono">{eyebrow}</div>{/if}
      {#if title}<h2>{title}</h2>{/if}
    </header>
  {/if}
  <div class="body">{@render children()}</div>
</section>

<style>
  section {
    scroll-margin-top: 24px;
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-md);
  }
  header { width: 100%; max-width: var(--maxw); }
  .body { width: 100%; display: flex; flex-direction: column; gap: var(--space-lg); }

  .measure .body { max-width: var(--maxw); }
  .figure  .body { max-width: var(--maxw-fig); }
  .page    .body { max-width: var(--maxw-page); }

  /* min-width:0 lets a flex child actually shrink below its content width --
     without it an 880px chart refuses to compress and pushes the page wide on
     a phone. This is the whole fix; the max-widths above are only ceilings. */
  .body > :global(*) { min-width: 0; max-width: 100%; }

  /* prose inside a wide section still reads at the measure */
  .figure .body :global(.prose),
  .page   .body :global(.prose) { max-width: var(--maxw); align-self: start; }

  .eyebrow { color: var(--ink-faint); font-size: 0.74rem; letter-spacing: 0.08em; text-transform: uppercase; }
  h2 { margin: 0; font-size: clamp(1.5rem, 4vw, 2rem); }
</style>
