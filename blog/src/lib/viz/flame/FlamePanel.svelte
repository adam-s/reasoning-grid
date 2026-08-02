<script lang="ts">
  /**
   * FlamePanel — reusable interactive flame-chart experience for a single
   * annotated thinking trace. Bundles: header pills, category legend,
   * zoomable flame view with labels + tooltip, X-axis with tick labels,
   * minimap brush for quick navigation, and an inspector panel that pins
   * the clicked step's full text.
   *
   * Extracted from the thinking-traces Figure so multiple sections can
   * render independently-controlled flame panels (e.g. the pass/fail pair
   * in ThinkingOps) without duplicating state.
   */
  import { scaleLinear } from 'd3-scale';
  import { MediaQuery } from 'svelte/reactivity';
  import FlameGraph from './FlameGraph.svelte';
  import CategoryLegend from './CategoryLegend.svelte';
  import MinimapBrush from './MinimapBrush.svelte';
  import { ChartViewport } from './ChartViewport.svelte';
  import type { Snippet } from 'svelte';
  import type { AnyFlameRow, AnyTrace, CategoryScheme } from '../../design/scheme';
  import { LAMBDA_SCHEME, metaFor } from '../../design/scheme';

  // Rows are typed structurally so this panel and FlameGraph agree. The
  // literal-union Category stayed out: the chart needs a colour for whatever
  // string it is handed, and a missing one is a data bug, not a type error.
  type FlameRow = AnyFlameRow;

  // Touch devices synthesize mouseenter on tap but never fire a matching
  // mouseleave, so the floating tooltip would stick. On no-hover primary
  // inputs, skip the tooltip entirely — the inspector panel below pins the
  // tapped segment with its full text, which is the canonical mobile view.
  const canHover = new MediaQuery('(hover: hover)');

  type Outcome = { label: string; tone: 'ok' | 'err' | 'neutral' };

  /** A moment worth calling out, pinned to the segment where it happens. */
  export type PanelAnnotation = { segment: number; kind: string; text: string };

  type Props = {
    trace: AnyTrace & { stepCount?: number; model?: string; algorithmId?: string;
                        detail?: string; elapsedSeconds?: number; outputTokens?: number };
    /** Optional override: replaces the default "{algorithm} · {detail}" title suffix. */
    titleOverride?: string | null;
    /** Optional right-aligned outcome badge (e.g. "passed · 8,962"). */
    outcome?: Outcome | null;
    /** Show the legend inside this panel. Turn off if a shared legend is used above. */
    showLegend?: boolean;
    /** Segment index to pre-highlight (renders as `selectedIndex` on first mount). */
    initialSelectedIndex?: number | null;
    /** Segment index to mark persistently as the root error (red outline + caret). */
    errorIndex?: number | null;
    /** Cap on the flame scroll height (px). Shallow traces will auto-shrink below this. */
    maxChartHeight?: number;
    /** External override of selectedIndex; when non-null, overrides internal selection. */
    forceSelectedIndex?: number | null;

    /* --- below: added for carrychain. Every one defaults to the λ behaviour, so
       the reference figure renders exactly as it did before. --- */

    /** Which categories colour this panel. */
    scheme?: CategoryScheme;
    /** Replaces the default header entirely. The λ header is model-specific
     *  (model badge, algorithm id, wall-clock) and does not fit every trace. */
    header?: Snippet;
    /** Formats an x-axis tick. λ shows raw offsets; a trace whose axis is a
     *  share of itself wants "50%". */
    formatTick?: (v: number) => string;
    /** Chooses tick positions for the visible domain. Needed when the labels are
     *  a transform of the axis: d3 picks round numbers in CHARACTERS, and those
     *  become 11%, 22%, 33% once converted. Returning round numbers in the
     *  displayed unit instead is the caller's job, because only the caller knows
     *  what the unit is. */
    tickValues?: (domain: readonly [number, number]) => number[];
    /** Numbered markers above the flame. Clicking one pins its note. */
    annotations?: readonly PanelAnnotation[];
    /** Which annotation is open on first mount. */
    initialAnnotation?: number | null;
    /** The minimap is worth its 64px on a long trace and repeats the chart on a
     *  short one. */
    showMinimap?: boolean;
    /** Controlled category filter. Omit and the panel keeps its own, which is
     *  what a lone panel wants; pass it when several panels share one legend so
     *  hiding a category hides it in all of them at once. */
    hiddenCategories?: ReadonlySet<string>;
    onToggleCategory?: (category: string) => void;
  };

  let {
    trace,
    titleOverride = null,
    outcome = null,
    showLegend = true,
    initialSelectedIndex = null,
    errorIndex = null,
    maxChartHeight = 360,
    forceSelectedIndex = null,
    scheme = LAMBDA_SCHEME,
    header = undefined,
    formatTick = undefined,
    tickValues = undefined,
    annotations = [],
    initialAnnotation = null,
    showMinimap = true,
    hiddenCategories: hiddenProp = undefined,
    onToggleCategory = undefined,
  }: Props = $props();

  // svelte-ignore state_referenced_locally
  let openAnnotation: number | null = $state(initialAnnotation);

  const stepCount = $derived(trace.stepCount ?? trace.rows.length);

  let hoveredIndex: number | null = $state(null);
  let selectedIndex: number | null = $state(initialSelectedIndex);
  let ownHidden: Set<string> = $state(new Set());
  const hiddenCategories = $derived(hiddenProp ?? ownHidden);

  type TooltipState = { x: number; y: number; row: FlameRow } | null;
  let tooltip: TooltipState = $state(null);

  let containerEl: HTMLDivElement | null = $state(null);
  let containerWidth = $state(840);
  const MINIMAP_HEIGHT = 64;
  const VIEWPORT_HEIGHT = 420;

  const totalSpan = $derived(
    trace.rows.reduce((acc, r) => Math.max(acc, r.start + r.width), 0),
  );

  // Adaptive flame-scroll height: computed from the trace's actual depth so
  // shallow traces (e.g. a 5-level modexp trace) don't reserve the full
  // 360px deep-trace budget. FlameGraph uses rows of up to 22px + axis 22px
  // + ~16px padding; clamp to maxChartHeight for deep traces that need
  // scrolling.
  const MAX_ROW_HEIGHT = 22;
  const CHART_PAD = 24;
  const MIN_CHART_HEIGHT = 96;
  const totalMaxDepth = $derived(
    trace.rows.reduce((acc, r) => Math.max(acc, r.depth), 0),
  );
  const idealChartHeight = $derived(
    (totalMaxDepth + 1) * MAX_ROW_HEIGHT + CHART_PAD,
  );
  const chartScrollHeight = $derived(
    Math.max(MIN_CHART_HEIGHT, Math.min(maxChartHeight, idealChartHeight)),
  );

  const viewport = new ChartViewport(840, VIEWPORT_HEIGHT);

  $effect(() => {
    if (totalSpan > 0 && viewport.max !== totalSpan) {
      viewport.setBounds(0, totalSpan);
    }
  });

  $effect(() => {
    if (!containerEl) return;
    const ro = new ResizeObserver((entries) => {
      const cr = entries[0]?.contentRect;
      if (cr) {
        containerWidth = Math.max(280, Math.floor(cr.width));
        viewport.updateViewportWidth(containerWidth);
      }
    });
    ro.observe(containerEl);
    return () => ro.disconnect();
  });

  const chartWidth = $derived(containerWidth);

  let programmaticScroll = false;
  $effect(() => {
    if (containerEl) {
      programmaticScroll = true;
      containerEl.scrollTop = viewport.scrollY;
      requestAnimationFrame(() => { programmaticScroll = false; });
    }
  });
  $effect(() => {
    if (!containerEl) return;
    const el = containerEl;
    const handler = () => {
      if (programmaticScroll) return;
      viewport.scrollY = el.scrollTop;
    };
    el.addEventListener('scroll', handler, { passive: true });
    return () => el.removeEventListener('scroll', handler);
  });

  const axisScale = $derived(
    scaleLinear().domain([...viewport.domain]).range([0, chartWidth]),
  );
  const axisTicks = $derived(
    tickValues ? tickValues(viewport.domain) : axisScale.ticks(6),
  );

  // Leaves carry the segment indices annotations point at. A container row
  // shares an index with the first segment it spans, so match on the un-muted
  // row first and only fall back if there is none.
  function rowForSegment(seg: number): FlameRow | undefined {
    return trace.rows.find((r) => r.index === seg && !r.muted)
        ?? trace.rows.find((r) => r.index === seg);
  }

  // Annotations can land within a few characters of each other -- one trace has
  // four inside a tenth of its length -- and overlapping circles hide their own
  // numbers. Push each right until it clears the last.
  const MARK_W = 17;
  const placedMarks = $derived.by(() => {
    let last = -Infinity;
    return annotations
      .map((a, i) => ({ a, i, at: axisScale(rowForSegment(a.segment)?.start ?? 0) }))
      .sort((x, y) => x.at - y.at)
      .map((m) => {
        const x = Math.max(m.at, last + MARK_W);
        last = x;
        return { ...m, x };
      });
  });

  function openMark(i: number): void {
    openAnnotation = openAnnotation === i ? null : i;
    const seg = annotations[i]?.segment;
    const row = seg === undefined ? undefined : rowForSegment(seg);
    selectedIndex = row ? trace.rows.indexOf(row) : null;
  }

  const TOOLTIP_W_EST = 320;
  const TOOLTIP_H_EST = 96;

  function handleHover(
    i: number | null,
    row: FlameRow | null,
    ev: MouseEvent | null,
  ): void {
    if (i === null || row === null || ev === null) {
      hoveredIndex = null;
      tooltip = null;
      return;
    }
    hoveredIndex = i;
    if (!canHover.current) {
      // Touch tap fires a synthesized mouseenter with no follow-up mouseleave;
      // suppress the floating tooltip and let the inspector below carry it.
      tooltip = null;
      return;
    }
    let x = ev.clientX + 14;
    let y = ev.clientY + 14;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    if (x + TOOLTIP_W_EST > vw) x = ev.clientX - TOOLTIP_W_EST - 14;
    if (y + TOOLTIP_H_EST > vh) y = ev.clientY - TOOLTIP_H_EST - 14;
    x = Math.max(4, Math.min(vw - TOOLTIP_W_EST - 4, x));
    y = Math.max(4, Math.min(vh - TOOLTIP_H_EST - 4, y));
    tooltip = { x, y, row };
  }

  // Safety net: if a tooltip is ever showing (e.g. on a hybrid mouse+touch
  // device where canHover is true but a finger tap also fires), dismiss it
  // on any pointerdown outside a flame-rect, or on scroll.
  $effect(() => {
    if (!tooltip) return;
    const onPointerDown = (ev: PointerEvent) => {
      const target = ev.target as Element | null;
      if (!target?.closest?.('.flame-rect')) {
        tooltip = null;
        hoveredIndex = null;
      }
    };
    const onScroll = () => {
      tooltip = null;
      hoveredIndex = null;
    };
    window.addEventListener('pointerdown', onPointerDown, { capture: true });
    window.addEventListener('scroll', onScroll, { capture: true, passive: true });
    return () => {
      window.removeEventListener('pointerdown', onPointerDown, { capture: true });
      window.removeEventListener('scroll', onScroll, { capture: true });
    };
  });

  function handleClick(i: number, row: FlameRow): void {
    if (selectedIndex === i) {
      selectedIndex = null;
      return;
    }
    selectedIndex = i;
    if (!viewport.isZoomed) {
      const pad = Math.max(row.width * 0.15, totalSpan * 0.01);
      viewport.setDomain(
        Math.max(0, row.start - pad),
        Math.min(totalSpan, row.start + row.width + pad),
      );
    }
  }

  function resetAll(): void {
    viewport.reset();
    selectedIndex = null;
  }

  function toggleCategory(cat: string): void {
    if (onToggleCategory) {
      onToggleCategory(cat);
      return;
    }
    const next = new Set(ownHidden);
    if (next.has(cat)) next.delete(cat);
    else next.add(cat);
    ownHidden = next;
  }

  const effectiveSelectedIndex = $derived(
    forceSelectedIndex !== null ? forceSelectedIndex : selectedIndex,
  );
  const selectedRow = $derived.by((): FlameRow | null => {
    if (effectiveSelectedIndex === null) return null;
    return trace.rows[effectiveSelectedIndex] ?? null;
  });

  function excerpt(text: string, n: number): string {
    if (text.length <= n) return text;
    return text.slice(0, n).trimEnd() + '\u2026';
  }

  function formatDuration(seconds: number): string {
    const s = Math.round(seconds);
    if (s < 60) return `${s}s`;
    const m = Math.floor(s / 60);
    const rem = s % 60;
    return `${m}m ${rem.toString().padStart(2, '0')}s`;
  }

  function formatTokens(n: number): string {
    return n.toLocaleString('en-US');
  }

  const titleText = $derived(
    titleOverride ??
      `${(trace.algorithmId ?? '').replace(/-/g, ' ')} · ${trace.detail ?? ''}`,
  );
