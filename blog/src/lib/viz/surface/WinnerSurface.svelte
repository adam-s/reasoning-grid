<script lang="ts">
  /**
   * The paired surface: Qwen alone, or the better of Qwen and Phi.
   *
   * Rendering is SurfaceCanvas's, copied rather than reinterpreted — the same
   * `ramp` from project.ts, the same quads between cell centres, the same white
   * seams, floor grid and camera-chosen axes. Two figures of the same quantity
   * a section apart should read as the same instrument, and every attempt to
   * give this one its own palette made them read as two instruments disagreeing.
   *
   * ONE HUE. Height is the quantity and the ramp is keyed to it, so a second hue
   * meaning "which model" would compete with a ramp meaning "how often". The 15
   * cells where Phi scored higher are marked with a dot instead. A category
   * cannot be painted onto quads honestly in any case: a quad spans four cells,
   * so colouring it by any one of them inflates 15 cells into 40 of 121.
   *
   * Grid is 12x12, not the 14x14 of the single-model surface, because the paired
   * sweep only reaches 12. That is a real difference in what was measured, so
   * the axes carry it rather than a smoother hiding it.
   */
  import { onMount, untrack } from 'svelte';
  import { WINNER } from '../../data/winner';
  import { project, groundOrder, ramp, type Camera } from './project';

  let canvas: HTMLCanvasElement | null = $state(null);
  let host: HTMLDivElement | null = $state(null);
  let w = $state(760);
  let h = $state(440);

  /** 0 = Qwen alone, 1 = the better of the two. Animated, never switched. */
  let mix = $state(0);
  let target = $state(0);
  let yaw = $state(-0.62);
  let pitch = $state(0.52);

  const DIM = WINNER.dim;
  const ZSCALE = 5.2;
  const PAD = 58;
  const F = WINNER.findings;

  const cam = $derived<Camera>({ yaw, pitch, dist: 900, zoom: 26 });
  const order = $derived(groundOrder(DIM - 1, yaw));

  function cell(a: number, b: number) {
    return WINNER.cells[`${a}x${b}`] ?? null;
  }
  function heightAt(a: number, b: number): number | null {
    const c = cell(a, b);
    if (!c) return null;
    return c.qwen + (Math.max(c.qwen, c.phi) - c.qwen) * mix;
  }
  function phiWins(a: number, b: number): boolean {
    const c = cell(a, b);
    return !!c && c.phi > c.qwen;
  }

  /**
   * Height anywhere on the half-step lattice, averaging only over the integer
   * neighbours the point lies between: at a cell centre the cell itself, on an
   * edge the two either side, at a face centre the four meeting there.
   *
   * That is exactly what bilinear interpolation across the face already gives,
   * so subdividing with this changes the GEOMETRY not at all — the sub-quads
   * trace the same surface the whole quads did. Only the colour gets finer.
   */
  function lattice(u: number, v: number): number | null {
    const us = Number.isInteger(u) ? [u] : [u - 0.5, u + 0.5];
    const vs = Number.isInteger(v) ? [v] : [v - 0.5, v + 0.5];
    let sum = 0;
    let k = 0;
    for (const a of us) {
      for (const b of vs) {
        const z = heightAt(a, b);
        if (z !== null) { sum += z; k += 1; }
      }
    }
    return k ? sum / k : null;
  }

  /**
   * Blue is chart 1's `ramp`, imported rather than copied so the two can never
   * drift. Orange is built to match its luminance at both ends, so neither hue
   * reads as heavier than the other at the same rate.
   */
  const ORANGE = [
    [247, 237, 224],
    [138, 74, 18],
  ] as const;
  /**
   * Blue at `mix` 0, that cell's orange at 1. The colour has to ride the toggle
   * or the surface is already orange before Phi has been added, which says the
   * opposite of what the toggle is for.
   *
   * The blue end is read back out of `ramp` rather than recomputed from the same
   * constants, so a change to project.ts cannot leave the two hues on different
   * scales without anyone noticing.
   */
  function shade(z: number, phi: boolean, k: number): string {
    const base = ramp(z);
    if (!phi || k <= 0) return base;
    const cool = base.match(/\d+/g)!.map(Number);
    const t = Math.max(0, Math.min(1, z));
    const warm = ORANGE[0].map((v, i) => v + (ORANGE[1][i] - v) * t);
    return `rgb(${cool.map((v, i) => Math.round(v + (warm[i] - v) * k)).join(',')})`;
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
    // Project the scene's corners about the origin, then apply one screen-space
    // multiplier: a viewport zoom rather than a camera move, so framing cannot
    // touch the perspective the camera already decided.
    const raw = (a: number, b: number, z: number) =>
      project(a - mid, b - mid, z * ZSCALE, cam, 0, 0);
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
    const availW = Math.max(80, w - PAD * 2);
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

    // Quads and markers go into ONE back-to-front pass. Drawn afterwards, a
    // marker on a far cell would print over terrain standing in front of it.
    const n = DIM - 1;
    const sy = Math.sin(yaw), cyw = Math.cos(yaw);
    type Item = { kind: 0 | 1; i: number; j: number; d: number; dir?: 0 | 1 };
    const items: Item[] = [];
    for (let k = 0; k < order.length; k++) {
      const q = order[k];
      const i = Math.floor(q / n) + 1;
      const j = (q % n) + 1;
      items.push({ kind: 0, i, j, d: (i + 0.5 - mid) * sy + (j + 0.5 - mid) * cyw });
    }
    if (mix > 0.01) {
      for (let a = 1; a <= DIM; a++) {
        for (let b = 1; b <= DIM; b++) {
          if (!phiWins(a, b)) continue;
          if (phiWins(a + 1, b)) {
            items.push({ kind: 1, i: a, j: b, dir: 0,
              d: (a + 0.5 - mid) * sy + (b - mid) * cyw });
          }
          if (phiWins(a, b + 1)) {
            items.push({ kind: 1, i: a, j: b, dir: 1,
              d: (a - mid) * sy + (b + 0.5 - mid) * cyw });
          }
        }
      }
    }
    items.sort((p, q) => q.d - p.d); // farthest first

    ctx.lineJoin = 'round';
    for (const it of items) {
      if (it.kind === 0) {
        const { i, j } = it;
        const zs = [
          heightAt(i, j),
          heightAt(i + 1, j),
          heightAt(i + 1, j + 1),
          heightAt(i, j + 1),
        ];
        if (zs.some((z) => z === null)) continue;

        // A face spans four cells, and "Phi won here" belongs to ONE of them,
        // so no single colour for the face can be right: painting it when any
        // corner is Phi's covers 33% of the sheet to say 10%, and painting it
        // only when most corners are collapses to nothing.
        //
        // Split the face at its midlines instead. The nearest-vertex boundary
        // inside a face IS the midlines, so each quarter lies wholly in one
        // cell's territory and takes that cell's colour with no blending —
        // which also means no muddy midpoint between navy and burnt orange.
        // One bisection is exact; there is no depth to tune.
        const OWNERS: Array<[number, number]> = [
          [i, j], [i + 1, j], [i + 1, j + 1], [i, j + 1],
        ];
        const mu = i + 0.5;
        const mv = j + 0.5;
        for (const [oa, ob] of OWNERS) {
          const a0 = Math.min(oa, mu), a1 = Math.max(oa, mu);
          const b0 = Math.min(ob, mv), b1 = Math.max(ob, mv);
          const quad: Array<[number, number]> = [[a0, b0], [a1, b0], [a1, b1], [a0, b1]];
          const zq = quad.map(([u, v]) => lattice(u, v));
          if (zq.some((z) => z === null)) continue;
          const pts = quad.map(([u, v], k) => P(u, v, zq[k]!));
          ctx.beginPath();
          ctx.moveTo(pts[0].sx, pts[0].sy);
          for (let k = 1; k < 4; k++) ctx.lineTo(pts[k].sx, pts[k].sy);
          ctx.closePath();
          ctx.fillStyle = shade(
            (zq[0]! + zq[1]! + zq[2]! + zq[3]!) / 4,
            phiWins(oa, ob),
            mix,
          );
          ctx.fill();
        }

        // Seams are stroked per FACE, not per quarter. The quarters are how the
        // colour is resolved, not something the data has; drawing their edges
        // would put a wireframe on the surface at twice the grid's resolution.
        const pts = [
          P(i, j, zs[0]!),
          P(i + 1, j, zs[1]!),
          P(i + 1, j + 1, zs[2]!),
          P(i, j + 1, zs[3]!),
        ];
        ctx.beginPath();
        ctx.moveTo(pts[0].sx, pts[0].sy);
        for (let p = 1; p < 4; p++) ctx.lineTo(pts[p].sx, pts[p].sy);
        ctx.closePath();
        ctx.strokeStyle = 'rgba(255,255,255,0.55)';
        ctx.lineWidth = 0.6;
        ctx.stroke();
        continue;
      }
      // Where two Phi cells are neighbours their territories touch and read as
      // one patch, so the shared edge gets a line -- the count is the finding.
      // Only that edge. Ringing every patch drew a brown border round all of
      // them, which reads as an artifact rather than a boundary, and doubled up
      // wherever it crossed a face seam.
      //
      // In the seam's own white, because this IS a mesh line: it separates two
      // cells exactly as the face seams separate faces, and a second colour for
      // it would be a third thing to explain.
      const { i: a, j: b } = it;
      const [u0, v0, u1, v1] = it.dir === 0
        ? [a + 0.5, b - 0.5, a + 0.5, b + 0.5]
        : [a - 0.5, b + 0.5, a + 0.5, b + 0.5];
      const cu0 = Math.max(1, Math.min(DIM, u0)), cv0 = Math.max(1, Math.min(DIM, v0));
      const cu1 = Math.max(1, Math.min(DIM, u1)), cv1 = Math.max(1, Math.min(DIM, v1));
      const za = lattice(cu0, cv0), zb = lattice(cu1, cv1);
      if (za === null || zb === null) continue;
      const pa = P(cu0, cv0, za), pb = P(cu1, cv1, zb);
      ctx.globalAlpha = Math.min(1, mix);
      ctx.beginPath();
      ctx.moveTo(pa.sx, pa.sy);
      ctx.lineTo(pb.sx, pb.sy);
      ctx.strokeStyle = 'rgba(255,255,255,0.55)';
      ctx.lineWidth = 0.6;
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
      const dx = px - centre.sx;
      const dy = py - centre.sy;
      const m = Math.hypot(dx, dy) || 1;
      return [px + (dx / m) * by, py + (dy / m) * by] as const;
    };

    ctx.textBaseline = 'middle';
    for (const ax of [
      { title: 'digits in A', fixed: near[1], along: 'a' as const },
      { title: 'digits in B', fixed: near[0], along: 'b' as const },
    ]) {
      const at = (v: number) =>
        ax.along === 'a' ? P(v, ax.fixed, 0) : P(ax.fixed, v, 0);
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

      const midE = at(mid);
      const [ttx, tty] = outward(midE.sx, midE.sy, 34);
      let angle = Math.atan2(e1.sy - e0.sy, e1.sx - e0.sx);
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
    mix; yaw; pitch; w; h; order;
    draw();
  });

  /**
   * Interpolate between the two height fields rather than swapping them.
   * Switching two static pictures makes a reader hunt for what changed, and
   * what changed IS the point: 15 cells rise a little, 129 do not move.
   *
   * `mix` is read UNTRACKED. Read normally it would make this effect depend on
   * the value its own animation frame writes, so every frame would invalidate
   * the effect, cancel the pending frame and restart the tween with the clock
   * reset — advancing by the first instant of an ease-in curve each time and
   * never arriving.
   */
  $effect(() => {
    const to = target;
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
        h = Math.max(300, Math.round(Math.min(480, r.width * 0.58)));
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
    pitch = Math.max(0.08, Math.min(1.35, pitch + (e.clientY - lastY) * 0.005));
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
      P(exactly correct) &mdash;
      <strong>{target === 0 ? 'Qwen alone' : 'the better of the two'}</strong>
    </span>
    <span class="meta mono">
      {WINNER.models[0]} + {WINNER.models[1]} · {WINNER.problems.toLocaleString()} problems
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
    aria-label="Reliability surface for the two models together: digits in factor A by
      digits in factor B by probability of an exactly correct product. Adding Phi raises
      {F.phiAhead} of {F.phiAhead + F.qwenLevelOrAhead} cells and leaves the rest
      unchanged. Drag to rotate."
  >
    <canvas bind:this={canvas} style:width="{w}px" style:height="{h}px"></canvas>
    <span class="hint mono">drag to rotate</span>
  </div>

  <div class="key">
    <span><i class="sw"></i>0 to 100% correct</span>
    <span><i class="dot"></i>a cell where Phi scored higher</span>
    <span class="dim">· 12&times;12, the sizes both models were asked</span>
  </div>

  <figcaption>
    Adding Phi raises <strong>{F.phiAhead} cells of {F.phiAhead + F.qwenLevelOrAhead}</strong>
    and leaves the rest exactly where they were. Both models hold the small sizes and fall
    off the same cliff: fitted, Qwen is still right half the time at
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
    margin-bottom: 6px;
  }
  .title { font-size: var(--text-sm); color: var(--ink-dim); }
  .title strong { color: var(--ink); }
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
  .ctl button:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }

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
    width: 40px;
    height: 10px;
    border-radius: 2px;
    vertical-align: -1px;
    margin-right: 7px;
    background: linear-gradient(90deg, rgb(232, 236, 243), rgb(27, 42, 94));
  }
  .dot {
    display: inline-block;
    width: 9px;
    height: 9px;
    border-radius: 50%;
    vertical-align: -1px;
    margin-right: 7px;
    background: var(--accent);
    box-shadow: 0 0 0 2px var(--bg);
  }

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
