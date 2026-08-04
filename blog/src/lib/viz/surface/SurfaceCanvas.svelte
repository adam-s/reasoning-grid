<script lang="ts">
  /**
   * The reliability surface, redrawn at every trial count.
   *
   * x = digits in one factor, y = digits in the other, height = probability the
   * model returns the exactly correct product. Scrubbing t recomputes every cell
   * as the running mean of its first t outcomes, so no frames are precomputed —
   * 2,426 stored outcomes carry all 55 of them.
   *
   * Canvas rather than the SVG the Python version emits. The repo's own dataviz
   * note says SVG wins below a few thousand elements and this is 169 quads, so
   * canvas has to earn it: it does, because the projection is perspective and
   * therefore orbitable, and orbiting means a redraw on every pointer move on
   * top of a redraw on every animation frame. Rebuilding 169 SVG nodes at that
   * rate is where SVG stops being free. The isometric SVG version cannot be
   * orbited at all — it has no camera.
   *
   * Draw order is exact, not approximate; see project.ts.
   */
  import { onMount } from 'svelte';
  import { observeWidth } from '../observeWidth.svelte';
  import { SURFACE } from '../../data/surface';
  import { project, groundOrder, rateAt, ramp, type Camera } from './project';
  import ConvergenceRail from './ConvergenceRail.svelte';
  import Cue from '../opener/Cue.svelte';

  /**
   * ---- THE API THE PROSE DRIVES -------------------------------------------
   *
   * Same split as the trace figure: the figure exposes one method and reports
   * one flag, and whoever owns the prose owns the button. `walk` is the whole
   * surface, so it takes no arguments -- there is only one thing to be walked
   * through, unlike a trace where the caller has to name a run and an offset.
   *
   * The flag exists so the caller can disable its own control while the walk
   * is running. Without it a second press restarts the surface from one trial
   * halfway through the first walk, which reads as the figure breaking.
   */
  type Props = {
    onWalkChange?: (walking: boolean) => void;
    /**
     * The reader worked the figure's own controls -- played it, scrubbed it, or
     * took hold of it. Fires for those and never for `walk`, so a caller showing
     * a cue can drop it the moment the reader shows they have already found the
     * figure. Pointing at a button someone has demonstrated they do not need is
     * nagging; see the tour note in App.svelte, which is the same rule.
     */
    onReaderDrive?: () => void;
  };
  let { onWalkChange, onReaderDrive }: Props = $props();

  let canvas: HTMLCanvasElement | null = $state(null);
  let host: HTMLDivElement | null = $state(null);
  let w = $state(760);
  let h = $state(440);

  const DIM = SURFACE.dim;
  // The scrub stops at 29, not at the 55 the longest cell reached. Past 29 only
  // four cells still have trials left, so the last 26 steps of a full-range
  // slider move almost nothing while eating three quarters of the travel. Those
  // four are shown truncated to 29 and the caption says so.
  const MAXT = Math.min(29, SURFACE.maxTrials);

  /**
   * ONE MOTION AT A TIME, as a mode rather than as a set of booleans. Playing
   * and walking both drive `t` and only one of them can be true, so two flags
   * would be four states for three situations, and the fourth is a surface
   * being stepped by two loops at once.
   *
   *   idle  nothing is moving. The reader owns the slider and the camera.
   *   play  the trial count advances. The camera stays where it was left.
   *   walk  the trial count advances AND the camera turns with it.
   */
  type Motion = 'idle' | 'play' | 'walk';

  /**
   * Where the camera comes to rest. Also its opening value, so a page that is
   * never touched looks like the end of a walk.
   *
   * Yaw is exactly a quarter turn, which is not a rounded-off number but the
   * one angle that puts the 1x14 corner dead in front of the viewer. Off the
   * diagonal that corner drifts to one side and the two axes stop being read
   * at the same rate, which is the whole reason the surface is worth turning.
   */
  const REST_YAW = -Math.PI / 4;
  /** Nearly edge-on, which is what makes the cliff a cliff. Seen from above the
   *  fall-off is a colour change; seen from here it is a drop with the eye level
   *  partway down it. Only 0.04 above the drag clamp, so there is almost nothing
   *  left to flatten by hand -- deliberate, since flatter than this the plateau
   *  closes up into a line. */
  const REST_PITCH = 0.12;
  /** Where a walk starts: further round and higher up, so the first frames are
   *  read down the cliff rather than across it, and the turn has somewhere to
   *  go. */
  const WALK_YAW = -1.34;
  const WALK_PITCH = 0.92;
  /** One trial per this many milliseconds, for both motions. The walk's turn is
   *  paced off the same number so the camera lands as the last trial does. */
  const STEP_MS = 130;

  let t = $state(1);
  let motion: Motion = $state('idle');
  /** Bumped by every `walk` call so a second press restarts the run loop, which
   *  a plain reassignment to the same mode would not. Same discipline as the
   *  trace figure's presenter generation. */
  let walkGen = $state(0);
  /** Between the press and the first trial, while the page is scrolling. */
  let arming = $state(false);
  const moving = $derived(motion !== 'idle');
  let rootEl: HTMLElement | null = $state(null);

  /**
   * The pointer is over the control row, so the play button wears a cue.
   *
   * HOVER, NOT ALWAYS. The row already sits under a labelled button that says
   * what it does, and a permanent arrow on a second control turns the figure
   * into a page of instructions. Showing it only while the pointer is in the
   * row costs a reader who has already found the control nothing, and catches
   * the one who is scanning the row without having spotted a 26px glyph.
   *
   * MOUSE ONLY. A touch pointer entering an element means a finger has landed
   * on it, so the cue would appear and be pressed through in the same gesture.
   * Nothing is lost by leaving it out: nobody needs telling to press what they
   * are already touching.
   */
  let overControls = $state(false);
  let yaw = $state(REST_YAW);
  let pitch = $state(REST_PITCH);
  let hovered = $state<{ cell: string; p: number; n: number; total: number } | null>(null);

  // Height in world units. The grid is ~14 wide, so this decides how much of a
  // cliff the boundary reads as.
  const ZSCALE = 5.2;

  const cam = $derived<Camera>({ yaw, pitch, dist: 900, zoom: 26 });

  // Space the scene is NOT allowed into: the rail on the right, and a margin all
  // round for tick labels and axis titles. Must match .rail-slot.
  const RAIL_W = 178;
  const PAD = 58;
  // One threshold, used by the reserved width, the height floor AND whether the
  // rail renders. A CSS media query cannot be that threshold: it measures the
  // viewport while everything here measures the container, and the two disagree
  // by the page gutters -- which is how the rail stayed visible at 720px inside
  // a plot that had already dropped to its short floor.
  const RAIL_MIN_W = 700;
  const showRail = $derived(w > RAIL_MIN_W);
  const railW = $derived(showRail ? RAIL_W : 0);
  const order = $derived(groundOrder(DIM - 1, yaw));

  /**
   * Cells that actually have `t` trials behind them, which is not all of them.
   *
   * This read `o.length >= 1` and so was the constant 196 under a title that
   * says "after {t} trials". At the end of the scrub the header claimed 196
   * cells at 55 trials, which is 10,780 outcomes against the 2,426 that exist;
   * only one cell reaches 55. `rateAt` already truncates each cell at its own
   * ceiling, so the surface was honest and the number above it was not.
   */
  const cellsAtT = $derived(Object.values(SURFACE.cells).filter((o) => o.length >= t).length);
  /** And the outcomes actually behind the shape, for the same reason. At t = 1
   *  the surface stands on 196 of the 2,426, one per cell. */
  const outcomesAtT = $derived(
    Object.values(SURFACE.cells).reduce((a, o) => a + Math.min(t, o.length), 0),
  );

  function heightAt(a: number, b: number): number | null {
    const r = rateAt(SURFACE.cells[`${a}x${b}`], t);
    return r ? r.p : null;
  }

  function draw() {
    const c = canvas;
    if (!c) return;
    const ctx = c.getContext('2d');
    if (!ctx) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    if (c.width !== Math.round(w * dpr) || c.height !== Math.round(h * dpr)) {
      c.width = Math.round(w * dpr);
      c.height = Math.round(h * dpr);
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    const mid = (DIM + 1) / 2;
    // Fit the scene to the space that is actually free, at whatever angle it is
    // being viewed from. Centring alone is not enough: the footprint is smallest
    // seen edge-on and largest seen from above, so a fixed zoom that looks right
    // at one pitch runs off the canvas and under the rail at another.
    //
    // Project the scene's corners about the origin first, then apply a single
    // screen-space multiplier. That is a viewport zoom, not a camera move, so it
    // rescales without touching the perspective the camera already decided.
    // EYE LEVEL SITS HALFWAY UP THE HEIGHT AXIS, not on the ground. Looking at
    // z=0 puts the whole surface above the line of sight, so every cell is read
    // from underneath and the plateau hides what is behind it. Centring on
    // ZSCALE/2 means the reliable half rises above the eye and the collapsed
    // half falls below it, and the boundary between them is the one place the
    // surface crosses the viewer's own level.
    const raw = (a: number, b: number, z: number) =>
      project(a - mid, b - mid, z * ZSCALE - ZSCALE / 2, cam, 0, 0);
    let bx0 = Infinity, bx1 = -Infinity, by0 = Infinity, by1 = -Infinity;
    for (const a0 of [1, DIM]) {
      for (const b0 of [1, DIM]) {
        for (const z0 of [0, 1]) {
          const q = raw(a0, b0, z0);
          bx0 = Math.min(bx0, q.sx); bx1 = Math.max(bx1, q.sx);
          by0 = Math.min(by0, q.sy); by1 = Math.max(by1, q.sy);
        }
      }
    }
    const availW = Math.max(80, w - railW - PAD * 2);
    const availH = Math.max(80, h - PAD * 2);
    const fit = Math.min(availW / Math.max(1, bx1 - bx0), availH / Math.max(1, by1 - by0));
    const cx = PAD + availW / 2 - ((bx0 + bx1) / 2) * fit;
    const cy = PAD + availH / 2 - ((by0 + by1) / 2) * fit;
    const P = (a: number, b: number, z: number) => {
      const q = raw(a, b, z);
      return { sx: cx + q.sx * fit, sy: cy + q.sy * fit, depth: q.depth };
    };

    // floor grid first, so the surface sits on something
    ctx.strokeStyle = 'rgba(70,80,105,0.32)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let g = 1; g <= DIM; g++) {
      const a0 = P(g, 1, 0);
      const a1 = P(g, DIM, 0);
      const b0 = P(1, g, 0);
      const b1 = P(DIM, g, 0);
      ctx.moveTo(a0.sx, a0.sy);
      ctx.lineTo(a1.sx, a1.sy);
      ctx.moveTo(b0.sx, b0.sy);
      ctx.lineTo(b1.sx, b1.sy);
    }
    ctx.stroke();

    // surface, back to front
    const n = DIM - 1;
    ctx.lineJoin = 'round';
    for (let k = 0; k < order.length; k++) {
      const q = order[k];
      const i = Math.floor(q / n) + 1;
      const j = (q % n) + 1;
      const zs = [
        heightAt(i, j),
        heightAt(i + 1, j),
        heightAt(i + 1, j + 1),
        heightAt(i, j + 1),
      ];
      if (zs.some((z) => z === null)) continue;
      const pts = [
        P(i, j, zs[0]!),
        P(i + 1, j, zs[1]!),
        P(i + 1, j + 1, zs[2]!),
        P(i, j + 1, zs[3]!),
      ];
      const mean = (zs[0]! + zs[1]! + zs[2]! + zs[3]!) / 4;

      ctx.beginPath();
      ctx.moveTo(pts[0].sx, pts[0].sy);
      for (let p = 1; p < 4; p++) ctx.lineTo(pts[p].sx, pts[p].sy);
      ctx.closePath();
      ctx.fillStyle = ramp(mean);
      ctx.fill();
      ctx.strokeStyle = 'rgba(255,255,255,0.55)';
      ctx.lineWidth = 0.6;
      ctx.stroke();
    }

    // ---- ground axes -------------------------------------------------
    //
    // The two labelled edges are CHOSEN from the camera, not fixed. Label a
    // fixed pair and the moment anyone orbits, half the ticks end up behind the
    // surface or printed across it. So: find the ground corner nearest the
    // camera, label the two edges meeting there, and push every label outward
    // along the screen-space direction from the plot centre. Labels then sit
    // outside the footprint on the near side at any angle, which is the whole
    // trick and costs four projections.
    //
    // No height axis. A vertical post floating off one corner reads as a stray
    // line, and the surface is already colour-ramped by the same quantity; the
    // caption carries the units.
    const corners: Array<[number, number]> = [
      [1, 1],
      [DIM, 1],
      [1, DIM],
      [DIM, DIM],
    ];
    let near = corners[0];
    let nearD = Infinity;
    for (const c of corners) {
      const d = P(c[0], c[1], 0).depth;
      if (d < nearD) {
        nearD = d;
        near = c;
      }
    }
    const centre = P((1 + DIM) / 2, (1 + DIM) / 2, 0);
    const outward = (px: number, py: number, by: number) => {
      const dx = px - centre.sx;
      const dy = py - centre.sy;
      const m = Math.hypot(dx, dy) || 1;
      return [px + (dx / m) * by, py + (dy / m) * by] as const;
    };

    // each entry: the fixed coordinate, and whether A or B runs along the edge
    const axes = [
      { title: 'digits in A', fixedB: near[1], along: 'a' as const },
      { title: 'digits in B', fixedA: near[0], along: 'b' as const },
    ];

    ctx.textBaseline = 'middle';
    for (const ax of axes) {
      const at = (v: number) =>
        ax.along === 'a' ? P(v, ax.fixedB!, 0) : P(ax.fixedA!, v, 0);

      // the edge itself, a shade stronger than the floor grid
      const e0 = at(1);
      const e1 = at(DIM);
      ctx.strokeStyle = 'rgba(50,60,82,0.58)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(e0.sx, e0.sy);
      ctx.lineTo(e1.sx, e1.sy);
      ctx.stroke();

      ctx.font = '10px ui-monospace, "SF Mono", monospace';
      ctx.fillStyle = 'rgba(52,62,84,0.92)';
      ctx.textAlign = 'center';
      for (let g = 2; g <= DIM; g += 2) {
        const t0 = at(g);
        const [tx, ty] = outward(t0.sx, t0.sy, 5);
        const [lx, ly] = outward(t0.sx, t0.sy, 15);
        ctx.beginPath();
        ctx.moveTo(t0.sx, t0.sy);
        ctx.lineTo(tx, ty);
        ctx.stroke();
        ctx.fillText(String(g), lx, ly);
      }

      // The title runs ALONG its edge, rotated to the edge's screen angle and
      // pushed outward past the tick labels. Set horizontally at the midpoint it
      // collides with the middle tick, and no outward offset reliably separates
      // them because near the middle the outward direction is roughly parallel
      // to the label's own width. Rotated, it is parallel to the row of ticks
      // instead of cutting across it, so clearing them is a single offset — and
      // an axis title that follows its axis is what a reader expects anyway.
      const midE = at((1 + DIM) / 2);
      const [ttx, tty] = outward(midE.sx, midE.sy, 34);
      let angle = Math.atan2(e1.sy - e0.sy, e1.sx - e0.sx);
      // never upside down
      if (angle > Math.PI / 2) angle -= Math.PI;
      if (angle < -Math.PI / 2) angle += Math.PI;
      ctx.save();
      ctx.translate(ttx, tty);
      ctx.rotate(angle);
      ctx.font = '600 11px system-ui, sans-serif';
      ctx.fillStyle = 'rgba(45,55,75,0.95)';
      ctx.textAlign = 'center';
      ctx.fillText(ax.title, 0, 0);
      ctx.restore();
    }
  }

  $effect(() => {
    // touch the reactive inputs so a change to any of them repaints
    t; yaw; pitch; w; h; order;
    draw();
  });

  observeWidth(() => host, (width) => {
    w = Math.max(280, Math.floor(width));
    // Where the rail is shown the plot must be at least as tall as it is, or
    // eight sparklines run off the bottom of a plot that shrank with the
    // window. Below the rail's breakpoint the shorter floor applies again.
    const floor = width > RAIL_MIN_W ? 450 : 300;
    h = Math.max(floor, Math.round(Math.min(480, width * 0.58)));
  });

  onMount(() => () => {
    // A `walk` parked on its scroll-settle timer outlives the component
    // otherwise, and wakes to set `motion` on state nothing renders. Bumping
    // the generation makes it return instead. Same reason as the panels below.
    walkGen += 1;
  });

  const lessMotion = () =>
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /** Scroll settle before the first trial lands. Nothing measures the scroll,
   *  so without the wait the reader watches the opening frames go past while
   *  the page is still moving, which is the half they most need to see. Same
   *  number and same reason as the trace figure's presenter. */
  const SETTLE_MS = 420;

  /**
   * Start at one trial, at the opening angle, and turn while it assembles.
   *
   * A RESET, not a resume. Someone pressing this has asked to see the thing
   * from the beginning, and starting the turn from wherever the last drag left
   * the camera would give two readers two different figures.
   *
   * The figure comes into view first and the clock starts after. `arming`
   * covers that gap in the reported flag, so the button is already disabled
   * while the page is travelling and a second press cannot stack a second walk
   * on top of the first.
   */
  export async function walk() {
    const gen = ++walkGen;
    arming = true;
    motion = 'idle'; // nothing steps while the page is moving
    t = 1;
    yaw = WALK_YAW;
    pitch = WALK_PITCH;

    const still = lessMotion();
    rootEl?.scrollIntoView({ behavior: still ? 'auto' : 'smooth', block: 'start' });
    if (!still) {
      await new Promise<void>((r) => setTimeout(r, SETTLE_MS));
      // A second press while this one was travelling owns the figure now, and
      // it has already set its own `arming`. Leave both alone.
      if (gen !== walkGen) return;
    }

    arming = false;
    motion = 'walk';
  }

  /** One place reports the flag, so every route out of `walk` -- finishing,
   *  pausing, scrubbing, grabbing the surface -- clears it without each of them
   *  having to remember to. */
  $effect(() => {
    onWalkChange?.(motion === 'walk' || arming);
  });

  // Playback runs once and stops on the last frame. Looping would restart the
  // surface from a single trial every few seconds, and the whole claim is that
  // it stops moving -- an animation that keeps resetting says the opposite.
  $effect(() => {
    if (motion === 'idle') return;
    const turning = motion === 'walk';
    walkGen; // restart the loop when `walk` is pressed during a walk
    // Read once. The RAF callback below is outside the effect's tracking scope,
    // which is what keeps a loop that writes `t` from re-running itself.
    const turnMs = (MAXT - 1) * STEP_MS;
    let raf = 0;
    let last = 0;
    let began = 0;
    const step = (now: number) => {
      if (!began) { began = now; last = now; }
      if (turning) {
        // Smoothstep, so the turn eases out of the opening angle and settles
        // into the resting one instead of stopping dead on the last frame.
        const u = Math.min(1, (now - began) / turnMs);
        const e = u * u * (3 - 2 * u);
        yaw = WALK_YAW + (REST_YAW - WALK_YAW) * e;
        pitch = WALK_PITCH + (REST_PITCH - WALK_PITCH) * e;
      }
      if (now - last > STEP_MS) {
        last = now;
        if (t >= MAXT) {
          // Land on the resting angle exactly. The eased turn gets within a
          // hair of it, and a surface left a hair off square is the kind of
          // thing a reader sees without being able to say what is wrong.
          if (turning) { yaw = REST_YAW; pitch = REST_PITCH; }
          motion = 'idle'; // button falls back to play; the frame stays put
          return;
        }
        t += 1;
      }
      raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  });

  function togglePlay() {
    onReaderDrive?.();
    // Pausing a walk leaves the camera where it got to. The reader stopped it
    // to look at that frame, and snapping the surface square would take away
    // the thing they stopped for.
    if (moving) { motion = 'idle'; return; }
    // pressing play on the last frame replays rather than doing nothing
    if (t >= MAXT) t = 1;
    motion = 'play';
  }

  // orbit
  let dragging = false;
  let lastX = 0;
  let lastY = 0;
  function down(e: PointerEvent) {
    onReaderDrive?.();
    dragging = true;
    lastX = e.clientX;
    lastY = e.clientY;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  }
  function move(e: PointerEvent) {
    if (!dragging) return;
    /**
     * TURNING IT BY HAND TAKES THE CAMERA, NOT THE CLOCK.
     *
     * A walk drives two things, and a drag only conflicts with one of them.
     * Stopping the trial count as well would punish the reader for looking at
     * the surface from a different side, which is the one thing the figure
     * spends its whole existence inviting. So a walk demotes to a play: the
     * camera is handed over mid-turn and the surface keeps filling.
     *
     * The demotion is here rather than in `down` on purpose. A press that never
     * moves is not a drag, and killing the turn on a stray click would make the
     * figure feel like it breaks when touched.
     *
     * Stopping is left to the controls that mean stop -- the pause button and
     * the trial slider. Both of those are the reader asking about the count,
     * which is the thing they actually stop.
     */
    if (motion === 'walk') motion = 'play';
    yaw += (e.clientX - lastX) * 0.008;
    pitch = Math.max(0.08, Math.min(1.35, pitch + (e.clientY - lastY) * 0.005));
    lastX = e.clientX;
    lastY = e.clientY;
  }
  function up(e: PointerEvent) {
    dragging = false;
    (e.currentTarget as HTMLElement).releasePointerCapture?.(e.pointerId);
  }
</script>

<figure class="surface" bind:this={rootEl}>
  <div class="head">
    <span class="title">P(exactly correct) after <strong>{t}</strong> {t === 1 ? 'trial' : 'trials'}</span>
    <span class="meta mono">
      {SURFACE.model} · {cellsAtT} of {DIM * DIM} cells · {outcomesAtT.toLocaleString()} of
      {SURFACE.outcomes.toLocaleString()} outcomes
    </span>
  </div>

  <div class="plot">
    <!-- The rail is a SIBLING of the stage, not a child. role="img" makes its
         element's whole subtree presentational, so a rail nested inside the
         stage had every one of its numbers hidden from screen readers. -->
    <div
      class="stage"
      bind:this={host}
      onpointerdown={down}
      onpointermove={move}
      onpointerup={up}
      onpointercancel={up}
      role="img"
      aria-label="Reliability surface: digits in factor A by digits in factor B by probability of an exactly correct product, at {t} {t === 1 ? 'trial' : 'trials'} each. Drag to rotate."
    >
      <canvas bind:this={canvas} style:width="{w}px" style:height="{h}px"></canvas>
      <span class="hint">drag to rotate</span>
    </div>
    <!-- The plot is centred, so its flanks are dead space at every camera angle.
         The rail overlays them rather than taking width from the canvas, and is
         pointer-transparent so a drag through it still orbits. -->
    {#if showRail}
      <div class="rail-slot"><ConvergenceRail {t} max={MAXT} /></div>
    {/if}
  </div>

  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="controls"
    onpointerenter={(e) => { if (e.pointerType === 'mouse') overControls = true; }}
    onpointerleave={() => (overControls = false)}
  >
    <span class="play-slot">
      {#if overControls && !moving}<Cue text="press me" side="right" />{/if}
      <button
        class="play"
        onclick={togglePlay}
        aria-label={moving ? 'Pause' : t >= MAXT ? 'Replay from the first trial' : 'Play'}
      >
        {moving ? '❚❚' : t >= MAXT ? '↺' : '▶'}
      </button>
    </span>
    <input
      type="range"
      min="1"
      max={MAXT}
      bind:value={t}
      oninput={() => { onReaderDrive?.(); motion = 'idle'; }}
      aria-label="Trials per cell"
    />
    <span class="count mono">{t}/{MAXT}</span>
  </div>

</figure>

<style>
  .surface {
    /* Aligning the figure's top to the viewport's top would push the walk
       button off the screen, and the reader who wants to press it again then
       has to hunt back up the page. This is roughly the button plus its own
       margins, so it lands just above the fold and stays reachable. */
    scroll-margin-top: 120px;
  }

  .head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 4px 12px;
    margin-bottom: 6px;
  }
  .title { font-size: var(--text-sm); color: var(--ink-dim); }
  .title strong { color: var(--ink); font-variant-numeric: tabular-nums; }
  .meta { font-size: 0.68rem; color: var(--ink-faint); }

  .plot {
    position: relative;
    border: 1px solid var(--line);
    border-radius: var(--radius-sm);
    background: var(--panel);
    overflow: hidden;
  }
  .stage {
    cursor: grab;
    touch-action: pan-y;
  }
  .stage:active { cursor: grabbing; }
  canvas { display: block; }
  .rail-slot {
    position: absolute;
    top: 10px;
    right: 10px;
    width: 158px; /* + the 10px inset = the RAIL_W the canvas reserves */
    pointer-events: none;
  }
  .hint {
    position: absolute;
    left: 10px;      /* the rail owns the right flank */
    bottom: 6px;
    font-family: var(--font-mono);
    font-size: 9px;
    color: var(--ink-faint);
    pointer-events: none;
    user-select: none;
  }

  .controls {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 8px;
  }
  /* The cue positions against this, not against the row, so the arrowhead
     lands on the button rather than somewhere along the slider. Sized to the
     button by `inline-flex` for the same reason. */
  .play-slot {
    position: relative;
    display: inline-flex;
    flex: 0 0 auto;
  }
  /* The cue's own resting height puts its arrowhead level with the button's
     bottom edge, which is exactly where the slider thumb sits at trial one.
     Lifting it to the button's top edge keeps the arrow on the button and the
     label clear of the track. The anchor belongs to the caller, which is why
     this override lives here and not in Cue. */
  .play-slot :global(.cue.right) {
    bottom: 15px;
  }
  .play {
    flex: 0 0 auto;
    width: 26px;
    height: 26px;
    border: 1px solid var(--line);
    border-radius: var(--radius-sm);
    background: var(--bg);
    color: var(--ink-dim);
    font-size: 10px;
    line-height: 1;
    cursor: pointer;
  }
  .play:hover { border-color: var(--line-strong); color: var(--ink); }
  input[type='range'] { flex: 1 1 auto; accent-color: var(--accent); }
  .count {
    flex: 0 0 auto;
    font-size: 0.7rem;
    color: var(--ink-faint);
    font-variant-numeric: tabular-nums;
    min-width: 3.4em;
    text-align: right;
  }

</style>
