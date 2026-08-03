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
   * Across the three runs there are 152 claims and exactly one is false, in the
   * run that got the answer wrong. It is an ADDITION: every multiplication in
   * every trace is correct. That is the whole opener.
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

  /** Characters of `thinking` revealed so far. */
  let cursor = $state(0);
  let playing = $state(false);
  let done = $derived(cursor >= trace.thinking.length);

  const CPS = 900; // characters a second; the whole of A runs in about 18s

  /**
   * The stream is rendered as one node per SEGMENT, not one per character.
   * Revealed segments are static, so only the segment the cursor is inside
   * re-renders on a frame — 16,000 characters otherwise means rebuilding the
   * whole subtree sixty times a second.
   */
  const shown = $derived.by(() => {
    const out: Array<{ start: number; text: string; colour: string; label: string }> = [];
    for (const s of trace.segments) {
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
  const colourFor = (c: string) => PALETTE[c]?.color ?? 'var(--ink-dim)';

  /** The first false claim in THIS run, if it has one. Trace A has none, and a
   *  caption that talks about carrying a bad total forward would be describing
   *  a run that never made the mistake. */
  const firstBad = $derived.by(() => {
    const i = trace.claims.findIndex((c) => !c.ok);
    return i < 0
      ? null
      : { index: i + 1, after: trace.thinking.length - trace.claims[i].end };
  });

  const landed = $derived(trace.claims.filter((c) => c.end <= cursor));
  const wrong = $derived(landed.filter((c) => !c.ok));

  const group = (s: string) => s.replace(/\B(?=(\d{3})+(?!\d))/g, '{,}');
  function tex(c: Claim, side: 'said' | 'truth'): string {
    const op = c.op === '×' ? '\\times' : '+';
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

  let streamEl: HTMLDivElement | null = $state(null);
  let mathEl: HTMLDivElement | null = $state(null);
  $effect(() => {
    cursor;
    // Follow the cursor. Both panes are append-only, so pinning to the bottom
    // is the whole behaviour.
    if (streamEl) streamEl.scrollTop = streamEl.scrollHeight;
    if (mathEl) mathEl.scrollTop = mathEl.scrollHeight;
  });

  $effect(() => {
    if (!playing) return;
    // `cursor` is read untracked: reading it normally would make this effect
    // depend on the value its own frame writes, so every frame would cancel and
    // restart the run with the clock reset, and it would crawl.
    const from = untrack(() => cursor);
    const t0 = performance.now();
    const total = trace.thinking.length;
    let raf = 0;
    const step = (now: number) => {
      const next = from + ((now - t0) / 1000) * CPS;
      if (next >= total) {
        cursor = total;
        playing = false;
        return;
      }
      cursor = Math.floor(next);
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
      cursor = OPENER[which].thinking.length;
      playing = false;
      return;
    }
    cursor = 0;
    playing = autoplay;
  }

  function toggle() {
    if (!playing && done) cursor = 0;
    playing = !playing;
  }

  function pick(i: number) {
    which = i;
    reset(false);
  }

  onMount(() => reset(true));
</script>

<figure class="opener">
  <div class="head">
    <div class="sum">
      <span class="mono num">{Number(trace.x).toLocaleString()}</span>
      <span class="op">&times;</span>
      <span class="mono num">{Number(trace.y).toLocaleString()}</span>
    </div>
    <div class="tabs" role="group" aria-label="which run">
      {#each OPENER as t, i}
        <button class:on={i === which} aria-pressed={i === which} onclick={() => pick(i)}>
          {t.verdict}
        </button>
      {/each}
    </div>
  </div>

  <div class="panes">
    <div class="pane stream" bind:this={streamEl} aria-label="the model's thinking">
      {#each shown as s (s.start)}<span
          class="seg" style:--c={s.colour}
          title={s.label}>{s.text}</span>{/each}{#if !done}<span class="caret"></span>{/if}
    </div>

    <div class="pane math" bind:this={mathEl} aria-label="the arithmetic it stated, checked">
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
    </div>
  </div>

  <div class="controls">
    <button class="play" onclick={toggle}
      aria-label={playing ? 'Pause' : done ? 'Replay' : 'Play'}>
      {playing ? '❚❚' : done ? '↺' : '▶'}
    </button>
    <input
      type="range" min="0" max={trace.thinking.length} bind:value={cursor}
      oninput={() => (playing = false)} aria-label="position in the trace" />
    <span class="tally mono" class:bad={wrong.length > 0}>
      {landed.length} claim{landed.length === 1 ? '' : 's'} &middot;
      {wrong.length} wrong
    </span>
  </div>

  <figcaption>
    Every closed arithmetic statement is checked against real arithmetic as it is
    made. Across all three runs there are <strong>152</strong> of them and exactly
    <strong>one</strong> is false &mdash; an addition. Every multiplication in
    every run is correct.
    {#if firstBad}
      This run states it at claim <strong>{firstBad.index}</strong>, then carries
      the bad total forward for another <strong>{firstBad.after.toLocaleString()}</strong>
      characters and reports it as the answer. Nothing in the prose marks the line:
      it goes on to check its work, and the check agrees with the wrong number.
    {:else if trace.answer === trace.truth}
      This is the run that got it right, and its {trace.claims.length} claims are all
      true &mdash; but read the left pane alone and it is not distinguishable from the
      one that did not.
    {:else}
      This run makes no arithmetic error at all. It computes the right answer and
      then never commits to it, re-deriving the same total until it runs out of
      room. Failing is not the same as being wrong.
    {/if}
  </figcaption>
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
    overflow-y: auto;
    border: 1px solid var(--line);
    border-radius: 5px;
    background: var(--panel);
    padding: 14px 16px;
    scrollbar-width: thin;
  }

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
  .seg { color: color-mix(in srgb, var(--c) 34%, var(--ink)); }
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
  .claim .ix { color: var(--ink-faint); font-size: 0.62rem; text-align: right; }
  .claim .eq { font-size: 0.82rem; overflow-x: auto; }
  .claim .mark { font-size: 0.72rem; color: var(--ink-faint); }
  .claim.bad { background: color-mix(in srgb, var(--pos) 12%, transparent);
    outline: 1px solid color-mix(in srgb, var(--pos) 40%, transparent); }
  .claim.bad .mark { color: var(--pos); font-weight: 600; }
  .claim.bad .eq :global(.katex) { color: var(--pos); }
  .claim .actual { opacity: 0.85; }
  .claim .eq.actual :global(.katex) { color: var(--ink); }

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

  figcaption {
    margin-top: 14px;
    font-family: var(--font-sans);
    font-size: 0.82rem;
    line-height: 1.6;
    color: var(--ink-faint);
    max-width: 66ch;
  }
  figcaption strong { color: var(--ink-dim); font-weight: 600; }

  @media (prefers-reduced-motion: reduce) {
    .caret { animation: none; }
    .tabs button { transition: none; }
  }
</style>
