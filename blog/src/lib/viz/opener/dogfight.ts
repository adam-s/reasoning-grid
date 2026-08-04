/**
 * A turning fight between two point-mass aircraft, each flying its own OODA
 * loop. Pure functions, no DOM.
 *
 * ## What this is, and what it is not
 *
 * THIS IS NOT A MEASUREMENT. Nothing in this file was observed. It is a
 * diagram of the argument in Boyd's parable, integrated rather than drawn, so
 * that the outcome falls out of the mechanism instead of being asserted by
 * whoever drew the arrows. Every other figure on this page is data; this one is
 * a model, and the caption says so.
 *
 * The reason to integrate it at all is that the parable makes a causal claim —
 * a small per-cycle cost decides the fight — and a causal claim is worth
 * more when a reader can turn the cost to zero and watch the outcome reverse.
 * A hand-drawn spiral cannot be falsified by its own reader. This can.
 *
 * ## The one asymmetry
 *
 * The airframes are deliberately lopsided IN THE MIG'S FAVOUR, because that is
 * the parable's setup: the MiG-15 climbed better, turned harder, and was the
 * aircraft designers preferred. Here it gets a higher structural limit, more
 * thrust, and lower induced drag. The F-86 gets exactly one thing: a loop
 * period that does not grow.
 *
 * `tax` is the whole experiment. It is the fraction by which the MiG pilot's
 * loop period grows per completed cycle — the stiff stick, compounding.
 *
 *     T(k+1) = T(k) * (1 + tax)
 *
 * Multiplicative, not additive, and that choice is the point of the second
 * paragraph on the page: the cost is not charged once, it is carried. At
 * tax = 0 the better aircraft wins, which is the result the designers expected.
 *
 * ## Energy
 *
 * The flight model is the one Boyd himself is known for. Specific excess power
 * is thrust minus drag over weight, drag has a parasite term rising with speed
 * and an induced term rising with load factor, and a hard turn is therefore
 * paid for in speed or in altitude. Nothing gives energy back except the
 * engine and gravity. A pilot who turns harder every cycle arrives at the next
 * cycle slower, and slower means a wider turn — which is the compounding the
 * page is about, in the physics rather than in the pilot.
 *
 * ## Staleness is the mechanism, not a fudge
 *
 * A pilot observes at the top of his loop and moves the stick at the bottom of
 * it. The command is therefore computed against a picture of the opponent that
 * is one full loop old. This is the INTENDED route by which loop PERIOD enters
 * the dynamics — no term anywhere rewards a short loop directly. It is not the
 * only route, and the earlier version of this sentence claiming it was should
 * not have survived: the flight-path clamp also binds more often as the tax
 * rises. See the note on the clamps above for both binding rates and for the
 * sensitivity check that says the outcome survives either. A longer loop
 * aims at where the other aircraft used to be, holds that aim longer, and
 * overshoots. That is Boyd's "getting inside his loop", and it emerges here
 * rather than being coded.
 *
 * An earlier version let each pilot see the opponent's CURRENT state and only
 * varied how often the stick moved. The fight was then decided almost entirely
 * by the structural limit, the MiG won at every tax, and the figure argued the
 * opposite of the page. Lag is the channel; the sampling rate alone is not.
 */

const G = 9.81;

/**
 * The two clamps, and what is known about them.
 *
 * BOTH BIND IN NORMAL RUNS. That is a defect of the model rather than a
 * property of aircraft: a point-mass pursuit law with no departure or recovery
 * behaviour will fly itself slow and nose-low, and something has to stop it.
 * Because a clamp that binds is a clamp that can decide the answer, both were
 * measured over the full 120-merge ensemble rather than assumed harmless.
 *
 * The speed floor was 95 m/s and bound on 4.2% of frames at tax 0, rising to
 * 6.7% at the top of the slider. Worse, it was an ENERGY SOURCE: below the
 * floor drag exceeds thrust, but the speed was held anyway, so a pinned
 * aircraft flew on free power while still being scored. At 50 m/s it binds on
 * 0.6% to 3.4% instead, and the win rate is unchanged within its interval
 * (10.8% -> 11.7% at tax 0; 70.0% -> 66.7% at tax 0.10).
 *
 * The flight-path clamp binds on 4.6% of frames at tax 0 and 10.1% at the top,
 * and it is the one that MOVES WITH THE TAX, so it is a second channel from
 * loop period to outcome alongside the staleness lag. Relaxing it to 1.50
 * roughly halves the binding and moves the win rate 11.7% -> 8.3% at tax 0 and
 * 66.7% -> 70.0% at tax 0.10 — inside the sampling interval at every point.
 *
 * So the result is robust to both, which is the only reason it is reportable.
 * It is NOT true that the staleness lag is the sole route from loop period to
 * flight path, and nothing in this repo should say so.
 */
