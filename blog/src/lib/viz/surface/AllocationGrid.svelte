<script lang="ts">
  /**
   * Where the runs go, and why.
   *
   * THIS FIGURE IS THE DECISION, NOT THE RECORD. Both numbers come out of
   * docs/runs-per-cell.md, which is where the allocation was decided. Nothing
   * here reports what the sweep did, and the sweep did not follow it.
   *
   * That distinction was got wrong twice while this was built, and both ways
   * are worth remembering. First the colour was the MEASURED rate, which
   * carries the noise of however many generations a cell happened to receive,
   * so a design figure was being drawn out of accidents of sampling. Then the
   * allocation was recomputed here from the sweep, which produced numbers near
   * the committed ones but not equal to them. Two allocations in one repository
   * is one too many. The doc owns the decision and this renders it.
   *
   * The left half reads the square diagonal as a table, because the shape of the
   * rule is easier to check as a column of numbers than as a field of colour.
   * Both halves load one generated file, so a table hand-copied beside a chart
   * cannot drift away from it.
   *
   * ## The thing the figure is for
   *
   * Runs do not climb with difficulty. They climb and then fall, because a cell
   * the model always fails is as settled as one it always solves. Reading the
   * `runs` column top to bottom shows that turn without a sentence having to
   * claim it.
   */
  import { ALLOCATION, ALLOC_MAX_A, ALLOC_MAX_B } from '../../data/allocation';
  import { ramp } from './project';

  const byKey = new Map(ALLOCATION.map((c) => [`${c.a}x${c.b}`, c]));
  const rowsA = Array.from({ length: ALLOC_MAX_A }, (_, i) => i + 1);
  const colsB = Array.from({ length: ALLOC_MAX_B }, (_, i) => i + 1);

  /** The square diagonal, which is the line the table reads. */
  const diagonal = rowsA
    .map((d) => byKey.get(`${d}x${d}`))
    .filter((c): c is NonNullable<typeof c> => !!c);

  /**
   * White on the dark end of the ramp, ink on the pale end. The ramp runs from
   * a near-white to a deep brown, so a single text colour is unreadable over
   * half of it. The threshold is on `p` rather than on a computed luminance
   * because the ramp is fixed and one comparison is cheaper than parsing a
   * colour back out of a string.
   */
  const inkFor = (p: number) => (p > 0.55 ? 'rgba(253,252,249,0.95)' : 'var(--ink)');

  let hover: string | null = $state(null);
  const hovered = $derived(hover ? byKey.get(hover) : null);
</script>

