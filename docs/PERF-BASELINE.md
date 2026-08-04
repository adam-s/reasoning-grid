# Performance baseline — blog page, before the animation fixes

Measured state of `blog/` at this commit, recorded so the fixes that follow have
something to be compared against. Every number here is reproducible from
committed scripts; none of it is estimated.

## How to regenerate

Serve the page and run both probes:

```sh
cd blog && npm run dev            # serves on 5175
node scripts/perf-probe.mjs http://localhost:5175/ 390 844     # phone
node scripts/perf-probe.mjs http://localhost:5175/ 768 1024    # tablet
node scripts/perf-probe.mjs http://localhost:5175/ 1440 900    # desktop
node scripts/raf-blame.mjs  http://localhost:5175/ 1440        # who is animating
```

`perf-probe.mjs` patches `requestAnimationFrame`, `setTimeout`, `setInterval`,
and `EventTarget.prototype.add/removeEventListener` before any app code runs, so
the counts are of the app's own scheduling rather than of anything the profiler
inferred. It then scrolls the whole page, clicks every button three times in
quick succession to try to start concurrent loops, and reads CDP
`Performance.getMetrics` either side of a forced GC.

**The frame rate of the measuring browser is not 60.** Headless Chromium here
services rAF at ~119.5 fps, so a single uncapped loop reports ~120 calls/sec and
not ~60. Reading 120 as "two loops at 60" is wrong, and an earlier pass of this
audit made exactly that mistake. Confirm the baseline rate before interpreting
any rAF count.

## What it measured

Numbers below are from the Vite dev server, which contributes one uncleared
`setInterval` of its own (the HMR ping). That interval is not app code and is
excluded from the leak count. No other tooling contributes rAF loops.

| | 390×844 | 768×1024 | 1440×900 |
|---|---|---|---|
| rAF calls/sec, idle at load | 480 | 482 | 482 |
| rAF calls/sec, idle after interacting | 480 | 480 | 482 |
| rAF callbacks queued at rest | 4 | 4 | 4 |
| longest task | 76 ms | 81 ms | 76 ms |
| frames slower than 34 ms | 2 | 2 | 2 |
| heap over 3 interaction rounds | 13.6 → 13.6 MB | 14.0 → 14.0 MB | 14.0 → 14.1 MB |
| horizontal overflow | none | none | none |

## The findings

**Four animation loops never stop.** At ~120 calls/sec each, they run from load,
they run while idle, and they keep running while scrolled far off screen. Blamed
by call site with `raf-blame.mjs`:

- `lib/viz/opener/IterationRings.svelte:492`
- `lib/viz/opener/Dogfight.svelte:697`
- `lib/viz/opener/Dogfight.svelte:713`
- `lib/viz/opener/SyncedTrace.svelte:619`

A fifth, `lib/viz/surface/DistributionPanels.svelte:217`, joins at ~82 calls/sec
once the reader scrolls to it. Its rAF handle is never stored, so nothing can
cancel it; it stops only when its own generation check happens to fail.

Nothing here leaks memory — the heap is flat across repeated interaction, so
these are steady-state loops rather than accumulating ones. The cost is CPU that
is spent whether or not anything is moving, which on a phone is battery and
scrolling smoothness.

**Thirteen touch targets are below the 44 px minimum.** The four verdict buttons
(`Solved`, `Wrong`, `Caught`, `Locked`) are 27 px tall, the transport controls
(`▶`, `❚❚`) are 26 px, and the eight moment links are 27–31 px. All are 44 px
wide or more, so this is a height problem only. The two `Walk it from the start`
buttons at 37 px are the closest to passing.

**`ResizeObserver loop completed with undelivered notifications`** fires at 390
and 768 px, and not at 1440. An observer callback is resizing something that
feeds back into the same observation, and the browser is dropping frames of
notification to break the cycle.

## Not measured yet

Production build rather than dev server; a real device rather than headless;
interaction latency under CPU throttling.
