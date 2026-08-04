<script lang="ts">
  /**
   * Four reasoning runs drawn as tree rings. One ring is one iteration of the
   * loop, and the colour of a band is which OODA phase the model was in.
   *
   * ## Why rings
   *
   * Boyd's argument is not that a fast loop repeats. It is that the output of
   * one cycle is the input to the next, so cycles accumulate rather than reset.
   * A ring records that: the spiral never comes back to where it started, it
   * steps outward once per iteration and keeps everything it already drew.
   * A dial would show the current cycle and throw away the run.
   *
   * ## What one lap is
   *
   * A lap closes on each ACT segment: everything since the previous act, then
   * the act. ACT is the phase that produces output, so counting acts counts
   * completed cycles. Segments that belong to NO phase do not close a lap.
   *
   * ## What is shared and what is not
   *
   * SHARED: the clock. All four advance at the same characters per second, so
   * the run that took 57,013 characters occupies over three times the wall time
   * of the one that took 16,367. Three rings finish and stop; the fourth keeps
   * turning. That is the whole figure.
   *
   * NOT SHARED: the radial pitch. Every trace fills the same disc, so pitch is
   * the disc divided by that trace's lap count. The discs are comparable by ring
   * DENSITY, not by size, and the lap count is printed under each so the reader
   * is not left to infer it from a smear. A common pitch would need a disc many
   * times wider than the ones that finished, which is honest and unreadable.
   *
   * ## The fourth phase, and what changed
   *
   * An earlier version of this figure showed DECIDE as an empty swatch reading
   * "0 of 524", because the only category mapped to it required the model to
   * change a value it had already written down -- a coding move that long
   * multiplication does not produce. The categories were rebuilt from these
   * traces instead of inherited, and DECIDE now holds committing to a
   * decomposition, abandoning one, revising a value, letting it stand, and
   * failing to settle a conflict. It is 14% of the reasoning.
   *
   * What is drawn hollow now is the OTHER absence, and it is real: 276 segments
   * of one trace are the same sentence repeated, which is not observing,
   * orienting, deciding or acting. Those are unphased, they do not close a lap,
   * and they take the scheme's fallback colour. An earlier line here defaulted
   * anything unmapped to ACT, which would have drawn the busiest ring in the
   * figure for the run that achieved least.
   *
   * Rubric, agreement and known defects:
   * .agents/reference/label-rubric-qwen-multiplication.md
   */
  import { untrack } from 'svelte';
  import { OPENER } from '../../data/opener';
  import { CATEGORY_PHASE, OODA_SCHEME, OODA_PHASES, type OodaPhase } from '../../design/ooda';
  import { metaFor } from '../../design/scheme';

  /** A phase, or the marker for segments that belong to none. */
  const UNPHASED_KEY = 'UNPHASED' as const;
  type Phase = OodaPhase | typeof UNPHASED_KEY;

  const TAU = Math.PI * 2;

  /** A stretch of one phase, as characters and as the angle it occupies. */
  type Band = {
    phase: Phase;
    c0: number;
    c1: number;
    th0: number;
    th1: number;
  };

  type Ring = {
    key: string;
    cell: string;
    verdict: string;
    /** digits x digits, spelled out */
    size: string;
    answer: string | null;
    correct: boolean;
    chars: number;
    laps: number;
    /** character offset at which each lap closes; drives the live counter */
    lapEnds: number[];
    bands: Band[];
  };

  function build(t: (typeof OPENER)[number]): Ring {
    // Split into laps. Each ACT closes one.
    //
    // UNPHASED SEGMENTS DO NOT CLOSE A LAP, and they are drawn in the scheme's
    // fallback colour rather than a phase colour. `LOOP` is the reason: 276
    // segments of one trace are the same sentence repeated, and an earlier
    // version of this line defaulted anything unmapped to ACT. That would have
    // counted 276 laps of "acting" for a run that had stopped doing anything,
    // and drawn the densest, busiest ring in the figure for the trace that
    // achieved least. The absence of a phase is the finding, so it is rendered
    // as an absence.
    const laps: { phase: Phase; chars: number }[][] = [];
    let cur: { phase: Phase; chars: number }[] = [];
    for (const s of t.segments) {
      const phase: Phase = CATEGORY_PHASE[s.category] ?? UNPHASED_KEY;
      cur.push({ phase, chars: s.end - s.start });
      if (phase === 'ACT') {
        laps.push(cur);
        cur = [];
      }
    }
    // A trace can stop mid-cycle -- that is what running out of context looks
    // like -- so a trailing remainder is a real partial lap, not a rounding
    // error to drop.
    if (cur.length) laps.push(cur);

    // ANGLE IS PROPORTIONAL TO CHARACTERS, over the whole trace.
    //
    // The first version gave every lap exactly one full turn and divided that
    // turn among the lap's own segments. That silently inflated whichever phase
    // closes a lap: a run of consecutive ACT segments becomes many laps of one
    // segment each, and each of those takes a WHOLE revolution, while a long
    // stretch of observing shares a single turn with the act that ends it.
    // Measured on trace A the ring read about three-quarters blue where ACT is
    // 39% of the characters -- a figure disagreeing with its own data.
    //
    // Advancing by characters instead makes coloured area equal character share
    // exactly. Turn COUNT still equals lap count, so ring density carries the
    // same meaning; lap boundaries simply no longer land at twelve o'clock.
    const totalChars = laps.reduce(
      (a, lap) => a + lap.reduce((b, s) => b + s.chars, 0), 0) || 1;
    const span = TAU * laps.length;
    const bands: Band[] = [];
    const lapEnds: number[] = [];
    let c = 0;
    laps.forEach((lap) => {
      for (const seg of lap) {
        bands.push({
          phase: seg.phase,
          c0: c,
          c1: c + seg.chars,
          th0: span * (c / totalChars),
          th1: span * ((c + seg.chars) / totalChars),
        });
        c += seg.chars;
      }
      lapEnds.push(c);
    });

    const [x, y] = t.cell.split('x');
    return {
      key: t.key,
      cell: t.cell,
      verdict: t.verdict,
      size: `${x} × ${y} digits`,
      answer: t.answer,
      correct: t.answer !== null && t.answer === t.truth,
      chars: c,
      laps: laps.length,
      lapEnds,
      bands,
    };
  }

  const RINGS: Ring[] = OPENER.map(build);
  const TOTAL = Math.max(...RINGS.map((r) => r.chars));

  const PHASES = OODA_PHASES.map((p) => ({ phase: p, ...metaFor(OODA_SCHEME, p) }));
  const COLOR = {
    ...Object.fromEntries(PHASES.map((p) => [p.phase, p.color])),
    [UNPHASED_KEY]: OODA_SCHEME.fallback.color,
  } as Record<Phase, string>;

  // 17s of drawing, then a hold so the finished figure can be read before it
  // starts over. Long for a hero, but the point of the figure is the stretch
  // where two rings have stopped and one has not, and that stretch is 69% of
  // the run by construction.
  const RUN_MS = 17_000;
  const HOLD_MS = 3_000;
  const CYCLE = RUN_MS + HOLD_MS;

  let host: HTMLElement | null = $state(null);
  let ringsEl: HTMLCanvasElement | null = $state(null);
  let headEl: HTMLCanvasElement | null = $state(null);
  let w = $state(880);
  let elapsed = $state(0);
  let playing = $state(true);
  let runId = $state(0);
  let reduced = $state(false);

  // ONE ROW, sized like the hero on the reliably-incorrect post: three objects
  // about 230px across inside an 880px figure, in a section more than twice as
  // tall as the objects themselves. The air is the point -- a hero earns
  // attention by being simple and unhurried, not by being big.
  //
  // Two earlier attempts got this wrong in opposite directions: a row squeezed
  // to the full page width, then a 2x2 grid that made the discs large and the
  // block dense. Both filled space the reference deliberately leaves empty.
  //
  // Geometry still follows the NUMBER OF RINGS rather than a constant -- these
  // were written as /6 when there were three traces, so a fourth drew off the
  // right-hand edge and the figure silently showed three.
  const COLS = $derived(RINGS.length);
  const ROWS = 1;
  const GUTTER = 14;
  const R_OUT = $derived(Math.max(52, Math.min(w / (2 * COLS) - GUTTER, 118)));
  const R_IN = $derived(Math.max(7, R_OUT * 0.11));
  const CELL_H = $derived(Math.round(R_OUT * 2 + GUTTER * 2));
  const H = $derived(CELL_H * ROWS);

  const progress = $derived(Math.min(1, elapsed / RUN_MS));
  /** Characters of thinking elapsed, on the one clock all three share. */
  const cursor = $derived(progress * TOTAL);

  function centreX(i: number): number {
    return (w * (2 * (i % COLS) + 1)) / (2 * COLS);
  }
  function centreY(i: number): number {
    return Math.floor(i / COLS) * CELL_H + R_OUT + GUTTER;
  }

  /** Radius at an angle, for a ring whose whole spiral spans `laps` turns. */
  function radius(th: number, laps: number): number {
    return R_IN + ((R_OUT - R_IN) * th) / (TAU * laps);
  }

  /**
   * Ribbon width. A gap between rings only when there is room for one: below
   * ~1.6px of pitch a proportional gap is thinner than a pixel, so it renders
   * as a wash that reads paler than the colour it is drawn in. Butted rings
   * keep the colour true and let the dense trace read as the solid field it is.
   */
  function ribbon(laps: number): number {
    const pitch = (R_OUT - R_IN) / laps;
    return pitch <= 1.6 ? Math.max(pitch, 0.85) : pitch * 0.78;
  }

  function point(cx: number, cy: number, th: number, r: number): [number, number] {
    // -PI/2 so every spiral starts at twelve o'clock.
    return [cx + Math.cos(th - Math.PI / 2) * r, cy + Math.sin(th - Math.PI / 2) * r];
  }

  function dpr(): number {
    return Math.min(window.devicePixelRatio || 1, 2);
  }

  function fit(c: HTMLCanvasElement): CanvasRenderingContext2D | null {
    const ctx = c.getContext('2d');
    if (!ctx) return null;
    const d = dpr();
    if (c.width !== Math.round(w * d) || c.height !== Math.round(H * d)) {
      c.width = Math.round(w * d);
      c.height = Math.round(H * d);
    }
    ctx.setTransform(d, 0, 0, d, 0, 0);
    return ctx;
  }

  /** Draw one band, or the part of it below `toChar`. */
  function arc(
    ctx: CanvasRenderingContext2D,
    cx: number,
    cy: number,
    b: Band,
    ring: Ring,
    from: number,
    to: number,
  ) {
    const span = b.c1 - b.c0 || 1;
    const a0 = b.th0 + ((b.th1 - b.th0) * (Math.max(from, b.c0) - b.c0)) / span;
    const a1 = b.th0 + ((b.th1 - b.th0) * (Math.min(to, b.c1) - b.c0)) / span;
    if (a1 <= a0) return;
    // Back up a step when continuing a band already part-drawn, so successive
    // frames butt cleanly. Never past th0: overlapping into the PREVIOUS band
    // would repaint its last few pixels in this band's colour and walk every
    // phase boundary outward.
    const step = 0.03;
    const start = Math.max(b.th0, from > b.c0 ? a0 - step : a0);

    ctx.strokeStyle = COLOR[b.phase];
    ctx.lineWidth = ribbon(ring.laps);
    ctx.lineCap = 'butt';
    ctx.beginPath();
    let th = start;
    for (;;) {
      const [x, y] = point(cx, cy, th, radius(th, ring.laps));
      if (th === start) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
      if (th >= a1) break;
      th = Math.min(th + step, a1);
    }
    ctx.stroke();
  }

  /** Everything that does not change while the spiral grows. */
  function chrome(ctx: CanvasRenderingContext2D) {
    ctx.clearRect(0, 0, w, H);
    RINGS.forEach((ring, i) => {
      const cx = centreX(i);
      ctx.strokeStyle = 'rgba(26,26,26,0.13)';
      ctx.lineWidth = 1;
      ctx.setLineDash([2, 4]);
      ctx.beginPath();
      ctx.arc(cx, centreY(i), R_OUT, 0, TAU);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.fillStyle = 'rgba(26,26,26,0.09)';
      ctx.beginPath();
      ctx.arc(cx, centreY(i), R_IN * 0.55, 0, TAU);
      ctx.fill();
    });
  }

  let drawnTo = 0;

  function paint(to: number, restart: boolean) {
    const c = ringsEl;
    if (!c) return;
    const ctx = fit(c);
    if (!ctx) return;
    if (restart) {
      chrome(ctx);
      drawnTo = 0;
    }
    if (to <= drawnTo) return;
    RINGS.forEach((ring, i) => {
      const cx = centreX(i);
      const end = Math.min(to, ring.chars);
      if (end <= drawnTo) return;
      for (const b of ring.bands) {
        if (b.c1 <= drawnTo || b.c0 >= end) continue;
        arc(ctx, cx, centreY(i), b, ring, drawnTo, end);
      }
    });
    drawnTo = to;
  }

  /** The moving head, and the mark left where a run stopped. Cleared each frame. */
  function heads(to: number) {
    const c = headEl;
    if (!c) return;
    const ctx = fit(c);
    if (!ctx) return;
    ctx.clearRect(0, 0, w, H);
    RINGS.forEach((ring, i) => {
      const cx = centreX(i);
      const done = to >= ring.chars;
      const at = Math.min(to, ring.chars);
      const b = ring.bands.find((q) => at >= q.c0 && at <= q.c1) ?? ring.bands[ring.bands.length - 1];
      const span = b.c1 - b.c0 || 1;
      const th = b.th0 + ((b.th1 - b.th0) * (at - b.c0)) / span;
      const r = radius(th, ring.laps);
      const [x, y] = point(cx, centreY(i), th, r);

      if (done) {
        // A run that stopped gets a radial tick, so the outer end reads as an
        // ending rather than as the drawing having been interrupted.
        const [x0, y0] = point(cx, centreY(i), th, r - 5);
        const [x1, y1] = point(cx, centreY(i), th, r + 5);
        ctx.strokeStyle = ring.answer === null ? '#9a9a9a' : '#1a1a1a';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(x0, y0);
        ctx.lineTo(x1, y1);
        ctx.stroke();
        return;
      }
      ctx.fillStyle = COLOR[b.phase];
      ctx.globalAlpha = 0.22;
      ctx.beginPath();
      ctx.arc(x, y, 7.5, 0, TAU);
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.beginPath();
      ctx.arc(x, y, 2.6, 0, TAU);
      ctx.fill();
    });
  }

  /**
   * What each run is doing RIGHT NOW: the phase of the band under the cursor.
   *
   * Binary search, not a scan -- this runs every frame over up to 403 bands. The
   * bands tile the trace with no gap, so the last band starting at or before the
   * cursor is the one containing it.
   */
  const counts = $derived(
    RINGS.map((r) => {
      const done = cursor >= r.chars;
      const at = Math.min(cursor, r.chars - 1);
      let phase: Phase | null = null;
      if (!done && r.bands.length && at >= 0) {
        let lo = 0, hi = r.bands.length - 1, best = 0;
        while (lo <= hi) {
          const mid = (lo + hi) >> 1;
          if (r.bands[mid].c0 <= at) { best = mid; lo = mid + 1; } else hi = mid - 1;
        }
        phase = r.bands[best].phase;
      }
      return { done, phase };
    }),
  );

  /**
   * ONE WORD, always. The card carries a single word under a hero ring, so every
   * value it can take has to be one -- and the scheme's own labels do not all
   * qualify: the four phases are single words but the fallback reads "Outside
   * the loop", which is the legend's wording and belongs there, not here.
   *
   * The unphased state gets "Repeating", which is what the model is literally
   * doing -- emitting the same sentence again -- and sits with that run's
   * outcome word, "Locked".
   */
  const UNPHASED_WORD = 'Repeating';
  const phaseWord = (p: Phase | null) =>
    p === null ? '' : p === UNPHASED_KEY ? UNPHASED_WORD : metaFor(OODA_SCHEME, p).label;

  // A word with a space in it is a bug, not a style choice, so it fails loudly
  // rather than quietly rendering two.
  $effect(() => {
    const words = [...PHASES.map((p) => p.label), UNPHASED_WORD,
                   ...RINGS.map((r) => r.verdict)];
    const bad = words.filter((word) => /\s/.test(word));
    if (bad.length) {
      console.error(`[IterationRings] card labels must be one word: ${bad.join(', ')}`);
    }
  });

  // --- clock -------------------------------------------------------------
  // One writer. `elapsed` is set by the frame loop, or by a seek, never both:
  // a seek bumps runId, which tears down the running loop before the new one
  // reads the new position. Two writers on this value is the bug that has bit
  // this figure's sibling three times.
  $effect(() => {
    if (!playing || reduced) return;
    runId;
    let t = untrack(() => elapsed);
    let prev = 0;
    let raf = requestAnimationFrame(function step(now: number) {
      if (prev) t = t + (now - prev);
      prev = now;
      if (t >= CYCLE) t = 0;
      elapsed = t;
      raf = requestAnimationFrame(step);
    });
    return () => cancelAnimationFrame(raf);
  });

  $effect(() => {
    const m = window.matchMedia('(prefers-reduced-motion: reduce)');
    const sync = () => {
      reduced = m.matches;
      if (m.matches) {
        playing = false;
        elapsed = RUN_MS;
      }
    };
    sync();
    m.addEventListener('change', sync);
    return () => m.removeEventListener('change', sync);
  });

  $effect(() => {
    if (!host) return;
    const ro = new ResizeObserver(([e]) => {
      w = Math.max(300, Math.round(e.contentRect.width));
    });
    ro.observe(host);
    return () => ro.disconnect();
  });

  // --- render ------------------------------------------------------------
  let lastCursor = -1;
  let lastW = -1;
  $effect(() => {
    const to = cursor;
    const width = w;
    // Geometry depends on width, and the accumulated canvas cannot be resized
    // without losing it, so a width change is a full redraw. So is a seek
    // backwards, and so is the loop starting over.
    const restart = width !== lastW || to < lastCursor;
    lastW = width;
    lastCursor = to;
    paint(to, restart);
    heads(to);
  });

  function seek(e: MouseEvent & { currentTarget: HTMLDivElement }) {
    const box = e.currentTarget.getBoundingClientRect();
    const f = Math.min(1, Math.max(0, (e.clientX - box.left) / box.width));
    runId++;
    elapsed = f * RUN_MS;
  }

  function nudge(d: number) {
    runId++;
    elapsed = Math.min(RUN_MS, Math.max(0, elapsed + d));
  }
