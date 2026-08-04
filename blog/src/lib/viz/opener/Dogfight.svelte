<script lang="ts">
  /**
   * Two aircraft, two OODA loops, one turning fight.
   *
   * ## What the reader is looking at
   *
   * SPACE carries the fight: the projected trajectories, broken into one dash
   * per completed loop. The dash pitch IS the loop rate, so the Sabre's track
   * is finely stippled and the MiG's grows coarser as its pilot tires. Nothing
   * else in the scene has to be read to see that.
   *
   * TIME carries the loops: under the scene, each pilot's cycles laid on a
   * shared axis in the four phase colours, and beneath those the position
   * advantage. The Sabre's blocks stay the same width all the way across. The
   * MiG's widen.
   *
   * The four phases are shown in the strip rather than on the trail, and that
   * is a legibility decision rather than a taste one. One Sabre loop is about
   * 310 m of flight path, which at this scale is roughly 15 px — four colours
   * inside that is a smear. In the strip each phase gets real width.
   *
   * ## What this figure no longer does, and what that costs
   *
   * It draws ONE fight, and one fight settles nothing. A turning fight is
   * chaotic: across a sweep of a single trajectory the outcome flips sign at
   * random, which is why the ensemble in dogfight.ts exists.
   *
   * This component used to carry that ensemble beside the scene — a slider for
   * the per-cycle loop cost, and a win-rate curve over 120 merges per point
   * with Wilson intervals. All of it was cut for simplicity, along with the
   * caption naming the figure a model rather than a measurement. What is left
   * illustrates the mechanism; it does not evidence it, and it does not say on
   * the page that it is simulated at all. Anyone re-adding evidence here should
   * know what the ensemble actually found, because it is less flattering than
   * the parable: the effect is real and rising, 12% of merges at no cost to 67%
   * at a cost of 10% per cycle, and weak — tripling the MiG pilot's loop still
   * leaves the Sabre at 37%, and nine-out-of-ten is nowhere in reach. The curve
   * is also not point-to-point monotone. `scripts/dogfight-curve.mjs` reprints
   * all of it.
   *
   * `TAX` below is the one number that survived: the crossing where the fight
   * comes to even odds.
   */
  import { untrack } from 'svelte';
  import { onscreen } from '../onscreen.svelte';
  import { observeWidth } from '../observeWidth.svelte';
  import { project, type Camera } from '../surface/project';
  import {
    simulate,
    SABRE,
    MIG,
    HERO_MERGE,
    type Fight,
    type Frame,
  } from './dogfight';
  import { OODA_SCHEME, OODA_PHASES } from '../../design/ooda';
  import { metaFor } from '../../design/scheme';

  /**
   * The two sides. Navy and brick are the house's opposed pair; they are not
   * `--model-a` / `--model-b`, which this post has already promised to Qwen and
   * Phi, and they are not the OODA phase hues, which are spoken for below.
   */
  const SABRE_INK = '#1f3a5f';
  const MIG_INK = '#b0423e';

  const PHASES = OODA_PHASES.map((p) => ({ phase: p, ...metaFor(OODA_SCHEME, p) }));
  const PHASE_COLORS = PHASES.map((p) => p.color);

  /** 78 s of fight in 24 s of screen time, then a hold so the end can be read. */
  const RUN_MS = 24_000;
  const HOLD_MS = 2_600;
  const CYCLE = RUN_MS + HOLD_MS;

  let host: HTMLElement | null = $state(null);
  /** Both loops below run forever. This is what stops them off screen. */
  const visible = onscreen(() => host);
  let stageEl: HTMLCanvasElement | null = $state(null);
  let railEl: HTMLCanvasElement | null = $state(null);

  let w = $state(880);
  let elapsed = $state(0);
  let reduced = $state(false);
  let runId = $state(0);

  /**
   * The MiG pilot's per-cycle loop cost, as a fraction his loop grows by each
   * time round. Fixed at 6.5% because that is where a 120-merge ensemble puts
   * the fight at even odds — the figure used to carry that curve beside it and
   * no longer does, so the number is a finding this file inherits rather than
   * one anything on the page demonstrates. Rerun scripts/dogfight-curve.mjs to
   * check it.
   */
  const TAX = 0.065;

  /** Orbit. Auto-turns until the reader takes hold of it. */
  let yaw = $state(-0.55);
  let pitch = $state(0.42);
  let grabbed = $state(false);
  let dragging = false;

  const STAGE_H = 400;
  const RAIL_H = 108;

  const fight: Fight = $derived(simulate({ tax: TAX, merge: HERO_MERGE }));
  const duration = $derived(fight.t[fight.t.length - 1]);

  const progress = $derived(Math.min(1, elapsed / RUN_MS));
  /** Index into the stored frames. One clock for the scene and the rail. */
  const cursor = $derived(Math.min(fight.sabre.length - 1, Math.round(progress * (fight.sabre.length - 1))));

  /**
   * Scene framing. Computed over the WHOLE fight rather than the part drawn so
   * far, so the camera never dollies while the trails grow — a frame that
   * retargets each tick reads as the aircraft standing still and the world
   * moving, which is exactly backwards.
   *
   * No vertical exaggeration. The altitude range really is about half the
   * horizontal one, and stretching it would make an energy fight look like a
   * vertical one for free.
   */
  const scene = $derived.by(() => {
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity, z0 = Infinity, z1 = -Infinity;
    for (const arr of [fight.sabre, fight.mig]) {
      for (const f of arr) {
        if (f.x < x0) x0 = f.x; if (f.x > x1) x1 = f.x;
        if (f.y < y0) y0 = f.y; if (f.y > y1) y1 = f.y;
        if (f.z < z0) z0 = f.z; if (f.z > z1) z1 = f.z;
      }
    }
    const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, cz = (z0 + z1) / 2;
    const span = Math.max(2600, (x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2);
    return { cx, cy, cz, span, floor: z0 - span * 0.12 };
  });

  /**
   * `dist` IS IN PIXELS, not world units. The divide in `project` is
   *
   *     scale = dist / (dist + depth * zoom)
   *
   * so `dist` is compared against `depth * zoom` and has to dominate it.
   * Written as 3.4 — a plausible-looking camera distance in the normalized
   * world — the denominator crossed zero wherever depth reached -0.009, and
   * every trail that passed through that plane was flung to infinity. On screen
   * it was six straight lines leaving the frame, which reads as a broken
   * transform rather than as a divide by zero, so it is worth naming.
   * SurfaceCanvas uses dist 900 against a zoom of 26; the ratio is what matters.
   */
  const cam: Camera = $derived({ yaw, pitch, dist: 1300, zoom: Math.min(w, 900) * 0.31 });

  /** World metres -> the unit-ish box `project` expects. */
  function toWorld(x: number, y: number, z: number): [number, number, number] {
    return [(x - scene.cx) / scene.span, (y - scene.cy) / scene.span, (z - scene.cz) / scene.span];
  }

  function px(x: number, y: number, z: number, cw: number, ch: number) {
    const [wx, wy, wz] = toWorld(x, y, z);
    return project(wx, wy, wz, cam, cw / 2, ch * 0.46);
  }

  function dpr(): number {
    return Math.min(window.devicePixelRatio || 1, 2);
  }

  function fit(c: HTMLCanvasElement, cw: number, ch: number): CanvasRenderingContext2D | null {
    const ctx = c.getContext('2d');
    if (!ctx) return null;
    const d = dpr();
    if (c.width !== Math.round(cw * d) || c.height !== Math.round(ch * d)) {
      c.width = Math.round(cw * d);
      c.height = Math.round(ch * d);
    }
    ctx.setTransform(d, 0, 0, d, 0, 0);
    return ctx;
  }

  // --- the aeroplane ------------------------------------------------------
  // Body frame: +x nose, +y right wing, +z up, roughly one unit nose to tail.
  // Swept wings and a tall fin, which is all that survives at this size; the
  // two aircraft are told apart by colour and by the tag that follows them,
  // not by planform. Drawing accurate silhouettes at 30 px would be work spent
  // where no reader can collect it.
  type Face = { v: [number, number, number][]; shade: number };
  const PLANE: Face[] = [
    // fuselage, two long slabs
    { v: [[1.05, 0, 0], [-0.15, 0.09, 0.04], [-0.95, 0.05, 0.05], [-0.95, -0.05, 0.05], [-0.15, -0.09, 0.04]], shade: 1 },
    { v: [[1.05, 0, 0], [-0.15, 0.09, -0.03], [-0.95, 0.05, -0.02], [-0.95, -0.05, -0.02], [-0.15, -0.09, -0.03]], shade: 0.72 },
    // wings, swept back
    { v: [[0.2, 0.07, 0], [-0.34, 0.92, 0.01], [-0.56, 0.92, 0.01], [-0.42, 0.07, 0]], shade: 0.94 },
    { v: [[0.2, -0.07, 0], [-0.34, -0.92, 0.01], [-0.56, -0.92, 0.01], [-0.42, -0.07, 0]], shade: 0.94 },
    // tailplane
    { v: [[-0.72, 0.05, 0.04], [-0.94, 0.42, 0.06], [-1.02, 0.42, 0.06], [-0.94, 0.05, 0.04]], shade: 0.86 },
    { v: [[-0.72, -0.05, 0.04], [-0.94, -0.42, 0.06], [-1.02, -0.42, 0.06], [-0.94, -0.05, 0.04]], shade: 0.86 },
    // fin
    { v: [[-0.66, 0, 0.03], [-0.95, 0, 0.42], [-1.03, 0, 0.42], [-0.98, 0, 0.03]], shade: 0.6 },
  ];

  /** Body axes for a frame: nose, right wing, and up, with bank applied. */
  function axes(f: Frame) {
    const cg = Math.cos(f.gam);
    const fwd: [number, number, number] = [cg * Math.cos(f.psi), cg * Math.sin(f.psi), Math.sin(f.gam)];
    // right0 is the wing line at zero bank; z-up means it is nose x world-up.
    let r0: [number, number, number] = [fwd[1], -fwd[0], 0];
    const rm = Math.hypot(r0[0], r0[1]) || 1;
    r0 = [r0[0] / rm, r0[1] / rm, 0];
    const u0: [number, number, number] = [
      r0[1] * fwd[2] - r0[2] * fwd[1],
      r0[2] * fwd[0] - r0[0] * fwd[2],
      r0[0] * fwd[1] - r0[1] * fwd[0],
    ];
    const cb = Math.cos(f.bank), sb = Math.sin(f.bank);
    const right: [number, number, number] = [
      r0[0] * cb - u0[0] * sb,
      r0[1] * cb - u0[1] * sb,
      r0[2] * cb - u0[2] * sb,
    ];
    const up: [number, number, number] = [
      right[1] * fwd[2] - right[2] * fwd[1],
      right[2] * fwd[0] - right[0] * fwd[2],
      right[0] * fwd[1] - right[1] * fwd[0],
    ];
    return { fwd, right, up };
  }

  // Nose-to-tail size of the GLYPH in world metres. An F-86 is about 11 m long,
  // so this is roughly forty times oversize — at true scale each aircraft would
  // be a third of a pixel against a fight five kilometres wide, and the figure
  // would be two trails and no aeroplanes. The trails are to scale; the shapes
  // on the end of them are not.
  const PLANE_M = 250;

  function shade(hex: string, k: number): string {
    const n = parseInt(hex.slice(1), 16);
    const r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
    const m = (c: number) => Math.round(Math.min(255, c * k + 255 * (1 - k) * 0.12));
    return `rgb(${m(r)},${m(g)},${m(b)})`;
  }

  type Poly = { pts: [number, number][]; depth: number; fill: string };

  function planePolys(f: Frame, ink: string, cw: number, ch: number): Poly[] {
    const { fwd, right, up } = axes(f);
    const out: Poly[] = [];
    for (const face of PLANE) {
      const pts: [number, number][] = [];
      let d = 0;
      for (const [bx, by, bz] of face.v) {
        const wx = f.x + PLANE_M * (bx * fwd[0] + by * right[0] + bz * up[0]);
        const wy = f.y + PLANE_M * (bx * fwd[1] + by * right[1] + bz * up[1]);
        const wz = f.z + PLANE_M * (bx * fwd[2] + by * right[2] + bz * up[2]);
        const p = px(wx, wy, wz, cw, ch);
        pts.push([p.sx, p.sy]);
        d += p.depth;
      }
      out.push({ pts, depth: d / face.v.length, fill: shade(ink, face.shade) });
    }
    return out;
  }

  // --- the scene ----------------------------------------------------------

  function drawFloor(ctx: CanvasRenderingContext2D, cw: number, ch: number) {
    const step = 1000;
    const half = Math.ceil(scene.span / step) * step;
    ctx.lineWidth = 1;
    for (let i = -half; i <= half; i += step) {
      for (const along of [0, 1]) {
        const a = along ? px(scene.cx + i, scene.cy - half, scene.floor, cw, ch)
                        : px(scene.cx - half, scene.cy + i, scene.floor, cw, ch);
        const b = along ? px(scene.cx + i, scene.cy + half, scene.floor, cw, ch)
                        : px(scene.cx + half, scene.cy + i, scene.floor, cw, ch);
        ctx.strokeStyle = i === 0 ? 'rgba(26,26,26,0.16)' : 'rgba(26,26,26,0.07)';
        ctx.beginPath();
        ctx.moveTo(a.sx, a.sy);
        ctx.lineTo(b.sx, b.sy);
        ctx.stroke();
      }
    }
  }

  /**
   * A trail, broken once per completed loop. The gaps are the whole point: they
   * are not a dash pattern chosen for looks, they are where that pilot's cycle
   * closed, so the spacing measures loop rate directly off the flight path.
   */
  function drawTrail(
    ctx: CanvasRenderingContext2D,
    arr: Frame[],
    to: number,
    ink: string,
    cw: number,
    ch: number,
  ) {
    ctx.lineCap = 'butt';
    ctx.lineJoin = 'round';
    let i = 0;
    while (i <= to) {
      const cyc = arr[i].cycle;
      let j = i;
      while (j + 1 <= to && arr[j + 1].cycle === cyc) j++;
      // Leave the last sample of each cycle undrawn — that gap is the loop
      // boundary. With no gap the trail is one unbroken line and the figure
      // loses its primary reading.
      const end = Math.max(i, j - 1);
      if (end > i) {
        const age = 1 - (to - j) / Math.max(1, to);
        ctx.strokeStyle = ink;
        ctx.globalAlpha = 0.22 + 0.62 * age;
        ctx.lineWidth = 1.6 + 1.5 * age;
        ctx.beginPath();
        for (let k = i; k <= end; k++) {
          const p = px(arr[k].x, arr[k].y, arr[k].z, cw, ch);
          if (k === i) ctx.moveTo(p.sx, p.sy);
          else ctx.lineTo(p.sx, p.sy);
        }
        ctx.stroke();
      }
      i = j + 1;
    }
    ctx.globalAlpha = 1;
  }

  function drawDrop(ctx: CanvasRenderingContext2D, f: Frame, ink: string, cw: number, ch: number) {
    const a = px(f.x, f.y, f.z, cw, ch);
    const b = px(f.x, f.y, scene.floor, cw, ch);
    ctx.strokeStyle = ink;
    ctx.globalAlpha = 0.2;
    ctx.lineWidth = 1;
    ctx.setLineDash([2, 3]);
    ctx.beginPath();
    ctx.moveTo(a.sx, a.sy);
    ctx.lineTo(b.sx, b.sy);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.globalAlpha = 0.28;
    ctx.beginPath();
    ctx.ellipse(b.sx, b.sy, 5, 2.2, 0, 0, Math.PI * 2);
    ctx.fillStyle = ink;
    ctx.fill();
    ctx.globalAlpha = 1;
  }

  function drawStage() {
    const c = stageEl;
    if (!c) return;
    const cw = w, ch = STAGE_H;
    const ctx = fit(c, cw, ch);
    if (!ctx) return;
    ctx.clearRect(0, 0, cw, ch);

    const to = cursor;
    drawFloor(ctx, cw, ch);

    drawTrail(ctx, fight.sabre, to, SABRE_INK, cw, ch);
    drawTrail(ctx, fight.mig, to, MIG_INK, cw, ch);

    const fs = fight.sabre[to];
    const fm = fight.mig[to];
    drawDrop(ctx, fs, SABRE_INK, cw, ch);
    drawDrop(ctx, fm, MIG_INK, cw, ch);

    // Both aircraft into one depth-sorted list, so the near one occludes the
    // far one. Sorting each aircraft separately draws whichever was painted
    // last on top regardless of where it is, which shows through as the MiG
    // flying in front of a Sabre that is nearer the camera.
    const polys = [
      ...planePolys(fs, SABRE_INK, cw, ch),
      ...planePolys(fm, MIG_INK, cw, ch),
    ].sort((a, b) => b.depth - a.depth);

    for (const p of polys) {
      ctx.beginPath();
      ctx.moveTo(p.pts[0][0], p.pts[0][1]);
      for (let i = 1; i < p.pts.length; i++) ctx.lineTo(p.pts[i][0], p.pts[i][1]);
      ctx.closePath();
      ctx.fillStyle = p.fill;
      ctx.fill();
      ctx.strokeStyle = 'rgba(253,252,249,0.55)';
      ctx.lineWidth = 0.6;
      ctx.stroke();
    }

    // Tags. Placed above each aircraft and never rotated with it, because a
    // label that tumbles is a label nobody reads.
    ctx.font = '600 11px Inter, system-ui, sans-serif';
    ctx.textAlign = 'center';
    for (const [f, ink, name] of [
      [fs, SABRE_INK, SABRE.name],
      [fm, MIG_INK, MIG.name],
    ] as const) {
      const p = px(f.x, f.y, f.z, cw, ch);
      ctx.fillStyle = ink;
      ctx.fillText(name, p.sx, p.sy - 17);
    }
    ctx.textAlign = 'left';
  }

  // --- the rail -----------------------------------------------------------

  /**
   * Cycle spans for one pilot: [start, end] in seconds, INCLUDING the one still
   * running when the fight ends. Without the trailing span the F-86's row —
   * fifty short cycles — stopped a visible distance short of the MiG's, which
   * reads as the faster pilot quitting early rather than as an unfinished
   * cycle.
   */
  function cycles(acts: readonly number[], end: number): [number, number][] {
    const out: [number, number][] = [];
    let prev = 0;
    for (const a of acts) {
      out.push([prev, a]);
      prev = a;
    }
    if (prev < end) out.push([prev, end]);
    return out;
  }

  function drawRail() {
    const c = railEl;
    if (!c) return;
    const cw = w, ch = RAIL_H;
    const ctx = fit(c, cw, ch);
    if (!ctx) return;
    ctx.clearRect(0, 0, cw, ch);

    const padL = 74;
    const plot = cw - padL - 6;
    const X = (t: number) => padL + (t / duration) * plot;

    const rowH = 13;
    const rows: [string, readonly number[], string][] = [
      [SABRE.name, fight.acts.sabre, SABRE_INK],
      [MIG.name, fight.acts.mig, MIG_INK],
    ];

    ctx.font = '500 10px Inter, system-ui, sans-serif';
    rows.forEach(([name, acts, ink], r) => {
      const y = 4 + r * (rowH + 5);
      ctx.fillStyle = ink;
      ctx.textAlign = 'right';
      ctx.fillText(name, padL - 8, y + rowH - 3);
      ctx.textAlign = 'left';

      for (const [t0, t1] of cycles(acts, duration)) {
        const x0 = X(t0), x1 = X(t1);
        const wdt = Math.max(0.7, x1 - x0);
        // Four phases across the cycle. Equal quarters is a modelling choice
        // and it is stated in the caption: nothing here measures how a pilot
        // divides his loop.
        for (let p = 0; p < 4; p++) {
          ctx.fillStyle = PHASE_COLORS[p];
          ctx.globalAlpha = t1 <= fight.t[cursor] ? 0.92 : 0.16;
          ctx.fillRect(x0 + (wdt * p) / 4, y, Math.max(0.4, wdt / 4 - 0.35), rowH);
        }
      }
      ctx.globalAlpha = 1;
    });

    // Advantage.
    const advY = 4 + 2 * (rowH + 5) + 6;
    const advH = ch - advY - 14;
    const mid = advY + advH / 2;
    const Y = (a: number) => mid - (a * advH) / 2;

    ctx.strokeStyle = 'rgba(26,26,26,0.18)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padL, mid);
    ctx.lineTo(padL + plot, mid);
    ctx.stroke();

    for (const side of [1, -1]) {
      ctx.beginPath();
      ctx.moveTo(X(0), mid);
      for (let i = 0; i <= cursor; i++) {
        const a = fight.adv[i];
        ctx.lineTo(X(fight.t[i]), Y(side > 0 ? Math.max(0, a) : Math.min(0, a)));
      }
      ctx.lineTo(X(fight.t[cursor]), mid);
      ctx.closePath();
      ctx.fillStyle = side > 0 ? SABRE_INK : MIG_INK;
      ctx.globalAlpha = 0.5;
      ctx.fill();
    }
    ctx.globalAlpha = 1;

    ctx.font = '500 9px Inter, system-ui, sans-serif';
    ctx.textAlign = 'right';
    // Name BOTH sides. A single "behind" beside the zero line does not say
    // whose, and the sign convention is the one thing the rail must not leave
    // to a guess.
    ctx.fillStyle = SABRE_INK;
    ctx.fillText('F-86 behind', padL - 8, mid - 5);
    ctx.fillStyle = MIG_INK;
    ctx.fillText('MiG behind', padL - 8, mid + 11);
    ctx.fillStyle = '#9a9a9a';
    ctx.textAlign = 'left';
    ctx.fillText('0 s', padL, ch - 3);
    ctx.textAlign = 'right';
    ctx.fillText(`${Math.round(duration)} s`, padL + plot, ch - 3);
    ctx.textAlign = 'left';

    const hx = X(fight.t[cursor]);
    ctx.strokeStyle = 'rgba(26,26,26,0.5)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(hx, 2);
    ctx.lineTo(hx, ch - 12);
    ctx.stroke();
  }

  // --- clock --------------------------------------------------------------
  // One writer, as in IterationRings: the frame loop owns `elapsed`, and a seek
  // bumps `runId` to tear the loop down before the new position is read.
  $effect(() => {
    if (reduced || !visible.current) return;
    runId;
    let t = untrack(() => elapsed);
    let prev = 0;
    let raf = requestAnimationFrame(function tick(ts: number) {
      if (prev) t += ts - prev;
      prev = ts;
      if (t >= CYCLE) t = 0;
      elapsed = t;
      raf = requestAnimationFrame(tick);
    });
    return () => cancelAnimationFrame(raf);
  });

  /** Slow orbit, surrendered permanently once the reader drags. */
  $effect(() => {
    if (grabbed || reduced || !visible.current) return;
    let prev = 0;
    let raf = requestAnimationFrame(function tick(ts: number) {
      if (prev) yaw += ((ts - prev) / 1000) * 0.055;
      prev = ts;
      raf = requestAnimationFrame(tick);
    });
    return () => cancelAnimationFrame(raf);
  });

  $effect(() => {
    const m = window.matchMedia('(prefers-reduced-motion: reduce)');
    const sync = () => {
      reduced = m.matches;
      // Show the finished fight rather than a frozen first frame.
      if (m.matches) elapsed = RUN_MS;
    };
    sync();
    m.addEventListener('change', sync);
    return () => m.removeEventListener('change', sync);
  });

  observeWidth(() => host, (width) => {
    // The floor was 300, which is wider than the content column on a 320px
    // phone (270 after the page gutters), so the whole figure hung 32px past
    // the right edge -- inside a canvas, so no scrollbar and nothing to drag.
    // 260 fits the narrowest phone still in use and the scene scales to it.
    w = Math.max(260, Math.round(width));
  });

  // --- paint --------------------------------------------------------------
  $effect(() => {
    // Everything the drawings depend on, read so the effect re-runs.
    cursor; yaw; pitch; w; scene;
    drawStage();
    drawRail();
  });

  function seekRail(e: PointerEvent & { currentTarget: HTMLElement }) {
    const box = e.currentTarget.getBoundingClientRect();
    const padL = 74;
    const f = (e.clientX - box.left - padL) / Math.max(1, box.width - padL - 6);
    runId++;
    elapsed = Math.min(RUN_MS, Math.max(0, f * RUN_MS));
  }

  /** Arrow-key scrubbing, so the rail is not pointer-only. */
  function keySeek(e: KeyboardEvent) {
    const step = RUN_MS / 40;
    const to =
      e.key === 'ArrowLeft' ? elapsed - step
      : e.key === 'ArrowRight' ? elapsed + step
      : e.key === 'Home' ? 0
      : e.key === 'End' ? RUN_MS
      : null;
    if (to === null) return;
    e.preventDefault();
    runId++;
    elapsed = Math.min(RUN_MS, Math.max(0, to));
  }

  function down(e: PointerEvent & { currentTarget: HTMLElement }) {
    dragging = true;
    grabbed = true;
    e.currentTarget.setPointerCapture(e.pointerId);
  }
  function move(e: PointerEvent) {
    if (!dragging) return;
    yaw += e.movementX * 0.006;
    pitch = Math.max(-0.15, Math.min(1.15, pitch + e.movementY * 0.004));
  }
  function up() {
    dragging = false;
  }
</script>

<figure class="fig" bind:this={host}>
  <div
    class="stage"
    style:height="{STAGE_H}px"
    role="img"
    aria-label="Simulated turning fight between an F-86 and a MiG-15, each flying its own OODA loop."
    onpointerdown={down}
    onpointermove={move}
    onpointerup={up}
    onpointercancel={up}
  >
    <canvas bind:this={stageEl} style:width="{w}px" style:height="{STAGE_H}px"></canvas>
    <div class="hint">drag to orbit</div>
  </div>

  <!-- The rail is the only way to scrub the fight, so it is a control and not
       decoration: focusable, arrow-key seekable, and labelled. It carried a
       blanket a11y suppression, which silenced the warning without answering it. -->
  <div
    class="rail"
    style:height="{RAIL_H}px"
    role="slider"
    tabindex="0"
    aria-label="Fight timeline. Each pilot's OODA cycles above, position advantage below."
    aria-valuemin={0}
    aria-valuemax={Math.round(duration)}
    aria-valuenow={Math.round(fight.t[cursor])}
    aria-valuetext="{Math.round(fight.t[cursor])} seconds of {Math.round(duration)}"
    onpointerdown={seekRail}
    onkeydown={keySeek}
  >
    <canvas bind:this={railEl} style:width="{w}px" style:height="{RAIL_H}px"></canvas>
  </div>

  <ul class="legend">
    {#each PHASES as p (p.phase)}
      <li><i style:background={p.color}></i>{p.label}</li>
    {/each}
    <!-- The four colours butted together, at the size they appear in the
         strip. Naming the unit in words left the reader counting colours to
         work out where one band ended; showing the unit does not. -->
    <li class="unit">
      <span class="band" aria-hidden="true">
        {#each PHASES as p (p.phase)}<i style:background={p.color}></i>{/each}
      </span>
      one band is one loop
    </li>
  </ul>

  <!--
    THE CAPTION SAYS THIS IS SIMULATED, and that is not optional.

    The header of this file records that the figure "illustrates the mechanism,
    it does not evidence it, and it does not say on the page that it is
    simulated at all." A reader has no way to tell a solved trajectory from a
    measured one by looking, so the figure has to say which it is. Everything
    else here is a reading key.
  -->
  <figcaption class="cap">
    Each band is one turn of a pilot's loop. The Sabre's stay the same width and
    the MiG's widen, because its controls are unboosted and every input costs the
    pilot effort that adds up. By the end the Sabre gets four adjustments for
    every one the MiG can make.
  </figcaption>

</figure>

<style>
  .fig {
    /* Explicit and symmetric. The section already puts --space-lg between its
       children; this is on top of that, so the figure has a defined band of air
       above and below rather than inheriting whatever its neighbours leave. */
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-md);
    width: 100%;
  }
  .stage {
    position: relative;
    width: 100%;
    /* VERTICAL SWIPES BELONG TO THE PAGE. This stage is 400px tall and full
       width, which on a phone is close to half the screen, so `none` meant a
       reader swiping up through the section put a finger down here and the
       article stopped moving while the camera orbited instead. `pan-y` hands
       vertical back to the page and keeps horizontal drags for the orbit,
       which is what the surface figure has always done. */
    touch-action: pan-y;
    cursor: grab;
    background: linear-gradient(180deg, rgba(240,237,229,0.5), rgba(253,252,249,0) 62%);
    border-radius: var(--radius-md);
  }
  .stage:active { cursor: grabbing; }
  canvas { display: block; }
  .stage canvas { position: absolute; inset: 0; }
  .hint {
    position: absolute;
    right: 10px;
    bottom: 8px;
    font-family: var(--font-sans);
    font-size: 10px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--ink-faint);
    pointer-events: none;
  }
  .rail { position: relative; width: 100%; cursor: crosshair; }
  .rail:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

  .legend {
    list-style: none;
    margin: 0;
    padding: 0 0 0 74px;
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-md);
    font-family: var(--font-sans);
    font-size: var(--text-xs);
    color: var(--ink-dim);
  }
  .legend li { display: flex; align-items: center; gap: 6px; }
  .legend i { width: 10px; height: 10px; border-radius: 2px; display: block; }
  /* The sample band. Segments butt together with no gap and no rounding
     between them, because the thing being shown is that four colours make ONE
     unit. Rounding only the outer corners keeps it reading as a single chip
     alongside the four square swatches rather than as four more of them. */
  .legend .unit { color: var(--ink-faint); font-style: italic; }
  .legend .band { display: flex; border-radius: 2px; overflow: hidden; }
  .legend .band i { width: 8px; height: 10px; border-radius: 0; display: block; }

  /* Held at the reading measure inside a figure that is wider than it, because
     a caption set to the full 880px stops being a caption and starts being a
     column of body text that happens to sit under a chart. */
  /* Full width of the figure. The strip above it runs the whole canvas, and a
     caption held to a reading measure under a chart that wide leaves a column
     of text against a field of empty space. */
  .cap {
    margin: var(--space-sm) 0 0;
    padding-left: 74px;          /* aligns with the strip, not the canvas edge */
    font-family: var(--font-sans);
    font-size: var(--text-xs);
    line-height: var(--leading-snug);
    color: var(--ink-dim);
  }


  @media (max-width: 640px) {
    .legend { padding-left: 0; }
    .cap { padding-left: 0; }
  }
</style>
