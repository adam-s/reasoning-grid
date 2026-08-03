<script lang="ts">
  /**
   * The better model at every size — Qwen alone, or the better of the two.
   *
   * Height is the chance of an exactly correct product. Colour is which model
   * reached it, with the reliability ramp running INSIDE each hue, so lightness
   * carries how well and hue carries which.
   *
   * ## One tile per cell, not quads between cells
   *
   * SurfaceCanvas draws quads spanning four cells, which is right when the only
   * thing on the surface is a continuous height. Here colour is a CATEGORY
   * attached to a cell, and a quad has four cells at its corners, so there is no
   * honest rule for colouring one. Painting a quad orange whenever any corner is
   * orange turns 15 cells into 40 of 121 quads; averaging the corners instead
   * turns them into 7. Neither is 15.
   *
   * So each cell owns a tile spanning half a step in every direction, and the
   * tile's corner heights are the mean of the cells meeting at that corner.
   * Adjacent tiles compute the same corner from the same neighbours, so the
   * sheet stays continuous with no cracks, and exactly 15 tiles are orange.
   *
   * The general rule, learned the expensive way on the published version: a
   * quantity attached to grid VERTICES must be drawn with vertex-owned tiles,
   * never with the faces between them. Faces interpolate, and on a steep slope
   * they turn toward the camera and fill the screen — the sheet version put
   * orange over 60% of the surface to represent 7.8% of the problems.
   *
   * Draw order and projection are project.ts, unchanged; see its note on why
   * ground-plane ordering is exact for a heightfield rather than approximate.
   */
  import { onMount, untrack } from 'svelte';
  import { WINNER } from '../../data/winner';
  import { project, type Camera } from './project';

  let canvas: HTMLCanvasElement | null = $state(null);
  let host: HTMLDivElement | null = $state(null);
  let w = $state(760);
  let h = $state(440);

  /** 0 = Qwen alone, 1 = the better of the two. Animated, never switched. */
  let mix = $state(0);
  let target = $state(0);
  let yaw = $state(-0.62);
  let pitch = $state(0.5);

  const DIM = WINNER.dim;
  const ZSCALE = 5.0;
  const PAD = 54;
  const HALF = 0.5;

  const cam = $derived<Camera>({ yaw, pitch, dist: 900, zoom: 26 });
  const F = WINNER.findings;

  // The published chart's ramp, which is this repo's surface ramp: pale at a low
  // rate, deep at a high one. Two hues rather than one, because the rate is
  // ordered but the winner is not. Blue is the shared --accent; the orange is
  // built to match its luminance so neither reads as heavier at the same rate.
  const RAMP = {
    qwen: [
      [232, 236, 243],
      [31, 58, 95],
    ],
    phi: [
      [247, 237, 224],
      [138, 74, 18],
    ],
  } as const;

  function at(a: number, b: number) {
    return WINNER.cells[`${a}x${b}`] ?? null;
  }
  /** Qwen alone at mix 0, the better of the two at mix 1. */
  function heightAt(a: number, b: number): number | null {
    const c = at(a, b);
    if (!c) return null;
    return c.qwen + (Math.max(c.qwen, c.phi) - c.qwen) * mix;
  }
  function phiWins(a: number, b: number): boolean {
    const c = at(a, b);
    return !!c && c.phi > c.qwen;
  }
  /** Fewer problems behind a cell, less saturated — never less bright, which
   *  would compete with the rate for the same channel. */
  function evidence(a: number, b: number): number {
    const c = at(a, b);
    return c ? 0.55 + 0.45 * Math.min(1, c.n / 12) : 0;
  }

  /**
   * A tile corner sits BETWEEN cells, so its height is the mean of the cells
   * meeting there. Adjacent tiles ask for the same corner and get the same
   * answer, which is what keeps the sheet continuous instead of cracked.
   */
  function cornerHeight(u: number, v: number): number | null {
    let sum = 0;
    let k = 0;
    for (const a of [u - HALF, u + HALF]) {
      for (const b of [v - HALF, v + HALF]) {
        const z = heightAt(a, b);
        if (z !== null) {
          sum += z;
          k += 1;
        }
      }
    }
    return k ? sum / k : null;
  }

  function tone(rate: number, phi: boolean, ev: number, blend: number): string {
    const t = Math.max(0, Math.min(1, rate));
    const k = phi ? blend : 0;
    const c = [0, 1, 2].map((i) => {
      const A = RAMP.qwen[0][i] + (RAMP.qwen[1][i] - RAMP.qwen[0][i]) * t;
      const B = RAMP.phi[0][i] + (RAMP.phi[1][i] - RAMP.phi[0][i]) * t;
      return A + (B - A) * k;
    });
    const lum = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
    return `rgb(${c.map((v) => Math.round(v + (lum - v) * (1 - ev))).join(',')})`;
  }

  function draw() {
    const el = canvas;
    if (!el) return;
    const ctx = el.getContext('2d');
    if (!ctx) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    if (el.width !== Math.round(w * dpr) || el.height !== Math.round(h * dpr)) {
      el.width = Math.round(w * dpr);
      el.height = Math.round(h * dpr);
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    const mid = (DIM + 1) / 2;
    // Fit the scene to the space actually free at whatever angle it is being
    // viewed from, as a screen-space multiplier applied AFTER the perspective
    // divide — a viewport zoom, not a camera move, so framing cannot skew the
    // projection. Corners include the half-step the tiles extend past the grid.
    const raw = (a: number, b: number, z: number) =>
      project(a - mid, b - mid, z * ZSCALE, cam, 0, 0);
    let bx0 = Infinity, bx1 = -Infinity, by0 = Infinity, by1 = -Infinity;
    for (const a0 of [1 - HALF, DIM + HALF]) {
      for (const b0 of [1 - HALF, DIM + HALF]) {
        for (const z0 of [0, 1]) {
          const q = raw(a0, b0, z0);
          bx0 = Math.min(bx0, q.sx); bx1 = Math.max(bx1, q.sx);
          by0 = Math.min(by0, q.sy); by1 = Math.max(by1, q.sy);
        }
      }
    }
    const availW = Math.max(80, w - PAD * 2);
    const availH = Math.max(80, h - PAD * 2);
    const fit = Math.min(availW / Math.max(1, bx1 - bx0), availH / Math.max(1, by1 - by0));
    const cx = PAD + availW / 2 - ((bx0 + bx1) / 2) * fit;
    const cy = PAD + availH / 2 - ((by0 + by1) / 2) * fit;
    const P = (a: number, b: number, z: number) => {
      const q = raw(a, b, z);
      return { sx: cx + q.sx * fit, sy: cy + q.sy * fit, depth: q.depth };
    };

    // floor grid, so the sheet reads as relief against something
    ctx.strokeStyle = 'rgba(70,80,105,0.30)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let g = 1; g <= DIM; g++) {
      const a0 = P(g, 1, 0), a1 = P(g, DIM, 0);
      const b0 = P(1, g, 0), b1 = P(DIM, g, 0);
      ctx.moveTo(a0.sx, a0.sy); ctx.lineTo(a1.sx, a1.sy);
      ctx.moveTo(b0.sx, b0.sy); ctx.lineTo(b1.sx, b1.sy);
    }
    ctx.stroke();

    // Tiles are keyed on their own cell centre, so the order is the same
    // ground-plane ordering project.ts justifies — just over cells rather than
    // over the quads between them.
    const s = Math.sin(yaw), c = Math.cos(yaw);
    const tiles: Array<{ a: number; b: number; d: number }> = [];
    for (let a = 1; a <= DIM; a++) {
      for (let b = 1; b <= DIM; b++) {
        if (heightAt(a, b) !== null) tiles.push({ a, b, d: (a - mid) * s + (b - mid) * c });
      }
    }
    tiles.sort((p, q) => q.d - p.d); // farthest first

    for (const tl of tiles) {
      const { a, b } = tl;
      const pts = [
        [-HALF, -HALF], [HALF, -HALF], [HALF, HALF], [-HALF, HALF],
      ].map(([u, v]) => P(a + u, b + v, cornerHeight(a + u, b + v) ?? 0));
      ctx.beginPath();
      ctx.moveTo(pts[0].sx, pts[0].sy);
      for (let k = 1; k < 4; k++) ctx.lineTo(pts[k].sx, pts[k].sy);
      ctx.closePath();
      ctx.fillStyle = tone(
        heightAt(a, b) as number,
        phiWins(a, b),
        evidence(a, b),
        phiWins(a, b) ? mix : 0,
      );
      ctx.fill();
      ctx.globalAlpha = 0.4;
      ctx.strokeStyle = '#f7f5f0';
      ctx.lineWidth = 0.7;
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    // Axes on the two ground edges nearest the camera, chosen from the camera
    // rather than fixed — label a fixed pair and half the ticks end up behind
    // the surface the moment anyone orbits.
    const corners: Array<[number, number]> = [[1, 1], [DIM, 1], [1, DIM], [DIM, DIM]];
    let near = corners[0];
    let nearD = Infinity;
    for (const cr of corners) {
      const d = P(cr[0], cr[1], 0).depth;
      if (d < nearD) { nearD = d; near = cr; }
    }
    const centre = P(mid, mid, 0);
    const outward = (px: number, py: number, by: number) => {
      const dx = px - centre.sx, dy = py - centre.sy;
      const m = Math.hypot(dx, dy) || 1;
      return [px + (dx / m) * by, py + (dy / m) * by] as const;
    };

    ctx.textBaseline = 'middle';
    for (const ax of [
      { title: 'digits in A', fixed: near[1], along: 'a' as const },
      { title: 'digits in B', fixed: near[0], along: 'b' as const },
    ]) {
      const pt = (v: number) =>
        ax.along === 'a' ? P(v, ax.fixed, 0) : P(ax.fixed, v, 0);
      const e0 = pt(1), e1 = pt(DIM);
      ctx.strokeStyle = 'rgba(50,60,82,0.55)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(e0.sx, e0.sy);
      ctx.lineTo(e1.sx, e1.sy);
      ctx.stroke();

      ctx.font = '10px ui-monospace, "SF Mono", monospace';
      ctx.fillStyle = 'rgba(52,62,84,0.92)';
      ctx.textAlign = 'center';
      for (let g = 2; g <= DIM; g += 2) {
        const t0 = pt(g);
        const [tx, ty] = outward(t0.sx, t0.sy, 5);
        const [lx, ly] = outward(t0.sx, t0.sy, 15);
        ctx.beginPath();
        ctx.moveTo(t0.sx, t0.sy);
        ctx.lineTo(tx, ty);
        ctx.stroke();
        ctx.fillText(String(g), lx, ly);
      }
      const midE = pt(mid);
      const [ttx, tty] = outward(midE.sx, midE.sy, 33);
      let angle = Math.atan2(e1.sy - e0.sy, e1.sx - e0.sx);
      if (angle > Math.PI / 2) angle -= Math.PI;
      if (angle < -Math.PI / 2) angle += Math.PI;
      ctx.save();
      ctx.translate(ttx, tty);
      ctx.rotate(angle);
      ctx.font = '600 11px system-ui, sans-serif';
      ctx.fillStyle = 'rgba(45,55,75,0.95)';
      ctx.fillText(ax.title, 0, 0);
      ctx.restore();
    }
  }

  $effect(() => {
    mix; yaw; pitch; w; h;
    draw();
  });

  /**
   * Interpolate between the two height fields rather than swapping them.
   * Switching two static pictures makes a reader hunt for what changed, and
   * what changed IS the point: 15 tiles rise a little and turn orange, and the
   * other 129 do not move at all.
   */
  $effect(() => {
    const to = target;
    // `mix` is READ UNTRACKED. Reading it normally makes this effect depend on
    // the value its own animation frame writes, so every frame invalidates the
    // effect, cancels the pending frame and restarts the tween from wherever it
    // got to -- with the clock reset, so each restart advances by the first
    // instant of an ease-in curve. The result creeps toward the target and
    // never arrives: the toggle appeared to do almost nothing.
    const from = untrack(() => mix);
    if (to === from) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      mix = to;
      return;
    }
    const t0 = performance.now();
    let raf = 0;
    const step = (now: number) => {
      const u = Math.min(1, (now - t0) / 520);
      const e = u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2;
      mix = from + (to - from) * e;
      if (u < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  });

  onMount(() => {
    const ro = new ResizeObserver((e) => {
      const r = e[0]?.contentRect;
      if (r) {
        w = Math.max(280, Math.floor(r.width));
        h = Math.max(320, Math.round(Math.min(470, r.width * 0.54)));
      }
    });
    if (host) ro.observe(host);
    return () => ro.disconnect();
  });

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
    // below ~0.16 the floor collapses to a line and it stops being a chart
    pitch = Math.max(0.16, Math.min(1.3, pitch + (e.clientY - lastY) * 0.005));
    lastX = e.clientX;
    lastY = e.clientY;
  }
  function up(e: PointerEvent) {
    dragging = false;
    (e.currentTarget as HTMLElement).releasePointerCapture?.(e.pointerId);
  }

  const pct = (x: number) => `${Math.round(x * 100)}%`;
</script>

<figure class="winner">
  <div class="head">
    <span class="title">
      {target === 0 ? 'Qwen alone' : 'The better of the two'} &mdash; P(exactly correct)
    </span>
    <span class="meta mono">
      {WINNER.problems.toLocaleString()} problems · both models, same questions
    </span>
  </div>

  <div class="ctl" role="group" aria-label="which models to include">
    <button class:on={target === 0} aria-pressed={target === 0} onclick={() => (target = 0)}>
      Qwen alone
    </button>
    <button class:on={target === 1} aria-pressed={target === 1} onclick={() => (target = 1)}>
      Better of the two
    </button>
  </div>

  <div
    class="stage"
    bind:this={host}
    onpointerdown={down}
    onpointermove={move}
    onpointerup={up}
    onpointercancel={up}
    role="img"
    aria-label="Surface of the probability of an exactly correct product by the digit
      counts of the two factors. {F.qwenLevelOrAhead} of {F.qwenLevelOrAhead + F.phiAhead}
      cells are Qwen level or higher; the {F.phiAhead} where Phi is higher are orange and
      scattered along the falling edge. Drag to rotate."
  >
    <canvas bind:this={canvas} style:width="{w}px" style:height="{h}px"></canvas>
    <span class="hint mono">drag to rotate</span>
  </div>

  <div class="key">
    <span><i class="sw qwen"></i>Qwen level or higher</span>
    <span><i class="sw phi"></i>Phi higher</span>
    <span class="dim">· pale to deep = 0 to 100% correct</span>
    <span class="dim">· greyer = fewer problems behind it</span>
  </div>

  <figcaption>
    Switching from Qwen alone to the better of the two lifts
    <strong>{F.phiAhead} tiles of {F.phiAhead + F.qwenLevelOrAhead}</strong> and leaves
    the rest exactly where they were. Both models hold the small sizes and fall off the
    same cliff: fitted, Qwen is still right half the time at
    <strong>{F.halfAt[0]}&times;{F.halfAt[0]}</strong> digits and Phi at
    <strong>{F.halfAt[1]}&times;{F.halfAt[1]}</strong> &mdash; the same curve shifted by
    {(F.halfAt[0] - F.halfAt[1]).toFixed(1)} digits, never crossing. Overall
    <strong>{pct(WINNER.overall[0])}</strong> against
    <strong>{pct(WINNER.overall[1])}</strong>.
  </figcaption>
</figure>

<style>
  .winner { margin: var(--space-md) 0 var(--space-lg); }

  .head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 4px 12px;
    margin-bottom: 8px;
  }
  .title { font-size: var(--text-sm); color: var(--ink-dim); }
  .meta { font-size: 0.68rem; color: var(--ink-faint); }

  .ctl {
    display: inline-flex;
    border: 1px solid var(--line);
    border-radius: 5px;
    overflow: hidden;
    background: var(--panel);
    margin-bottom: 10px;
  }
  .ctl button {
    appearance: none;
    border: 0;
    background: none;
    cursor: pointer;
    color: var(--ink-dim);
    font-family: var(--font-sans);
    font-size: 0.78rem;
    padding: 7px 15px;
    transition: background 0.15s, color 0.15s;
  }
  .ctl button + button { border-left: 1px solid var(--line); }
  .ctl button:hover { color: var(--ink); }
  .ctl button.on { background: var(--accent); color: var(--bg); }
  .ctl button:focus-visible { outline: 2px solid var(--pos); outline-offset: -2px; }

  .stage {
    position: relative;
    border: 1px solid var(--line);
    border-radius: 5px;
    background: var(--panel);
    overflow: hidden;
    touch-action: pan-y;
    cursor: grab;
  }
  .stage:active { cursor: grabbing; }
  canvas { display: block; }
  .hint {
    position: absolute;
    left: 11px;
    bottom: 8px;
    font-size: 0.56rem;
    letter-spacing: 0.08em;
    color: var(--ink-faint);
    pointer-events: none;
  }

  .key {
    display: flex;
    gap: 18px;
    align-items: center;
    flex-wrap: wrap;
    margin-top: 12px;
    font-family: var(--font-sans);
    font-size: 0.74rem;
    color: var(--ink-dim);
  }
  .key .dim { color: var(--ink-faint); }
  .sw {
    display: inline-block;
    width: 34px;
    height: 10px;
    border-radius: 2px;
    vertical-align: -1px;
    margin-right: 7px;
  }
  .sw.qwen { background: linear-gradient(90deg, rgb(232, 236, 243), rgb(31, 58, 95)); }
  .sw.phi { background: linear-gradient(90deg, rgb(247, 237, 224), rgb(138, 74, 18)); }

  figcaption {
    margin-top: 14px;
    font-family: var(--font-sans);
    font-size: 0.82rem;
    line-height: 1.6;
    color: var(--ink-faint);
    max-width: 66ch;
  }
  figcaption strong { color: var(--ink-dim); font-weight: 600; }

  @media (prefers-reduced-motion: reduce) {
    .ctl button { transition: none; }
  }
</style>