const FLOOR_V = 50;
const GAM_MAX = 1.35;

export type V3 = readonly [number, number, number];

const sub = (a: V3, b: V3): V3 => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const dot = (a: V3, b: V3) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const len = (a: V3) => Math.hypot(a[0], a[1], a[2]);
const unit = (a: V3): V3 => {
  const m = len(a) || 1;
  return [a[0] / m, a[1] / m, a[2] / m];
};
const cross = (a: V3, b: V3): V3 => [
  a[1] * b[2] - a[2] * b[1],
  a[2] * b[0] - a[0] * b[2],
  a[0] * b[1] - a[1] * b[0],
];
const clamp = (x: number, lo: number, hi: number) => (x < lo ? lo : x > hi ? hi : x);

/** Velocity direction from heading and flight-path angle. */
export function heading(psi: number, gam: number): V3 {
  const cg = Math.cos(gam);
  return [cg * Math.cos(psi), cg * Math.sin(psi), Math.sin(gam)];
}

/**
 * Per-airframe constants. Drag is written per unit mass so nothing here needs a
 * weight: `parasite * v^2` and `induced * n^2 / v^2` are both accelerations in
 * m/s^2, and `thrust` is one too.
 */
export type Airframe = {
  readonly name: string;
  /** Structural limit, g. */
  readonly nMax: number;
  /** Lift limit coefficient: the most g available at speed v is `lift * v^2`. */
  readonly lift: number;
  /** Thrust over mass, m/s^2. */
  readonly thrust: number;
  readonly parasite: number;
  readonly induced: number;
  /** Roll rate, rad/s. Bank slews toward the command at this rate. */
  readonly roll: number;
  /** Loop period at the merge, seconds. */
  readonly loop0: number;
  /** Does this pilot's loop period grow? Only the MiG's does. */
  readonly fatigues: boolean;
};

/**
 * The numbers are 1952-plausible at around 8 km, not looked up. They are round
 * because they are a setting for an argument, and quoting them to three figures
 * would imply a source that does not exist.
 *
 * `induced` is the one that had to be pinned to something rather than picked.
 * Chosen freely it was four times too large, and the fight it produced was
 * nonsense in a way that still animated convincingly: both aircraft hit the
 * speed floor fifteen seconds after the merge and stayed there, so the rest of
 * the run was two stalled aircraft wallowing, and every tax value gave the same
 * degenerate answer. It is now set by solving thrust = drag at a SUSTAINED
 * turn — the speed and load factor where the aircraft holds its energy —
 *
 *     thrust = parasite * v^2 + induced * n^2 / v^2
 *
 * at v = 220 m/s, giving about 3 g sustained for the Sabre and 3.9 g for the
 * MiG. Those two figures are the ones to argue with; everything else follows.
 *
 * MIG BETTER ON EVERY AXIS THAT APPEARS HERE. That is the setup, not an
 * oversight — see the header.
 */
export const SABRE: Airframe = {
  name: 'F-86',
  nMax: 6.3,
  lift: 6.3 / (185 * 185),
  thrust: 2.45,
  parasite: 2.2e-5,
  induced: 7.4e3,
  roll: 2.6,
  loop0: 1.55,
  fatigues: false,
};

