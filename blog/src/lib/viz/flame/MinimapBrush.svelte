<script lang="ts">
  /**
   * MinimapBrush — horizontal viewport selector over the minimap.
   *
   * Matches flame-chart-js TimeframeSelectorPlugin exactly:
   *   - Two knobs (left/right) control the visible time range
   *   - Drag a knob to resize the viewport
   *   - Drag between knobs to pan
   *   - Click outside knobs to move nearest knob
   *   - Double-click to reset to full extent
   *   - No vertical handles (vertical scroll is by drag on main chart)
   *
   * Knob position formula (from flame-chart-js):
   *   leftKnob  = (positionX - min) * initialZoom
   *   rightKnob = (positionX - min + realView) * initialZoom
   *   where initialZoom = minimapWidth / (max - min)
   */
  import type { ChartViewport } from './ChartViewport.svelte';

  type Props = {
    viewport: ChartViewport;
    width: number;
    height: number;
  };

  let {
    viewport,
    width,
    height,
  }: Props = $props();

  let svgEl: SVGSVGElement | null = $state(null);

  // The minimap's own zoom — maps full domain to minimap pixel width.
  // Equivalent to flame-chart-js getInitialZoom().
  const mZoom = $derived(
    viewport.totalSpan > 0 ? width / viewport.totalSpan : 1,
  );

  // Knob positions in minimap pixels (flame-chart-js formula).
  const leftKnobPos = $derived((viewport.positionX - viewport.min) * mZoom);
  const rightKnobPos = $derived(
    (viewport.positionX - viewport.min + viewport.realView) * mZoom,
  );

  // Clamp for rendering.
  const visLeft = $derived(Math.max(0, leftKnobPos));
  const visRight = $derived(Math.min(width, rightKnobPos));
  const visW = $derived(Math.max(2, visRight - visLeft));

  const KNOB_W = 6;
  const KNOB_H_FRAC = 0.33; // knobs occupy top 1/3 of minimap (like flame-chart-js)
  const knobH = $derived(Math.round(height * KNOB_H_FRAC));

  type DragMode = 'left-knob' | 'right-knob' | 'pan' | 'select' | null;
  let dragMode: DragMode = $state(null);
  let selectStartPx = 0;

  // Double-click detection (300ms, same as flame-chart-js).
  let clickTimeout: ReturnType<typeof setTimeout> | null = $state(null);

  let cachedRect: DOMRect | null = null;

  function svgRect(): DOMRect | null {
    return cachedRect ?? svgEl?.getBoundingClientRect() ?? null;
  }

  /**
   * Convert a CSS pixel X position (relative to SVG left edge) to
   * a minimap pixel position, accounting for CSS scaling.
   */
  function cssXToMinimapPx(clientX: number, rect: DOMRect): number {
    return ((clientX - rect.left) / rect.width) * width;
  }

  /**
   * Convert a minimap pixel position to a domain time value.
   * Equivalent to flame-chart-js: pixelToTime(px) + min.
   */
  function minimapPxToTime(px: number): number {
    return px / mZoom + viewport.min;
  }

  // ── Knob setters (flame-chart-js algorithm, line-for-line) ──

  function setLeftKnobPosition(mouseXpx: number): void {
    const maxPosition = rightKnobPos;
    if (mouseXpx < maxPosition - 1) {
      const oldRealView = viewport.realView;
      const newPosX = Math.max(viewport.min, minimapPxToTime(mouseXpx));
      const delta = newPosX - viewport.positionX;
      viewport.positionX = newPosX;
      const newZoom = viewport.viewportWidth / (oldRealView - delta);
      viewport.setZoom(newZoom);
    }
  }

  function setRightKnobPosition(mouseXpx: number): void {
    const minPosition = leftKnobPos;
    if (mouseXpx > minPosition + 1) {
      const oldRealView = viewport.realView;
      const rightTime = Math.min(viewport.max, minimapPxToTime(mouseXpx));
      const delta = viewport.positionX + oldRealView - rightTime;
      const newZoom = viewport.viewportWidth / (oldRealView - delta);
      viewport.setZoom(newZoom);
    }
  }

  // ── Event handlers ──

  function handlePointerDown(ev: PointerEvent): void {
    ev.preventDefault();
    cachedRect = svgEl?.getBoundingClientRect() ?? null;
    const rect = cachedRect;
    if (!rect) return;
    const px = cssXToMinimapPx(ev.clientX, rect);

    // Determine what was clicked: left knob, right knob, between them, or outside.
    const leftKnobLeft = leftKnobPos - KNOB_W / 2;
    const leftKnobRight = leftKnobPos + KNOB_W / 2;
    const rightKnobLeft = rightKnobPos - KNOB_W / 2;
    const rightKnobRight = rightKnobPos + KNOB_W / 2;

    if (px >= leftKnobLeft && px <= leftKnobRight) {
      dragMode = 'left-knob';
    } else if (px >= rightKnobLeft && px <= rightKnobRight) {
      dragMode = 'right-knob';
    } else if (px > leftKnobRight && px < rightKnobLeft) {
      dragMode = 'pan';
    } else {
      dragMode = 'select';
      selectStartPx = px;
    }

    svgEl?.setPointerCapture(ev.pointerId);
  }

  function handlePointerMove(ev: PointerEvent): void {
    if (!dragMode) return;
    const rect = svgRect();
    if (!rect) return;
    const px = cssXToMinimapPx(ev.clientX, rect);

    if (dragMode === 'left-knob') {
      setLeftKnobPosition(px);
    } else if (dragMode === 'right-knob') {
      setRightKnobPosition(px);
    } else if (dragMode === 'pan') {
      // Pan: convert pixel delta to domain delta, update positionX.
      const dxPx = ev.movementX;
      if (dxPx !== 0) {
        const rect2 = svgRect();
        if (rect2) {
          const dxDomain = (dxPx / rect2.width) * viewport.totalSpan;
          viewport.tryToChangePosition(dxDomain);
        }
      }
    } else if (dragMode === 'select') {
      // Drag-to-select: set both knobs.
      if (selectStartPx >= px) {
        setLeftKnobPosition(px);
        setRightKnobPosition(selectStartPx);
      } else {
        setLeftKnobPosition(selectStartPx);
        setRightKnobPosition(px);
      }
    }
  }

  function handlePointerUp(ev: PointerEvent): void {
    cachedRect = null;
    const wasDrag = dragMode;
    const rect = svgRect();
    const px = rect ? cssXToMinimapPx(ev.clientX, rect) : 0;

    // Check for click (no significant movement).
    const isClick = wasDrag === 'select' && Math.abs(px - selectStartPx) < 3;

    // Double-click detection.
    let isDoubleClick = false;
    if (clickTimeout !== null) {
      isDoubleClick = true;
      clearTimeout(clickTimeout);
      clickTimeout = null;
    } else {
      clickTimeout = setTimeout(() => { clickTimeout = null; }, 300);
    }

    dragMode = null;

    if (isDoubleClick) {
      // Double-click: reset to full extent.
      viewport.reset();
      return;
    }

    if (isClick && rect) {
      // Single click: move nearest knob to click position.
      if (px > rightKnobPos) {
        setRightKnobPosition(px);
      } else if (px > leftKnobPos && px < rightKnobPos) {
        // Between knobs: move the closer one.
        if (px - leftKnobPos > rightKnobPos - px) {
          setRightKnobPosition(px);
        } else {
          setLeftKnobPosition(px);
        }
      } else {
        setLeftKnobPosition(px);
      }
    }

    try { svgEl?.releasePointerCapture(ev.pointerId); } catch { /* ignore */ }
  }
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<svg
  bind:this={svgEl}
  class="minimap-brush"
  {width}
  {height}
  viewBox="0 0 {width} {height}"
  role="group"
  aria-label="Viewport selector"
  onpointerdown={handlePointerDown}
  onpointermove={handlePointerMove}
  onpointerup={handlePointerUp}
  onpointercancel={handlePointerUp}
