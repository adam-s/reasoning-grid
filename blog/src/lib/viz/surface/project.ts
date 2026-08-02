/**
 * 3D -> 2D for the reliability surface. Pure functions, no DOM.
 *
 * Projection follows ~/Projects/grpo/docs/3d-on-2d/02-projection-math.md: yaw,
 * then pitch, then a perspective divide
 *
 *     scale = CAM_DIST / (CAM_DIST + z)
 *
 * which is similar triangles and nothing more. Large CAM_DIST approaches an
 * isometric look; small CAM_DIST exaggerates depth. The committed Python chart
 * (probe/render_animation.py) used a true isometric projection instead —
 * px = (x−y)/√2, py = (x+y−2z)/√6 — which has no camera and therefore cannot be
 * orbited. Perspective is what buys the drag-to-rotate, and rotation is what
 * makes a surface with a ridge in it readable.
 *
 * ## Hidden surfaces, and the bug this fixes
 *
 * The Python version collects every quad, computes a depth key that mixes the
 * ground position with the HEIGHT —
 *
 *     depth += x + y + z * ZSCALE
 *
 * — sorts on it, and paints back to front. Averaged-depth painter's sorting is
 * the standard approximation, and it is the same one that makes matplotlib's
 * mplot3d render intersecting surfaces wrong. Folding height into the key makes
 * it worse than it needs to be here: a tall cell at the back gets a larger key
 * than a short cell in front of it and is painted later, so a far peak can
 * overwrite a near valley that should occlude it.
 *
 * For a heightfield the exact answer is cheaper than the approximation. Cell
 * footprints on the ground plane are disjoint and convex, so along any view ray
 * the surface is single-valued: order the cells by the depth of their ground
 * centre, ignore height entirely, and painting back to front is provably
 * correct rather than usually correct. This is the same property voxel terrain
 * renderers rely on. It costs one sort of 196 keys per orbit — not per frame,
 * since the order only changes when the camera moves.
 */

export type Camera = {
  /** Rotation about the vertical axis, radians. */
  readonly yaw: number;
  /** Rotation about the horizontal axis, radians. Positive looks down. */
  readonly pitch: number;
  /** Camera-to-scene distance in world units. Larger = flatter. */
  readonly dist: number;
  /** World units to pixels, before the perspective divide. */
  readonly zoom: number;
};

export type Projected = {
  readonly sx: number;
  readonly sy: number;
  /** View-space depth. Bigger is farther. */
  readonly depth: number;
};

/**
 * World point to screen. `world` is centred on the scene origin already.
 * `cx`/`cy` are the pixel coordinates the origin lands on.
 */
export function project(
  x: number,
  y: number,
  z: number,
  cam: Camera,
  cx: number,
  cy: number,
): Projected {
  const cyaw = Math.cos(cam.yaw);
  const syaw = Math.sin(cam.yaw);
  const cpit = Math.cos(cam.pitch);
  const spit = Math.sin(cam.pitch);

  // yaw about the vertical axis (our vertical is +z, so yaw mixes x and y)
  const x1 = x * cyaw - y * syaw;
  const y1 = x * syaw + y * cyaw;

  // pitch: tilt the ground plane toward the viewer. y1 runs into the screen,
  // z is height, so the screen's vertical axis is a blend of the two.
  const depth = y1 * cpit - z * spit;
  const vy = y1 * spit + z * cpit;

  const scale = cam.dist / (cam.dist + depth * cam.zoom);
  return {
    sx: cx + x1 * cam.zoom * scale,
    sy: cy - vy * cam.zoom * scale,
    depth,
  };
}

/**
 * Back-to-front draw order for a `dim`×`dim` cell grid, keyed on the ground
 * plane only. Correct for any heightfield; see the note above on why height
 * must stay out of the key.
 *
 * Depends only on yaw, so callers should recompute it when the camera turns and
 * not once per animation frame.
 */
export function groundOrder(dim: number, yaw: number): Int16Array {
  const n = dim * dim;
  const idx = new Int16Array(n);
  const key = new Float32Array(n);
  const c = Math.cos(yaw);
  const s = Math.sin(yaw);
  const mid = (dim + 1) / 2;

  for (let i = 0; i < dim; i++) {
    for (let j = 0; j < dim; j++) {
      const k = i * dim + j;
      idx[k] = k;
      // the y' of a yaw rotation is the into-screen axis; pitch is monotonic in
      // it, so it alone decides the ordering
      key[k] = (i + 1 - mid) * s + (j + 1 - mid) * c;
    }
  }
  const order = Array.from(idx);
  order.sort((a, b) => key[b] - key[a]); // farthest first
  return Int16Array.from(order);
}

/** Running success rate over the first `t` trials, or null if the cell is empty. */
export function rateAt(
  outcomes: readonly number[] | undefined,
  t: number,
): { p: number; n: number; total: number } | null {
  if (!outcomes || outcomes.length === 0) return null;
  const n = Math.min(t, outcomes.length);
  if (n === 0) return null;
  let k = 0;
  for (let i = 0; i < n; i++) k += outcomes[i];
  return { p: k / n, n, total: outcomes.length };
}

/** Sequential ramp, pale to deep. One hue: the data is ordered, not categorical. */
const RAMP_LO = [232, 236, 243];
const RAMP_HI = [27, 42, 94];

export function ramp(p: number): string {
  const t = Math.max(0, Math.min(1, p));
  const m = (a: number, b: number) => Math.round(a + (b - a) * t);
  return `rgb(${m(RAMP_LO[0], RAMP_HI[0])},${m(RAMP_LO[1], RAMP_HI[1])},${m(RAMP_LO[2], RAMP_HI[2])})`;
}
