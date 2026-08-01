"""Rank candidate partner models by how well they PAIR with an anchor model.

The two-vendor claim is settled by the off-diagonal of the paired 2x2 table:
how often each model gets a problem the other misses. If one model is simply
stronger, the off-diagonal is one-sided and the honest conclusion is "use the
better model" -- which is a real result, but not the one a second vendor is
bought for. So the quantity to maximise when choosing a partner is not the
partner's accuracy, it is the BALANCE of that off-diagonal.

Balance = min(only_a, only_b) / (only_a + only_b). 50% is symmetric
disagreement; near 0% means one model dominates and the pair is uninformative.

Ranking on measured d* alone would be a proxy. This projects the actual paired
table over the actual cell allocation, which is what the experiment reports.

  .venv/bin/python probe/pick_partner.py --anchor Qwen/Qwen3-4B --dim 12

Caveat stated plainly: the projection assumes the two models succeed
independently within a cell. They do not -- an instance that is hard for one is
somewhat hard for the other, so real balance will run below these numbers. It
is a ranking tool, and the ordering is what it is trusted for.
"""

import argparse
import glob
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reduce_grid import load, cells          # noqa: E402
from render_grid import fit_dstar            # noqa: E402


def curve_from_dstar(dstar, slope):
    """logistic in log N whose 50% crossing sits at dstar digits"""
    return (-slope * math.log(dstar * dstar), slope)


def fit_slope(cs):
    """Recover (alpha, beta) rather than only d*, so the projection uses each
    model's own steepness. A shallow model disagrees over a wider band."""
    pts = [(c["N"], c["k"], c["n"]) for c in cs.values() if c["valid"] and c["n"] > 0]
    if len(pts) < 3:
        return None
    a, b, ridge = 5.0, -1.5, 1e-3

    def ll(a, b):
        t = 0.0
        for N, k, n in pts:
            z = max(-30.0, min(30.0, a + b * math.log(N)))
            p = min(max(1 / (1 + math.exp(-z)), 1e-12), 1 - 1e-12)
            t += k * math.log(p) + (n - k) * math.log(1 - p)
        return t - ridge * (a * a + b * b)

    cur = ll(a, b)
    for _ in range(300):
        g0 = g1 = h00 = h01 = h11 = 0.0
        for N, k, n in pts:
            x = math.log(N)
            p = 1 / (1 + math.exp(-max(-30.0, min(30.0, a + b * x))))
            r, w = k - n * p, n * p * (1 - p)
            g0 += r; g1 += r * x
            h00 += w; h01 += w * x; h11 += w * x * x
        g0 -= 2 * ridge * a; g1 -= 2 * ridge * b
        h00 += 2 * ridge; h11 += 2 * ridge
        det = h00 * h11 - h01 * h01
        if abs(det) < 1e-12:
            break
        da, db = (h11 * g0 - h01 * g1) / det, (h00 * g1 - h01 * g0) / det
        m = max(abs(da), abs(db))
        if m > 1.0:
            da, db = da / m, db / m
        step = 1.0
        for _ in range(30):
            if ll(a + step * da, b + step * db) >= cur:
                a, b = a + step * da, b + step * db
                cur = ll(a, b)
                break
            step /= 2
        else:
            break
    return (a, b) if b < -1e-6 else None