</script>

<figure class="rings" bind:this={host} style:--ring-cols={COLS}>
  <div class="stage" style:height="{H}px">
    <canvas bind:this={ringsEl} style:width="{w}px" style:height="{H}px"></canvas>
    <canvas class="over" bind:this={headEl} style:width="{w}px" style:height="{H}px"></canvas>
  </div>

  <ul class="cards">
    {#each RINGS as ring, i (ring.key)}
      <!-- ONE WORD, and it changes meaning when the run ends. While the ring is
           drawing it names the phase the model is in; once the trace is spent it
           names how the run came out. Two labels side by side said the same
           thing twice, and a placeholder like "stopped" spent the most legible
           line in the figure on nothing. -->
      <li class="card" class:settled={counts[i].done}>
        <span
          class="word"
          style:color={counts[i].done
            ? 'var(--ink)'
            : counts[i].phase
              ? COLOR[counts[i].phase]
              : 'var(--ink-faint)'}
        >{counts[i].done ? ring.verdict : phaseWord(counts[i].phase)}</span>
      </li>
    {/each}
  </ul>



</figure>

<style>
  .rings {
    /* The hero's whitespace, matched to the reference: content sits in roughly
       a third of the block and the rest is air. Written as padding on the figure
       rather than margin on the section so it cannot be collapsed away by a
       neighbour.

       The TOP is much smaller than the bottom, and deliberately: this began as a
       bare hero with nothing above it and took the reference's ~180px, but the
       figure now sits under its own section title, which already separates it
       from what came before. Keeping 180px there left the title floating away
       from the figure it names. */
    /* Measured off the reliably-incorrect hero rather than guessed: its objects
       are 261px tall inside a 587px section, with about 180px of air above them
       and 150px below. The first attempt at this used the space scale (88/72)
       and came out visibly tighter than the reference. Clamped so a phone does
       not inherit a desktop's whitespace. */
    margin: 0;
    padding: clamp(24px, 5vw, 64px) 0 clamp(52px, 11vw, 150px);
    display: flex;
    flex-direction: column;
    gap: calc(var(--space-xl) * 1.4);
    width: 100%;
  }
  .stage {
    position: relative;
    width: 100%;
  }
  canvas {
    display: block;
    position: absolute;
    inset: 0;
  }
  .over {
    pointer-events: none;
  }

  /* The list reset is load-bearing, not cosmetic. This is a <ul>, and a
     browser's default `padding-inline-start: 40px` shrinks the grid to 840px
     inside an 880px canvas -- so the four columns become 210px against the
     canvas's 220px and every label drifts off its own ring, by 35px at the left
     and 5px at the right. The labels stay centred in their columns throughout,
     which is exactly why it reads as a drawing bug rather than a CSS one. */
  .cards {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(var(--ring-cols, 4), 1fr);
  }
  .card {
    display: flex;
    align-items: baseline;
    justify-content: center;
    gap: 8px;
    padding: 0 var(--space-sm);
    /* Reserved, so a run reaching its end cannot reflow the row. */
    min-height: 1.4em;
  }
  .word {
    font-family: var(--font-sans);
    font-size: 1rem;
    font-weight: 600;
    letter-spacing: 0.01em;
    transition: color 140ms linear;
  }




  @media (max-width: 620px) {
    .word { font-size: 0.82rem; }
  }
</style>
