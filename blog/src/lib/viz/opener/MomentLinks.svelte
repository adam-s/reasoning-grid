<script lang="ts">
  /**
   * The row of "take me there" controls under a trace figure.
   *
   * These are BUTTONS, not links. They move a figure already on the page rather
   * than navigating, so an anchor would promise the reader a destination and a
   * back button that do not exist.
   *
   * The component holds no state. Which moment is current, whether the figure
   * is mid-flight, and which control the cue points at all live with whoever
   * owns the figure, because two copies of any of that would be two copies to
   * get out of step. See the presenter note in SyncedTrace.svelte and the tour
   * note in App.svelte.
   */
  import Cue from './Cue.svelte';
  type Moment = {
    /** Stable id. The figure reports this back on arrival. */
    readonly id: string;
    /** Index into the figure's run list. */
    readonly run: number;
    /** Character offset into that run's response. */
    readonly at: number;
    readonly label: string;
  };

  type Props = {
    moments: readonly Moment[];
    /** Names the row. Required in practice once two rows stack, because the
     *  numerals restart at 1 in each and without a label the second row reads
     *  as a continuation of the first. */
    label?: string;
    /** The moment the reader is currently sitting on, or null once they have
     *  moved the cursor themselves. */
    active?: string | null;
    /** True while the figure is scrolling or seeking and owns the cursor. */
    busy?: boolean;
    /** Id of the one moment to point at, if it is in this row. The tour owns
     *  this decision; the row only renders it. */
    cueOn?: string | null;
    cueText?: string;
    onPick: (m: Moment) => void;
  };

  let {
    moments, label, active = null, busy = false,
    cueOn = null, cueText = 'next', onPick,
  }: Props = $props();
</script>

{#if label}<p class="row-label">{label}</p>{/if}
<ol class="moments">
  {#each moments as m, i (m.id)}
    <li class:cued={cueOn === m.id}>
      {#if cueOn === m.id}<Cue text={cueText} />{/if}
      <button
        type="button"
        class:on={active === m.id}
        disabled={busy}
        aria-current={active === m.id ? 'true' : undefined}
        onclick={() => onPick(m)}
      >
        <span class="n mono">{i + 1}</span>
        <span class="label">{m.label}</span>
      </button>
    </li>
  {/each}
</ol>

<style>
  /* Equal air above and below, and more of it than the gap between two
     paragraphs. The row is a control group sitting inside prose, so it has to
     read as its own thing rather than as a line of that prose.

     The top value is larger than it looks: the paragraph above contributes its
     own bottom margin and the two collapse, so this sets the gap rather than
     adding to it. */
  .row-label {
    margin: var(--space-lg) 0 var(--space-sm);
    font-family: var(--font-sans);
    font-size: var(--text-xs);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--ink-faint);
  }
  /* A labelled row owns the space above it through its label, so the row itself
     must not add more or the two would stack into a gap twice the size. */
  .row-label + .moments { margin-top: 0; }

  /* EVEN CELLS, NOT A WRAPPING ROW.
     Flex-wrap sizes each button to its own label and then breaks wherever it
     runs out of width, so the four moments came out four different widths, and
     the two rows of the figure broke in different places from each other. A
     fixed column count gives every moment the same box at every width, and the
     step numerals line up down the page. */
  .moments {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: var(--space-sm);
    margin: var(--space-lg) 0;
    padding: 0;
    list-style: none;
  }
  /* Every item is a real cell, and they are all the same kind of cell.
     This used to be `display: contents` with the cued one promoted to
     `inline-flex` so the cue had something to position against -- which made
     exactly one button in the row size itself differently from its neighbours,
     and it was always the one being pointed at. `position: relative` on all of
     them costs nothing and the cue works from any. */
  li {
    display: block;
    position: relative;
    min-width: 0;
  }

  button {
    display: inline-flex;
    align-items: baseline;
    gap: 8px;
    /* Fills its cell, so the boxes are even whatever the labels do. */
    width: 100%;
    height: 100%;
    /* And the two rows match each other. Equal columns mean a long label wraps
       to two lines, which made the first row 48px tall against the second row's
       31px -- even within itself, obviously uneven against its pair. The floor
       is the two-line height, so every moment on the page is one size. */
    min-height: 48px;
    padding: 6px 12px;
    background: var(--bg);
    border: 1px solid var(--line-strong);
    border-radius: var(--radius-sm);
    font-family: var(--font-sans);
    font-size: var(--text-sm);
    color: var(--ink);
    cursor: pointer;
    text-align: left;
    transition: border-color 150ms ease, background 150ms ease, color 150ms ease;
  }
  button:hover:not(:disabled) {
    border-color: var(--accent);
    color: var(--accent);
  }
  button:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }

  /* The current moment is marked by the border and the numeral, never by
     weight. A bolder label is a wider label, and a row that reflows every time
     the reader arrives somewhere is a row that appears to twitch. */
  button.on {
    border-color: var(--accent);
    background: var(--panel);
  }
  button.on .n { color: var(--accent); }

  /* Disabled means the figure is mid-flight, which lasts under a second. Dim
     it enough to read as unavailable without the row flashing grey on every
     click. */
  button:disabled {
    opacity: 0.55;
    cursor: default;
  }

  .n {
    font-size: var(--text-xs);
    color: var(--ink-faint);
    font-variant-numeric: tabular-nums;
  }

  /* TWO AND TWO, NOT THREE AND ONE.
     Wrapping is what a flex row does when it runs out of width, and what it
     does is fit as many as it can and drop the remainder -- so four moments
     came out as a row of three and an orphan, and the two rows of the figure
     broke in different places from each other. A two-column grid puts the same
     four buttons in a block, equal width, with the step numbers lining up
     vertically. The label of the longest moment sets the column, so nothing is
     truncated. */
  @media (max-width: 700px) {
    .moments {
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 6px;
    }
    button { font-size: var(--text-xs); padding: 5px 10px; }
  }
</style>