export const MIG: Airframe = {
  name: 'MiG-15',
  nMax: 7.1,
  lift: 7.1 / (178 * 178),
  thrust: 2.95,
  parasite: 2.0e-5,
  induced: 6.3e3,
  roll: 2.6,
  loop0: 1.55,
  fatigues: true,
};

type State = {
  p: V3;
  psi: number;
  gam: number;
  v: number;
  /** Current bank, radians. Slews toward `cmdBank`. */
  bank: number;
  /** Held between acts — this is what "the stick has not moved yet" means. */
  cmdBank: number;
  cmdN: number;
  /** Seconds until this pilot's current cycle closes. */
  toAct: number;
  /** Length of the cycle now running. */
  period: number;
  cycle: number;
  /** The opponent as seen at the top of this cycle. */
  seen: { p: V3; h: V3; v: number };
};

/** One stored frame per ship. */
export type Frame = {
  readonly x: number;
  readonly y: number;
  readonly z: number;
  readonly psi: number;
  readonly gam: number;
  readonly bank: number;
  readonly v: number;
  /** Completed cycles so far. Trails are broken between cycles on this. */
  readonly cycle: number;
  /** Position within the current cycle, 0..1. Drives the phase colour. */
  readonly phase: number;
};

export type Fight = {
  readonly dt: number;
  readonly t: Float32Array;
  readonly sabre: Frame[];
  readonly mig: Frame[];
  /**
   * Position advantage to the Sabre, in [-1, 1]. See `advantage`.
   */
  readonly adv: Float32Array;
  /** Metres between them. */
  readonly range: Float32Array;
  /** Seconds at which each pilot committed a control input. */
  readonly acts: { readonly sabre: number[]; readonly mig: number[] };
  /** The MiG's loop period over time, seconds. The compounding, plotted. */
  readonly migPeriod: Float32Array;
  readonly sabrePeriod: number;
  readonly outcome: Outcome;
};

export type Outcome = {
  /**
   * Mean position advantage over the closing fight. Positive is the Sabre.
   * This is the scalar the whole figure is decided on, so it is worth saying
   * what it excludes: the opening 45% is the approach and the first merge,
   * where the advantage is near zero for geometric reasons rather than because
   * anyone is flying well. Averaging from t=0 would pull every fight toward
   * zero in proportion to how long the aircraft took to arrive.
   */
  readonly settled: number;
  /** The most advantage each ever held, at any instant. */
  readonly bestSabre: number;
  readonly bestMig: number;
  readonly cyclesSabre: number;
  readonly cyclesMig: number;
  /** The MiG's final loop period, seconds, and as a multiple of its first. */
  readonly finalPeriod: number;
  readonly fatigue: number;
};

/** Where the closing fight starts, as a fraction of the run. */
const SETTLE_FROM = 0.45;

/**
 * Position advantage to A over B.
 *
 *     adv = ((hA + hB) . u) / 2,    u = unit vector from A to B
 *
 * +1 is A directly astern of B on the same heading, -1 is the reverse, 0 is a
 * head-on merge or a neutral pass. The identity is worth checking rather than
 * trusting: the two nose vectors add, so the metric asks whether BOTH aircraft
 * are pointing the same way along the line between them, which is exactly what
 * being on someone's tail means. It needs no arctangents and no case analysis,
 * and it is symmetric — advantage to B is its negation, by construction, so the
 * figure cannot show both winning.
 */
export function advantage(pA: V3, hA: V3, pB: V3, hB: V3): number {
  const u = unit(sub(pB, pA));
  return clamp((dot(hA, u) + dot(hB, u)) / 2, -1, 1);
}

/**
 * What the pilot does with what he saw one cycle ago.
 *
 * Pure pursuit with a lead, then roll the lift vector onto it and pull. The
 * lead is computed from the REMEMBERED opponent velocity, so a stale picture
 * produces a confidently wrong aim point rather than a vague one — which is the
 * failure mode a slow loop actually has.
 */
