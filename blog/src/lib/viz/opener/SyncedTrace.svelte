<script lang="ts">
  /**
   * One run, three views, one clock.
   *
   * The flame graph on top is the shape of the whole trace. Under it, the
   * thinking as the model wrote it, and every arithmetic claim it makes graded
   * against real arithmetic as it is made. A playhead crosses the flame while
   * the two panes fill beneath it, so a bar lighting up and a line of text and
   * an equation landing are the same moment seen three ways.
   *
   * ## Why the sync is exact rather than approximate
   *
   * Both figures index ONE STRING: the model's response verbatim, tags and
   * final answer included. The flame's x axis is character offsets into it and
   * so is the cursor, so `playhead={cursor}` is the whole of the sync, and the
   * playhead reaches the right-hand edge exactly as the last character lands.
   *
   * Getting there took two corrections, both of which showed the two panes
   * disagreeing while looking plausible:
   *
   *   1. `instance_uid` names the PROBLEM, not the generation. The same problem
   *      was sampled several times, across sweeps and at two temperatures, so
   *      matching on the uid alone gave a different run from the one the flame
   *      was built from -- for two of the three traces. The loader now pins the
   *      response length as well.
   *   2. The stream stripped the `<think>` tag and trimmed the ends, which
   *      shifted every bar seven characters off the text it labels and left the
   *      stream shorter than the graph driving it, so the playhead stopped
   *      short of the end. The response is now carried verbatim.
   *
   * The generator asserts the segments tile that string exactly, so the bars
   * and the characters cannot drift apart again without the build failing.
   *
   * ## The clock
   *
   * Time is divided evenly across the claims, not across the characters. At a
   * constant character rate the maths pane is at the mercy of how verbose the
   * model happened to be between two equations: measured, claims land a median
   * 0.11s apart but a p90 of 2.2s, so thirteen arrive in one second and then
   * nothing for thirteen. Each claim gets a beat instead, and the cursor sweeps
   * whatever prose lies between them, easing out so the text decelerates into
   * the landing. The stretch after the last claim takes its share of the text
   * rather than one beat, which stops the conclusion blurring past.
   */
  import { onMount, untrack } from 'svelte';
  import katex from 'katex';
  import 'katex/dist/katex.min.css';
  import { OPENER, type Claim } from '../../data/opener';
  import { CARRY_TRACES } from '../../data/carrychain-traces';
  import { CARRY_SCHEME } from '../../design/scheme';
  import { carryCategoryMeta } from '../../design/carrychain-categories';
  import FlamePanel from '../flame/FlamePanel.svelte';

  let which = $state(0);
  const trace = $derived(OPENER[which]);
  /** The same run in the flame figure's shape, matched on uid rather than order. */
  const flame = $derived(
    CARRY_TRACES.find((t) => t.uid === trace.uid) ?? CARRY_TRACES[which],
  );

  /**
   * The flame graph and the stream measure the same string, so its span and the
   * text length are the same number. Asserted rather than assumed: an earlier
   * version divided the axis by the text length while the graph spanned a
   * different generation, and the axis read 0% to 141%. Deriving the axis from
   * the graph's own span would have hidden that -- the ticks would have read
   * 0-100% while the playhead quietly stopped short -- so the two are compared
   * and a mismatch is loud.
   */
  const flameSpan = $derived(
    flame.rows.reduce((m, r) => Math.max(m, r.start + r.width), 0) || 1,
  );
  $effect(() => {
    if (flameSpan !== trace.text.length) {
      console.error(
        `[SyncedTrace] ${trace.key}: flame spans ${flameSpan} but the text is ` +
        `${trace.text.length}. The two figures are not showing the same string.`,
      );
    }
  });

  const RUN_MS = 20_000;
  let elapsed = $state(0);
  let playing = $state(false);

  const knots = $derived([0, ...trace.claims.map((c) => c.end), trace.text.length]);
  const schedule = $derived.by(() => {
    const total = trace.text.length;
    const tailChars = total - (knots.length > 2 ? knots[knots.length - 2] : 0);
    const share = Math.max(0.03, Math.min(0.35, tailChars / Math.max(1, total)));
    const tailMs = RUN_MS * share;
    const beat = (RUN_MS - tailMs) / Math.max(1, knots.length - 2);
    const at = [0];
    for (let i = 1; i < knots.length; i++) {
      at.push(at[i - 1] + (i === knots.length - 1 ? tailMs : beat));
    }
    return at;
  });

  function cursorAt(ms: number): number {
    const at = schedule;
    let i = 0;
    while (i < at.length - 2 && ms >= at[i + 1]) i++;
    const span = at[i + 1] - at[i] || 1;
    const u = Math.max(0, Math.min(1, (ms - at[i]) / span));
    return Math.floor(knots[i] + (knots[i + 1] - knots[i]) * (1 - (1 - u) ** 3));
  }

  const cursor = $derived(cursorAt(elapsed));
  const done = $derived(elapsed >= RUN_MS);

  /**
   * WHO OWNS THE CURSOR.
   *
   * Exactly one thing writes it at a time: the clock while running, the seek
   * tween while seeking, the reader through the slider when idle. Two writers
   * on one value is the bug that has already appeared twice here -- an effect
   * that invalidated itself by reading what its own frame wrote, and a scroll
   * pin that fought the reader it was meant to follow -- so the states are
   * explicit rather than inferred from a pile of booleans.
   *
   * Zoom is deliberately outside all of this. It changes the VIEW, not the
   * cursor, and nothing else reads it, so it can never race the clock and is
   * available in every state.
   */
  let seeking = $state(false);
  const idle = $derived(!playing && !seeking);

  /** Time at which the cursor reaches a character offset: cursorAt inverted. */
  function timeAt(offset: number): number {
    const at = schedule;
    let i = 0;
    while (i < knots.length - 2 && knots[i + 1] <= offset) i++;
    const span = knots[i + 1] - knots[i];
    const frac = span > 0 ? Math.max(0, Math.min(1, (offset - knots[i]) / span)) : 0;
    const u = 1 - Math.cbrt(1 - frac);          // undo the ease-out
    return at[i] + u * (at[i + 1] - at[i]);
  }

  /**
   * Move the cursor to a character offset, smoothly. Everything follows for
   * free: the playhead, the text and the claims are all functions of `elapsed`,
   * so there is nothing to keep in step by hand.
   */
  let seekRaf = 0;
  function seekTo(offset: number) {
    if (!idle) return;                          // the clock or another seek owns it
    const to = timeAt(offset);
    const from = elapsed;
    // The dead zone is in CHARACTERS. Expressed in milliseconds it scaled with
    // the local sweep rate -- 8ms is 291 characters inside the long tail of the
    // run that never answered, so a click near the cursor there did nothing.
    if (Math.abs(cursorAt(to) - cursorAt(from)) < 2) return;
    cancelAnimationFrame(seekRaf);
    if (lessMotion()) {
      elapsed = to;
      return;
    }
    seeking = true;
    const t0 = performance.now();
    const step = (now: number) => {
      const u = Math.min(1, (now - t0) / 620);
      const e = u < 0.5 ? 4 * u ** 3 : 1 - (-2 * u + 2) ** 3 / 2;
      elapsed = from + (to - from) * e;
      if (u < 1) seekRaf = requestAnimationFrame(step);
      else seeking = false;
    };
    seekRaf = requestAnimationFrame(step);
  }

  // ---- the stream ---------------------------------------------------------
  const PALETTE: Record<string, { color: string }> = carryCategoryMeta;
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
  const mixHex = (a: string, b: string, t: number) =>
    '#' + chan(a).map((v, i) => Math.round(v + (chan(b)[i] - v) * t)
      .toString(16).padStart(2, '0')).join('');
  /** Darken only as far as legibility needs. A flat mix crushes every hue into
   *  the same near-black and the error red stops being red. */
  const readable = new Map<string, string>();
  function colourFor(c: string): string {
    const raw = PALETTE[c]?.color;
    if (!raw) return 'var(--ink-dim)';
    let out = readable.get(raw);
    if (out === undefined) {
      out = raw;
      for (let t = 0; t <= 1.0001 && contrast(out, PANEL) < 4.5; t += 0.05) {
        out = mixHex(raw, INK, t);
      }
      readable.set(raw, out);
    }
    return out;
  }

  const ordered = $derived([...trace.segments].sort((a, b) => a.start - b.start));
  const shown = $derived.by(() => {
    const out: Array<{ start: number; text: string; colour: string; label: string }> = [];
    for (const s of ordered) {
      if (s.start >= cursor) break;
      out.push({
        start: s.start,
        text: trace.text.slice(s.start, Math.min(s.end, cursor)),
        colour: colourFor(s.category),
        label: s.label,
      });
    }
    return out;
  });

  // ---- the maths ----------------------------------------------------------
  const landed = $derived(trace.claims.filter((c) => c.end <= cursor));
  const wrong = $derived(landed.filter((c) => !c.ok));
  const verdict = $derived.by(() => {
    if (cursor < trace.text.length) return null;
    if (!trace.answer) return { said: null, truth: trace.truth, ok: false };
    return { said: trace.answer, truth: trace.truth, ok: trace.answer === trace.truth };
  });

  /** Thousands separators on the integer part only: 371.448 is not 371{,}448. */
  const group = (s: string) => {
    const [whole, frac] = s.split('.');
    const g = whole.replace(/\B(?=(\d{3})+(?!\d))/g, '{,}');
    return frac ? `${g}.${frac}` : g;
  };
  function tex(c: Claim, side: 'said' | 'truth'): string {
    const op = c.op === '×' ? '\\times' : c.op === '−' ? '-' : '+';
    return `${group(c.a)} ${op} ${group(c.b)} = ${group(side === 'said' ? c.said : c.truth)}`;
  }
  const cache = new Map<string, string>();
  function render(src: string): string {
    let html = cache.get(src);
    if (html === undefined) {
      html = katex.renderToString(src, { throwOnError: false, displayMode: false });
      cache.set(src, html);
    }
    return html;
  }

  // ---- panes follow the cursor while it runs ------------------------------
  let streamEl: HTMLDivElement | null = $state(null);
  let mathEl: HTMLDivElement | null = $state(null);
  $effect(() => {
    cursor;
    if (streamEl) streamEl.scrollTop = streamEl.scrollHeight;
    if (mathEl) mathEl.scrollTop = mathEl.scrollHeight;
  });

  $effect(() => {
    if (!playing) return;
    // `elapsed` is read UNTRACKED: read normally this effect would depend on
    // the value its own frame writes, cancelling and restarting the run every
    // frame with the clock reset, and it would crawl.
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
  function reset(autoplay: boolean) {
    cancelAnimationFrame(seekRaf);
    seeking = false;
    if (lessMotion()) {
      elapsed = RUN_MS;
      playing = false;
      return;
    }
    elapsed = 0;
    playing = autoplay;
  }
  function toggle() {
    if (!playing && done) {
      reset(true);
      return;
    }
    cancelAnimationFrame(seekRaf);
    seeking = false;
    playing = !playing;
  }
  const tabEls: Array<HTMLButtonElement | null> = $state([]);
  function pick(i: number) {
    which = i;
    reset(true);
  }
  function arrows(e: KeyboardEvent) {
    const d = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 1
            : e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? -1 : 0;
    if (!d) return;
    e.preventDefault();
    const next = (which + d + OPENER.length) % OPENER.length;
    pick(next);
    tabEls[next]?.focus();
  }
  onMount(() => reset(true));

  const commas = (d: string) => d.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
</script>

<figure class="synced">
  <div class="head">
    <span class="sum mono">{commas(trace.x)} &times; {commas(trace.y)}</span>
    <div class="tabs" role="radiogroup" aria-label="which run" tabindex="-1" onkeydown={arrows}>
      {#each OPENER as t, i}
        <button
          role="radio" aria-checked={i === which} class:on={i === which}
          tabindex={i === which ? 0 : -1} bind:this={tabEls[i]}
          onclick={() => pick(i)}>{t.verdict}</button>
      {/each}
    </div>
  </div>

  <!-- The shape of the whole run, with the playhead crossing it. Minimap,
       inspector and zoom hint are off: this panel is a timeline here, and the
       two panes below are the inspector. -->
  <div class="flame" class:busy={!idle}>
    <!-- An empty header: the run is already named by the tabs above, and the
         panel's own badge-and-pills header would say it a second time. -->
    {#snippet header()}<span class="sr-only">{flame.verdict}</span>{/snippet}
    <FlamePanel
      trace={{ ...flame, name: flame.verdict, stepCount: flame.segments }}
      scheme={CARRY_SCHEME}
      {header}
      playhead={cursor}
      dimAhead={true}
      onSelect={(_i, row) => seekTo(row.start)}
      showInspector={false}
      showMinimap={false}
      showInspectorHint={false}
      showZoomHint={false}
      showLegend={true}
      maxChartHeight={150}
      formatTick={(t) => `${Math.round((t / flameSpan) * 100)}%`}
    />
  </div>

  <div class="panes">
    <!-- Labelled, because the left pane shows the response VERBATIM and its
         final section is the model's markdown answer. Rendering that would
         change the character count every flame bar indexes, so it stays raw and
         the label says so rather than leaving it looking broken. -->
    <p class="pane-label" id="lab-stream">what it emitted, verbatim</p>
    <p class="pane-label" id="lab-math">the arithmetic in it, checked</p>
    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
    <!-- A scrolling region has to be keyboard reachable (WCAG 2.1.1); the lint
         rule disagrees and WCAG wins. No aria-live: announcing a 36,000
         character stream as it types would be unusable. -->
    <div
      class="pane stream" bind:this={streamEl} tabindex="0"
      style:overflow-y={idle ? 'auto' : 'hidden'}
      role="region" aria-labelledby="lab-stream">
      {#each shown as s (s.start)}<span
          class="seg" style:--c={s.colour} title={s.label}>{s.text}</span
        >{/each}{#if !done}<span class="caret"></span>{/if}
    </div>

    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
    <div
      class="pane math" bind:this={mathEl} tabindex="0"
      style:overflow-y={idle ? 'auto' : 'hidden'}
      role="region" aria-labelledby="lab-math">
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
            <div class="lead">{verdict.said ? 'It answered' : 'It never answered'}</div>
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
    <input
      type="range" min="0" max={RUN_MS} step={RUN_MS / 200}
      bind:value={elapsed}
      oninput={() => { cancelAnimationFrame(seekRaf); seeking = false; playing = false; }}
      aria-label="position in the run"
      aria-valuetext="{Math.round((elapsed / RUN_MS) * 100)}% through,
        {landed.length} of {trace.claims.length} claims" />
    <span class="tally mono" class:bad={wrong.length > 0}>
      {landed.length} claim{landed.length === 1 ? '' : 's'} &middot; {wrong.length} wrong
    </span>
  </div>
</figure>

<style>
  .synced { margin: var(--space-md) 0 var(--space-lg); }

  .head {
    display: flex; align-items: baseline; justify-content: space-between;
    flex-wrap: wrap; gap: 6px 14px; margin-bottom: 10px;
  }
  .sum { font-size: 1.02rem; color: var(--ink); font-variant-numeric: tabular-nums; }

  .tabs {
    display: inline-flex; border: 1px solid var(--line); border-radius: 5px;
    overflow: hidden; background: var(--panel);
  }
  .tabs button {
    appearance: none; border: 0; background: none; cursor: pointer;
    color: var(--ink-dim); font-family: var(--font-sans); font-size: 0.76rem;
    padding: 6px 13px; transition: background 0.15s, color 0.15s;
  }
  .tabs button + button { border-left: 1px solid var(--line); }
  .tabs button:hover { color: var(--ink); }
  .tabs button.on { background: var(--accent); color: var(--bg); }
  .tabs button:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }

  /* The panel is styled as a figure in its own right; here it is the top third
     of one, so its frame and padding are pulled back. */
  /* A block is only a seek control when nothing else owns the cursor. Leaving
     it looking clickable while the run is playing promises something the state
     machine will refuse. Zooming still works -- that is a view change. */
  .flame.busy :global(.flame-rect) { cursor: default; }

  .flame :global(.flame-panel) {
    padding: var(--space-sm) var(--space-md);
    gap: var(--space-sm);
  }
  .sr-only {
    position: absolute; width: 1px; height: 1px; overflow: hidden;
    clip: rect(0 0 0 0); white-space: nowrap;
  }

  .panes {
    display: grid; grid-template-columns: 1.15fr 1fr;
    grid-template-rows: auto 1fr; gap: 4px 10px; margin-top: 10px;
  }
  @media (max-width: 720px) { .panes { grid-template-columns: 1fr; } }
  .pane-label {
    margin: 0; font-family: var(--font-sans); font-size: 0.66rem;
    letter-spacing: 0.05em; text-transform: uppercase; color: var(--ink-faint);
  }

  .pane {
    height: 290px; border: 1px solid var(--line); border-radius: 5px;
    background: var(--panel); padding: 13px 15px; scrollbar-width: thin;
  }
  .pane:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

  .stream {
    font-family: var(--font-mono); font-size: 0.7rem; line-height: 1.7;
    white-space: pre-wrap; word-break: break-word; color: var(--ink-dim);
  }
  .seg { color: var(--c); }
  .caret {
    display: inline-block; width: 0.5em; height: 1em; vertical-align: -0.15em;
    background: var(--accent); animation: blink 1s steps(2, start) infinite;
  }
  @keyframes blink { to { visibility: hidden; } }

  .math { display: flex; flex-direction: column; gap: 6px; }
  .claim {
    display: grid; grid-template-columns: 1.5rem 1fr auto;
    align-items: baseline; gap: 2px 9px; padding: 3px 5px; border-radius: 3px;
    animation: land 220ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
  }
  @keyframes land {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: none; }
  }
  .claim .ix, .final .ix {
    color: var(--ink-faint); font-size: 0.6rem; text-align: right;
  }
  .claim .eq { font-size: 0.8rem; overflow-x: auto; }
  .claim .mark { font-size: 0.7rem; color: var(--ink-faint); }
  .claim.bad {
    background: color-mix(in srgb, var(--pos) 12%, transparent);
    outline: 1px solid color-mix(in srgb, var(--pos) 40%, transparent);
  }
  .claim.bad .mark { color: var(--pos); font-weight: 600; }
  .claim.bad .eq :global(.katex) { color: var(--pos); }
  .claim .eq.actual :global(.katex) { color: var(--ink); }

  .final {
    display: grid; grid-template-columns: 1.5rem 1fr auto; align-items: baseline;
    gap: 2px 9px; padding: 8px 5px; margin-top: 3px;
    border-top: 1px solid var(--line);
    animation: land 260ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
  }
  .final .lead {
    font-family: var(--font-sans); font-size: 0.68rem; color: var(--ink-faint);
  }
  .final .eq { font-size: 0.84rem; margin: 1px 0 3px; }
  .final .mark { font-size: 0.76rem; color: var(--ink-faint); }
  .final.bad .mark { color: var(--pos); font-weight: 600; }
  .final.bad .eq:not(.actual) :global(.katex) { color: var(--pos); }

  .controls { display: flex; align-items: center; gap: 12px; margin-top: 11px; }
  .play {
    appearance: none; border: 1px solid var(--line); background: var(--panel);
    color: var(--ink-dim); cursor: pointer; border-radius: 4px;
    width: 30px; height: 26px; font-size: 0.64rem; line-height: 1;
  }
  .play:hover { color: var(--ink); }
  .controls input[type='range'] { flex: 1; accent-color: var(--accent); }
  .tally {
    font-size: 0.66rem; color: var(--ink-faint); white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }
  .tally.bad { color: var(--pos); }

  @media (prefers-reduced-motion: reduce) {
    .caret { animation: none; }
    .claim, .final { animation: none; }
    .tabs button { transition: none; }
  }
</style>
