<script lang="ts">
  /**
   * The opener: a model's thinking on the left, the arithmetic it states on the
   * right, landing as it is said and already checked.
   *
   * The point is the relationship between the two panes. Reasoning traces read
   * as fluent whether or not they are correct, so a reader watching only the
   * left pane cannot tell a good run from a bad one — and neither, it turns
   * out, can the model. The right pane grades every closed claim against real
   * arithmetic as it appears, which is the check the model is not doing.
   *
   * Across the three runs there is exactly one false claim, in the run that got
   * the answer wrong, and it is an ADDITION: every multiplication in every trace
   * is correct. That is the whole opener. The totals are computed below rather
   * than written here, because this comment said 152 for a while after the real
   * number became 160.
   *
   * Verdicts are computed in probe/build_opener.py, not here, and the numbers
   * run past Number.MAX_SAFE_INTEGER so they travel as decimal strings.
   */
  import { onMount, untrack } from 'svelte';
  import katex from 'katex';
  import 'katex/dist/katex.min.css';
  import { OPENER, type Claim } from '../../data/opener';
  import { carryCategoryMeta } from '../../design/carrychain-categories';

  let which = $state(0);
  const trace = $derived(OPENER[which]);

  /**
   * THE CLAIMS ARE THE CLOCK, not the characters.
   *
   * At a constant character rate the right pane is at the mercy of how verbose
   * the model happened to be between two equations. Measured on this data that
   * means claims arriving a median 0.11s apart but a p90 of 2.2s: thirteen
   * equations dumped inside one second, then nothing for thirteen seconds while
   * the left pane races on. It is not a rhythm, it is a stutter — and the burst
   * is also what broke the scrolling, since rendering thirteen KaTeX blocks
   * stalls the frame long enough for the stream to jump past any "is the reader
   * still at the bottom" threshold.
   *
   * So time is divided evenly across the claims instead. Each one gets a beat;
   * the cursor sweeps whatever prose lies between them, fast across a dry
   * stretch and slow through dense work, easing out so the text decelerates
   * into the landing and the equation arrives ON the beat. Every run then takes
   * the same time and has the same pulse, whatever its length.
   */
  const RUN_MS = 20_000;

  let elapsed = $state(0);
  let playing = $state(false);

  /**
   * When each offset is due.
   *
   * Claims are evenly spaced -- that is the cadence the figure runs on -- but
   * the stretch AFTER the last claim is not a claim interval and must not be
   * squeezed into one beat. In the run that got it wrong that stretch is 30% of
   * the text, and a single beat pushed it to 6,200 characters a second against
   * 411 in the body: a blur over the passage where the model checks its work,
   * finds the check agrees, and says so. That passage is the point of the run.
   *
   * So the tail takes its share of the text. That makes its reading rate equal
   * the body's by construction, while claims stay evenly spaced within the
   * body. Clamped, so a run that ends on its last claim still gets a beat to
   * land and one that trails off cannot eat the whole clock.
   */
  const schedule = $derived.by(() => {
    const ends = trace.claims.map((c) => c.end);
    const total = trace.thinking.length;
    const knots = [0, ...ends, total];
    const tailChars = total - (ends.length ? ends[ends.length - 1] : 0);
    const share = Math.max(0.03, Math.min(0.35, tailChars / Math.max(1, total)));
    const tailMs = RUN_MS * share;
    const beat = (RUN_MS - tailMs) / Math.max(1, knots.length - 2);
    const at = [0];
    for (let i = 1; i < knots.length; i++) {
      at.push(at[i - 1] + (i === knots.length - 1 ? tailMs : beat));
    }
    return { knots, at };
  });

  function cursorAt(ms: number): number {
    const { knots, at } = schedule;
    let i = 0;
    while (i < at.length - 2 && ms >= at[i + 1]) i++;
    const span = at[i + 1] - at[i] || 1;
    const u = Math.max(0, Math.min(1, (ms - at[i]) / span));
    const e = 1 - Math.pow(1 - u, 3);   // decelerate into each landing
    return Math.floor(knots[i] + (knots[i + 1] - knots[i]) * e);
  }

  const cursor = $derived(cursorAt(elapsed));
  const done = $derived(elapsed >= RUN_MS);

  /**
   * The stream is rendered as one node per SEGMENT, not one per character.
   * Revealed segments are static, so only the segment the cursor is inside
   * re-renders on a frame — 16,000 characters otherwise means rebuilding the
   * whole subtree sixty times a second.
   */
  /** Sorted defensively. The generator sorts too, but this loop is only
   *  correct on ascending input and the failure is silent: it renders a prefix
   *  of the trace, in the wrong order, and the pane still looks full. */
  const ordered = $derived([...trace.segments].sort((a, b) => a.start - b.start));

  const shown = $derived.by(() => {
    const out: Array<{ start: number; text: string; colour: string; label: string }> = [];
    for (const s of ordered) {
      if (s.start >= cursor) break;
      out.push({
        start: s.start,
        text: trace.thinking.slice(s.start, Math.min(s.end, cursor)),
        colour: colourFor(s.category),
        label: s.label,
      });
    }
    return out;
  });

  /** The scheme is keyed by the nine category literals; segments arrive as
   *  plain strings, so a category the scheme does not define falls back rather
   *  than throwing. A missing one is a data bug in build_flame.py, not
   *  something this component should crash on. */
  const PALETTE: Record<string, { color: string }> = carryCategoryMeta;

  /**
   * Darken a category colour only as far as legibility needs, then stop.
   *
   * A flat mix toward the ink crushes every hue into the same near-black: at
   * 34% the error red #d4503c came out #592c26, a brown, and all nine
   * categories landed between 6:1 and 13:1 against the panel — uniformly darker
   * than they need to be and no longer told apart. Blending until the contrast
   * ratio first clears 4.5:1 keeps the already-dark ones exactly as designed
   * and only pulls down the pale ones, so red still reads as red.
   */
  const PANEL = '#f7f5f0';
  const INK = '#1a1a1a';
  const chan = (h: string) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  function luminance(hex: string) {
    return chan(hex)
      .map((v) => v / 255)
      .map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4))
      .reduce((a, v, i) => a + v * [0.2126, 0.7152, 0.0722][i], 0);
  }
  const contrast = (a: string, b: string) => {
    const [x, y] = [luminance(a), luminance(b)].sort((m, n) => n - m);
    return (x + 0.05) / (y + 0.05);
  };
  function blend(a: string, b: string, t: number) {
    const [A, B] = [chan(a), chan(b)];
    return '#' + A.map((v, i) => Math.round(v + (B[i] - v) * t)
      .toString(16).padStart(2, '0')).join('');
  }
  const readable = new Map<string, string>();
  function colourFor(c: string): string {
    const raw = PALETTE[c]?.color;
    if (!raw) return 'var(--ink-dim)';
    let out = readable.get(raw);
    if (out === undefined) {
      out = raw;
      for (let t = 0; t <= 1.0001 && contrast(out, PANEL) < 4.5; t += 0.05) {
        out = blend(raw, INK, t);
      }
      readable.set(raw, out);
    }
    return out;
  }

  /** The first false claim in THIS run, if it has one. Trace A has none, and a
   *  caption that talks about carrying a bad total forward would be describing
   *  a run that never made the mistake. */
  const firstBad = $derived.by(() => {
    const i = trace.claims.findIndex((c) => !c.ok);
    return i < 0
      ? null
      : { index: i + 1, after: trace.thinking.length - trace.claims[i].end };
  });

  /** Totals over ALL runs, computed. A hardcoded 152 survived in the prose
   *  after subtraction was added and the real total became 160. */
  const TOTAL = OPENER.reduce((n, t) => n + t.claims.length, 0);
  const TOTAL_BAD = OPENER.reduce(
    (n, t) => n + t.claims.filter((x) => !x.ok).length, 0);

  /**
   * The run's verdict, landing with the last of the text.
   *
   * Without it the maths pane simply stops while the thinking scrolls on, which
   * reads as the figure being broken rather than as the model having finished
   * its arithmetic. The trace does end in something checkable — the answer it
   * reports, against the product — so that is the last row.
   */
  const verdict = $derived.by(() => {
    if (cursor < trace.thinking.length) return null;
    if (!trace.answer) return { said: null, truth: trace.truth, ok: false };
    return { said: trace.answer, truth: trace.truth, ok: trace.answer === trace.truth };
  });

  const landed = $derived(trace.claims.filter((c) => c.end <= cursor));
  const wrong = $derived(landed.filter((c) => !c.ok));

  /** Thousands separators on the integer part only: 371.448 is not 371{,}448. */
  const group = (s: string) => {
    const [whole, frac] = s.split('.');
    const g = whole.replace(/\B(?=(\d{3})+(?!\d))/g, '{,}');
    return frac ? `${g}.${frac}` : g;
  };
  function tex(c: Claim, side: 'said' | 'truth'): string {
    const op = c.op === '×' ? '\\times' : c.op === '−' ? '-' : '+';
    const rhs = side === 'said' ? c.said : c.truth;
    return `${group(c.a)} ${op} ${group(c.b)} = ${group(rhs)}`;
  }
  /** KaTeX output is deterministic per claim, so render each string once. */
  const cache = new Map<string, string>();
  function render(src: string): string {
    let html = cache.get(src);
    if (html === undefined) {
      html = katex.renderToString(src, { throwOnError: false, displayMode: false });
      cache.set(src, html);
    }
    return html;
  }

  /** Roving focus for the radio group: one tab stop, arrows move inside it. */
  const tabEls: Array<HTMLButtonElement | null> = $state([]);
  function arrows(e: KeyboardEvent) {
    const d = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 1
            : e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? -1 : 0;
    if (!d) return;
    e.preventDefault();
    const next = (which + d + OPENER.length) % OPENER.length;
    pick(next);
    tabEls[next]?.focus();
  }

  let streamEl: HTMLDivElement | null = $state(null);
  let mathEl: HTMLDivElement | null = $state(null);
  /**
   * While it is running the pane is being driven, so it does not scroll: the
   * reader cannot fight it, and following can be unconditional.
   *
   * The version before this tried to detect the reader taking over and hand
   * control back. It could not be made to work — the pane is growing under them
   * the whole time, so "scrolled back to the bottom" is a target that keeps
   * moving, and once following stopped it never resumed. Pause, and it scrolls
   * normally; the cursor is not moving then either, so nothing fights.
   */
  $effect(() => {
    cursor;
    if (streamEl) streamEl.scrollTop = streamEl.scrollHeight;
    if (mathEl) mathEl.scrollTop = mathEl.scrollHeight;
  });

  $effect(() => {
    if (!playing) return;
    // `elapsed` is read UNTRACKED. Read normally it would make this effect
    // depend on the value its own frame writes, so every frame would cancel and
    // restart the run with the clock reset, and it would crawl.
    const from = untrack(() => elapsed);
    const t0 = performance.now();
    let raf = 0;
    const step = (now: number) => {
      const next = from + (now - t0);
      if (next >= RUN_MS) {
        elapsed = RUN_MS;
        playing = false;
        return;
      }
      elapsed = next;
      raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  });

  const lessMotion = () =>
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /**
   * Reset for a run. A reader who has asked for less motion gets the finished
   * state rather than a blank pane they have to work out how to fill -- and
   * gets it on EVERY run, not just the first. Handling that only in onMount
   * left them staring at an empty figure the moment they changed tab, with
   * nothing to say the way to fill it was to drag a slider.
   */
  function reset(autoplay: boolean) {
    if (lessMotion()) {
      elapsed = RUN_MS;
      playing = false;
      return;
    }
    elapsed = 0;
    playing = autoplay;
  }

  /** Thousands separators without going through Number(). These values travel
   *  as strings because products here exceed MAX_SAFE_INTEGER; the operands are
   *  short enough to be safe today, and parsing them anyway is a trap left for
   *  the first 16-digit cell. */
  const commas = (d: string) => d.replace(/\B(?=(\d{3})+(?!\d))/g, ',');

  function toggle() {
    // Replay from the start, unless the reader asked for less motion -- in
    // which case they get the finished state, the same as every other path.
    if (!playing && done) {
      reset(true);
      return;
    }
    playing = !playing;
  }

  function pick(i: number) {
    which = i;
    // Autoplay. Landing on a paused, empty figure after choosing a run reads as
    // the figure being broken, not as an invitation to press play.
    reset(true);
  }

  onMount(() => reset(true));
</script>

<figure class="opener">
  <div class="head">
    <div class="sum">
      <span class="mono num">{commas(trace.x)}</span>
      <span class="op">&times;</span>
      <span class="mono num">{commas(trace.y)}</span>
    </div>
    <!-- One of three, so a radio group: aria-pressed describes a toggle, and
         three independent toggles is not what this is. Roving tabindex, so the
         group is one tab stop and the arrows move within it. -->
    <div
      class="tabs" role="radiogroup" aria-label="which run" tabindex="-1"
      onkeydown={arrows}>
      {#each OPENER as t, i}
        <button
          role="radio" aria-checked={i === which} class:on={i === which}
          tabindex={i === which ? 0 : -1}
          bind:this={tabEls[i]}
          onclick={() => pick(i)}>{t.verdict}</button>
      {/each}
    </div>
  </div>

  <div class="panes">
    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
    <!-- The rule and WCAG disagree here and WCAG wins: a 340px scrolling region
         has to be reachable and scrollable from the keyboard (2.1.1), and
         tabindex="0" on the region is how that is done. Deliberately no
         aria-live -- announcing a 36,000-character stream as it types would be
         unusable. -->
    <div
      class="pane stream" bind:this={streamEl} tabindex="0"
      style:overflow-y={playing ? 'hidden' : 'auto'}
      role="region" aria-label="the model's thinking, as raw text">
      {#each shown as s (s.start)}<span
          class="seg" style:--c={s.colour}
          title={s.label}>{s.text}</span>{/each}{#if !done}<span class="caret"></span>{/if}
    </div>

    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
    <div
      class="pane math" bind:this={mathEl} tabindex="0"
      style:overflow-y={playing ? 'hidden' : 'auto'}
      role="region" aria-label="the arithmetic it stated, checked as it is stated">
      {#if landed.length === 0}
        <p class="wait">waiting for the first claim&hellip;</p>
      {/if}
      {#each landed as c, i (c.at)}
        <div class="claim" class:bad={!c.ok}>
          <span class="ix mono">{i + 1}</span>
          <span class="eq">{@html render(tex(c, 'said'))}</span>
          <span class="mark">{c.ok ? '✓' : '✗'}</span>
          {#if !c.ok}
            <span class="ix mono"></span>
            <span class="eq actual">{@html render(tex(c, 'truth'))}</span>
            <span class="mark actual">actually</span>
          {/if}
        </div>
      {/each}
      {#if verdict}
        <div class="final" class:bad={!verdict.ok}>
          <span class="ix mono">&rarr;</span>
          <div>
            <div class="lead">
              {verdict.said ? 'It answered' : 'It never answered'}
            </div>
            {#if verdict.said}
              <div class="eq">{@html render(group(verdict.said))}</div>
            {/if}
            {#if !verdict.ok}
              <div class="lead">the product is</div>
              <div class="eq actual">{@html render(group(verdict.truth))}</div>
            {/if}
          </div>
          <span class="mark">{verdict.ok ? '✓' : '✗'}</span>
        </div>
      {/if}
    </div>
  </div>

  <div class="controls">
    <button class="play" onclick={toggle}
      aria-label={playing ? 'Pause' : done ? 'Replay' : 'Play'}>
      {playing ? '❚❚' : done ? '↺' : '▶'}
    </button>
    <!-- Scrubs TIME, not characters. The cursor is a function of the clock now,
         so a character-indexed slider would be scrubbing the output. 200 steps
         keeps it usable from the keyboard whatever the trace length. -->
    <input
      type="range" min="0" max={RUN_MS} step={RUN_MS / 200}
      bind:value={elapsed} oninput={() => (playing = false)}
      aria-label="position in the run"
      aria-valuetext="{Math.round((elapsed / RUN_MS) * 100)}% through,
        {landed.length} of {trace.claims.length} claims" />
    <span class="tally mono" class:bad={wrong.length > 0}>
      {landed.length} claim{landed.length === 1 ? '' : 's'} &middot;
      {wrong.length} wrong
    </span>
  </div>
</figure>

<style>
  .opener { margin: var(--space-md) 0 var(--space-xl); }

  .head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 8px 16px;
    margin-bottom: 10px;
  }
  .sum { display: flex; align-items: baseline; gap: 8px; }
  .num { font-size: 1.05rem; color: var(--ink); font-variant-numeric: tabular-nums; }
  .op { color: var(--ink-faint); }

  .tabs { display: inline-flex; border: 1px solid var(--line); border-radius: 5px;
    overflow: hidden; background: var(--panel); }
  .tabs button {
    appearance: none; border: 0; background: none; cursor: pointer;
    color: var(--ink-dim); font-family: var(--font-sans); font-size: 0.74rem;
    padding: 6px 12px; transition: background 0.15s, color 0.15s;
  }
  .tabs button + button { border-left: 1px solid var(--line); }
  .tabs button:hover { color: var(--ink); }
  .tabs button.on { background: var(--accent); color: var(--bg); }

  .panes {
    display: grid;
    grid-template-columns: 1.15fr 1fr;
    gap: 12px;
  }
  @media (max-width: 720px) { .panes { grid-template-columns: 1fr; } }

  .pane {
    height: 340px;
    border: 1px solid var(--line);
    border-radius: 5px;
    background: var(--panel);
    padding: 14px 16px;
    scrollbar-width: thin;
  }
  .pane:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .tabs button:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }

  .stream {
    font-family: var(--font-mono);
    font-size: 0.72rem;
    line-height: 1.72;
    white-space: pre-wrap;
    word-break: break-word;
    color: var(--ink-dim);
  }
  /* Tint by what kind of move the model was making, using the same nine
     categories the flame figure colours by -- but only a third of the way. The
     palette is built for filled flame bars on a light ground, so three of the
     nine are pale enough to vanish as text. Legibility wins; the category is a
     hint here and the flame figure is where it is the point. */
  /* Already darkened to a readability floor in colourFor(); mixing again here
     would undo the point of doing it per category. */
  .seg { color: var(--c); }
  .caret {
    display: inline-block; width: 0.5em; height: 1em; vertical-align: -0.15em;
    background: var(--accent); animation: blink 1s steps(2, start) infinite;
  }
  @keyframes blink { to { visibility: hidden; } }

  .math { display: flex; flex-direction: column; gap: 7px; }
  .wait { color: var(--ink-faint); font-family: var(--font-sans); font-size: 0.78rem; margin: 0; }
  .claim {
    display: grid;
    grid-template-columns: 1.6rem 1fr auto;
    align-items: baseline;
    gap: 2px 10px;
    padding: 4px 6px;
    border-radius: 3px;
  }
  @keyframes land {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: none; }
  }
  @media (prefers-reduced-motion: reduce) {
    .claim { animation: none; }
  }
  .claim .ix { color: var(--ink-faint); font-size: 0.62rem; text-align: right; }
  .claim .eq { font-size: 0.82rem; overflow-x: auto; }
  .claim .mark { font-size: 0.72rem; color: var(--ink-faint); }
  .claim.bad { background: color-mix(in srgb, var(--pos) 12%, transparent);
    outline: 1px solid color-mix(in srgb, var(--pos) 40%, transparent); }
  .claim.bad .mark { color: var(--pos); font-weight: 600; }
  .claim.bad .eq :global(.katex) { color: var(--pos); }
  .claim .actual { opacity: 0.85; }
  .claim .eq.actual :global(.katex) { color: var(--ink); }

  .final {
    display: grid;
    grid-template-columns: 1.6rem 1fr auto;
    align-items: baseline;
    gap: 2px 10px;
    padding: 9px 6px;
    margin-top: 4px;
    border-top: 1px solid var(--line);
    animation: land 260ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
  }
  .final .ix { color: var(--ink-faint); text-align: right; }
  .final .lead {
    font-family: var(--font-sans);
    font-size: 0.7rem;
    color: var(--ink-faint);
    letter-spacing: 0.02em;
  }
  .final .eq { font-size: 0.86rem; margin: 1px 0 3px; }
  .final .mark { font-size: 0.78rem; color: var(--ink-faint); }
  .final.bad .mark { color: var(--pos); font-weight: 600; }
  .final.bad .eq:not(.actual) :global(.katex) { color: var(--pos); }

  .controls {
    display: flex; align-items: center; gap: 12px; margin-top: 12px;
  }
  .play {
    appearance: none; border: 1px solid var(--line); background: var(--panel);
    color: var(--ink-dim); cursor: pointer; border-radius: 4px;
    width: 30px; height: 26px; font-size: 0.66rem; line-height: 1;
  }
  .play:hover { color: var(--ink); }
  .controls input[type='range'] { flex: 1; accent-color: var(--accent); }
  .tally { font-size: 0.68rem; color: var(--ink-faint); white-space: nowrap;
    font-variant-numeric: tabular-nums; }
  .tally.bad { color: var(--pos); }


  @media (prefers-reduced-motion: reduce) {
    .caret { animation: none; }
    .tabs button { transition: none; }
  }
</style>