function command(s: State, af: Airframe): { bank: number; n: number } {
  const h = heading(s.psi, s.gam);
  const rel = sub(s.seen.p, s.p);
  const dist = len(rel);

  // Time of flight to where he will be, capped so a distant contact does not
  // produce an aim point off in the next county.
  const tau = clamp(dist / Math.max(s.v, 1), 0, 2.5);
  const aim: V3 = [
    s.seen.p[0] + s.seen.h[0] * s.seen.v * tau,
    s.seen.p[1] + s.seen.h[1] * s.seen.v * tau,
    s.seen.p[2] + s.seen.h[2] * s.seen.v * tau,
  ];
  const e = unit(sub(aim, s.p));

  // Body-ish frame: nose, horizontal right, and the lift direction.
  const right = unit(cross(h, [0, 0, 1]));
  const up = cross(right, h);

  const ef = clamp(dot(e, h), -1, 1);
  const err = Math.acos(ef);

  // SOLVE FOR THE LIFT VECTOR, do not point it at the target.
  //
  // Two earlier versions banked straight at the contact — `atan2(e.right,
  // e.up)` — and both produced a fight that descended into the ground and kept
  // going, one of them 19 km below sea level while accelerating. The reason is
  // that a level target off the wing puts `e` in the horizontal plane, so
  // pointing lift at it commands ninety degrees of bank, and at ninety degrees
  // no part of the lift opposes gravity. Every turn dropped the nose and
  // nothing picked it up. Adding a floor on load factor did not fix it, because
  // the floor divides by cos(bank) and bank was still ninety.
  //
  // The lift vector has two jobs and they have to be added as vectors, once:
  // turn the velocity toward the target, and hold the flight path against
  // gravity. Gravity's pull perpendicular to the velocity is `g cos(gam)`
  // along the in-plane up axis, so
  //
  //     L = a_turn + g cos(gam) * up,    n = |L| / g,    bank = atan2(L.r, L.u)
  //
  // and the familiar numbers fall out rather than being imposed: asking for 4g
  // of turn in level flight gives 76 degrees of bank at 4.1g, which holds
  // altitude. When the wing cannot supply |L| the clamp below takes the
  // magnitude and keeps the direction, so a hard turn descends — correctly, and
  // for the physical reason, instead of by accident.
  // The direction to turn is the part of the line of sight across the nose.
  // It vanishes when the target is dead ahead AND when it is dead astern, and
  // the second case is the one that matters in a fight: with the contact
  // exactly behind there is no preferred direction, so keep rolling the way the
  // aircraft is already rolling, which is what a pilot does.
  const perp: V3 = [e[0] - ef * h[0], e[1] - ef * h[1], e[2] - ef * h[2]];
  const pm = len(perp);
  const dir: V3 =
    pm > 1e-3
      ? [perp[0] / pm, perp[1] / pm, perp[2] / pm]
      : [
          Math.cos(s.bank) * up[0] + Math.sin(s.bank) * right[0],
          Math.cos(s.bank) * up[1] + Math.sin(s.bank) * right[1],
          Math.cos(s.bank) * up[2] + Math.sin(s.bank) * right[2],
        ];

  // HOW HARD HE IS WILLING TO PULL, which is an energy decision and not a
  // pointing one. Written as "pull whatever the wing allows" both pilots sat on
  // the lift limit from the merge onward, bled to the speed floor within forty
  // seconds, and spent the rest of the run mushing. Every difference between the
  // two airframes — and every value of the tax — vanished into that, because a
  // fight where both aircraft are pinned at minimum speed is decided by the
  // clamp rather than by either pilot.
  //
  // The sustained load factor is the one the engine pays for, from the same
  // drag polar the integrator uses, solved for n at thrust = drag:
  //
  //     n_sust = v * sqrt((thrust - parasite v^2) / induced)
  //
  // Above corner speed there is energy to spend, so the pilot spends it up to
  // the lift or structural limit. Below it he eases back toward what he can
  // hold. This is the whole of E-M fighting and it is three lines.
  //
  // `nAllow` is capped at the wing's own limit as well. Below about 110 m/s
  // `nSust` exceeds `nLimit` — the engine would pay for more g than the wing can
  // generate — and without the cap the pilot was authorised to pull load that
  // did not exist.
  const vCorner = Math.sqrt(af.nMax / af.lift);
  const excess = Math.max(af.thrust - af.parasite * s.v * s.v, 0);
  const nSust = s.v * Math.sqrt(excess / af.induced);
  const nLimit = Math.min(af.nMax, af.lift * s.v * s.v);
  const spend = clamp((s.v - 150) / (vCorner - 150), 0, 1);
  const nAllow = clamp(nSust + (nLimit - nSust) * spend, 1, Math.max(1, nLimit));

  // Cap the TURN component, not the total, so that bank angle and load factor
  // stay consistent with each other. Clamping n after building the lift vector
  // leaves bank at the angle the uncapped demand asked for, and a 90-degree
  // bank at reduced load is a descent — the bug this figure already had twice.
  //
  // The cap has to account for the fact that the turn direction is NOT
  // perpendicular to the gravity term. Solving |dir*m + up*gc| = G*nAllow for m
  // is a quadratic, and dropping its cross term — the earlier
  // `sqrt((G nAllow)^2 - gc^2)` — is only right when the target sits in the
  // horizontal plane. Whenever it was above, |L| came out past the wing limit,
  // the final clamp cut the magnitude and left the bank angle alone, and the
  // inconsistency this block exists to prevent came back on one command in six.
  const gc = G * Math.cos(s.gam);
  const du = dot(dir, up);
  const disc = (G * nAllow) ** 2 - gc * gc * (1 - du * du);
  const maxTurn = Math.max(0, -gc * du + Math.sqrt(Math.max(0, disc)));
  const turnMag = Math.min(G * (1 + 3.4 * err), maxTurn);

  const L: V3 = [
    dir[0] * turnMag + up[0] * gc,
    dir[1] * turnMag + up[1] * gc,
    dir[2] * turnMag + up[2] * gc,
  ];

  const bank = Math.atan2(dot(L, right), dot(L, up));

  // Up to whatever the wing and the airframe allow at this speed. The lift
  // limit is what stops a slow aircraft from turning its way out of trouble,
  // and it is the term through which spent energy comes back to bite.
  const limit = Math.min(af.nMax, af.lift * s.v * s.v);
  const n = clamp(len(L) / G, 1, Math.max(1, limit));
  return { bank, n };
}

