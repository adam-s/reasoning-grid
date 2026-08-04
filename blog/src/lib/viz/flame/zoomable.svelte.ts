/**
 * `zoomable` — Svelte action wiring pointer/wheel/keyboard events to
 * a ChartViewport instance.
 *
 * All viewport mutations are batched via requestAnimationFrame so that
 * multiple events per frame (common with wheel/pointermove at 60Hz+)
 * produce at most ONE reactive update per animation frame.
 *
 * Reference: flame-chart-js InteractionsEngine
 */

import type { Action } from 'svelte/action';
import type { ChartViewport } from './ChartViewport.svelte';

export type ZoomableParams = {
  readonly viewport: ChartViewport;
  readonly enabled?: boolean;
};

const CLICK_VS_DRAG_THRESHOLD = 6;
const PAN_STEP_PX = 160;
const ZOOM_FACTOR_KEY = 0.3;
const ZOOM_FACTOR_KEY_SHIFT = 0.8;

export const zoomable: Action<SVGSVGElement, ZoomableParams> = (
  node,
  initialParams,
) => {
  let params = initialParams;
  let teardowns: Array<() => void> = [];

  function vp(): ChartViewport {
    return params.viewport;
  }

  // ── rAF batching ──
  // Accumulate deltas from multiple events per frame, flush once.

  let pendingPanX = 0;
  let pendingPanY = 0;
  let pendingZoom: { delta: number; px: number } | null = null;
  let rafId: number | null = null;

  function flush(): void {
    rafId = null;
    if (pendingZoom) {
      vp().changeZoom(pendingZoom.delta, pendingZoom.px);
      pendingZoom = null;
    }
    if (pendingPanX !== 0 || pendingPanY !== 0) {
      vp().panBoth(pendingPanX, pendingPanY);
      pendingPanX = 0;
      pendingPanY = 0;
    }
  }

  function scheduleFlush(): void {
    if (rafId === null) {
      rafId = requestAnimationFrame(flush);
    }
  }

  function queuePan(dx: number, dy: number): void {
    pendingPanX += dx;
    pendingPanY += dy;
    scheduleFlush();
  }

  function queueZoom(delta: number, px: number): void {
    if (pendingZoom) {
      pendingZoom.delta += delta;
    } else {
      pendingZoom = { delta, px };
    }
    scheduleFlush();
  }

  // ── wheel ──

  /**
   * A WHEEL EVENT THIS FIGURE DOES NOT USE MUST REACH THE PAGE.
   *
   * This used to call preventDefault on every wheel event and map a plain
   * vertical wheel to zoom. The figure sits inline in the middle of a long
   * article, so scrolling down the page with the cursor anywhere over it stopped
   * the page dead and zoomed the trace instead, with nothing on screen to say
   * why. `touch-action: pan-y` already protected touch, which left the trap set
   * for exactly the mouse and trackpad readers who make up most of this page.
   *
   * Zoom now takes the modifier every map on the web uses. preventDefault moved
   * inside the branches that actually consume the event, so anything this figure
   * ignores scrolls the article as usual.
   */
  const wheelHandler = (ev: WheelEvent): void => {
    if (!params.enabled) return;

    // Ctrl/Cmd + wheel → zoom at cursor
    if (ev.ctrlKey || ev.metaKey) {
      ev.preventDefault();
      ev.stopImmediatePropagation();
      const rect = node.getBoundingClientRect();
      const cursorPx = ((ev.clientX - rect.left) / rect.width) * vp().viewportWidth;
      queueZoom((ev.deltaY / 1000) * vp().zoom, cursorPx);
      return;
    }

    // Shift + wheel → horizontal pan
    if (ev.shiftKey && ev.deltaY !== 0) {
      ev.preventDefault();
      ev.stopImmediatePropagation();
      queuePan(ev.deltaY, 0);
      return;
    }

    // Horizontal-dominant trackpad swipe → horizontal pan. Vertical-dominant is
    // the reader scrolling the page, and is left alone.
    if (Math.abs(ev.deltaX) > Math.abs(ev.deltaY) && ev.deltaX !== 0) {
      ev.preventDefault();
      ev.stopImmediatePropagation();
      queuePan(ev.deltaX, 0);
    }
  };

  // ── keyboard ──

  const keyHandler = (ev: KeyboardEvent): void => {
    if (!params.enabled) return;

    const shift = ev.shiftKey;
    switch (ev.key) {
      case 'a':
      case 'A':
      case 'ArrowLeft':
        ev.preventDefault();
        vp().panX(-PAN_STEP_PX);
        break;
      case 'd':
      case 'D':
      case 'ArrowRight':
        ev.preventDefault();
        vp().panX(PAN_STEP_PX);
        break;
      case 'w':
      case 'W':
      case 'ArrowUp':
      case '=':
      case '+':
        ev.preventDefault();
        vp().zoomCenter(1 - (shift ? ZOOM_FACTOR_KEY_SHIFT : ZOOM_FACTOR_KEY));
        break;
      case 's':
      case 'S':
      case 'ArrowDown':
      case '-':
        ev.preventDefault();
        vp().zoomCenter(1 + (shift ? ZOOM_FACTOR_KEY_SHIFT : ZOOM_FACTOR_KEY));
        break;
      case 'Home':
        ev.preventDefault();
        vp().reset();
        break;
      default:
        return;
    }
  };

  // ── drag ──

  let isDragging = false;
  let pointerId: number | null = null;
  let lastDragX = 0;
  let lastDragY = 0;
  let movedSinceDown = 0;
  let dragSuppressed = false;

  const pointerDownHandler = (ev: PointerEvent): void => {
    if (!params.enabled) return;
    if (ev.button !== 0) return;
    pointerId = ev.pointerId;
    lastDragX = ev.clientX;
    lastDragY = ev.clientY;
    movedSinceDown = 0;
    isDragging = true;
    dragSuppressed = false;
  };

  const pointerMoveHandler = (ev: PointerEvent): void => {
    if (!isDragging || pointerId !== ev.pointerId) return;
    const dx = ev.clientX - lastDragX;
    const dy = ev.clientY - lastDragY;
    lastDragX = ev.clientX;
    lastDragY = ev.clientY;
    movedSinceDown += Math.abs(dx) + Math.abs(dy);

    if (movedSinceDown < CLICK_VS_DRAG_THRESHOLD) return;

    if (!dragSuppressed) {
      try {
        node.setPointerCapture(ev.pointerId);
      } catch {
        // Ignore detached node errors.
      }
      dragSuppressed = true;
    }

    queuePan(-dx, -dy);
    ev.preventDefault();
  };

  const pointerUpHandler = (ev: PointerEvent): void => {
    if (!isDragging || pointerId !== ev.pointerId) return;
    // Flush any pending updates immediately on pointer up
    if (rafId !== null) {
      cancelAnimationFrame(rafId);
      flush();
    }
    if (dragSuppressed) {
      const suppressClick = (e: MouseEvent) => {
        e.stopPropagation();
        e.preventDefault();
        node.removeEventListener('click', suppressClick, true);
      };
      node.addEventListener('click', suppressClick, true);
      setTimeout(() => node.removeEventListener('click', suppressClick, true), 50);
      try {
        node.releasePointerCapture(ev.pointerId);
      } catch {
        // Ignore.
      }
    }
    isDragging = false;
    pointerId = null;
    dragSuppressed = false;
  };

  // ── lifecycle ──

  function attach(): void {
    teardowns.forEach((t) => t());
    teardowns = [];
    if (!params.enabled) return;

    if (!node.hasAttribute('tabindex')) {
      node.setAttribute('tabindex', '0');
    }

    node.addEventListener('wheel', wheelHandler, { passive: false });
    node.addEventListener('keydown', keyHandler);
    node.addEventListener('pointerdown', pointerDownHandler);
    node.addEventListener('pointermove', pointerMoveHandler);
    node.addEventListener('pointerup', pointerUpHandler);
    node.addEventListener('pointercancel', pointerUpHandler);
    /**
     * THE RELEASE CAN HAPPEN SOMEWHERE ELSE.
     *
     * Pointer capture is only taken once the drag passes the click threshold,
     * which leaves a gap: press inside the figure, move three pixels, release
     * outside it. No pointerup reaches the node, so `isDragging` stays true with
     * no button held, and the next time the cursor crosses the figure it pans
     * under a bare mouse until the reader presses and releases inside again.
     *
     * The window sees every release, so it is what closes the gap. It cannot
     * take the place of capture — capture is what keeps a real drag smooth once
     * it leaves the node — so both are here.
     */
    window.addEventListener('pointerup', pointerUpHandler);
    window.addEventListener('pointercancel', pointerUpHandler);
    teardowns.push(
      () => node.removeEventListener('wheel', wheelHandler),
      () => node.removeEventListener('keydown', keyHandler),
      () => node.removeEventListener('pointerdown', pointerDownHandler),
      () => node.removeEventListener('pointermove', pointerMoveHandler),
      () => node.removeEventListener('pointerup', pointerUpHandler),
      () => node.removeEventListener('pointercancel', pointerUpHandler),
      () => window.removeEventListener('pointerup', pointerUpHandler),
      () => window.removeEventListener('pointercancel', pointerUpHandler),
    );
  }

  attach();

  return {
    update(newParams: ZoomableParams) {
      const wasEnabled = params.enabled;
      params = newParams;
      if (wasEnabled !== newParams.enabled) attach();
    },
    destroy() {
      if (rafId !== null) cancelAnimationFrame(rafId);
      teardowns.forEach((t) => t());
      teardowns = [];
    },
  };
};