>
  <!-- Left dimmed overlay -->
  <rect class="dim" x={0} y={0} width={Math.max(0, visLeft)} height={height} />
  <!-- Right dimmed overlay -->
  <rect class="dim" x={visRight} y={0} width={Math.max(0, width - visRight)} height={height} />

  <!-- Edge lines at knob positions -->
  <line class="edge-line" x1={visLeft} x2={visLeft} y1={0} y2={height} />
  <line class="edge-line" x1={visRight} x2={visRight} y1={0} y2={height} />

  <!-- Viewport body: grab cursor for panning -->
  <rect
    class="body-hit"
    x={visLeft + KNOB_W / 2}
    y={0}
    width={Math.max(0, visW - KNOB_W)}
    height={height}
  />

  <!-- Left knob (visual + hit area) -->
  <rect
    class="knob"
    x={visLeft - KNOB_W / 2}
    y={0}
    width={KNOB_W}
    height={knobH}
  />
  <rect
    class="knob-hit"
    x={visLeft - KNOB_W}
    y={0}
    width={KNOB_W * 2}
    height={height}
  />

  <!-- Right knob (visual + hit area) -->
  <rect
    class="knob"
    x={visRight - KNOB_W / 2}
    y={0}
    width={KNOB_W}
    height={knobH}
  />
  <rect
    class="knob-hit"
    x={visRight - KNOB_W}
    y={0}
    width={KNOB_W * 2}
    height={height}
  />
</svg>

<style>
  .minimap-brush {
    position: absolute;
    inset: 4px 0;
    width: 100%;
    height: calc(100% - 8px);
    cursor: text;
  }

  .dim {
    fill: rgba(112, 112, 112, 0.5);
    pointer-events: none;
  }

  .edge-line {
    stroke: rgba(112, 112, 112, 0.7);
    stroke-width: 1;
    pointer-events: none;
  }

  .body-hit {
    fill: white;
    fill-opacity: 0;
    cursor: grab;
  }

  .body-hit:active {
    cursor: grabbing;
  }

  .knob {
    fill: rgb(131, 131, 131);
    stroke: white;
    stroke-width: 1;
    pointer-events: none;
  }

  .knob-hit {
    fill: white;
    fill-opacity: 0;
    cursor: ew-resize;
  }
</style>
