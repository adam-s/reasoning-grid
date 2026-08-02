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
  import { SURFACE } from '../../data/surface';
  import { project, groundOrder, rateAt, ramp, type Camera } from './project';

  let canvas: HTMLCanvasElement | null = $state(null);
  let host: HTMLDivElement | null = $state(null);
  let w = $state(760);
  let h = $state(440);

  const DIM = SURFACE.dim;
  const MAXT = SURFACE.maxTrials;

  let t = $state(1);
  let playing = $state(false);
  let yaw = $state(-0.62);
  let pitch = $state(0.52);
  let dark = $state(false);
  let hovered = $state<{ cell: string; p: number; n: number; total: number } | null>(null);

  // Height in world units. The grid is ~14 wide, so this decides how much of a
  // cliff the boundary reads as.
  const ZSCALE = 5.2;

  const cam = $derived<Camera>({ yaw, pitch, dist: 900, zoom: 26 });
  const order = $derived(groundOrder(DIM - 1, yaw));

  const stillMeasuring = $derived(
    Object.values(SURFACE.cells).filter((o) => o.length > t).length,
  );
  const cellsAtT = $derived(Object.values(SURFACE.cells).filter((o) => o.length >= 1).length);

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
    // cx/cy are added after the perspective divide, so framing is a pure
    // translation: project the scene's corners about the origin, then shift the
    // whole thing so its bounding box is centred. Without this the composition
    // slides off as soon as anyone orbits.
    let bx0 = Infinity, bx1 = -Infinity, by0 = Infinity, by1 = -Infinity;
    for (const a0 of [1, DIM]) {
      for (const b0 of [1, DIM]) {
        for (const z0 of [0, 1]) {
          const q = project(a0 - mid, b0 - mid, z0 * ZSCALE, cam, 0, 0);
          bx0 = Math.min(bx0, q.sx); bx1 = Math.max(bx1, q.sx);
          by0 = Math.min(by0, q.sy); by1 = Math.max(by1, q.sy);
        }
      }
    }
    const cx = w / 2 - (bx0 + bx1) / 2;
    const cy = h / 2 - (by0 + by1) / 2;
    const P = (a: number, b: number, z: number) =>
      project(a - mid, b - mid, z * ZSCALE, cam, cx, cy);

    // floor grid first, so the surface sits on something
    ctx.strokeStyle = dark ? 'rgba(190,200,220,0.30)' : 'rgba(70,80,105,0.32)';
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
      ctx.fillStyle = ramp(mean, dark);
      ctx.fill();
      ctx.strokeStyle = dark ? 'rgba(10,14,22,0.55)' : 'rgba(255,255,255,0.55)';
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
      ctx.strokeStyle = dark ? 'rgba(205,214,232,0.62)' : 'rgba(50,60,82,0.58)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(e0.sx, e0.sy);
      ctx.lineTo(e1.sx, e1.sy);
      ctx.stroke();

      ctx.font = '10px ui-monospace, "SF Mono", monospace';
      ctx.fillStyle = dark ? 'rgba(212,220,236,0.92)' : 'rgba(52,62,84,0.92)';
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
      ctx.fillStyle = dark ? 'rgba(210,218,232,0.95)' : 'rgba(45,55,75,0.95)';
      ctx.textAlign = 'center';
      ctx.fillText(ax.title, 0, 0);
      ctx.restore();
    }
  }

  $effect(() => {
    // touch the reactive inputs so a change to any of them repaints
    t; yaw; pitch; w; h; dark; order;
    draw();
  });

  onMount(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const readTheme = () => {
      const attr = document.documentElement.dataset.theme;
      dark = attr === 'dark' ? true : attr === 'light' ? false : mq.matches;
    };
    readTheme();
    mq.addEventListener('change', readTheme);
    const mo = new MutationObserver(readTheme);
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

    const ro = new ResizeObserver((e) => {
      const r = e[0]?.contentRect;
      if (r) {
        w = Math.max(280, Math.floor(r.width));
        h = Math.max(300, Math.round(Math.min(480, r.width * 0.58)));
      }
    });
    if (host) ro.observe(host);

    return () => {
      mq.removeEventListener('change', readTheme);
      mo.disconnect();
      ro.disconnect();
    };
  });

  // playback
  $effect(() => {
    if (!playing) return;
    let raf = 0;
    let last = 0;
    const step = (now: number) => {
      if (now - last > 130) {
        last = now;
        t = t >= MAXT ? 1 : t + 1;
      }
      raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  });

  // orbit
  let dragging = false;
  let lastX = 0;
  let lastY = 0;
  function down(e: PointerEvent) {
    dragging = true;
    lastX = e.clientX;
    lastY = e.clientY;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  }
  function move(e: PointerEvent) {
    if (!dragging) return;
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

<figure class="surface">
  <div class="head">
    <span class="title">P(exactly correct) after <strong>{t}</strong> {t === 1 ? 'trial' : 'trials'}</span>
    <span class="meta mono">
      {SURFACE.model} · {cellsAtT} cells · {SURFACE.outcomes.toLocaleString()} outcomes
    </span>
  </div>

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

  <div class="controls">
    <button class="play" onclick={() => (playing = !playing)} aria-label={playing ? 'Pause' : 'Play'}>
      {playing ? '❚❚' : '▶'}
    </button>
    <input
      type="range"
      min="1"
      max={MAXT}
      bind:value={t}
      oninput={() => (playing = false)}
      aria-label="Trials per cell"
    />
    <span class="count mono">{t}/{MAXT}</span>
  </div>

  <figcaption>
    <strong>{stillMeasuring}</strong> of {cellsAtT} cells still have trials left at this point.
    Saturated corners were given three and freeze early; cells in the transition band were given
    twelve or more and keep moving. Where the terrain is still changing late is exactly where the
    sampling plan decided the answer was worth buying.
  </figcaption>
</figure>

<style>
  .surface { margin: var(--space-md) 0 var(--space-lg); }

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

  .stage {
    position: relative;
    border: 1px solid var(--line);
    border-radius: var(--radius-sm);
    background: var(--panel);
    overflow: hidden;
    cursor: grab;
    touch-action: pan-y;
  }
  .stage:active { cursor: grabbing; }
  canvas { display: block; }
  .hint {
    position: absolute;
    right: 8px;
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

  figcaption {
    margin-top: 8px;
    font-size: var(--text-xs);
    line-height: 1.55;
    color: var(--ink-faint);
  }
  figcaption strong { color: var(--ink-dim); font-variant-numeric: tabular-nums; }
</style>
