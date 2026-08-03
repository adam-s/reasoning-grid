<script lang="ts">
  /**
   * FlameGraph — flat flame chart for annotated thinking traces.
   *
   * d3 for math, Svelte for DOM. Uses a ChartViewport class for
   * unified 2-axis pan/zoom state when provided.
   */
  import { scaleLinear } from 'd3-scale';
  import type { AnyFlameRow, AnyTrace, CategoryScheme } from '../../design/scheme';
  import { LAMBDA_SCHEME, metaFor } from '../../design/scheme';
  import type { ChartViewport } from './ChartViewport.svelte';
  import { zoomable } from './zoomable.svelte';

  type FlameRow = AnyFlameRow;

  type Props = {
    trace: AnyTrace;
    /** Which categories colour this chart. Defaults to the λ set. */
    scheme?: CategoryScheme;
    selectedIndex: number | null;
    hoveredIndex: number | null;
    /** Optional index of a segment to persistently mark as the root error.
     *  Rendered with a red outline + caret above, independent of selection. */
    errorIndex?: number | null;
    onHover: (
      iterationIndex: number | null,
      row: FlameRow | null,
      event: MouseEvent | null,
    ) => void;
    onClick: (iterationIndex: number, row: FlameRow) => void;
    width: number;
    /** Optional zoom window (used when no viewport). */
    zoomDomain?: readonly [number, number] | null;
    /** Unified 2-axis viewport. When provided, zoomDomain is ignored. */
    viewport?: ChartViewport;
    /** When true, attach gesture handlers. */
    enableZoom?: boolean;
    showLabels?: boolean;
    showAxis?: boolean;
    showCursorGuide?: boolean;
    interactive?: boolean;
    minRowHeight?: number;
    targetHeight?: number;
    /** How far the run has reached, in trace coordinates (character offsets).
     *  null leaves the graph static, which is what every existing call does. */
    playhead?: number | null;
    /** Fade rows that start after the playhead. */
    dimAhead?: boolean;
  };

  let {
    trace,
    scheme = LAMBDA_SCHEME,
    selectedIndex,
    hoveredIndex,
    errorIndex = null,
    onHover,
    onClick,
    width,
    zoomDomain = null,
    viewport = undefined,
    enableZoom = false,
    showLabels = true,
    showAxis = true,
    showCursorGuide = true,
    interactive = true,
    minRowHeight = 7,
    targetHeight = 520,
    playhead = null,
    dimAhead = false,
  }: Props = $props();

  const MAX_ROW_HEIGHT = 22;
  const AXIS_HEIGHT = 22;
  const CHART_PAD_TOP = 4;

  const totalSpan = $derived(
    trace.rows.reduce((acc, r) => Math.max(acc, r.start + r.width), 0),
  );

  const effectiveDomain = $derived<readonly [number, number]>(
    viewport ? viewport.domain : (zoomDomain ?? [0, totalSpan || 1]),
  );

  // Total max depth across ALL rows (stable — doesn't change with zoom/pan).
  const totalMaxDepth = $derived(
    trace.rows.reduce((acc, r) => Math.max(acc, r.depth), 0),
  );

  const rowHeight = $derived(
    Math.max(
      minRowHeight,
      Math.min(
        MAX_ROW_HEIGHT,
        Math.floor(
          (targetHeight - (showAxis ? AXIS_HEIGHT : 0)) / (totalMaxDepth + 1),
        ),
      ),
    ),
  );

  const chartHeight = $derived((totalMaxDepth + 1) * rowHeight + CHART_PAD_TOP);
  const totalHeight = $derived(chartHeight);

  // Keep viewport's totalHeight in sync with our computed totalHeight.
  $effect(() => {
    if (viewport) {
      viewport.updateTotalHeight(totalHeight);
    }
  });

  const xScale = $derived(
    scaleLinear().domain([...effectiveDomain]).range([0, width]),
  );

  const ticks = $derived(xScale.ticks(6));

  let cursorX: number | null = $state(null);

  function rectX(row: FlameRow): number {
    return xScale(row.start);
  }
  function rectW(row: FlameRow): number {
    return Math.max(1, xScale(row.start + row.width) - xScale(row.start));
  }
  function rectY(row: FlameRow): number {
    return row.depth * rowHeight + CHART_PAD_TOP;
  }
  function rectH(): number {
    return Math.max(2, rowHeight - 1);
  }
  function fillFor(row: FlameRow): string {
    return metaFor(scheme, row.category).color;
  }
  function opacityFor(row: FlameRow): number {
    return row.muted ? 0.5 : 1;
  }
  function labelFor(row: FlameRow): string {
    const txt = row.text.replace(/\s+/g, ' ').trim();
    return txt || metaFor(scheme, row.category).label;
  }

  function fitChars(rectWidth: number, fontPx: number): number {
    const avgCharPx = fontPx * 0.55;
    const usable = rectWidth - 4;
    return Math.max(0, Math.floor(usable / avgCharPx));
  }

  function visibleLabel(row: FlameRow, rectWidth: number, fontPx: number): string {
    const max = fitChars(rectWidth, fontPx);
    if (max < 3) return '';
    const full = labelFor(row);
    if (full.length <= max) return full;
    return full.slice(0, max - 1) + '\u2026';
  }

  // Throttled hover: at most one onHover call per animation frame.
  let hoverRafId: number | null = null;
  let pendingHoverEvent: MouseEvent | null = null;
  let pendingHoverIndex: number | null = null;
  let pendingHoverRow: FlameRow | null = null;

  function scheduleHover(i: number | null, row: FlameRow | null, ev: MouseEvent | null): void {
    pendingHoverIndex = i;
    pendingHoverRow = row;
    pendingHoverEvent = ev;
    if (hoverRafId === null) {
      hoverRafId = requestAnimationFrame(() => {
        hoverRafId = null;
        onHover(pendingHoverIndex, pendingHoverRow, pendingHoverEvent);
      });
    }
  }

  function handleSvgMouseMove(ev: MouseEvent): void {
    if (!showCursorGuide) return;
    const target = ev.currentTarget as SVGSVGElement;
    const rect = target.getBoundingClientRect();
    cursorX = ((ev.clientX - rect.left) / rect.width) * width;
  }
  function handleSvgMouseLeave(): void {
    cursorX = null;
    if (hoverRafId !== null) {
      cancelAnimationFrame(hoverRafId);
      hoverRafId = null;
    }
    onHover(null, null, null);
  }

  const labelFontPx = $derived(Math.max(9, Math.min(13, rowHeight - 5)));
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<svg
  class="flame-svg"
  class:is-playing={playhead !== null}
  class:is-interactive={interactive}
  class:is-zoomable={enableZoom}
  viewBox="0 0 {width} {totalHeight}"
  width={width}
  height={totalHeight}
  role="img"
  aria-label="Flame graph of thinking trace {trace.name ?? ''}"
  onmousemove={handleSvgMouseMove}
  onmouseleave={handleSvgMouseLeave}
  use:zoomable={{
    viewport: viewport!,
    enabled: enableZoom && !!viewport,
  }}