</script>

<div class="flame-panel">
  {#if header}
    {@render header()}
  {:else}
  <header class="figure-header">
    <div class="title-row">
      <span class="model-badge" data-model={trace.model}>{trace.model}</span>
      <span class="detail">{titleText}</span>
      {#if outcome}
        <span class="outcome-badge" data-tone={outcome.tone}>{outcome.label}</span>
      {/if}
    </div>
    <div class="meta-row">
      {#if trace.elapsedSeconds !== undefined}
        <span class="meta-pill">
          <span class="meta-pill-value">{formatDuration(trace.elapsedSeconds)}</span>
          <span class="meta-pill-label">thinking</span>
        </span>
      {/if}
      {#if trace.outputTokens !== undefined}
        <span class="meta-pill">
          <span class="meta-pill-value">{formatTokens(trace.outputTokens)}</span>
          <span class="meta-pill-label">output tokens</span>
        </span>
      {/if}
      <span class="meta-pill">
        <span class="meta-pill-value">{stepCount}</span>
        <span class="meta-pill-label">steps</span>
      </span>
      <span class="meta-pill">
        <span class="meta-pill-value">{trace.rows.length}</span>
        <span class="meta-pill-label">annotated rows</span>
      </span>
    </div>
  </header>
  {/if}

  {#if showLegend}
    <CategoryLegend {hiddenCategories} onToggle={toggleCategory} rows={trace.rows} {scheme} />
  {/if}

  {#if placedMarks.length}
    <div class="marks">
      {#each placedMarks as m (m.i)}
        <button
          type="button"
          class="mark"
          class:is-open={openAnnotation === m.i}
          style:left="{m.x}px"
          onclick={() => openMark(m.i)}
          aria-expanded={openAnnotation === m.i}
          aria-label="{m.a.kind.replace(/_/g, ' ')}"
        >{m.i + 1}</button>
      {/each}
    </div>
  {/if}

  <div class="chart-toolbar">
    <div class="toolbar-left">
      {#if viewport.isZoomed}
        <span class="zoom-badge">
          zoomed
          <span class="zoom-range">
            {Math.round(viewport.positionX).toLocaleString()}
            –
            {Math.round(viewport.positionX + viewport.realView).toLocaleString()}
          </span>
        </span>
      {:else}
        <span class="zoom-hint">Click any block to zoom in</span>
      {/if}
    </div>
    <button
      type="button"
      class="reset-btn"
      onclick={resetAll}
      disabled={!viewport.isZoomed && selectedIndex === null}
      aria-label="Reset zoom and selection"
    >
      Reset
    </button>
  </div>

  <div
    class="flame-scroll"
    bind:this={containerEl}
    style:height="{chartScrollHeight}px"
  >
    <FlameGraph
      {trace}
      {scheme}
      {hiddenCategories}
      selectedIndex={effectiveSelectedIndex}
      {hoveredIndex}
      {errorIndex}
      width={chartWidth}
      {viewport}
      onHover={handleHover}
      onClick={handleClick}
      enableZoom={true}
      minRowHeight={17}
    />
  </div>

  <svg class="x-axis" viewBox="0 0 {chartWidth} 22" width={chartWidth} height={22}>
    <line class="axis-line" x1={0} x2={chartWidth} y1={0} y2={0} />
    {#each axisTicks as t, i (t)}
      {@const x = axisScale(t)}
      <g transform="translate({x}, 0)">
        <line class="tick" y1={0} y2={4} />
        <text
          class="tick-label"
          y={14}
          text-anchor={x < 12 ? 'start' : x > chartWidth - 12 ? 'end' : 'middle'}
          >{formatTick ? formatTick(t) : Math.round(t).toLocaleString()}</text>
      </g>
    {/each}
  </svg>

  {#if tooltip}
    <div
      class="tooltip"
      style:left="{tooltip.x}px"
      style:top="{tooltip.y}px"
      role="tooltip"
    >
      <div class="tooltip-label">
        <span
          class="tooltip-swatch"
          style:background={metaFor(scheme, tooltip.row.category).color}
          aria-hidden="true"
        ></span>
        {metaFor(scheme, tooltip.row.category).label}
        <span class="tooltip-step">{tooltip.row.index < stepCount ? `· step ${tooltip.row.index}` : '· span'}</span>
      </div>
      <div class="tooltip-text">{excerpt(tooltip.row.text, 140)}</div>
    </div>
  {/if}

  {#if showMinimap}
  <div class="minimap" aria-label="Trace overview minimap — drag to select a zoom window">
    <div class="minimap-chart" style:height="{MINIMAP_HEIGHT}px">
      <FlameGraph
        {trace}
        {scheme}
        {hiddenCategories}
        selectedIndex={null}
        hoveredIndex={null}
        {errorIndex}
        width={chartWidth}
        zoomDomain={null}
        onHover={() => {}}
        onClick={() => {}}
        showLabels={false}
        showAxis={false}
        showCursorGuide={false}
        interactive={false}
        minRowHeight={1}
        targetHeight={MINIMAP_HEIGHT}
      />
    </div>
    <MinimapBrush
      {viewport}
      width={chartWidth}
      height={MINIMAP_HEIGHT}
    />
  </div>
  {/if}

  <div class="inspector" aria-live="polite">
    {#if openAnnotation !== null && annotations[openAnnotation]}
      {@const a = annotations[openAnnotation]}
      <div class="inspector-note">
        <span class="note-n">{openAnnotation + 1}</span>
        <span>
          <span class="note-kind">{a.kind.replace(/_/g, ' ')}</span>
          {a.text}
        </span>
      </div>
    {/if}
    {#if selectedRow}
      {@const meta = metaFor(scheme, selectedRow.category)}
      <div class="inspector-header">
        <span class="inspector-swatch" style:background={meta.color}></span>
        <span class="inspector-label">{meta.label}</span>
        <span class="inspector-step">
          {selectedRow.index < stepCount ? `step ${selectedRow.index} / ${stepCount - 1}` : 'span'}
        </span>
        <button
          type="button"
          class="inspector-close"
          onclick={() => (selectedIndex = null)}
          aria-label="Clear selection"
        >
          ×
        </button>
      </div>
      <div class="inspector-description">{meta.description}</div>
      <blockquote class="inspector-text">{selectedRow.text}</blockquote>
    {:else if openAnnotation === null}
      <div class="inspector-empty">
        Click any block above to pin it here and read the full thinking text.
      </div>
    {/if}
  </div>
</div>

<style>
  .flame-panel {
    display: flex;
    flex-direction: column;
    gap: var(--space-md);
    width: 100%;
    min-width: 0;
    max-width: 100%;
    padding: var(--space-lg) var(--space-xl);
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    overflow: hidden;
  }

  .figure-header {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding-bottom: var(--space-sm);
    border-bottom: 1px solid var(--border);
  }

  .title-row {
    display: flex;
    align-items: baseline;
    gap: var(--space-sm);
    font-family: var(--font-serif);
    font-size: var(--text-lg);
    color: var(--ink);
    flex-wrap: wrap;
  }

  .model-badge {
    display: inline-block;
    padding: 2px 8px;
    font-family: var(--font-sans);
    font-size: var(--text-xs);
    font-weight: var(--weight-medium);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--bg);
    background: var(--ink);
    border-radius: var(--radius-sm);
  }
  .model-badge[data-model='opus'] { background: #1f3a5f; }
  .model-badge[data-model='sonnet'] { background: #2f7a6b; }
  .model-badge[data-model='haiku'] { background: #6c757d; }

  .detail {
    font-family: var(--font-serif);
    font-size: var(--text-base);
    color: var(--ink-muted);
  }

  .outcome-badge {
    margin-left: auto;
    padding: 3px 10px;
    font-family: var(--font-sans);
    font-size: var(--text-xs);
    font-weight: var(--weight-medium);
    border-radius: var(--radius-sm);
  }
  .outcome-badge[data-tone='ok'] {
    background: rgba(47, 168, 90, 0.12);
    color: #1d7a40;
  }
  .outcome-badge[data-tone='err'] {
    background: rgba(217, 76, 76, 0.12);
    color: #9a2d2d;
  }
  .outcome-badge[data-tone='neutral'] {
    background: var(--surface);
    color: var(--ink-muted);
  }

  .meta-row {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-sm);
    font-family: var(--font-sans);
    font-variant-numeric: tabular-nums;
    margin-top: 2px;
  }

  .meta-pill {
    display: inline-flex;
    align-items: baseline;
    gap: 6px;
    padding: 4px 10px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
  }

  .meta-pill-value {
    font-family: var(--font-mono);
    font-size: var(--text-sm);
    font-weight: var(--weight-medium);
    color: var(--ink);
  }

  .meta-pill-label {
    font-size: var(--text-xs);
    color: var(--ink-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .chart-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-md);
    padding: 6px 0;
    min-height: 28px;
    font-family: var(--font-sans);
    font-size: var(--text-xs);
  }

  .toolbar-left {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    color: var(--ink-muted);
    min-width: 0;
    flex: 1;
  }

  .zoom-hint { font-style: italic; }

  .zoom-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 8px;
    background: var(--surface);
    border: 1px solid var(--accent);
    border-radius: var(--radius-sm);
    color: var(--accent);
    font-weight: var(--weight-medium);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .zoom-range {
    font-family: var(--font-mono);
    color: var(--ink);
    font-weight: normal;
    text-transform: none;
    letter-spacing: 0;
    font-variant-numeric: tabular-nums;
  }

  .reset-btn {
    padding: 4px 12px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    font-family: var(--font-sans);
    font-size: var(--text-xs);
    color: var(--ink);
    cursor: pointer;
    transition:
      border-color 150ms ease,
      background 150ms ease;
  }

  .reset-btn:hover:not(:disabled) {
    border-color: var(--accent);
    color: var(--accent);
  }

  .reset-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .flame-scroll {
    position: relative;
    width: 100%;
    min-width: 0;
    max-width: 100%;
    /* height is set inline from FlamePanel's chartScrollHeight derived */
    overflow-x: hidden;
    overflow-y: scroll;
    overscroll-behavior: contain;
    padding: var(--space-sm) 0;
    scrollbar-width: none;
  }

  .flame-scroll::-webkit-scrollbar { display: none; }

  .x-axis {
    display: block;
    width: 100%;
    flex-shrink: 0;
  }
  .x-axis .axis-line { stroke: var(--border); stroke-width: 1; }
  .x-axis .tick { stroke: var(--ink-muted); stroke-width: 1; }
  .x-axis .tick-label {
    font-family: var(--font-mono);
    font-size: 10px;
    fill: var(--ink-muted);
    font-variant-numeric: tabular-nums;
  }

  .minimap {
    position: relative;
    width: 100%;
    min-width: 0;
    max-width: 100%;
    overflow: hidden;
    padding: 4px 0;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
  }
  .minimap-chart { overflow: hidden; }
  .minimap-chart :global(svg) { width: 100%; height: 100% !important; }

  .tooltip {
    position: fixed;
    z-index: 50;
    max-width: 320px;
    padding: var(--space-sm) var(--space-md);
    background: var(--ink);
    color: var(--bg);
    font-family: var(--font-sans);
    font-size: var(--text-xs);
    line-height: var(--leading-snug);
    border-radius: var(--radius-sm);
    box-shadow: 0 4px 16px -4px rgba(0, 0, 0, 0.25);
    pointer-events: none;
  }
  .tooltip-label {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 4px;
    font-weight: var(--weight-medium);
  }
  .tooltip-swatch {
    width: 10px;
    height: 10px;
    border-radius: 2px;
  }
  .tooltip-step {
    opacity: 0.7;
    font-weight: normal;
  }
  .tooltip-text {
    font-family: var(--font-serif);
    font-style: italic;
    color: rgba(253, 252, 249, 0.85);
  }

  .inspector {
    padding: var(--space-md);
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    min-height: 96px;
  }
  .inspector-header {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    margin-bottom: var(--space-xs);
  }
  .inspector-swatch {
    width: 12px;
    height: 12px;
    border-radius: 2px;
    flex-shrink: 0;
  }
  .inspector-label {
    font-family: var(--font-sans);
    font-size: var(--text-sm);
    font-weight: var(--weight-medium);
    color: var(--ink);
  }
  .inspector-step {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: var(--ink-subtle);
    font-variant-numeric: tabular-nums;
    margin-left: auto;
  }
  .inspector-close {
    background: transparent;
    border: none;
    color: var(--ink-muted);
    cursor: pointer;
    font-size: var(--text-lg);
    line-height: 1;
    padding: 0 4px;
    margin-left: 4px;
  }
  .inspector-close:hover { color: var(--ink); }
  .inspector-description {
    font-family: var(--font-sans);
    font-size: var(--text-xs);
    color: var(--ink-muted);
    margin-bottom: var(--space-sm);
    line-height: var(--leading-snug);
  }
  .inspector-text {
    margin: 0;
    padding: var(--space-sm) var(--space-md);
    border-left: 2px solid var(--accent);
    background: var(--bg);
    font-family: var(--font-serif);
    font-size: var(--text-sm);
    line-height: var(--leading-relaxed);
    color: var(--ink);
    white-space: pre-wrap;
    max-height: 120px;
    overflow-y: auto;
  }
  /* annotation markers */
  .marks { position: relative; height: 18px; }
  .mark {
    position: absolute;
    top: 0;
    transform: translateX(-50%);
    width: 16px;
    height: 16px;
    padding: 0;
    border-radius: 50%;
    border: 1px solid var(--line);
    background: var(--bg);
    color: var(--ink-dim);
    font-family: var(--font-mono);
    font-size: 9.5px;
    font-weight: 600;
    line-height: 14px;
    cursor: pointer;
    transition: background 130ms ease, color 130ms ease, border-color 130ms ease;
  }
  .mark:hover { border-color: var(--ink-dim); color: var(--ink); }
  .mark.is-open { background: var(--ink); color: #fff; border-color: var(--ink); }
  .mark::after {
    content: '';
    position: absolute;
    left: 50%;
    top: 100%;
    width: 1px;
    height: 3px;
    background: var(--line);
  }

  .inspector-note {
    display: flex;
    gap: 8px;
    margin-bottom: 8px;
    font-size: var(--text-sm);
    line-height: 1.5;
    color: var(--ink-dim);
  }
  .note-n {
    flex: 0 0 auto;
    width: 16px;
    height: 16px;
    margin-top: 2px;
    border-radius: 50%;
    background: var(--ink);
    color: var(--bg);
    font-family: var(--font-mono);
    font-size: 9.5px;
    line-height: 16px;
    text-align: center;
  }
  .note-kind {
    display: block;
    font-family: var(--font-mono);
    font-size: 0.66rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--ink-faint);
    margin-bottom: 1px;
  }

  .inspector-empty {
    font-family: var(--font-serif);
    font-style: italic;
    font-size: var(--text-sm);
    color: var(--ink-subtle);
    padding: var(--space-md) 0;
    text-align: center;
  }

  @media (max-width: 720px) {
    .flame-panel {
      padding: var(--space-md);
    }
    .title-row {
      font-size: var(--text-base);
    }
  }
</style>