def project(anchor, cand, dim, n_per_cell=12):
    def p(ab, prm):
        A, B = prm
        return 1 / (1 + math.exp(-max(-30, min(30, A + B * math.log(ab)))))
    t = {"br": 0.0, "oa": 0.0, "ob": 0.0, "bw": 0.0}
    for a in range(1, dim + 1):
        for b in range(1, dim + 1):
            pa, pb = p(a * b, anchor), p(a * b, cand)
            t["br"] += n_per_cell * pa * pb
            t["oa"] += n_per_cell * pa * (1 - pb)
            t["ob"] += n_per_cell * (1 - pa) * pb
            t["bw"] += n_per_cell * (1 - pa) * (1 - pb)
    off = t["oa"] + t["ob"]
    t["balance"] = min(t["oa"], t["ob"]) / off if off else 0.0
    t["disagree"] = off
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anchor", default="Qwen/Qwen3-4B")
    ap.add_argument("--anchor-glob", default="runs/05-grid-t07*.jsonl")
    ap.add_argument("--cand-glob", default="runs/08-screen-*.jsonl")
    ap.add_argument("--dim", type=int, default=12)
    ap.add_argument("--temperature", type=float, default=0.7)
    # the anchor may have been measured under a different temperature than the
    # candidates; filtering both with one value silently empties the anchor
    ap.add_argument("--anchor-temperature", type=float, default=None)
    args = ap.parse_args()
    atemp = args.anchor_temperature if args.anchor_temperature is not None \
        else args.temperature

    def surface(paths, model=None, temp=None):
        recs = load(sorted(glob.glob(paths)), model=model, temperature=temp)
        recs = [r for r in recs if r["a"] <= args.dim and r["b"] <= args.dim]
        return recs, cells(recs)

    arecs, acells = surface(args.anchor_glob, args.anchor, atemp)
    aprm = fit_slope(acells)
    ad = fit_dstar(acells)
    if not aprm:
        raise SystemExit("anchor fit failed")
    ak = sum(c["k"] for c in acells.values()); an = sum(c["n"] for c in acells.values())
    print(f"anchor  {args.anchor}")
    print(f"  d* = {ad:.2f} digits   slope {aprm[1]:.2f}   "
          f"{ak}/{an} correct over {len(acells)} cells\n")

    # Group ALL files by model first. Skipping a file because its model was
    # already seen silently drops every chunk after the first, which halves the
    # data behind each fit without changing anything visible in the output.
    by_model = {}
    for f in sorted(glob.glob(args.cand_glob)):
        for r in load([f], temperature=args.temperature):
            by_model.setdefault(r["model"], []).append(r)

    rows = []
    for m, recs in by_model.items():
        recs = [r for r in recs if r["a"] <= args.dim and r["b"] <= args.dim]
        cs = cells(recs)
        prm, d = fit_slope(cs), fit_dstar(cs)
        k = sum(c["k"] for c in cs.values()); n = sum(c["n"] for c in cs.values())
        bound = sum(1 for c in cs.values() if not c["valid"])
        if not prm or not d:
            rows.append((m, d, None, k, n, bound, None))
            continue
        rows.append((m, d, prm[1], k, n, bound, project(aprm, prm, args.dim)))

    rows.sort(key=lambda r: -(r[6]["balance"] if r[6] else -1))
    print(f"{'candidate':<40}{'d*':>7}{'gap':>7}{'slope':>7}{'correct':>10}"
          f"{'bound':>7}{'disagree':>10}{'balance':>9}")
    for m, d, sl, k, n, bound, pr in rows:
        if not pr:
            print(f"{m.split('/')[-1]:<40}{'--':>7}{'--':>7}{'--':>7}{k:>5}/{n:<4}{bound:>7}"
                  f"{'--':>10}{'  FIT FAILED':>9}")
            continue
        print(f"{m.split('/')[-1]:<40}{d:>7.2f}{d-ad:>7.2f}{sl:>7.2f}{k:>5}/{n:<4}"
              f"{bound:>7}{pr['disagree']:>10.0f}{pr['balance']:>8.0%}")
    if rows and rows[0][6]:
        w = rows[0]
        print(f"\nbest pairing: {args.anchor.split('/')[-1]} + {w[0].split('/')[-1]}")
        print(f"  projected at n=12 over {args.dim}x{args.dim}: "
              f"{w[6]['oa']:.0f} anchor-only, {w[6]['ob']:.0f} partner-only, "
              f"balance {w[6]['balance']:.0%}")
        print("  (independence assumed within a cell; real balance will be lower)")


if __name__ == "__main__":
    main()
