/**
 * ChartViewport — reactive 2D viewport state for flame graphs.
 *
 * Adopts the flame-chart-js viewport model:
 *   Primary state: zoom (pixels/unit) + positionX (left edge in domain units)
 *   Everything else derived: realView, domain, initialZoom, etc.
 *
 * Reference: flame-chart-js BasicRenderEngine + InteractionsEngine
 */

const MAX_ACCURACY = 6;

export class ChartViewport {
  // ── primary state ──

  /** Left edge of viewport in domain units. */
  positionX = $state(0);

  /** Pixels per domain unit. Higher = more zoomed in. */
  zoom = $state(1);

  /** Vertical scroll offset in pixels. */
  scrollY = $state(0);

  /** Domain minimum (typically 0). */
  min = $state(0);

  /** Domain maximum (total trace span). */
  max = $state(0);

  /** Full chart height in pixels (all rows at current row height). */
  totalHeight = $state(0);

  /** Visible viewport width in pixels. */
  viewportWidth = $state(0);

  /** Visible viewport height in pixels. */
  viewportHeight = $state(0);

  // ── derived ──

  /** Visible time span in domain units. */
  readonly realView = $derived(this.zoom > 0 ? this.viewportWidth / this.zoom : 0);

  /** Zoom level that fits the entire domain in the viewport. */
  readonly initialZoom = $derived(
    this.max - this.min > 0 ? this.viewportWidth / (this.max - this.min) : 1,
  );

  /** Domain tuple for d3-scale: [left, left + realView]. */
  readonly domain = $derived(
    [this.positionX, this.positionX + this.realView] as readonly [number, number],
  );

  /** Total domain span. */
  readonly totalSpan = $derived(this.max - this.min);

  /** Max scrollY given current chart and viewport heights. */
  readonly maxScrollY = $derived(
    Math.max(0, this.totalHeight - this.viewportHeight),
  );

  /** Whether the view is zoomed in (not showing full extent). */
  readonly isZoomed = $derived(this.zoom > this.initialZoom * 1.005);

  constructor(
    viewportWidth: number,
    viewportHeight: number,
  ) {
    this.viewportWidth = viewportWidth;
    this.viewportHeight = viewportHeight;
  }

  // ── position ──

  /**
   * Pan by a domain-unit delta, clamped to [min, max - realView].
   * Matches flame-chart-js tryToChangePosition().
   */
  tryToChangePosition(delta: number): void {
    const realView = this.realView;
    const newPos = this.positionX + delta;

    if (newPos >= this.min && newPos + realView <= this.max) {
      this.positionX = newPos;
    } else if (newPos < this.min) {
      this.positionX = this.min;
    } else {
      this.positionX = this.max - realView;
    }
  }

  // ── zoom ──

  /**
   * Set zoom directly, clamped to [initialZoom, maxZoom].
   * Returns true if zoom was accepted.
   */
  setZoom(newZoom: number): boolean {
    const resolved = Math.max(newZoom, this.initialZoom);
    if (resolved !== this.zoom) {
      this.zoom = resolved;
      return true;
    }
    return false;
  }

  /**
   * Change zoom by a delta, anchored at a screen pixel position.
   * Matches flame-chart-js changeZoom() + fixPositionAfterZoom().
   *
   * zoomDelta > 0 means zoom OUT (subtract from zoom).
   */
  changeZoom(zoomDelta: number, fromPx: number = this.viewportWidth / 2): void {
    const oldRealView = this.realView;
    const zoomed = this.setZoom(this.zoom - zoomDelta);
    if (zoomed) {
      this.fixPositionAfterZoom(oldRealView, fromPx);
    }
  }

  /**
   * After a zoom change, shift positionX so that the time value under
   * `fromPx` stays at the same screen position.
   */
  private fixPositionAfterZoom(oldRealView: number, fromPx: number): void {
    const proportion = fromPx / this.viewportWidth;
    const newRealView = this.realView;
    const timeDelta = oldRealView - newRealView;
    this.tryToChangePosition(timeDelta * proportion);
  }

  // ── convenience pan methods ──

  /** Pan the time axis by a pixel delta. */
  panX(deltaPx: number): void {
    if (this.zoom <= 0) return;
    this.tryToChangePosition(deltaPx / this.zoom);
  }

  /** Pan the vertical axis by a pixel delta. */
  panY(deltaPx: number): void {
    this.scrollY = this.clampScrollY(this.scrollY + deltaPx);
  }

  /** Pan both axes simultaneously (for drag gestures). */
  panBoth(dxPx: number, dyPx: number): void {
    if (dxPx !== 0) this.panX(dxPx);
    if (dyPx !== 0) this.panY(dyPx);
  }

  /** Zoom around center by a factor (< 1 = zoom in, > 1 = zoom out). */
  zoomCenter(factor: number): void {
    const oldRealView = this.realView;
    const newRealView = oldRealView * factor;
    const newZoom = this.viewportWidth / Math.max(
      this.totalSpan * 0.005,
      Math.min(this.totalSpan, newRealView),
    );
    const zoomed = this.setZoom(newZoom);
    if (zoomed) {
      this.fixPositionAfterZoom(oldRealView, this.viewportWidth / 2);
    }
  }

  // ── domain setters ──

  /** Set the visible time window directly (e.g., from click-to-zoom). */
  setDomain(left: number, right: number): void {
    const span = Math.max(this.totalSpan * 0.005, right - left);
    this.positionX = Math.max(this.min, Math.min(this.max - span, left));
    this.zoom = this.viewportWidth / span;
  }

  /** Reset to full extent and scroll to top. */
  reset(): void {
    this.positionX = this.min;
    this.zoom = this.initialZoom;
    this.scrollY = 0;
  }

  // ── dimension updates ──

  /** Update viewport width, preserving the visible time span. */
  updateViewportWidth(newWidth: number): void {
    const oldRealView = this.realView;
    this.viewportWidth = newWidth;
    if (oldRealView > 0 && this.zoom > 0) {
      this.zoom = newWidth / oldRealView;
    }
    this.setZoom(this.zoom);
  }

  /** Update total chart height, preserving scroll proportion. */
  updateTotalHeight(newHeight: number): void {
    const oldMaxScroll = Math.max(1, this.totalHeight - this.viewportHeight);
    const fraction = oldMaxScroll > 0 ? this.scrollY / oldMaxScroll : 0;
    this.totalHeight = newHeight;
    const newMaxScroll = this.maxScrollY;
    this.scrollY = Math.max(0, Math.min(newMaxScroll, fraction * newMaxScroll));
  }

  /** Set the data bounds and reset to full extent. */
  setBounds(min: number, max: number): void {
    this.min = min;
    this.max = max;
    this.positionX = min;
    this.zoom = this.initialZoom;
  }

  private clampScrollY(y: number): number {
    return Math.max(0, Math.min(this.maxScrollY, y));
  }
}
