<script lang="ts">
  /**
   * One carrychain trace as a flame chart.
   *
   * Differences from FlamePanel, which renders the λ reference figure:
   *
   * The axis is a PERCENTAGE of the trace, not an absolute offset. The three
   * traces are 16k, 18k and 57k characters, so on a shared absolute axis the
   * two that finished would be slivers next to the one that did not. Percent
   * makes the shape comparable, and the header carries the real length in
   * tokens so nothing is hidden by the normalisation.
   *
   * There is no minimap. These traces are two levels deep; a 64px overview of
   * three rows repeats the chart rather than summarising it.
   *
   * Annotations are the payload. Each is pinned to a segment index and drawn as
   * a numbered marker on the timeline — the moments the post argues about, in
   * their real positions, rather than described in prose and left to the reader
   * to locate.
   */
  import { scaleLinear } from 'd3-scale';
  import { MediaQuery } from 'svelte/reactivity';
  import FlameGraph from './FlameGraph.svelte';
  import { ChartViewport } from './ChartViewport.svelte';
  import { CARRY_SCHEME, metaFor, type AnyFlameRow } from '../../design/scheme';
  import type { CarryFlameRow, CarryTrace } from '../../data/carrychain-traces';

  const canHover = new MediaQuery('(hover: hover)');

  type Props = {
    trace: CarryTrace;
    hiddenCategories: ReadonlySet<string>;
    /** Start with one annotation already open, so the panel is never blank. */
    initialAnnotation?: number | null;
  };

  let { trace, hiddenCategories, initialAnnotation = 0 }: Props = $props();

  let hoveredIndex: number | null = $state(null);
  let selectedIndex: number | null = $state(null);
  // svelte-ignore state_referenced_locally
  // Initial value only, by design -- the panel owns which note is open after mount.
  let openAnnotation: number | null = $state(initialAnnotation);
  let tooltip: { x: number; y: number; row: CarryFlameRow } | null = $state(null);

  let hostEl: HTMLDivElement | null = $state(null);
  let width = $state(760);

  const CHART_H = 70; // 3 depth levels at ~22px
  const viewport = new ChartViewport(760, CHART_H);

  $effect(() => {
    if (trace.chars > 0 && viewport.max !== trace.chars) viewport.setBounds(0, trace.chars);
  });

  $effect(() => {
    if (!hostEl) return;
    const ro = new ResizeObserver((e) => {
      const w = e[0]?.contentRect.width;
      if (w) {
        width = Math.max(260, Math.floor(w));
        viewport.updateViewportWidth(width);
      }
    });
    ro.observe(hostEl);
    return () => ro.disconnect();
  });

  const pct = $derived(scaleLinear().domain([...viewport.domain]).range([0, width]));
  const TICKS = [0, 0.25, 0.5, 0.75, 1];

  // Leaf rows only — containers span their children and would double-count.
  const leaves = $derived(trace.rows.filter((r) => !r.container));

  const marks = $derived(
    trace.annotations.map((a, i) => {
      const row = leaves.find((r) => r.index === a.segment);
      return { ...a, i, start: row ? row.start : 0, frac: row ? row.start / trace.chars : 0 };
    }),
  );

  // Several annotations can land within a few characters of each other — C has
  // four inside one tenth of its trace — and overlapping circles hide their own
  // numbers. Push each one right until it clears the last, so the ordering stays
  // readable; the hairline under each marker still points at the true position.
  const MARK_W = 17;
  const placed = $derived.by(() => {
    let last = -Infinity;
    return marks
      .map((m) => ({ m, at: pct(m.start) }))
      .sort((a, b) => a.at - b.at)
      .map(({ m, at }) => {
        const x = Math.max(at, last + MARK_W);
        last = x;
        return { m, x, at };
      });
  });

  const selectedRow = $derived(
    selectedIndex === null ? null : (trace.rows[selectedIndex] ?? null),
  );

  const tone = $derived(
    trace.outcome === 'converged_right' ? 'ok' : trace.outcome === 'grind' ? 'wait' : 'err',
  );

  function onHover(i: number | null, row: AnyFlameRow | null, ev: MouseEvent | null) {
    if (i === null || row === null || ev === null) {
      hoveredIndex = null;
      tooltip = null;
      return;
    }
    hoveredIndex = i;
    if (!canHover.current) return; // touch taps never fire mouseleave
    const w = 300;
    const h = 92;
    let x = ev.clientX + 14;
    let y = ev.clientY + 14;
    if (x + w > window.innerWidth) x = ev.clientX - w - 14;
    if (y + h > window.innerHeight) y = ev.clientY - h - 14;
    // FlameGraph is generic over rows; every row it hands back here came from
    // trace.rows, so it carries the container flag the tooltip reads.
    tooltip = { x: Math.max(4, x), y: Math.max(4, y), row: row as CarryFlameRow };
  }

  function onClick(i: number) {
    selectedIndex = selectedIndex === i ? null : i;
    openAnnotation = null;
  }

  function openMark(i: number) {
    openAnnotation = openAnnotation === i ? null : i;
    const seg = trace.annotations[i]?.segment;
    selectedIndex = seg === undefined ? null : trace.rows.findIndex((r) => !r.container && r.index === seg);
  }

  const fmt = new Intl.NumberFormat('en-US');