/** One Euler step of the point-mass equations. */
function step(s: State, af: Airframe, dt: number) {
  const n = s.cmdN;
  const mu = s.bank;
  const cg = Math.cos(s.gam);

  const drag = af.parasite * s.v * s.v + (af.induced * n * n) / (s.v * s.v);
  const vdot = af.thrust - drag - G * Math.sin(s.gam);
  const gdot = (G / s.v) * (n * Math.cos(mu) - cg);
  // NEGATIVE, and the sign is the whole of it. This frame has z up, so the
  // right wing of an aircraft heading +x points at -y, and a right bank must
  // therefore DECREASE psi. Written positive — the aero-textbook sign, which
  // assumes z down — both pilots turned away from the contact for the entire
  // fight. It looked like a plausible fight the whole time: two aircraft
  // circling, banking, bleeding speed, never converging. What gave it away was
  // the range, which never fell below 2 km and topped out at 6.
  //
  // cos(gam) is bounded away from zero, so this cannot blow up at the vertical.
  // A pure-vertical pull has no defined heading anyway.
  const pdot = -(G * n * Math.sin(mu)) / (s.v * Math.max(cg, 0.2));

  const h = heading(s.psi, s.gam);
  s.p = [s.p[0] + h[0] * s.v * dt, s.p[1] + h[1] * s.v * dt, s.p[2] + h[2] * s.v * dt];
  // A floor on speed rather than a stall model. See FLOOR_V: it binds, it was
  // measured, and the outcome does not depend on it.
  s.v = Math.max(FLOOR_V, s.v + vdot * dt);
  s.gam = clamp(s.gam + gdot * dt, -GAM_MAX, GAM_MAX);
  s.psi += pdot * dt;

  // Bank slews. The command is a step; the aircraft is not.
  const d = s.cmdBank - s.bank;
  const wrapped = Math.atan2(Math.sin(d), Math.cos(d));
  const move = clamp(wrapped, -af.roll * dt, af.roll * dt);
  s.bank += move;
}

