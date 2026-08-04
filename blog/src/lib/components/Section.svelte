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
    /** Optional so a section can stand as a header alone -- a slot held open
     *  while its prose is being written. The body div goes away with it, so an
     *  empty section contributes no stray gap to the page flow. */
    children?: Snippet;
  };
  let { eyebrow, title, id, width = 'measure', children }: Props = $props();
</script>

<section {id} class={width}>
  {#if eyebrow || title}
    <header>
      {#if eyebrow}<div class="eyebrow">{eyebrow}</div>{/if}
      {#if title}<h2>{title}</h2>{/if}
    </header>
  {/if}
  {#if children}<div class="body">{@render children()}</div>{/if}
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

  /* Prose inside a wide section still reads at the measure, and sits in the SAME
     column as the section's own header.
     `align-self: start` put it against the left edge of the 880px figure block
     while the header stayed centred at the 640px measure, so every heading was
     indented 120px from the body text under it at 1440px wide -- the two text
     columns simply did not line up. On the live posts every text block shares
     one column, measured: left 400, width 640 at that viewport. */
  .figure .body :global(.prose),
  .page   .body :global(.prose) { max-width: var(--maxw); align-self: center; }

  /* Both sizes come from the shared scale. They were 0.74rem and a clamp whose
     lower bound was --text-xl and upper bound --text-2xl; the clamp meant the
     section title only reached the house size at wide viewports and silently
     shrank a step below it everywhere else. The eyebrow's 0.74rem was a near
     miss for --text-xs at 0.75rem. Letter-spacing and case stay here: those are
     this component's voice, not the site's scale. */
  /* Inter medium, not the mono face. Measured on the live reliably-incorrect
     page: 12px / 20.4px, weight 500, letter-spacing 0.96px = 0.08em. This
     carried a `mono` class, which set JetBrains Mono and made the eyebrow read
     as code rather than as a label. */
  .eyebrow {
    font-family: var(--font-sans);
    font-size: var(--text-xs);
    font-weight: var(--weight-medium);
    line-height: var(--leading-relaxed);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--ink-faint);
  }
  h2 { margin: 0; font-size: var(--text-2xl); }
</style>
