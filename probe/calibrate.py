"""Derive every planning constant from runs/, so the plan is never stale.

Three constants drive the whole budget, and all three have been wrong at least
once because they were typed into a document instead of computed:

  surface     p(correct | a, b)      -- decides which cells carry information
  token model tokens(a, b)           -- decides what a cell costs
  throughput  tok/s given cell size  -- decides what a token costs

This recomputes all three from the raw records with the current parser, and
prints the allocation that follows. Run it after any new data lands.

  .venv/bin/python probe/calibrate.py
"""
import glob
import json
import math
import pathlib
import re
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
_src = (ROOT / "probe" / "bakeoff.py").read_text()
_ns = {}
exec(compile(re.search(r"^def parse_answer\(.*?(?=\n# ---)", _src, re.S | re.M).group(0),
             "p", "exec"), _ns)
parse_answer = _ns["parse_answer"]


def load(model=None, thinking=True, budget="max"):
    """Records for ONE model under one condition.

    `model` is required in practice. Pooling models fits a single surface across
    capabilities that differ by six digits: at 12x12 Qwen is 0/11 and gpt-oss is
    6/8, which averaged to 32% and made the surface non-monotone. A calibration
    that silently mixes models produces an allocation that is wrong for both.
    """
    out = []
    for f in glob.glob(str(ROOT / "runs" / "*.jsonl")):
        for line in open(f):
            r = json.loads(line)
            if model and r["model"] != model:
                continue
            if r.get("thinking_requested", r.get("thinking")) is not thinking:
                continue
            formula = 2000 + 200 * r["a"] * r["b"]
            mode = r.get("budget_mode") or (
                "formula" if r.get("tokens_wanted") == formula else "max")
            if budget and mode != budget:
                continue
            out.append(r)
    return out


def logistic_fit(cells):
    """cells: {(a,b): (k,n)} -> (alpha, beta) for logit p = a + b*log(N)."""
    pts = [(a * b, k, n) for (a, b), (k, n) in cells.items() if n]
    al, be = 5.0, -1.5
    for _ in range(300):
        g0 = g1 = h00 = h01 = h11 = 0.0
        for N, k, n in pts:
            x = math.log(N)
            p = 1 / (1 + math.exp(-max(-30, min(30, al + be * x))))
            w = n * p * (1 - p); r = k - n * p
            g0 += r; g1 += r * x; h00 += w; h01 += w * x; h11 += w * x * x
        h00 += 2e-3; h11 += 2e-3
        det = h00 * h11 - h01 * h01
        if abs(det) < 1e-12:
            break
        da = (h11 * g0 - h01 * g1) / det; db = (h00 * g1 - h01 * g0) / det
        m = max(abs(da), abs(db), 1.0)
        al += da / m; be += db / m
    return al, be


def powerfit(pairs):
    """pairs: [(x, y)] -> (k, e) for y = k * x^e, plus R^2."""
    lx = [math.log(x) for x, _ in pairs]; ly = [math.log(y) for _, y in pairs]
    mx = sum(lx) / len(lx); my = sum(ly) / len(ly)
    e = sum((a - mx) * (b - my) for a, b in zip(lx, ly)) / sum((a - mx) ** 2 for a in lx)
    k = math.exp(my - e * mx)
    r2 = 1 - sum((b - (my + e * (a - mx))) ** 2 for a, b in zip(lx, ly)) / \
        sum((b - my) ** 2 for b in ly)
    return k, e, r2


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "Qwen/Qwen3-4B"
    recs = load(model=model)
    print(f"calibrating {model} on {len(recs)} reasoning-on max-room records\n")

    cells = defaultdict(lambda: [0, 0])
    toks = defaultdict(list)
    for r in recs:
        if r["finish_reason"] == "length":
            continue
        c = cells[(r["a"], r["b"])]; c[1] += 1
        c[0] += parse_answer(r["raw_text"])[0] == r["truth"]
        toks[(r["a"], r["b"])].append(r["completion_tokens"])

    al, be = logistic_fit({k: tuple(v) for k, v in cells.items()})
    dstar = math.sqrt(math.exp(-al / be))
    print(f"SURFACE   logit p = {al:.3f} {be:+.3f}*log(N)     d* = {dstar:.2f} digits")
    print(f"          from {len(cells)} cells, {sum(v[1] for v in cells.values())} generations")

    tp = [(a * b, sum(v) / len(v)) for (a, b), v in toks.items() if len(v) >= 3]
    ts = [(a + b, sum(v) / len(v)) for (a, b), v in toks.items() if len(v) >= 3]
    kp, ep, r2p = powerfit(tp)
    ks, es, r2s = powerfit(ts)
    print(f"\nTOKENS    a*b : {kp:6.0f} * N^{ep:.3f}   R2={r2p:.3f}")
    print(f"          a+b : {ks:6.1f} * S^{es:.3f}   R2={r2s:.3f}"
          f"   {'<- better' if r2s > r2p else ''}")
    return al, be, kp, ep


if __name__ == "__main__":
    main()
