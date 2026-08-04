<script lang="ts">
  /**
   * A hand-drawn nudge at the one control the reader should press next.
   *
   * Ported in shape from the "hear it" cue on the CLAP post, which is the
   * house precedent: a short italic label, a curved arrow, and nothing that can
   * be clicked. Kept as a component rather than repeated markup because it now
   * has to appear against several different controls and one of them moves.
   *
   * ## Rules it enforces so callers cannot get them wrong
   *
   * NEVER CLICKABLE. `pointer-events: none` throughout. A cue that swallows the
   * click it is asking for is worse than no cue.
   *
   * NEVER LOAD-BEARING. It is `aria-hidden`, and it never carries information
   * that is not already in the control it points at. A screen reader gets the
   * button's own label, which is the real one.
   *
   * NEVER RESERVES SPACE. Absolutely positioned against the caller's own
   * positioned box. If it took part in layout, every appearance and
   * disappearance would shift the row it is pointing at, which is the one thing
   * guaranteed to make a reader miss the target.
   *
   * The caller decides WHEN it shows. This file only decides what it looks
   * like, because the question of which control is next is a question about the
   * tour, and the tour is not this component's business.
   */
  type Props = {
    /** Two or three words. It is a nudge, not an instruction. */
    text: string;
    /**
     * Which side of the target it sits on. `above` hangs over the top edge and
     * points down, which suits a control in a row of others. `right` sits
     * outside the right edge, for a control at the end of a line.
     */
    side?: 'above' | 'right';
  };
  let { text, side = 'above' }: Props = $props();
</script>

<div class="cue {side}" aria-hidden="true">
  {#if side === 'above'}
    <span class="hint mono">{text}</span>
    <svg class="arrow" viewBox="0 0 40 32" width="40" height="32">
      <path
        d="M3 3 C 22 2, 33 8, 34 25"
        fill="none" stroke="var(--accent)" stroke-width="1.7" stroke-linecap="round" />
      <path
        d="M27 20 L 35 27 L 37 16"
        fill="none" stroke="var(--accent)" stroke-width="1.7"
        stroke-linecap="round" stroke-linejoin="round" />
    </svg>
  {:else}
    <svg class="arrow" viewBox="0 0 40 32" width="40" height="32">
      <path
        d="M37 3 C 18 2, 7 8, 6 25"
        fill="none" stroke="var(--accent)" stroke-width="1.7" stroke-linecap="round" />
      <path
        d="M13 20 L 5 27 L 3 16"
        fill="none" stroke="var(--accent)" stroke-width="1.7"
        stroke-linecap="round" stroke-linejoin="round" />
    </svg>
    <span class="hint mono">{text}</span>
  {/if}
</div>

<style>
  .cue {
    position: absolute;
    display: flex;
    align-items: flex-end;
    gap: 2px;
    pointer-events: none;
    z-index: 2;
  }
  /* Sits over the top-left of the target and leans in. Bottom is negative of
     the arrow height so the arrowhead lands on the control's own top edge. */
  .cue.above { left: 4px; bottom: calc(100% - 10px); }
  .cue.right { left: calc(100% - 6px); bottom: 2px; }

  .hint {
    color: var(--accent);
    font-size: 0.74rem;
    font-style: italic;
    white-space: nowrap;
    margin-bottom: 10px;
  }

  .arrow {
    overflow: visible;
    animation: nudge 1.6s ease-in-out infinite;
  }
  @keyframes nudge {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(3px); }
  }

  /* The arrow is the whole point, so it stays. Only the motion goes. */
  @media (prefers-reduced-motion: reduce) {
    .arrow { animation: none; }
  }

  @media (max-width: 600px) {
    .hint { font-size: 0.68rem; }
    .arrow { width: 30px; height: 24px; }
  }
</style>