/**
 * How the two aircraft arrive at the merge. Varied across the ensemble, because
 * one fight decides nothing — see `ensemble`.
 */
export type Merge = {
  /** Half the head-on separation, metres. */
  readonly reach: number;
  /** Lateral offset, metres. Zero is a collision course. */
  readonly offset: number;
  /** How much higher the MiG starts, metres. */
  readonly split: number;
  /** Crossing angle added to the MiG's heading, radians. */
  readonly cross: number;
};

export const HERO_MERGE: Merge = { reach: 2400, offset: 700, split: 320, cross: 0 };

export type Setup = {
  /** Fractional growth of the MiG's loop period per completed cycle. */
  readonly tax: number;
  readonly duration?: number;
  readonly merge?: Merge;
};

const DT = 0.01;
/** Store every Nth integration step. 0.05 s of trail is finer than the eye. */
const STRIDE = 5;

export function simulate({ tax, duration = 78, merge = HERO_MERGE }: Setup): Fight {
  const dt = DT;
  const nSteps = Math.round(duration / dt);

  const start = (p: V3, psi: number): State => ({
    p,
    psi,
    gam: 0,
    v: 250,
    bank: 0,
    cmdBank: 0,
    cmdN: 1,
    toAct: 0,
    period: 0,
    cycle: 0,
    seen: { p: [0, 0, 0], h: [1, 0, 0], v: 250 },
  });

  // The merge. Offset laterally so they pass abeam rather than colliding, and
  // split in height so the first turn is not planar — a planar merge gives a
  // two-dimensional fight and wastes the projection.
  const A = start([-merge.reach, -merge.offset, 8000], 0);
  const B = start([merge.reach, merge.offset, 8000 + merge.split], Math.PI + merge.cross);

  const ships: [State, Airframe][] = [
    [A, SABRE],
    [B, MIG],
  ];

  // Both pilots open their first cycle at t=0 against what is actually there.
  for (const [s, af] of ships) {
    const other = s === A ? B : A;
    s.seen = { p: other.p, h: heading(other.psi, other.gam), v: other.v };
    s.period = af.loop0;
    s.toAct = af.loop0;
  }

  const nFrames = Math.floor(nSteps / STRIDE) + 1;
  const t = new Float32Array(nFrames);
  const adv = new Float32Array(nFrames);
  const range = new Float32Array(nFrames);
  const migPeriod = new Float32Array(nFrames);
  const sabre: Frame[] = [];
  const mig: Frame[] = [];
  const acts = { sabre: [] as number[], mig: [] as number[] };

  let bestSabre = -1;
  let bestMig = -1;
  let settleSum = 0;
  let settleN = 0;
  const settleAfter = duration * SETTLE_FROM;

  const snap = (s: State, af: Airframe): Frame => ({
    x: s.p[0],
    y: s.p[1],
    z: s.p[2],
    psi: s.psi,
    gam: s.gam,
    bank: s.bank,
    v: s.v,
    cycle: s.cycle,
    // Where in the loop this pilot is. `toAct` counts DOWN to the act, so the
    // fraction has to be inverted or the phase colours run backwards — which
    // looked fine and was wrong, because a four-colour cycle has no obvious
    // direction until you check it against the act marks.
    phase: clamp(1 - s.toAct / (s.period || af.loop0), 0, 1),
  });

  let f = 0;
  for (let i = 0; i <= nSteps; i++) {
    const now = i * dt;

    if (i % STRIDE === 0 && f < nFrames) {
      const hA = heading(A.psi, A.gam);
      const hB = heading(B.psi, B.gam);
      const a = advantage(A.p, hA, B.p, hB);
      const r = len(sub(B.p, A.p));
      t[f] = now;
      adv[f] = a;
      range[f] = r;
      migPeriod[f] = B.period;
      sabre.push(snap(A, SABRE));
      mig.push(snap(B, MIG));
      f++;

      if (a > bestSabre) bestSabre = a;
      if (-a > bestMig) bestMig = -a;
      if (now >= settleAfter) {
        settleSum += a;
        settleN++;
      }
    }

    // Cycles close independently. Whoever's timer expires acts, then opens a
    // new cycle by looking again — observe, orient, decide, act, look again.
    for (const [s, af] of ships) {
      s.toAct -= dt;
      if (s.toAct > 0) continue;
      const c = command(s, af);
      s.cmdBank = c.bank;
      s.cmdN = c.n;
      s.cycle++;
      (s === A ? acts.sabre : acts.mig).push(now);

      const next = af.fatigues ? s.period * (1 + tax) : af.loop0;
      s.period = next;
      s.toAct += next;

      const other = s === A ? B : A;
      s.seen = { p: other.p, h: heading(other.psi, other.gam), v: other.v };
    }

    for (const [s, af] of ships) step(s, af, dt);
  }

  return {
    dt: dt * STRIDE,
    t,
    sabre,
    mig,
    adv,
    range,
    acts,
    migPeriod,
    sabrePeriod: SABRE.loop0,
    outcome: {
      settled: settleN ? settleSum / settleN : 0,
      bestSabre,
      bestMig,
      cyclesSabre: A.cycle,
      cyclesMig: B.cycle,
      finalPeriod: B.period,
      fatigue: B.period / MIG.loop0,
    },
  };
}

