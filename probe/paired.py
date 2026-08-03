#!/usr/bin/env python3
"""Paired Qwen/Phi outcomes, loaded once and shared by every comparison chart.

Four render scripts had grown their own copy of this loader. They agreed when
written and would not have stayed that way: the estimator changed once already
(from "did the model ever solve it" to P(correct)) and a copy left behind would
have kept publishing the old number under a new chart's name.

The unit of pairing is `instance_uid`, which is the only key that means "the
same problem". Filenames, positions and cell coordinates all fail: a cell holds
many different problems, and comparing two independently sampled rates throws
away the per-problem pairing that makes McNemar and sign tests possible.

A CELL'S VALUE IS A PROBABILITY. It is the mean over the cell's problems of how
often each model got that problem right. Scoring by whether a model ever solved
a problem is not a probability -- it climbs with the number of times you ask,
and repeat runs here were allocated unevenly (1,579 Qwen generations against
1,206 Phi), so that scoring silently favours whichever model was run more.
"""
import collections
import glob
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reduce_grid import _parser  # noqa: E402

QWEN, PHI = "Qwen3-4B", "Phi-4-reasoning"


def load(runs="runs", a=QWEN, b=PHI):
    """-> (instances, gens)

    instances: list of dicts, one per problem both models answered:
        {uid, a, b, cell, pa, pb, na, nb}   pa/pb are that problem's hit rates
    gens: [correct_a, total_a, correct_b, total_b] over raw generations
    """
    pa = _parser()
    by, cell = collections.defaultdict(dict), {}
    for f in sorted(glob.glob(os.path.join(runs, "*.jsonl"))):
        for line in open(f):
            if not line.strip():
                continue
            j = json.loads(line)
            if (j.get("temperature") != 0.7 or j.get("top_p") != 1.0
                    or j.get("thinking_observed") is not True):
                continue
            u = j.get("instance_uid")
            if not u:
                continue
            ans, _ = pa(j.get("raw_text") or "")
            cell[u] = (j["a"], j["b"])
            by[u].setdefault((j.get("model") or "").split("/")[-1], []).append(
                ans is not None and str(ans) == str(j["truth"]))

    inst, gens = [], [0, 0, 0, 0]
    for u, d in by.items():
        if a not in d or b not in d:
            continue
        ca, cb = d[a], d[b]
        inst.append({"uid": u, "a": cell[u][0], "b": cell[u][1], "cell": cell[u],
                     "pa": sum(ca) / len(ca), "pb": sum(cb) / len(cb),
                     "na": len(ca), "nb": len(cb)})
        gens[0] += sum(ca); gens[1] += len(ca)
        gens[2] += sum(cb); gens[3] += len(cb)
    return inst, gens


def cells(inst):
    """-> {(a,b): (rate_a, rate_b, n_problems)}   equal weight per problem."""
    g = collections.defaultdict(list)
    for r in inst:
        g[r["cell"]].append((r["pa"], r["pb"]))
    return {c: (sum(x[0] for x in v) / len(v), sum(x[1] for x in v) / len(v), len(v))
            for c, v in g.items()}


def wilson(k, n, z=1.96):
    """Interval on a rate. Normal-approximation intervals put a 0-of-3 cell at
    exactly zero width, which is the one place a reader most needs a warning."""
    if not n:
        return 0.0, 1.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def logistic_fit(rows, iters=60):
    """IRLS for logit(p) = B0 + B1*(a+b) + B2*min(a,b), weighted by trials.

    Both terms are identifiable on this grid: 6x6 and 11x1 share a+b=12 while
    their chain lengths are 6 and 1, so the design varies them independently.
    That check comes before the fit, not after -- a design that cannot separate
    two terms does not return imprecise estimates, it returns unrecoverable
    ones, and no amount of extra sampling converts one into the other.

    rows: [(a, b, k, n)]  ->  [B0, B1, B2]
    """
    import numpy as np
    X = np.array([[1.0, a + b, min(a, b)] for a, b, _, _ in rows])
    k = np.array([float(x[2]) for x in rows])
    n = np.array([float(x[3]) for x in rows])
    beta = np.zeros(3)
    for _ in range(iters):
        eta = X @ beta
        mu = 1 / (1 + np.exp(-np.clip(eta, -30, 30)))
        w = np.maximum(n * mu * (1 - mu), 1e-9)
        z = eta + (k - n * mu) / w
        A = X.T @ (w[:, None] * X) + np.eye(3) * 1e-8
        step = np.linalg.solve(A, X.T @ (w * z)) - beta
        beta = beta + step
        if np.max(np.abs(step)) < 1e-10:
            break
    return beta.tolist()


def marching_squares(f, lo, hi, level, step=0.25):
    """Contour of a scalar field at `level`, as a list of screen-space segments
    in DATA coordinates. Sampled on a fine lattice rather than on the 12x12
    grid, because a contour drawn through 144 noisy cells is a staircase of
    islands and the eye reads the staircase as structure."""
    xs, ys, segs = [], [], []
    x = lo
    while x <= hi + 1e-9:
        xs.append(round(x, 6)); x += step
    ys = list(xs)
    V = [[f(x, y) for y in ys] for x in xs]
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            c = [(xs[i], ys[j], V[i][j]), (xs[i + 1], ys[j], V[i + 1][j]),
                 (xs[i + 1], ys[j + 1], V[i + 1][j + 1]), (xs[i], ys[j + 1], V[i][j + 1])]
            pts = []
            for m in range(4):
                (x0, y0, v0), (x1, y1, v1) = c[m], c[(m + 1) % 4]
                if (v0 - level) * (v1 - level) < 0:
                    t = (level - v0) / (v1 - v0)
                    pts.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
            if len(pts) == 2:
                segs.append((pts[0], pts[1]))
    return segs
