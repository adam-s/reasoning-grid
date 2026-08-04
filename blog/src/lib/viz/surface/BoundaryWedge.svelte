<script lang="ts">
  /**
   * Two models over 144 measured cells -- 288 rates, one per model per cell --
   * and the distance between where each one stops being right half the time.
   *
   * ## Why this figure and not the paired one
   *
   * What used to sit here plotted the better of the two models with Phi-wins
   * cells marked, which is a COVERAGE claim: that a second vendor reaches
   * problems the first cannot. `probe/self_rescue.py` killed it. At 1.50 Qwen
   * attempts per problem and 1.14 Phi attempts, a second sample of QWEN would
   * have rescued 102.7 of Qwen's failures against Phi's actual 82, and both
   * directions sit inside the noise of a null where every problem in a cell is
   * equally hard.
   *
   * The MARGINAL comparison survives that untouched, because it needs no
   * pairing. Two models built by different companies on different data with
   * different tokenizers hold the same shape of curve and differ only in where
   * along it they sit. That is a claim about the task rather than about either
   * model, and it is what makes the grid an instrument rather than one model's
   * benchmark.
   *
   * ## The x axis is a + b, and choosing it is a finding
   *
   * The rest of this project plots difficulty against N = a*b, the count of
   * single-digit operations. `probe/difficulty_axis.py` fits the alternatives
   * against each other and the total wins by a wide margin: on the 196-cell
   * Qwen pool, a+b scores -1183.9 log-likelihood against log(a*b) at -1251.5 on
   * the same parameter count, and adding the product on top of the total buys
   * 1.1 for one more parameter.
   *
   * It shows in single cells without any fitting. At a total of 16, 2x14 needs
   * 28 operations and lands 57%, while 8x8 needs 64 and lands 85%. Less than
   * half the work, worse result.
   *
   * THAT EXAMPLE IS FROM THE 196-CELL SURFACE POOL, NOT FROM `WINNER`. This
   * file's data stops at 12 digits, so it holds no 2x14 at all, and its own 8x8
   * Qwen rate is 0.8333 rather than 0.85. The point stands and the numbers are
   * not this figure's to check -- said without the provenance, they read as
   * something a reader could verify against the dots above, and they cannot.
   *
   * That contradicts the allocation caption in section 01 and the published
   * distribution chart, both of which are built on a*b. Neither is fixed by
   * this file. `probe/difficulty_axis.py` records what needs revisiting.
   *
   * ## What is drawn
   *
   * DOTS are measured cells, one per model per cell, at the cell's own rate.
   * Cells sharing a total stack in a column, so the vertical spread inside a
   * column is the part a+b does not explain.
   *
   * BANDS are the fit, not a smoothing of the dots. At each total the band runs
   * from the least to the most favourable value of min(a,b) available at that
   * total, so its thickness IS the leftover shape effect. It is a couple of
   * points wide, which is the visual form of B2 being small.
   *
   * The 50% crossings are marked and the distance between them labelled,
   * because that distance is the only number this figure exists to deliver.
   */
  import { WINNER } from '../../data/winner';
  import { observeWidth } from '../observeWidth.svelte';

  const [QWEN_FIT, PHI_FIT] = WINNER.fits;
  const [QWEN_NAME, PHI_NAME] = WINNER.models;
  const [QWEN_HALF, PHI_HALF] = WINNER.findings.halfAt;
  const HI = WINNER.dim;

  const T_LO = 2;
  const T_HI = HI * 2;

  /**
   * ---- ONE SCALE FOR THE TYPE AND THE ROOM IT NEEDS -----------------------
   *
   * The svg is `width: 100%` over a fixed viewBox, so everything inside it,
   * type included, scales with the container. At a 430px viewport the content
   * column is 414px against this 834-unit box, which renders the axis ticks at
   * 5.5px and the "1.7 digits" callout -- the one number this figure exists to
   * deliver -- at 6.0px. The shapes survive that; the labels do not.
   *
   * `u` is one rendered CSS pixel expressed in viewBox units, so type written
   * as `calc(11px * var(--u))` comes out 11px on the glass at any width.
   *
   * THE GUTTERS SCALE WITH IT, and that is the half that is easy to miss.
   * Growing the type alone was tried first: the y-axis labels ran off the left
   * edge, both model names were cut in half on the right, and the axis title
   * landed on top of the tick row. Padding sized for 11px type does not hold
   * 24px type. The box stays fixed and the plot inside it gives up whatever the
   * labels need.
   *
   * IT ONLY EVER GROWS TYPE. Clamped at 1 below, because on a wide screen the
   * svg is drawn larger than its viewBox and counter-scaling there would shrink
   * the labels -- fixing the phone by breaking the desktop. At u = 1 every
   * number here is what it was before any of this, so the desktop figure is
   * unchanged by construction. Capped at 2.2, past which the gutters start
   * eating the plot they exist to label.
   */
  let host: HTMLElement | null = $state(null);
  let u = $state(1);

  /** The viewBox is fixed: `u` is measured against it, so it cannot depend on u. */
  const W = 834;
  const H = 378;
  const PAD = $derived({ l: 46 * u, r: 128 * u, t: 16 * u, b: 42 * u });
  const PW = $derived(W - PAD.l - PAD.r);
  const PH = $derived(H - PAD.t - PAD.b);

  observeWidth(() => host, (px) => {
    u = Math.min(2.2, Math.max(1, W / px));
  });

  const sx = (t: number) => PAD.l + ((t - T_LO) / (T_HI - T_LO)) * PW;
  const sy = (p: number) => PAD.t + (1 - p) * PH;

  const sigmoid = (z: number) => 1 / (1 + Math.exp(-Math.max(-30, Math.min(30, z))));

  /** The fit's prediction at one total, as the range it spans across every
   *  problem shape that total allows. Returns [low, high]. */
  function span(fit: readonly number[], t: number): [number, number] {
    const [b0, b1, b2] = fit;
    const mLo = Math.max(1, t - HI);
    const mHi = t / 2;
    const a = sigmoid(b0 + b1 * t + b2 * mLo);
    const b = sigmoid(b0 + b1 * t + b2 * mHi);
    return a < b ? [a, b] : [b, a];
  }

  /** Closed band polygon: the high edge left to right, the low edge back. */
  function band(fit: readonly number[]) {
    const hi: string[] = [];
    const lo: string[] = [];
    for (let t = T_LO; t <= T_HI + 1e-9; t += 0.25) {
      const [l, h] = span(fit, t);
      hi.push(`${sx(t).toFixed(1)},${sy(h).toFixed(1)}`);
      lo.push(`${sx(t).toFixed(1)},${sy(l).toFixed(1)}`);
    }
    return [...hi, ...lo.reverse()].join(' ');
  }

  /** Mid-line through the band, so a thin band still reads as a curve. */
  function spine(fit: readonly number[]) {
    const p: string[] = [];
    for (let t = T_LO; t <= T_HI + 1e-9; t += 0.25) {
      const [l, h] = span(fit, t);
      p.push(`${sx(t).toFixed(1)},${sy((l + h) / 2).toFixed(1)}`);
    }
    return p.join(' ');
  }

  type Dot = { t: number; q: number; p: number; n: number };
  const DOTS: Dot[] = Object.entries(WINNER.cells).map(([k, c]) => {
    const [a, b] = k.split('x').map(Number);
    return { t: a + b, q: c.qwen, p: c.phi, n: c.n };
  });

  /* Crossings are quoted per factor, which is what halfAt measures, and drawn
     at the total, which is what the axis is. Both appear so neither has to be
     inferred from the other. */
  const xQ = QWEN_HALF * 2;
  const xP = PHI_HALF * 2;
  /* Two forms of one distance, and they must not be swapped. The label ON the
     plane has to be the one a reader can measure against the axis, which is the
     TOTAL. Per factor is half of it and belongs in the caption beside the two
     crossings it is derived from. Labelling the drawn segment 0.85 while it
     spans 1.7 axis units is the figure lying about its own geometry. */
  const gapTotal = (xQ - xP).toFixed(1);
  const gap = (QWEN_HALF - PHI_HALF).toFixed(2);

  /** Half the gap between the two models' dots for one cell, in viewBox units. */
  const DODGE = $derived((PW / (T_HI - T_LO)) * 0.075);

  const Y_TICKS = [0, 0.25, 0.5, 0.75, 1];
  const X_TICKS = [4, 8, 12, 16, 20, 24];
  const pct = (p: number) => `${Math.round(p * 100)}%`;
