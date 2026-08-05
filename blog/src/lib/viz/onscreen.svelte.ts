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
    // THE LAST ENTRY, NOT THE FIRST. One delivery can carry several records for
    // the same element, and they are in time order, so entries[0] is the oldest
    // thing the observer saw and the only one that is definitely stale.
    //
    // Taking the first froze the opener. Reload the page scrolled down and
    // scroll back up: the figure reports 205px tall and off screen, then 508px
    // and on screen once it has sized itself, and when those two land in one
    // delivery the 205px record won. `near` stayed false, the frame loop never
    // restarted, and the rings sat at two percent of their first lap forever.
    // It reproduced about one reload in three, which is what a batching race
    // looks like from the outside.
    const io = new IntersectionObserver(
      (entries) => { near = entries[entries.length - 1].isIntersecting; },
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
