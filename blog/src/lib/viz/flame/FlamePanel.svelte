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
   *
   * `scheme` and `header` are both REQUIRED, and neither used to be. Both
   * defaulted to what the λ-bench reference figure wanted — λ's nine categories,
   * and a header built from a model badge, an algorithm id and a wall-clock.
   * That figure is gone. A default scheme would have coloured a reasoning-grid trace
   * with the wrong nine labels instead of failing, and the default header would
   * have rendered an empty badge from fields reasoning-grid traces do not carry.
   */
  import { scaleLinear } from 'd3-scale';
  import { MediaQuery } from 'svelte/reactivity';
  import FlameGraph from './FlameGraph.svelte';
  import CategoryLegend from './CategoryLegend.svelte';
  import MinimapBrush from './MinimapBrush.svelte';
  import { ChartViewport } from './ChartViewport.svelte';
  import { observeWidth } from '../observeWidth.svelte';
  import type { Snippet } from 'svelte';
  import type { AnyFlameRow, AnyTrace, CategoryScheme } from '../../design/scheme';
  import { metaFor } from '../../design/scheme';

  // Rows are typed structurally so this panel and FlameGraph agree. The
  // literal-union Category stayed out: the chart needs a colour for whatever
  // string it is handed, and a missing one is a data bug, not a type error.
  type FlameRow = AnyFlameRow;

  // Touch devices synthesize mouseenter on tap but never fire a matching
  // mouseleave, so the floating tooltip would stick. On no-hover primary
  // inputs, skip the tooltip entirely — the inspector panel below pins the
  // tapped segment with its full text, which is the canonical mobile view.
  const canHover = new MediaQuery('(hover: hover)');

  type Props = {
    trace: AnyTrace & { stepCount?: number };
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

    /** Which categories colour this panel. */
    scheme: CategoryScheme;
    /** The panel's header. Every trace names itself differently, so the panel
     *  does not try to. */
    header: Snippet;
    /** Formats an x-axis tick. The default is the raw offset; a trace whose axis
     *  is a share of itself wants "50%". */
    formatTick?: (v: number) => string;
    /** Chooses tick positions for the visible domain. Needed when the labels are
     *  a transform of the axis: d3 picks round numbers in CHARACTERS, and those
     *  become 11%, 22%, 33% once converted. Returning round numbers in the
     *  displayed unit instead is the caller's job, because only the caller knows
     *  what the unit is. */
    tickValues?: (domain: readonly [number, number]) => number[];
    /** The minimap is worth its 64px on a long trace and repeats the chart on a
     *  short one. */
    showMinimap?: boolean;
    /** Reserve the inspector and its "click a block" hint when nothing is
     *  selected. One panel wants it. Three stacked panels turn it into three
     *  identical empty boxes, and the hint only needs saying once. */
    showInspectorHint?: boolean;
    /** Keep the zoom hint and Reset visible when there is nothing to reset.
     *  With several panels stacked it is the same sentence three times beside a
     *  disabled button; off, the row appears exactly when it does something. */
    showZoomHint?: boolean;
    /** Controlled category filter. Omit and the panel keeps its own, which is
     *  what a lone panel wants; pass it when several panels share one legend so
     *  hiding a category hides it in all of them at once. */
    /** Passed to the graph: how far the run has reached, in character offsets.
     *  null keeps the panel static. */
    playhead?: number | null;
    dimAhead?: boolean;
    /** Render the inspector panel under the chart. Off when the caller shows
     *  the selected text somewhere better. */
    showInspector?: boolean;
    /** Fired on every block click, before the panel zooms. */
    onSelect?: (index: number, row: FlameRow) => void;
    /** Highlighted in the legend: the category at the playhead. */
    activeCategory?: string | null;
  };

  let {
    trace,
    showLegend = true,
    initialSelectedIndex = null,
    errorIndex = null,
    maxChartHeight = 360,
    forceSelectedIndex = null,
    scheme,
    header,
    formatTick = undefined,
    tickValues = undefined,
    showMinimap = true,
    showInspectorHint = true,
    showZoomHint = true,
    playhead = null,
    dimAhead = false,
    activeCategory = null,
    showInspector = true,
    onSelect = undefined,
  }: Props = $props();

  const stepCount = $derived(trace.stepCount ?? trace.rows.length);

  let hoveredIndex: number | null = $state(null);
  // svelte-ignore state_referenced_locally
  // Initial value only, by design -- the panel owns the selection after mount.
  let selectedIndex: number | null = $state(initialSelectedIndex);

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

  observeWidth(() => containerEl, (width) => {
    // The 280 floor stops the flame collapsing into a smear, and below a 280px
    // container it wins -- which on a 320px phone drew a 280px chart inside a
    // 270px box, 10px of it off the edge with nothing to scroll. `.flame-scroll`
    // holds the overflow so the floor can stay.
    containerWidth = Math.max(280, Math.floor(width));
    viewport.updateViewportWidth(containerWidth);
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
    // The caller hears about every click, including the one that clears a
    // selection, and decides for itself whether to act. Zooming is a VIEW
    // change and stays unconditional; anything the caller does with the click
    // is its own business.
    onSelect?.(i, row);
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

</script>

<div class="flame-panel">
  {@render header()}

  {#if showLegend}
    <CategoryLegend rows={trace.rows} {scheme} active={activeCategory} />
  {/if}


  {#if showZoomHint || viewport.isZoomed || selectedIndex !== null}
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
  {/if}

  <div
    class="flame-scroll"
    bind:this={containerEl}
    style:height="{chartScrollHeight}px"
  >
    <FlameGraph
      {trace}
      {scheme}
      selectedIndex={effectiveSelectedIndex}
      {hoveredIndex}
      {errorIndex}
      width={chartWidth}
      {viewport}
      onHover={handleHover}
      onClick={handleClick}
      enableZoom={true}
      minRowHeight={17}
      {playhead}
      {dimAhead}
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

  {#if showInspector && (selectedRow || showInspectorHint)}
  <div class="inspector" aria-live="polite">
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
    {:else}
      <div class="inspector-empty">
        Click any block above to pin it here and read the full thinking text.
      </div>
    {/if}
  </div>
  {/if}
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
    /* `auto` rather than `hidden`, so the 280px floor on the chart width has
       somewhere to go on a 320px phone instead of hanging 10px off the edge
       where it can be neither seen nor reached. Above that container width the
       chart matches its box and no scrollbar appears at all. */
    overflow-x: auto;
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
  }
</style>