</script>

<figure class="panel" class:is-grind={trace.outcome === 'grind'}>
  <header>
    <span class="badge" data-tone={tone}>{trace.verdict}</span>
    <span class="blurb">{trace.blurb}</span>
    <span class="stats mono">
      {trace.cell} · N={trace.n} · T={trace.temperature} · {fmt.format(trace.tokens)} tok
    </span>
  </header>

  <div class="chart" bind:this={hostEl}>
    <!-- annotation markers, positioned in the trace's own coordinates -->
    <div class="marks" style:height="18px">
      {#each placed as { m, x, at } (m.i)}
        {#if x >= -8 && x <= width + 8}
          <button
            class="mark"
            class:is-open={openAnnotation === m.i}
            style:left="{x}px"
            style:--lean="{at - x}px"
            onclick={() => openMark(m.i)}
            aria-label="{m.kind.replace(/_/g, ' ')} at {(m.frac * 100).toFixed(0)}% of the trace"
            aria-expanded={openAnnotation === m.i}
          >{m.i + 1}</button>
        {/if}
      {/each}
    </div>

    <FlameGraph
      {trace}
      scheme={CARRY_SCHEME}
      {hiddenCategories}
      {selectedIndex}
      {hoveredIndex}
      {viewport}
      {width}
      enableZoom={true}
      showAxis={false}
      showLabels={true}
      minRowHeight={6}
      targetHeight={CHART_H}
      {onHover}
      onClick={(i) => onClick(i)}
    />

    <svg class="axis" {width} height="20" role="presentation">
      {#each TICKS as t (t)}
        {@const x = pct(t * trace.chars)}
        {#if x >= 0 && x <= width}
          <line x1={x} x2={x} y1="0" y2="4" />
          <text {x} y="15" text-anchor={t === 0 ? 'start' : t === 1 ? 'end' : 'middle'}>
            {t * 100}%
          </text>
        {/if}
      {/each}
    </svg>

    {#if viewport.isZoomed}
      <button class="reset" onclick={() => viewport.reset()}>reset zoom</button>
    {/if}
  </div>

  {#if openAnnotation !== null && trace.annotations[openAnnotation]}
    {@const a = trace.annotations[openAnnotation]}
    <figcaption class="note">
      <span class="note-n">{openAnnotation + 1}</span>
      <span class="note-body">
        <span class="note-kind mono">{a.kind.replace(/_/g, ' ')}</span>
        {a.text}
      </span>
    </figcaption>
  {:else if selectedRow}
    {@const meta = metaFor(CARRY_SCHEME, selectedRow.category)}
    <figcaption class="note">
      <span class="note-swatch" style:background={meta.color}></span>
      <span class="note-body">
        <span class="note-kind mono">{meta.label} · segment {selectedRow.index}</span>
        {selectedRow.text}
      </span>
    </figcaption>
  {/if}
</figure>

{#if tooltip}
  <div class="tip" style:left="{tooltip.x}px" style:top="{tooltip.y}px" role="tooltip">
    <span class="tip-head">
      <span class="tip-swatch" style:background={metaFor(CARRY_SCHEME, tooltip.row.category).color}
      ></span>
      {metaFor(CARRY_SCHEME, tooltip.row.category).label}
      <span class="tip-step mono">
        {tooltip.row.container ? 'span' : `segment ${tooltip.row.index}`}
      </span>
    </span>
    <span class="tip-text">{tooltip.row.text.slice(0, 150)}{tooltip.row.text.length > 150 ? '…' : ''}</span>
  </div>
{/if}

<style>
  .panel {
    margin: 0 0 var(--space-lg);
    padding: 0;
  }

  header {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 6px 10px;
    margin-bottom: 8px;
  }
  .badge {
    font-family: var(--font-sans);
    font-size: var(--text-xs);
    font-weight: 600;
    letter-spacing: 0.02em;
    padding: 2px 8px;
    border-radius: var(--radius-sm);
    border: 1px solid;
  }
  .badge[data-tone='ok'] { color: #2d7d6a; border-color: #2d7d6a55; background: #2d7d6a12; }
  .badge[data-tone='err'] { color: #bf4536; border-color: #bf453655; background: #bf453612; }
  .badge[data-tone='wait'] { color: #b07a1e; border-color: #b07a1e55; background: #b07a1e12; }

  .blurb {
    font-size: var(--text-sm);
    color: var(--ink-dim);
    flex: 1 1 12rem;
  }
  .stats {
    font-size: 0.68rem;
    color: var(--ink-faint);
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }

  .chart { position: relative; }

  .marks { position: relative; }
  .mark {
    position: absolute;
    top: 0;
    transform: translateX(-50%);
    width: 16px;
    height: 16px;
    padding: 0;
    border-radius: 50%;
    border: 1px solid var(--line);
    background: var(--paper);
    color: var(--ink-dim);
    font-family: var(--font-mono);
    font-size: 9.5px;
    font-weight: 600;
    line-height: 14px;
    cursor: pointer;
    transition: background 130ms ease, color 130ms ease, border-color 130ms ease;
  }
  .mark:hover { border-color: var(--ink-dim); color: var(--ink); }
  .mark.is-open {
    background: var(--ink);
    color: #fff;
    border-color: var(--ink);
  }
  /* a hairline from the marker down to the bar it names */
  .mark::after {
    content: '';
    position: absolute;
    left: calc(50% + var(--lean, 0px) / 2);
    top: 100%;
    width: 1px;
    height: 3px;
    background: var(--line);
  }

  .axis { display: block; }
  .axis line { stroke: var(--line); stroke-width: 1; }
  .axis text {
    font-family: var(--font-mono);
    font-size: 9px;
    fill: var(--ink-faint);
  }

  .reset {
    position: absolute;
    top: 20px;
    right: 0;
    font-family: var(--font-mono);
    font-size: 9px;
    padding: 2px 6px;
    border: 1px solid var(--line);
    border-radius: var(--radius-sm);
    background: var(--paper);
    color: var(--ink-dim);
    cursor: pointer;
  }

  .note {
    display: flex;
    gap: 8px;
    margin-top: 8px;
    padding: 8px 10px;
    border-left: 2px solid var(--line);
    background: var(--panel);
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    font-size: var(--text-sm);
    line-height: 1.5;
    color: var(--ink-dim);
  }
  .note-n {
    flex: 0 0 auto;
    width: 15px;
    height: 15px;
    margin-top: 2px;
    border-radius: 50%;
    background: var(--ink);
    color: var(--paper);
    font-family: var(--font-mono);
    font-size: 8.5px;
    line-height: 15px;
    text-align: center;
  }
  .note-swatch {
    flex: 0 0 auto;
    width: 3px;
    align-self: stretch;
    border-radius: 1px;
  }
  .note-kind {
    display: block;
    font-size: 0.66rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--ink-faint);
    margin-bottom: 1px;
  }

  .tip {
    position: fixed;
    z-index: 40;
    max-width: 300px;
    padding: 7px 9px;
    background: var(--ink);
    color: var(--paper);
    border-radius: var(--radius-sm);
    font-size: var(--text-xs);
    line-height: 1.45;
    pointer-events: none;
  }
  .tip-head { display: flex; align-items: center; gap: 5px; margin-bottom: 3px; font-weight: 600; }
  .tip-swatch { width: 7px; height: 7px; border-radius: 1px; }
  .tip-step { opacity: 0.6; font-size: 0.64rem; margin-left: auto; }
  .tip-text { opacity: 0.85; }

  @media (max-width: 620px) {
    .stats { flex-basis: 100%; }
    .blurb { flex-basis: 100%; }
  }
</style>
