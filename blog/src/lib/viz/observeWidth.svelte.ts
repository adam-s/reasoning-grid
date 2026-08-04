/**
 * Watch an element's width, and only its width.
 *
 * Every figure here sizes itself from the width it is given and derives its own
 * height from that. Observing the element the obvious way makes each of them
 * report `ResizeObserver loop completed with undelivered notifications` at phone
 * and tablet widths: the callback sets a height, setting the height resizes the
 * observed box, and the box reports again inside the same delivery. The browser
 * breaks the cycle by dropping a notification.
 *
 * Dropping notifications is the part that matters. A dropped one during a device
 * rotation leaves the figure drawn at the width it had in the other orientation,
 * which is a figure that does not fit and no error anybody sees.
 *
 * Two things fix it. Ignoring deliveries whose width is unchanged means a height
 * echo is not treated as a resize, and doing the write in a frame callback moves
 * the layout change out of the delivery so there is no cycle to break.
 */
export function observeWidth(
  getEl: () => Element | null | undefined,
  apply: (width: number) => void,
) {
  $effect(() => {
    const el = getEl();
    if (!el) return;

    let seen = -1;
    let raf = 0;
    const ro = new ResizeObserver(([entry]) => {
      const width = entry.contentRect.width;
      if (Math.abs(width - seen) < 0.5) return; // a height echo, not a resize
      seen = width;
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => apply(width));
    });
    ro.observe(el);

    return () => {
      ro.disconnect();
      cancelAnimationFrame(raf);
    };
  });
}