/**
 * ---------------------------------------------------------------------------
 * The ensemble
 * ---------------------------------------------------------------------------
 *
 * ONE FIGHT DECIDES NOTHING, and this was not a guess — it is the reason this
 * section exists. Swept across loop period and drag with a single merge, the
 * outcome jumped around non-monotonically: at a 1.0 s loop the closing
 * advantage went -0.44, +0.04, -0.47, -0.50, +0.26 over five evenly spaced
 * taxes. A turning fight is chaotic, and a reader dragging the slider on one
 * trajectory would have watched the argument reverse itself at random and
 * concluded, correctly, that the figure was noise.
 *
 * So the hero fight is an anecdote, shown as one, and the claim rests on a
 * sample of merges instead. Same aircraft, same tax, different starting
 * geometry, and the reported quantity is the fraction the Sabre wins.
 *
 * The geometry comes from a small LCG rather than `Math.random` so the curve is
 * reproducible from the seed alone, which is what lets it be precomputed by a
 * committed script and checked later.
 */

/** Deterministic merges. Ranges are wide enough to change the fight, not the sport. */
export function mergeSample(n: number, seed = 12345): Merge[] {
  let x = seed;
  const r = () => {
    x = (1103515245 * x + 12345) % 2147483648;
    return x / 2147483648;
  };
  const out: Merge[] = [];
  for (let i = 0; i < n; i++) {
    out.push({
      reach: 2200 + r() * 700,
      offset: -900 + r() * 1800,
      split: -450 + r() * 900,
      cross: -0.3 + r() * 0.6,
    });
  }
  return out;
}

export type CurvePoint = {
  readonly tax: number;
  readonly wins: number;
  readonly n: number;
  readonly rate: number;
  /** Wilson 95% interval. A bare rate over 120 fights invites over-reading. */
  readonly lo: number;
  readonly hi: number;
};

/** Wilson score interval — the one that behaves near 0 and 1, unlike normal-approx. */
export function wilson(k: number, n: number, z = 1.96): [number, number] {
  if (n === 0) return [0, 1];
  const p = k / n;
  const d = 1 + (z * z) / n;
  const c = (p + (z * z) / (2 * n)) / d;
  const h = (z * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n))) / d;
  return [Math.max(0, c - h), Math.min(1, c + h)];
}

/** Sabre win rate against tax, over a fixed sample of merges. Slow — precompute it. */
export function ensemble(taxes: readonly number[], n = 120, seed = 12345): CurvePoint[] {
  const merges = mergeSample(n, seed);
  return taxes.map((tax) => {
    let wins = 0;
    for (const merge of merges) {
      if (simulate({ tax, merge }).outcome.settled > 0) wins++;
    }
    const [lo, hi] = wilson(wins, n);
    return { tax, wins, n, rate: wins / n, lo, hi };
  });
}