<figure class="alloc">
  <div class="split">
    <div class="left">
      <p class="cap-label">the square diagonal</p>
      <!-- PREDICTED p, not measured. The allocation runs off the fitted curve
           because a rate from three generations is too noisy to spend against,
           and this column has to show the number the runs column was actually
           computed from. See probe/build_allocation.py. -->
      <table>
        <thead>
          <tr><th>cell</th><th>predicted p</th><th>p(1 &minus; p)</th><th>runs</th></tr>
        </thead>
        <tbody>
          {#each diagonal as c (c.a)}
            {@const v = c.p * (1 - c.p)}
            <tr
              class:peak={c.runs === Math.max(...diagonal.map((d) => d.runs))}
              class:on={hover === `${c.a}x${c.b}`}
              onmouseenter={() => (hover = `${c.a}x${c.b}`)}
              onmouseleave={() => (hover = null)}
            >
              <td>{c.a} &times; {c.b}</td>
              <td>{Math.round(c.p * 100)}%</td>
              <td>{v.toFixed(3)}</td>
              <td>{c.runs}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <div class="right">
      <p class="cap-label">
        every cell &middot; colour is the predicted rate, number is the runs it earns
      </p>
      <div class="grid" style:--cols={ALLOC_MAX_B}>
        {#each rowsA as a (a)}
          {#each colsB as b (b)}
            {@const c = byKey.get(`${a}x${b}`)}
            {#if c}
              <div
                class="cell"
                class:on={hover === `${a}x${b}`}
                style:background={ramp(c.p)}
                style:color={inkFor(c.p)}
                title="{a} x {b} digits · predicted {Math.round(c.p * 100)}% · {c.runs} runs"
                onmouseenter={() => (hover = `${a}x${b}`)}
                onmouseleave={() => (hover = null)}
                role="presentation"
              >{c.runs}</div>
            {:else}
              <div class="cell empty"></div>
            {/if}
          {/each}
        {/each}
      </div>
      <div class="axes">
        <span>1 digit</span>
        <span class="readout mono">
          {#if hovered}
            {hovered.a} &times; {hovered.b} &middot;
            {Math.round(hovered.p * 100)}% &middot;
            {hovered.runs} runs
          {:else}
            hover a cell
          {/if}
        </span>
        <span>{ALLOC_MAX_B} digits</span>
      </div>
    </div>
  </div>

  <figcaption>
    Colour is the predicted pass rate. The number is the runs that cell earns
    under cost-weighted Neyman allocation. The ridge follows a hyperbola rather
    than the diagonal, because difficulty tracks the two digit counts multiplied
    together, so 5 by 13 costs the same attention as 8 by 8.
  </figcaption>
</figure>

<style>
  .alloc { margin: var(--space-lg) 0; }

  /* Two halves, and they stack rather than shrink on a narrow screen. A 12 by
     12 grid squeezed into half a phone is unreadable at any font size. */
  .split {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: var(--space-xl);
    align-items: start;
  }
  @media (max-width: 760px) {
    .split { grid-template-columns: minmax(0, 1fr); gap: var(--space-lg); }
  }

  .cap-label {
    margin: 0 0 var(--space-sm);
    font-family: var(--font-sans);
    font-size: var(--text-xs);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--ink-faint);
  }

  table { width: 100%; border-collapse: collapse; font-family: var(--font-sans); }
  th, td {
    padding: 4px 8px;
    border-bottom: 1px solid var(--line);
    text-align: right;
    font-size: var(--text-sm);
  }
  th:first-child, td:first-child { text-align: left; }
  th {
    border-bottom-color: var(--line-strong);
    color: var(--ink-dim);
    font-size: var(--text-xs);
    font-weight: var(--weight-medium);
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }
  td { font-variant-numeric: tabular-nums; }
  td:not(:first-child) { font-family: var(--font-mono); }
  /* Background, never weight. A bold numeral is a wider numeral even with
     tabular figures on, and a table that reflows on hover reads as broken. */
  tr.peak td { background: var(--panel); }
  tr.on td { background: var(--panel-2); }

  .grid {
    display: grid;
    grid-template-columns: repeat(var(--cols), minmax(0, 1fr));
    gap: 1px;
  }
  .cell {
    aspect-ratio: 1;
    display: grid;
    place-items: center;
    font-family: var(--font-mono);
    font-size: 0.58rem;
    font-variant-numeric: tabular-nums;
    line-height: 1;
    cursor: default;
  }
  .cell.empty { background: var(--panel); }
  /* Outline rather than a background change, so hovering never alters the value
     the colour is encoding.

     `currentColor`, not a fixed ink. Each cell already picks white or ink for
     its numeral from where it sits on the ramp, so the outline inherits that
     same decision and stays visible at both ends. A fixed dark outline vanished
     against the deep end of the ramp, which is the half of the grid a reader is
     most likely to be poking at. */
  .cell.on { outline: 2px solid currentColor; outline-offset: -2px; }

  .axes {
    display: flex;
    justify-content: space-between;
    gap: var(--space-sm);
    margin-top: 6px;
    font-family: var(--font-sans);
    font-size: var(--text-xs);
    color: var(--ink-faint);
  }
  .readout { font-family: var(--font-mono); color: var(--ink-dim); }

  figcaption {
    margin-top: var(--space-md);
    font-family: var(--font-sans);
    font-size: var(--text-xs);
    line-height: var(--leading-snug);
    color: var(--ink-dim);
  }
</style>
