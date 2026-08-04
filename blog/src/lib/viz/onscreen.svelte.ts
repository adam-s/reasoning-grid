/**
 * Is this figure worth animating right now?
 *
 * Every looping figure on the page used to run its frame loop from the moment
 * it mounted until the tab closed, whether or not it was on screen. Four of
 * them together serviced ~480 requestAnimationFrame callbacks per second while
 * the reader sat still, and they kept doing it while scrolled a full page away.
 * Nothing leaked — the heap was flat — the cost was CPU spent painting things
 * nobody could see, which on a phone is battery and a stuttering scroll.
 *
 * A loop gated on this runs when the figure is near the viewport and the tab is
 * in front, and stops otherwise. The measured effect is in docs/PERF-BASELINE.md.
 *
 * WHY THE MARGIN IS NOT ZERO. Gating on strict intersection means the first
 * frame a reader sees is the frame the loop started on, so a figure that
 * animates on arrival appears to stutter into life. Half a screen of lead means
 * it is already running by the time it is looked at. A full screen was the first
 * try and it is too much on a phone, where one viewport of slack in each
 * direction keeps most of the page's figures inside the gate at once.
 *
 * WHY IT DEFAULTS TO TRUE. Between the call and the observer's first delivery
 * there is a frame or two where nothing is known. Defaulting to false there
 * makes an above-the-fold figure miss its opening; the observer corrects a
 * wrong `true` on the next frame, and the wrong direction is cheaper.
 */
export function onscreen(
  getEl: () => Element | null | undefined,
  rootMargin = '50% 0px',
) {
  let near = $state(true);
  let foreground = $state(true);

  $effect(() => {
    const el = getEl();
    if (!el) return;
    const io = new IntersectionObserver(
      ([e]) => { near = e.isIntersecting; },
      { rootMargin },
    );
    io.observe(el);
    return () => io.disconnect();
  });

  $effect(() => {
    const sync = () => { foreground = document.visibilityState === 'visible'; };
    sync();
    document.addEventListener('visibilitychange', sync);
    return () => document.removeEventListener('visibilitychange', sync);
  });

  return {
    get current() {
      return near && foreground;
    },
  };
}
