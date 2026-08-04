#!/usr/bin/env python3
"""Is difficulty the digit PRODUCT or the digit TOTAL?

    python probe/difficulty_axis.py

THE ANSWER IS THE TOTAL, AND SEVERAL PUBLISHED THINGS SAY OTHERWISE.

The project has assumed throughout that difficulty tracks N = a*b, the count of
single-digit operations longhand multiplication needs. It is a good story: the
chain length is the thing being measured, so the chain length should be the
axis. `probe/boundary_fit.py` fits logit(p) = alpha + beta*log(N). The published
distribution chart plots every cell against N on a log axis. The allocation
caption in the blog says the ridge follows a hyperbola because difficulty tracks
the two digit counts multiplied together, so 5x13 costs what 8x8 costs.

Fitting the alternatives against each other says otherwise. On the 196-cell
Qwen3-4B pool at temperature 0.7 with reasoning on, 2,810 generations:

    a + b            loglik -1183.9   AIC 2371.8
    a * b            loglik -1234.2   AIC 2472.4
    log(a * b)       loglik -1251.5   AIC 2506.9
    a + b, log(a*b)  loglik -1182.8   AIC 2371.6

Same parameter count, and a+b beats log(a*b) by 67.6 log-likelihood units.
Adding the product on top of the total buys 1.1 for one more parameter, which is
nothing. The same ordering holds on the 144-cell paired pool used by
`build_winner.py`, by 14.3 for Qwen and 16.7 for Phi.

The cells make it concrete without any fitting. Held at one total, the operation
count varies by more than two to one and the rate does not follow it:

    total 16:  2x14 is N=28 at 57%,  8x8 is N=64 at 85%
    total 17:  3x14 is N=42 at 56%,  9x8 is N=72 at 56%
    total 18:  4x14 is N=56 at 56%,  9x9 is N=81 at 57%

2x14 needs 28 single-digit operations and does worse than 8x8's 64. A model that
was failing in proportion to the number of steps could not do that.

WHAT IT AFFECTS

  - The distribution chart's x axis and its dispersion figure. Part of the phi =
    1.68 excess scatter it reports is cells being plotted against the wrong
    predictor, not genuine extra variance.
  - `boundary_fit.py`, which fits in log N, and every d* it has reported.
  - The cost-weighted Neyman allocation in the blog's evaluation section. Runs
    were allocated from a predicted p computed on the hyperbola, so they went to
    somewhat the wrong cells. Nothing measured is invalidated by that; the sweep
    simply did not buy the narrowing it was designed to buy.

WHAT IT DOES NOT SETTLE

Why the total should win is open. One candidate is that a lopsided problem like
2x14 makes a long partial product that has to be carried and added across many
places, so the addition rather than the multiplication is what costs. Another is
tokenization, since digit runs are grouped differently at different lengths.
Neither is tested here and this script does not claim one.
"""
import collections
import glob
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reduce_grid import _parser  # noqa: E402

MODEL = "Qwen3-4B"


def pool(runs="runs", model=MODEL):
    """-> {(a, b): [correct, total]} over the comparable generations only."""
    parse = _parser()
    agg = collections.defaultdict(lambda: [0, 0])
    for f in sorted(glob.glob(os.path.join(runs, "*.jsonl"))):
        for line in open(f):
            if not line.strip():
                continue
            j = json.loads(line)
            if (j.get("temperature") != 0.7 or j.get("top_p") != 1.0
                    or j.get("thinking_observed") is not True):
                continue
            if (j.get("model") or "").split("/")[-1] != model:
                continue
            ans, _ = parse(j.get("raw_text") or "")
            c = agg[(j["a"], j["b"])]
            c[0] += 1 if (ans is not None and str(ans) == str(j["truth"])) else 0
            c[1] += 1
    return agg


def fit(X, k, n, iters=250):
    """IRLS, same shape as paired.logistic_fit. Returns (beta, loglik)."""
    import numpy as np
    X = np.asarray(X, float)
    k = np.asarray(k, float)
    n = np.asarray(n, float)
    beta = np.zeros(X.shape[1])
    for _ in range(iters):
        eta = X @ beta
        mu = 1 / (1 + np.exp(-np.clip(eta, -30, 30)))
        w = np.maximum(n * mu * (1 - mu), 1e-9)
        z = eta + (k - n * mu) / w
        A = X.T @ (w[:, None] * X) + np.eye(X.shape[1]) * 1e-8
        beta = np.linalg.solve(A, X.T @ (w * z))
    eta = X @ beta
    mu = np.clip(1 / (1 + np.exp(-np.clip(eta, -30, 30))), 1e-12, 1 - 1e-12)
    return beta, float((k * np.log(mu) + (n - k) * np.log(1 - mu)).sum())


def main(runs="runs"):
    agg = pool(runs)
    cs = sorted(agg)
    ks = [agg[c][0] for c in cs]
    ns = [agg[c][1] for c in cs]
    print(f"{MODEL}: {len(cs)} cells, {sum(ns)} generations, "
          f"t=0.7, reasoning on")

    forms = {
        "a + b          ": [[1, a + b] for a, b in cs],
        "a * b          ": [[1, a * b] for a, b in cs],
        "log(a * b)     ": [[1, math.log(a * b)] for a, b in cs],
        "a + b, min(a,b)": [[1, a + b, min(a, b)] for a, b in cs],
        "a + b, log(a*b)": [[1, a + b, math.log(a * b)] for a, b in cs],
    }
    print("\n  model              k    loglik      AIC")
    for name, X in forms.items():
        beta, ll = fit(X, ks, ns)
        print(f"  {name}  {len(beta)}  {ll:9.1f}  {2*len(beta)-2*ll:9.1f}")

    # The comparison that needs no fit at all. Hold the total, vary the shape,
    # and watch the operation count move without the rate following it.
    print("\n  held at one total, extremes of operation count:")
    by = collections.defaultdict(list)
    for (a, b), (k, n) in agg.items():
        if n >= 6:
            by[a + b].append((a * b, a, b, k / n, n))
    for t in sorted(by):
        row = sorted(by[t])
        if len(row) < 2 or row[-1][0] < 1.8 * row[0][0]:
            continue
        lo, hi = row[0], row[-1]
        print(f"    total {t:2d}:  {lo[1]:2d}x{lo[2]:<2d} N={lo[0]:3d} "
              f"{lo[3]*100:3.0f}%   against   {hi[1]:2d}x{hi[2]:<2d} "
              f"N={hi[0]:3d} {hi[3]*100:3.0f}%")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "runs")