</script>

<figure bind:this={host} style:--u={u}>
  <svg
    viewBox="0 0 {W} {H}"
    role="img"
    aria-label="Success rate against the total digit count, for {QWEN_NAME} and
      {PHI_NAME}. Both fall along the same shape. {QWEN_NAME} crosses fifty
      percent at {QWEN_HALF} digits per factor and {PHI_NAME} at {PHI_HALF},
      a difference of {gap} digits."
  >
    {#each Y_TICKS as p}
      <line x1={PAD.l} y1={sy(p)} x2={PAD.l + PW} y2={sy(p)}
            class="grid" class:half={p === 0.5} />
      <text x={PAD.l - 9 * u} y={sy(p) + 4 * u} class="tick end">{pct(p)}</text>
    {/each}

    <!-- Measured cells. Drawn under the fit so the fit reads as a claim about
         them rather than as a replacement for them. -->
<!-- THE PAIR IS NUDGED APART. Both dots for a cell used to sit on the same
         cx, so wherever a cell scored the same for both models the second dot
         was drawn exactly on top of the first and one of the two vanished.
         Across the grid that hid 166 of the 288, most of them along the 100%
         line at the easy sizes, where a reader saw only red and could conclude
         Qwen had not been measured there at all. The offset is a twentieth of a
         step on an integer axis, which is too small to misread a total by and
         enough to keep both dots on the page. -->
    {#each DOTS as d}
      <circle cx={sx(d.t) - DODGE} cy={sy(d.q)} r={d.n === 12 ? 3.4 : d.n === 6 ? 2.7 : 2}
              class="dot qwen" />
      <circle cx={sx(d.t) + DODGE} cy={sy(d.p)} r={d.n === 12 ? 3.4 : d.n === 6 ? 2.7 : 2}
              class="dot phi" />
    {/each}

    <polygon points={band(QWEN_FIT)} class="band qwen" />
    <polygon points={band(PHI_FIT)} class="band phi" />
    <polyline points={spine(QWEN_FIT)} class="spine qwen" />
    <polyline points={spine(PHI_FIT)} class="spine phi" />

    <!-- The gap, on the 50% line, with both crossings marked. This is the one
         number the figure is for, so it is measured on the plane. -->
    <line x1={sx(xP)} y1={sy(0.5)} x2={sx(xQ)} y2={sy(0.5)} class="gap-rule" />
    <circle cx={sx(xP)} cy={sy(0.5)} r="3.6" class="knot phi" />
    <circle cx={sx(xQ)} cy={sy(0.5)} r="3.6" class="knot qwen" />
    <text x={(sx(xP) + sx(xQ)) / 2} y={sy(0.5) - 13 * u} class="gap">{gapTotal} digits</text>

    <text x={PAD.l + PW + 8 * u} y={sy(span(QWEN_FIT, T_HI - 2)[1]) - 22 * u}
          class="key qwen">{QWEN_NAME}</text>
    <text x={PAD.l + PW + 8 * u} y={sy(span(PHI_FIT, T_HI - 2)[1]) + 2 * u}
          class="key phi">{PHI_NAME}</text>

    {#each X_TICKS as t}
      <text x={sx(t)} y={PAD.t + PH + 18 * u} class="tick mid">{t}</text>
    {/each}
    <text x={PAD.l + PW / 2} y={H - 6 * u} class="axis">digits in a plus digits in b</text>
  </svg>

  <figcaption>
    Every one of the {Object.keys(WINNER.cells).length} cells contributes two
    dots, one per model, scored on {WINNER.problems.toLocaleString()} problems
    both models answered. Cells that share a digit total sit in the same column,
    so where several agree their dots land on each other and read as one. Right
    half the time at {QWEN_HALF} digits per factor for {QWEN_NAME} and
    {PHI_HALF} for {PHI_NAME}. The bands are the fit across every problem shape at each total,
    so their width is what shape is worth once the total is known. Of the
    {Object.keys(WINNER.cells).length} cells,
    {WINNER.findings.outsideNoise} differ by more than noise and
    {WINNER.findings.outsideNoisePhi} of those favour {PHI_NAME}.
  </figcaption>
</figure>

<style>
  figure { width: 100%; }
  svg { display: block; width: 100%; height: auto; overflow: visible; }

  .grid { stroke: var(--line); stroke-width: 1; }
  .grid.half { stroke: var(--line-strong); }

  .dot { fill-opacity: 0.4; }
  .dot.qwen { fill: var(--model-a); }
  .dot.phi { fill: var(--model-b); }

  .band { fill-opacity: 0.28; }
  .band.qwen { fill: var(--model-a); }
  .band.phi { fill: var(--model-b); }

  .spine { fill: none; stroke-width: 1.75; }
  .spine.qwen { stroke: var(--model-a); }
  .spine.phi { stroke: var(--model-b); }

  .gap-rule { stroke: var(--ink); stroke-width: 1.25; }
  .knot { stroke: var(--bg); stroke-width: 1.5; }
  .knot.qwen { fill: var(--model-a); }
  .knot.phi { fill: var(--model-b); }

  .gap {
    font-family: var(--font-sans);
    font-size: calc(12px * var(--u, 1));
    font-weight: var(--weight-medium);
    fill: var(--ink);
    text-anchor: middle;
  }

  .key {
    font-family: var(--font-sans);
    font-size: calc(13px * var(--u, 1));
    font-weight: var(--weight-medium);
    dominant-baseline: middle;
  }
  .key.qwen { fill: var(--model-a); }
  .key.phi { fill: var(--model-b); }

  .tick {
    font-family: var(--font-mono);
    font-size: calc(11px * var(--u, 1));
    fill: var(--ink-faint);
  }
  .tick.mid { text-anchor: middle; }
  .tick.end { text-anchor: end; }

  .axis {
    font-family: var(--font-sans);
    font-size: calc(12px * var(--u, 1));
    fill: var(--ink-dim);
    letter-spacing: 0.04em;
    text-anchor: middle;
  }

  figcaption {
    margin-top: var(--space-md);
    max-width: var(--maxw);
    font-family: var(--font-sans);
    font-size: var(--text-sm);
    line-height: var(--leading-snug);
    color: var(--ink-dim);
  }
</style>
