"""Continuous boundary estimate with a bootstrap interval.

`analyze.py` reports the boundary as an integer bracket ("largest size above
70%"), whose resolution is one whole digit. It therefore cannot distinguish a
model that breaks at 4.2 digits from one that breaks at 4.8 — the question the
model-pairing decision turns on — at ANY sample size.

This fits a logistic in log N instead:

    logit P(correct) = alpha + beta * log(N),     N = a*b

and reports d* , the diagonal digit count where P crosses 0.5, i.e.
sqrt(N*) where logit = 0. The bootstrap is over cells, resampling each cell's
Bernoulli trials, so the interval reflects the real sample size rather than the
number of cells.

  .venv/bin/python probe/boundary_fit.py runs/*.jsonl
"""

import json
import math
import random
import sys
from collections import defaultdict


def _fit(points, iters=200, ridge=1e-3):
    """Damped, ridge-penalised IRLS. Undamped Newton diverges on this data.

    Cells pinned at 0/n or n/n make the likelihood monotone (complete or quasi
    separation), so the unpenalised MLE runs to infinity. Plain Newton then
    produced alpha=1.5e11, beta=-5.5e10 whose RATIO happened to give exactly
    ln(16) -- reporting a boundary of 4.00 digits with a zero-width bootstrap
    interval, on data whose 4x4 cell was at 86%. A confident wrong number.

    Three guards: a small ridge penalty so separation cannot send coefficients
    to infinity, step-length limiting, and backtracking on the log-likelihood.
    """
    import math

    def loglik(a, b):
        t = 0.0
        for N, k, n in points:
            z = max(-30.0, min(30.0, a + b * math.log(N)))
            p = 1 / (1 + math.exp(-z))
            p = min(max(p, 1e-12), 1 - 1e-12)
            t += k * math.log(p) + (n - k) * math.log(1 - p)
        return t - ridge * (a * a + b * b)

    a, b = 5.0, -1.5
    cur = loglik(a, b)
    for _ in range(iters):
        g0 = g1 = h00 = h01 = h11 = 0.0
        for N, k, n in points:
            x = math.log(N)
            z = max(-30.0, min(30.0, a + b * x))
            p = 1 / (1 + math.exp(-z))
            w = n * p * (1 - p)
            r = k - n * p
            g0 += r; g1 += r * x
            h00 += w; h01 += w * x; h11 += w * x * x
        g0 -= 2 * ridge * a; g1 -= 2 * ridge * b
        h00 += 2 * ridge; h11 += 2 * ridge
        det = h00 * h11 - h01 * h01
        if abs(det) < 1e-12:
            break
        da = (h11 * g0 - h01 * g1) / det
        db = (h00 * g1 - h01 * g0) / det
        # limit the step, then backtrack until the likelihood actually improves
        m = max(abs(da), abs(db))
        if m > 1.0:
            da, db = da / m, db / m
        step = 1.0
        for _ in range(30):
            na, nb = a + step * da, b + step * db
            nl = loglik(na, nb)
            if nl >= cur:
                a, b, cur = na, nb, nl
                break
            step /= 2
        else:
            break
        if abs(step * da) < 1e-9 and abs(step * db) < 1e-9:
            break
    return a, b


def dstar(a, b):
    """Diagonal digit count at the 50% crossing. None if the fit is degenerate."""
    if b >= -1e-6:
        return None
    N = math.exp(-a / b)
    return math.sqrt(N) if N > 0 else None


def fit_boundary(cells, boots=600, seed=7):
    """cells: {(a,b): (k, n)}. Returns dict with d_star and a bootstrap CI."""
    pts = [(a * b, k, n) for (a, b), (k, n) in cells.items() if n > 0]
    if len(pts) < 2:
        return None
    a0, b0 = _fit(pts)
    d0 = dstar(a0, b0)

    rng = random.Random(seed)
    draws = []
    for _ in range(boots):
        rs = []
        for N, k, n in pts:
            p = k / n
            kk = sum(1 for _ in range(n) if rng.random() < p)
            rs.append((N, kk, n))
        aa, bb = _fit(rs)
        d = dstar(aa, bb)
        if d is not None and 0.5 < d < 100:
            draws.append(d)
    draws.sort()
    lo = draws[int(0.025 * len(draws))] if draws else None
    hi = draws[int(0.975 * len(draws))] if draws else None
    return {"d_star": d0, "lo": lo, "hi": hi, "alpha": a0, "beta": b0,
            "n_cells": len(pts), "n_gens": sum(n for _, _, n in pts),
            "degenerate_frac": 1 - len(draws) / boots}


def cells_from(recs, model=None, temperature=None, thinking=None,
               exclude_truncated=True):
    """Build {(a,b): (k,n)} with the validity rule applied.

    A generation that hit the token ceiling measures the ceiling, not the
    model, so it is dropped rather than counted as a failure.
    """
    by = defaultdict(lambda: [0, 0])
    for r in recs:
        if model and r.get("model") != model:
            continue
        if temperature is not None and r.get("temperature") != temperature:
            continue
        if thinking is not None:
            got = r.get("thinking_observed", r.get("thinking"))
            if got != thinking:
                continue
        if exclude_truncated and r.get("finish_reason") == "length":
            continue
        c = by[(r["a"], r["b"])]
        c[1] += 1
        c[0] += 1 if r["correct"] else 0
    return {k: tuple(v) for k, v in by.items()}


if __name__ == "__main__":
    recs = []
    for p in sys.argv[1:]:
        with open(p) as fh:
            recs += [json.loads(x) for x in fh if x.strip()]

    groups = defaultdict(list)
    for r in recs:
        groups[(r.get("model"), r.get("temperature"),
                r.get("thinking_observed", r.get("thinking")))].append(r)

    for key in sorted(groups, key=lambda k: str(k)):
        model, temp, think = key
        cells = cells_from(groups[key])
        if len(cells) < 2:
            continue
        f = fit_boundary(cells)
        if not f:
            continue
        ci = (f"[{f['lo']:.2f}, {f['hi']:.2f}]"
              if f["lo"] is not None else "[degenerate]")
        width = (f["hi"] - f["lo"]) if f["lo"] is not None else float("nan")
        print(f"\n{model}  temp={temp}  thinking={think}")
        print(f"  cells {f['n_cells']}  generations {f['n_gens']}")
        print(f"  boundary d* = {f['d_star']:.2f} digits   95% CI {ci}"
              f"   width {width:.2f}")
        if f["degenerate_frac"] > 0.02:
            print(f"  WARNING {f['degenerate_frac']:.0%} of bootstrap fits were "
                  f"degenerate — too few cells or too little signal")
        for (a, b), (k, n) in sorted(cells.items()):
            print(f"    {a}x{b}  {k:>3}/{n:<3}  N={a*b}")