>
  {#if showAxis}
    <g class="gridlines">
      {#each ticks as t (t)}
        <line
          x1={xScale(t)}
          x2={xScale(t)}
          y1={0}
          y2={chartHeight}
          class="gridline"
        />
      {/each}
    </g>
  {/if}

  {#each trace.rows as row, i (i)}
    {@const isHover = hoveredIndex === i}
    {@const isSelected = selectedIndex === i}
    {@const isError = errorIndex === i}
    {@const x = rectX(row)}
    {@const w = rectW(row)}
    {@const y = rectY(row)}
    {@const h = rectH()}
    {@const ahead = dimAhead && playhead !== null && row.start > playhead}
    {@const clipX = Math.max(0, x)}
    {@const clipW = Math.max(1, Math.min(width, x + w) - clipX)}
    {#if x + w >= 0 && x <= width}
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
      <rect
        class="flame-rect"
        class:is-hover={isHover}
        class:is-selected={isSelected}
        class:is-error={isError}
        x={clipX}
        y={y}
        width={clipW}
        height={h}
        fill={fillFor(row)}
        opacity={ahead ? opacityFor(row) * 0.2 : opacityFor(row)}
        rx="1.5"
        onmouseenter={(e) => scheduleHover(i, row, e)}
        onmousemove={(e) => scheduleHover(i, row, e)}
        onclick={(e) => {
          e.stopPropagation();
          onClick(i, row);
        }}
        role="button"
        tabindex="-1"
        aria-label="{metaFor(scheme, row.category).label} · step {row.index}{isError ? ' · root error' : ''}"
      ></rect>
      {#if isError && clipW >= 3}
        <!-- Downward caret above the error segment -->
        <polygon
          class="error-caret"
          points="{clipX + clipW / 2 - 5},{y - 8} {clipX + clipW / 2 + 5},{y - 8} {clipX + clipW / 2},{y - 2}"
        />
      {/if}
      {#if showLabels && clipW > 28 && h >= 13}
        {@const label = visibleLabel(row, clipW, labelFontPx)}
        {#if label}
          <text
            class="flame-label"
            class:is-muted={row.muted}
            x={clipX + 5}
            y={y + h / 2 + 0.5}
            dominant-baseline="central"
            font-size={labelFontPx}
                pointer-events="none"
          >{label}</text>
        {/if}
      {/if}
    {/if}
  {/each}

  {#if playhead !== null}
    <!-- The playhead is in TRACE coordinates, which are character offsets --
         the same units a scrubbing cursor counts in. So a synchronised figure
         needs no mapping between clocks: xScale(playhead) is exact. -->
    <line class="playhead" x1={xScale(playhead)} x2={xScale(playhead)}
      y1={0} y2={chartHeight} />
  {/if}

  {#if showCursorGuide && cursorX !== null}
    <line
      class="cursor-guide"
      x1={cursorX}
      x2={cursorX}
      y1={0}
      y2={chartHeight}
    />
  {/if}

</svg>

<style>
  .flame-svg {
    display: block;
    overflow: hidden;
    user-select: none;
    outline: none;
  }

  .flame-svg:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
    border-radius: 2px;
  }

  .flame-svg.is-zoomable {
    cursor: grab;
    touch-action: pan-y;
    overscroll-behavior-x: contain;
  }
  .flame-svg.is-zoomable:active {
    cursor: grabbing;
  }

  .flame-rect {
    transition:
      opacity 180ms ease,
      stroke-width 120ms ease;
    stroke: transparent;
    stroke-width: 0;
  }

  .flame-svg.is-zoomable:active .flame-rect {
    transition: none;
  }

  /* No opacity easing under a playhead. The transition exists for hover, where
     exactly one rect changes; with a playhead sweeping the chart every bar it
     crosses starts its own 180ms animation, and a few hundred overlapping eases
     read as the whole figure shimmering. A clean switch is calmer than a
     staggered fade. */
  .flame-svg.is-playing .flame-rect {
    transition: none;
  }

  .is-interactive .flame-rect {
    cursor: pointer;
  }

  .is-interactive .flame-rect.is-hover {
    stroke: var(--ink);
    stroke-width: 1.5;
  }

  .is-interactive .flame-rect.is-selected {
    stroke: var(--accent);
    stroke-width: 2;
  }

  /* Persistent error marker — visible regardless of hover/selection state. */
  .flame-rect.is-error {
    stroke: #d94c4c;
    stroke-width: 2.5;
  }
  .error-caret {
    fill: #d94c4c;
    pointer-events: none;
  }

  .flame-label {
    fill: rgba(255, 255, 255, 0.96);
    font-family: var(--font-sans);
    font-weight: 500;
    paint-order: stroke;
    stroke: rgba(0, 0, 0, 0.18);
    stroke-width: 0.6;
  }
  /* On a half-strength fill, dark text with a light halo reads; white does not. */
  .flame-label.is-muted {
    fill: rgba(26, 26, 26, 0.82);
    font-weight: 600;
    stroke: rgba(255, 255, 255, 0.55);
    stroke-width: 1.4;
  }

  .gridline {
    stroke: var(--border);
    stroke-width: 0.5;
    stroke-dasharray: 2 4;
  }

  /* Solid, unlike the dashed hover guide: this marks how far the run has got,
     which is a fact about the data, while the guide only tracks a mouse. */
  .playhead { stroke: var(--accent); stroke-width: 1.5; pointer-events: none; }

  .cursor-guide {
    stroke: var(--ink);
    stroke-width: 1;
    stroke-dasharray: 3 3;
    pointer-events: none;
    opacity: 0.55;
  }

</style>
