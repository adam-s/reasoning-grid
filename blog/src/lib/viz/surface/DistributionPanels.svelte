<script lang="ts">
  /**
   * Three charts, one argument, no words.
   *
   * LEFT is the outcome: 500 independent twelve-problem scores of one cell,
   * piled into the value each came back with. RIGHT is the cause, twice: the
   * running estimate for each run with its 95% envelope, so a reader can see
   * how far in you have to go before the number stops moving.
   *
   * Reading order is left to right and then top to bottom on the right, which
   * is why the histogram is the tall single panel and the funnels are stacked
   * beside it. The histogram is what a benchmark reports; the funnels are what
   * it took to know that.
   *
   * ## Minimal, not bare
   *
   * It ran with no labels at all for a while and read as decoration. What went
   * back is the least that lets it be checked: what each panel counts, the value
   * it settles on, and how wide the interval is. Nothing that the prose around
   * it should be saying.
   *
   * ## Flush by construction
   *
   * All three panels are the same four rows: label, plot, axis numerals, note.
   * Every row but the plot has a fixed height set in one place, so the plots are
   * the only thing that flexes and they land on identical top and bottom edges
   * without anyone measuring anything.
   *
   * The numerals sit in HTML rather than inside the svg. That is what lets the
   * plots stretch -- `preserveAspectRatio="none"` would smear type, and it
   * cannot touch a row that is not in the svg. It also means the first and last
   * numeral can be nudged inward instead of being clipped by the viewBox.
   *
   * ## What is shared and what is not
   *
   * The two funnels share a vertical range of 0 to 100 and a log x axis scaled
   * to the LONGER run, so the shorter one visibly stops early instead of being
   * stretched to fill the same width. That difference is the point: one run
   * bought a quarter of the precision for three times the money.
   *
   * The histogram has its own scale and shares nothing, because it is counting
   * a different thing.
   *
   * ## Two kinds of motion, and why they are not the same kind
   *
   * THE FUNNELS REPLAY. `pts` is ordered by generation, so drawing left to
   * right shows the estimate arriving in the order it actually arrived. Nothing
   * is invented; the frame at generation 40 is the number that was on screen
   * after forty generations.
   *
   * THE HISTOGRAM ONLY REVEALS. `SCORES` is a count per bucket with no arrival
   * order in it, so there is no sequence to replay. Filling it group by group
   * would mean inventing an order and showing it as though it were measured,
   * which is the one thing this file's header forbids. The bars therefore rise
   * together, which reads as a chart appearing rather than as data arriving --
   * that difference is the whole point of doing it this way, so do not "improve"
   * it into a sequential fill.
   */
  import { onMount } from 'svelte';
  import { SCORES, SCORES_GROUP, SCORES_RATE } from '../../data/sampling';
  import { CONVERGENCE } from '../../data/convergence';

  /**
   * The figure exposes one method and the prose owns the button, same split as
   * the surface above it. `play` takes no arguments because there is one thing
   * to play.
   */
  type Props = { onPlayChange?: (playing: boolean) => void };
  let { onPlayChange }: Props = $props();

  let rootEl: HTMLElement | null = $state(null);

  /**
   * Two clocks.
   *
   *   reveal  0 to 1, the histogram's bars rising together
   *   clock   0 to 1, position of the drawing front in LOG generations
   *
   * BOTH START AT ZERO, which is the opposite of the surface above and worth
   * the paragraph. The surface rests finished because it sits high enough that
   * a reader meets it before any trigger could fire, so an empty one would be a
   * broken-looking figure. These panels are far enough down that nobody reaches
   * them without scrolling, and the observer below always fires first.
   *
   * Resting finished cost more than it bought. It forced the trigger to fire
   * hundreds of pixels early to hide the blanking, and firing that early meant
   * the surface's own scroll tripped it, so the charts drew off-screen and were
   * sitting complete by the time anyone arrived. Starting empty removes the
   * blanking, which lets the trigger wait for the figure to actually be looked
   * at, which is the behaviour that was wanted in the first place.
   */
  let reveal = $state(0);
  let clock = $state(0);
  let playGen = $state(0);
  /** Frame handle for the draw below, so teardown can cancel it. */
  let drawRaf = 0;
  /** Once true, the figure has had its one automatic run and will not get
   *  another. The button can still replay it as often as it is pressed. */
  let seen = false;

  const lessMotion = () =>
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const SETTLE_MS = 420;
  const REVEAL_MS = 600;
  /** The funnels start before the bars have finished, so the two read as one
   *  movement rather than as a slideshow. */
  const DRAW_FROM = 400;
  const DRAW_MS = 2800;

  /**
   * `scroll` is false when the reader arrived under their own steam. Dragging
   * the page under someone who is already looking at the figure is the worst
   * thing an autoplay can do, and it is the reason the observer below passes
   * false.
   */
  export async function play(scroll = true) {
    const gen = ++playGen;
    seen = true; // whoever got here first, the observer has nothing left to do
    onPlayChange?.(true);

    if (lessMotion()) {
      if (scroll) rootEl?.scrollIntoView({ behavior: 'auto', block: 'nearest' });
      reveal = 1;
      clock = 1;
      onPlayChange?.(false);
      return;
    }

    reveal = 0;
    clock = 0;
    if (scroll) {
      rootEl?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      await new Promise<void>((r) => setTimeout(r, SETTLE_MS));
      if (gen !== playGen) return;
    }

    const began = performance.now();
    // THE HANDLE IS KEPT so the loop can be cancelled. Without it the only way
    // this stopped was its own generation check, which means a component
    // destroyed mid-draw left a loop running that wrote to dead state until it
    // happened to finish.
    await new Promise<void>((done) => {
      const step = (now: number) => {
        if (gen !== playGen) return; // a newer play owns the clocks now
        const ms = now - began;
        const ease = (x: number) => x * x * (3 - 2 * x);
        reveal = ease(Math.min(1, ms / REVEAL_MS));
        clock = Math.min(1, Math.max(0, (ms - DRAW_FROM) / DRAW_MS));
        if (reveal >= 1 && clock >= 1) { drawRaf = 0; done(); return; }
        drawRaf = requestAnimationFrame(step);
      };
      drawRaf = requestAnimationFrame(step);
    });
    if (gen !== playGen) return;
    onPlayChange?.(false);
  }

  /**
   * ---- IT DRAWS WHEN THE READER GETS TO IT --------------------------------
   *
   * The walk button is two figures and about five seconds up the page, so
   * chaining off it alone means the charts only ever move for someone who
   * pressed it and then sat still. Everyone who scrolls down finds them
   * already finished, which is the same as not animating at all.
   *
   * ONCE, AND ONLY ONCE. A figure that replays every time it re-enters the
   * viewport turns a scroll back up the page into a fresh animation, and the
   * reader who scrolled back to re-read a number instead has to wait for it to
   * be drawn again. The button is the way to see it a second time.
   *
   * THE TEST IS WHERE THE FIGURE IS IN THE VIEWPORT, not how much of it shows.
   * Cutting 35% off the bottom of the root means the top edge has to climb into
   * the upper two thirds of the screen before this counts as arrival. Any
   * sighting at all is far too loose: the walk button parks the surface at the
   * top of the viewport, which leaves these panels resting against the bottom
   * edge, and they would draw while the reader is still watching the surface
   * turn.
   *
   * A fraction OF THE FIGURE would have been the obvious thing to measure and
   * it is the wrong one. These panels stack on a narrow screen and get taller
   * than the viewport, and a figure that cannot fit can never show a large
   * enough fraction of itself, so the trigger would simply never fire. Where
   * the top edge sits is a question every screen can answer.
   */
  onMount(() => {
    if (!rootEl) return;
    const io = new IntersectionObserver(
      (entries) => {
        if (!entries.some((e) => e.isIntersecting)) return;
        io.disconnect();
        if (seen) return; // the button got here first
        play(false); // already on screen, so do not drag the page around
      },
      { rootMargin: '0px 0px -35% 0px', threshold: 0 },
    );
    io.observe(rootEl);
    return () => {
      io.disconnect();
      // Bumping the generation is what stops an in-flight `play` that is
      // parked on its scroll-settle timer: it wakes after teardown, finds a
      // generation that is no longer its own, and returns without starting a
      // frame loop against state nothing is rendering.
      playGen += 1;
      cancelAnimationFrame(drawRaf);
    };
  });

  // ---- histogram ------------------------------------------------------------
  const G = SCORES_GROUP;
  const totalGroups = SCORES.reduce((a, c) => a + c, 0);
  const hMax = Math.max(...SCORES) / totalGroups;

  /** Middle 95% of the observed scores, as shares. */
  const hBand = (() => {
    let acc = 0;
    let lo = 0;
    let hi = G;
    for (let k = 0; k <= G; k++) {
      acc += SCORES[k] / totalGroups;
      if (acc >= 0.025) { lo = k; break; }
    }
    acc = 0;
    for (let k = G; k >= 0; k--) {
      acc += SCORES[k] / totalGroups;
      if (acc >= 0.025) { hi = k; break; }
    }
    return { lo: lo / G, hi: hi / G };
  })();

  const HW = 300;
  const HH = 300;
  const HP = { l: 6, r: 6, t: 12, b: 6 };
  const hPlotW = HW - HP.l - HP.r;
  const hPlotH = HH - HP.t - HP.b;
  const hx = (s: number) => HP.l + s * hPlotW;
  const pct = (v: number) => `${Math.round(v * 100)}%`;
  const hh = (s: number) => (s / hMax) * hPlotH;

  // ---- funnels --------------------------------------------------------------
  const CW = 300;
  const CH = 140;
  const CP = { l: 4, r: 4, t: 8, b: 18 };
  const cPlotW = CW - CP.l - CP.r;
  const cPlotH = CH - CP.t - CP.b;

  const maxN = Math.max(...CONVERGENCE.map((r) => r.n));
  const lx = (n: number) => CP.l + (Math.log(n) / Math.log(maxN)) * cPlotW;
  const ly = (p: number) => CP.t + (1 - p) * cPlotH;

  const decades = [1, 10, 100, 1000, 6000].filter((d) => d <= maxN);

  const runPath = (pts: readonly (readonly number[])[]) =>
    pts.map((p, i) => `${i ? 'L' : 'M'}${lx(p[0]).toFixed(1)},${ly(p[1]).toFixed(1)}`).join(' ');

  /** Up the high edge, back along the low one, closed. */
  const envPath = (pts: readonly (readonly number[])[]) => {
    const up = pts.map((p, i) => `${i ? 'L' : 'M'}${lx(p[0]).toFixed(1)},${ly(p[3]).toFixed(1)}`);
    const down = [...pts].reverse().map((p) => `L${lx(p[0]).toFixed(1)},${ly(p[2]).toFixed(1)}`);
    return `${up.join(' ')} ${down.join(' ')} Z`;
  };

  /**
   * ---- THE DRAWING FRONT ---------------------------------------------------
   *
   * ONE CLOCK FOR BOTH RUNS, AND IT TICKS IN LOG GENERATIONS.
   *
   * The x axis is log, so a front moving at a constant number of generations
   * per second would cross the first decade in a blink and then spend the rest
   * of the run creeping across the flat tail where nothing happens. The early
   * swing is the entire reason these panels exist, so the front moves at a
   * constant number of DECADES per second instead, and every decade of the axis
   * gets the same slice of time as every other.
   *
   * Both runs read the same clock rather than each finishing on its own
   * schedule. That is what makes the 256-generation run visibly stop while the
   * 6,000 one keeps going, which is the comparison the shared axis was chosen
   * for in the first place. Giving each its own timeline would land them
   * together and quietly delete it.
   */
  const frontFor = (n: number, u: number) => Math.min(n, Math.exp(u * Math.log(maxN)));

  /**
   * The run's points up to the front, with one interpolated point sitting
   * exactly on it.
   *
   * The interpolation is not a flourish. Early points are one generation apart
   * in the data and a long way apart on a log axis, so a front that could only
   * land on stored points would advance in visible hops across the part of the
   * chart that matters most. Interpolating in log x keeps the leading edge
   * moving at the speed the clock says it is moving.
   *
   * Returns null below two points, because a path needs a line to be.
   */
  function upTo(
    pts: readonly (readonly number[])[],
    front: number,
  ): (readonly number[])[] | null {
    const out: (readonly number[])[] = [];
    for (const p of pts) {
      if (p[0] <= front) { out.push(p); continue; }
      const prev = out[out.length - 1];
      if (prev) {
        const a = Math.log(prev[0]);
        const w = (Math.log(front) - a) / (Math.log(p[0]) - a);
        out.push([
          front,
          prev[1] + (p[1] - prev[1]) * w,
          prev[2] + (p[2] - prev[2]) * w,
          prev[3] + (p[3] - prev[3]) * w,
        ]);
      }
      break;
    }
    return out.length >= 2 ? out : null;
  }

  /** One entry per run, recomputed as the clock moves. */
  const drawn = $derived(
    CONVERGENCE.map((r) => upTo(r.pts, frontFor(r.n, clock))),
  );
