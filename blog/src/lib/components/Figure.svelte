<script lang="ts">
  /**
   * Holds a figure's box open while the figure is not there yet.
   *
   * The page is prerendered to HTML at build time, so the prose paints before
   * any JavaScript runs. None of these figures can be rendered on the server —
   * they are canvas, rAF and matchMedia — so the server emits this wrapper
   * empty and the figure appears on mount. Without a reserved box the reader
   * would get the essay, then watch nine figures shove it down the page.
   *
   * The heights come from `scripts/measure-figures.mjs`, which sweeps the real
   * page across widths and writes `figure-heights.css`. They are measured, not
   * guessed, and per figure rather than per tier: these figures do not share
   * breakpoints and they do not scale by aspect ratio. The opener is 510px tall
   * on a phone and 517px on a desktop three times as wide, while the trace
   * figure is 891px tall on a phone and 542px on a tablet. One `aspect-ratio`
   * rule would be wrong at every width.
   *
   * `data-fig` is the key into that stylesheet and the selector the measuring
   * and verifying scripts use. It has to stay stable.
   */
  import { onMount, type Snippet } from 'svelte';

  type Props = { name: string; alt: string; children: Snippet };
  let { name, alt, children }: Props = $props();

  /**
   * Not `typeof window !== 'undefined'`. That is true on the very first client
   * render, which is the hydration pass, and it would make the client's output
   * disagree with the server's. Flipping in onMount means hydration matches
   * what the server sent and the figure arrives one tick later.
   */
  let mounted = $state(false);
  onMount(() => {
    mounted = true;
  });
</script>

<div class="fig" data-fig={name} class:pending={!mounted}>
  {#if mounted}{@render children()}{/if}
  <!-- No spinner. With JavaScript on this box is empty for about a tenth of a
       second, and anything drawn there would flash rather than reassure. With
       JavaScript off the figure never arrives at all, and an unexplained blank
       the height of a phone screen reads as a broken page — so that is the case
       worth answering, and <noscript> answers exactly it. -->
  <noscript><p class="alt">{alt}</p></noscript>
</div>

<style>
  .fig {
    min-width: 0;
    max-width: 100%;
  }

  /* Set like a caption, because that is what it is. It stands in for the whole
     figure for a reader who will never see one, so it takes the same alignment,
     size and ink as a real figcaption rather than the smaller, fainter, centred
     treatment of a footnote. Centring it also wanted `display: flex` on .fig,
     which was not free: it re-sized GridKey from 229px to 293px, and
     `measure-figures.mjs --check` was the only thing that noticed. */
  .alt {
    margin: 0;
    max-width: var(--maxw);
    padding-bottom: var(--space-md);
    font-family: var(--font-sans);
    font-size: var(--text-sm);
    line-height: var(--leading-snug);
    color: var(--ink-dim);
  }
</style>
