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

  .moments {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-sm);
    margin: var(--space-lg) 0;
    padding: 0;
    list-style: none;
  }
  /* `display: contents` lets the buttons be direct flex children of the row, so
     the `li` adds no box. A cued item has to become a box again, because the
     cue is positioned against it. It is `inline-flex` rather than `block` so it
     still sits in the row at its own width. */
  li { display: contents; }
  li.cued { display: inline-flex; position: relative; }

  button {
    display: inline-flex;
    align-items: baseline;
    gap: 8px;
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

  @media (max-width: 600px) {
    .moments { gap: 6px; }
    button { font-size: var(--text-xs); padding: 5px 10px; }
  }
</style>