</script>

<figure class="panels" bind:this={rootEl}>
  <div class="left">
    <div class="lab mono">
      <span class="cell">{totalGroups} scores of {G}</span>
      <span class="n">5 &times; 5</span>
      <span class="val">{pct(SCORES_RATE)}</span>
    </div>
    <svg viewBox="0 0 {HW} {HH}" preserveAspectRatio="none" role="img"
      aria-label="{totalGroups} independent scores of {G} problems, counted by the value each returned">
      <rect
        class="band"
        x={hx(hBand.lo)}
        y={HP.t}
        width={Math.max(1, hx(hBand.hi) - hx(hBand.lo))}
        height={hPlotH}
      />
      {#each SCORES as c, k (k)}
        {#if c > 0}
          <rect
            class="bar"
            x={hx(k / G) - (hPlotW / (G + 1) - 3) / 2}
            y={HP.t + hPlotH - hh(c / totalGroups) * reveal}
            width={hPlotW / (G + 1) - 3}
            height={hh(c / totalGroups) * reveal}
          />
        {/if}
      {/each}
      <!-- Over the bars, not under. It is the value every one of them was
           trying to find, and it was invisible behind the tall ones. -->
      <line class="settle" x1={hx(SCORES_RATE)} x2={hx(SCORES_RATE)}
        y1={HP.t - 4} y2={HP.t + hPlotH} />
      <line class="axis" x1={HP.l} x2={HP.l + hPlotW} y1={HP.t + hPlotH} y2={HP.t + hPlotH} />
    </svg>
    <div class="hax mono" aria-hidden="true">
      {#each [0, 3, 6, 9, 12] as k (k)}
        <span style:left="{(hx(k / G) / HW) * 100}%">{Math.round((k / G) * 100)}</span>
      {/each}
    </div>
    <p class="foot mono">
      score reported &middot; {pct(hBand.lo)} to {pct(hBand.hi)} holds 19 in 20
    </p>
  </div>

  <div class="right">
    {#each CONVERGENCE as r, ri (r.key)}
      <div class="panel">
      <div class="lab mono">
        <span class="cell">{r.label}</span>
        <span class="n">{r.note}</span>
        <span class="val">{pct(r.p)}</span>
      </div>
      <svg viewBox="0 0 {CW} {CH}" preserveAspectRatio="none" role="img"
        aria-label="Running rate for {r.label} over {r.n} generations with its 95% interval">
        <line class="settle" x1={CP.l} x2={CP.l + cPlotW} y1={ly(r.p)} y2={ly(r.p)} />
        {#if drawn[ri]}
          <path class="env" d={envPath(drawn[ri])} />
          <path class="run" d={runPath(drawn[ri])} />
        {/if}
        {#each decades as d (d)}
          {#if d <= r.n}
            <line class="tick" x1={lx(d)} x2={lx(d)} y1={CP.t + cPlotH} y2={CP.t + cPlotH + 5} />
          {/if}
        {/each}
        <!-- The dot rides the front while it draws and parks on the settled
             value at the end. It is the same element either way, so there is
             nothing to appear or disappear at the finish. -->
        {#if drawn[ri]}
          {@const last = drawn[ri][drawn[ri].length - 1]}
          <circle cx={lx(last[0])} cy={ly(last[1])} r="2.4" />
        {/if}
      </svg>
      <div class="hax mono" aria-hidden="true">
        {#each decades as d (d)}
          {#if d <= r.n}
            <span style:left="{(lx(d) / CW) * 100}%">{d >= 1000 ? `${d / 1000}k` : d}</span>
          {/if}
        {/each}
      </div>
      <p class="foot mono">
        {r.n.toLocaleString()} generations &middot; {pct(r.lo)} to {pct(r.hi)}
      </p>
      </div>
    {/each}
  </div>

  <figcaption>
    Left, what a twelve problem benchmark of one cell reports, five hundred times
    over. Right, the running rate for two runs with the 95% interval around it,
    generations on a log scale. The dashes are the rate each run settles on.
  </figcaption>
</figure>

<style>
  /* ONE RHYTHM, THREE PANELS.
     Every panel is label / plot / numerals / note. These four numbers are the
     only vertical measurements in the file, and because every row but the plot
     is fixed, the plots absorb the difference and land on the same edges. */
  .panels {
    --lab-h: 14px;
    --hax-h: 13px;
    --foot-h: 13px;
    --row-gap: 4px;

    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: var(--space-lg);
    align-items: stretch;
  }
  @media (max-width: 720px) {
    .panels { grid-template-columns: minmax(0, 1fr); }
  }

  .left,
  .right .panel {
    display: flex;
    flex-direction: column;
    gap: var(--row-gap);
    min-width: 0;
    min-height: 0;
  }

  /* Two panels split the right column, with the same gap between them as the
     grid uses between columns, so the seam reads as one spacing system. */
  .right {
    display: grid;
    grid-template-rows: 1fr 1fr;
    gap: var(--space-lg);
    min-width: 0;
    min-height: 0;
  }

  svg {
    width: 100%;
    display: block;
    background: color-mix(in srgb, var(--panel) 84%, transparent);
    border-radius: var(--radius-sm);
  }

  /* SOMETHING HAS TO SET THE HEIGHT. Every panel flexing meant no panel had an
     intrinsic height, the grid row collapsed to the fixed rows, and both funnel
     svgs measured exactly zero pixels tall.
     The histogram is that something: a fixed square at whatever width the
     column gets. Everything else divides what is left. */
  .left svg { flex: 0 0 auto; aspect-ratio: 1; height: auto; }

  /* And these are the ones that divide it. `height: 0` stops the viewBox from
     setting a floor the flexbox would then have to honour. */
  .right .panel svg { flex: 1 1 0; height: 0; min-height: 0; }

  /* ---- STACKED, THERE IS NO SHARED HEIGHT LEFT TO DIVIDE -----------------
     Below the breakpoint the two columns become one, so `.right` is a grid row
     sized by its own content -- and a `1fr` track holding a `flex: 1 1 0;
     height: 0` child resolves to nothing at all. Both funnel svgs measured
     exactly 374x0 on a phone: the label, the axis numerals and the note all
     rendered, and the curve they describe was clipped out of existence. The
     panel that divides a column has to size itself once it is no longer in one.

     The histogram is squared off the column width, which on a phone is a full
     screen of a single chart before the reader has reached the two panels that
     answer it. Wider than tall says the same thing in a third of the scroll. */
  @media (max-width: 720px) {
    .left svg { aspect-ratio: 3 / 2; }
    /* THE TWO FUNNELS GO SIDE BY SIDE AND SMALL. They are the supporting half
       of the figure -- the histogram is what the paragraph is about, and these
       say "and it settles" -- so stacking them full width spent two more
       screens of scroll on the part that matters least. Paired, they also read
       as the comparison they are, reasoning on against reasoning off, which
       one above the other never quite did. */
    .right {
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      grid-template-rows: auto;
      gap: var(--space-md);
    }
    .right .panel svg {
      flex: 0 0 auto;
      height: auto;
      min-height: 0;
      aspect-ratio: 3 / 2;
    }
  }

  .lab {
    display: flex;
    align-items: baseline;
    gap: 6px;
    height: var(--lab-h);
    line-height: var(--lab-h);
    font-size: 0.64rem;
    font-variant-numeric: tabular-nums;
  }
  .cell { color: var(--ink); }
  .n { color: var(--ink-faint); }
  .val { margin-left: auto; color: var(--ink); }

  /* Numerals live here rather than in the svg, so stretching the plot cannot
     smear type. The end labels are pulled inward so neither is clipped. */
  .hax {
    position: relative;
    height: var(--hax-h);
    line-height: var(--hax-h);
    font-size: 0.62rem;
    font-variant-numeric: tabular-nums;
    color: var(--ink-faint);
  }
  .hax span { position: absolute; transform: translateX(-50%); }
  .hax span:first-child { transform: none; }
  .hax span:last-child { transform: translateX(-100%); }

  .foot {
    margin: 0;
    height: var(--foot-h);
    line-height: var(--foot-h);
    font-size: 0.62rem;
    font-variant-numeric: tabular-nums;
    color: var(--ink-faint);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .bar { fill: var(--accent); }
  .band { fill: var(--line-strong); opacity: 0.4; }

  /* No stroke on the envelope. An outlined band reads as two more series, and
     there are only two things here: an estimate and its uncertainty. */
  .env { fill: var(--accent); opacity: 0.16; }
  .run {
    fill: none;
    stroke: var(--accent);
    stroke-width: 1.6;
    stroke-linejoin: round;
    stroke-linecap: round;
    /* The plot is scaled non-uniformly, so a plain stroke-width would thin out
       vertically. This keeps the line one weight whatever the panel height. */
    vector-effect: non-scaling-stroke;
  }
  circle { fill: var(--accent); }

  .settle {
    stroke: var(--ink);
    stroke-width: 1;
    stroke-dasharray: 3 3;
    opacity: 0.45;
    vector-effect: non-scaling-stroke;
  }
  .axis { stroke: var(--line-strong); stroke-width: 1; vector-effect: non-scaling-stroke; }
  .tick { stroke: var(--ink-faint); stroke-width: 1; vector-effect: non-scaling-stroke; }

  figcaption {
    grid-column: 1 / -1;
    margin-top: var(--space-xs);
    font-family: var(--font-sans);
    font-size: var(--text-xs);
    line-height: var(--leading-snug);
    color: var(--ink-dim);
  }
</style>
