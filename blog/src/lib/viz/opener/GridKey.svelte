<script lang="ts">
  /**
   * The 14 by 14 grid, at thumbnail size, with nothing in it.
   *
   * ## Why it carries no data
   *
   * Section 02 draws this same grid with a reliability rate in every cell. If
   * this one were shaded too -- by problem count, say -- a reader would meet two
   * fourteen-by-fourteen grids carrying different quantities and reasonably
   * assume they were the same picture. An empty lattice cannot be mistaken for
   * a measurement, so it orients without competing.
   *
   * It also has nothing to show. Problem count per cell is 10^(a+b), a clean
   * exponential, so a heatmap of it is a smooth gradient from one corner to the
   * other and says only "it grows" -- which the sentence beside it already says,
   * with the actual number.
   *
   * ## What it is for
   *
   * One job: make "every problem size gets a cell of its own" a thing the reader
   * has seen rather than a thing they have been told. The marked cell is the one
   * the prose names in the same breath, so the sentence and the picture point at
   * the same square.
   */

  /** The cell the prose names: one digit against nine. */
  const MARK = { a: 1, b: 9 };

  const N = 14;
  const CELL = 9;
  const GAP = 1.6;
  const PAD = { l: 34, r: 6, t: 6, b: 30 };
  const SIDE = N * CELL + (N - 1) * GAP;
  const W = PAD.l + SIDE + PAD.r;
  const H = PAD.t + SIDE + PAD.b;

  /**
   * A DOWN THE SIDE, B ACROSS THE TOP, BOTH STARTING AT 1 IN THE TOP LEFT.
   *
   * Copied from AllocationGrid rather than chosen: its `rowsA` is the outer loop
   * and `colsB` the inner, so a CSS grid lays A down and B across with 1 at the
   * top left. This diagram is the reader's first sight of the lattice, so if it
   * disagreed with the real one the disagreement would be theirs to unlearn.
   */
  const x = (b: number) => PAD.l + (b - 1) * (CELL + GAP);
  const y = (a: number) => PAD.t + (a - 1) * (CELL + GAP);

  const cells = Array.from({ length: N }, (_, i) =>
    Array.from({ length: N }, (_, j) => ({ a: i + 1, b: j + 1 })),
  ).flat();
</script>

<div class="wrap">
  <svg
    viewBox="0 0 {W} {H}"
    role="img"
    aria-label="A fourteen by fourteen lattice of cells, one per problem size,
      with the cell for one digit against nine digits picked out."
  >
    {#each cells as c}
      <rect
        x={x(c.b)}
        y={y(c.a)}
        width={CELL}
        height={CELL}
        class="cell"
        class:mark={c.a === MARK.a && c.b === MARK.b}
      />
    {/each}

    <text x={x(1) + CELL / 2} y={H - 16} class="tick mid">1</text>
    <text x={x(N) + CELL / 2} y={H - 16} class="tick mid">14</text>
    <text x={PAD.l - 6} y={y(1) + CELL} class="tick end">1</text>
    <text x={PAD.l - 6} y={y(N) + CELL} class="tick end">14</text>

    <text x={PAD.l + SIDE / 2} y={H - 4} class="axis">digits in B</text>
    <text x={-(PAD.t + SIDE / 2)} y={9} class="axis" transform="rotate(-90)"
      >digits in A</text>
  </svg>
  <p class="note">
    One cell per problem size, digits against digits. The marked one is a single
    digit against nine.
  </p>
</div>

<style>
  /* Sits in the reading column at the size of a diagram, not a figure. Anything
     larger and it reads as the section's chart rather than as a key to it.

     Centred and stacked rather than set beside the note, because it runs ABOVE
     the paragraph it explains: a side-by-side block reads as an aside the reader
     may skip, and this one has to be looked at before the sentence lands. */
  .wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-sm);
    margin: var(--space-lg) 0 var(--space-xl);
  }

  svg {
    display: block;
    width: 186px;
    flex: none;
    height: auto;
    overflow: visible;
  }

  .cell { fill: var(--line); }
  .cell.mark { fill: var(--ink-dim); }

  .tick {
    font-family: var(--font-mono);
    font-size: 8px;
    fill: var(--ink-faint);
  }
  .tick.mid { text-anchor: middle; }
  .tick.end { text-anchor: end; }

  .axis {
    font-family: var(--font-sans);
    font-size: 8px;
    fill: var(--ink-dim);
    letter-spacing: 0.04em;
    text-anchor: middle;
  }

  .note {
    margin: 0;
    max-width: 42ch;
    font-family: var(--font-sans);
    font-size: var(--text-sm);
    line-height: var(--leading-snug);
    color: var(--ink-dim);
    text-align: center;
    text-wrap: balance;
  }
</style>
