"""Derive the two essay charts from raw records, to prove they are capturable.

  .venv/bin/python probe/chartdata.py runs/<file>.jsonl

Chart 1 — running pass rate over trials at one cell, with a Wilson band that
          narrows as trials accumulate. This is the convergence argument: the
          per-trial result is noisy, the aggregate settles.
Chart 2 — pass rate by cell with Wilson intervals and the trial count.
"""
import json
import math
import sys
from collections import defaultdict


def _cond(rec, key):
    """Condition variables are never defaulted. A missing key means the record
    predates the field, and silently calling that False is how a thinking-ON
    run gets labelled thinking-OFF -- the exact error this project already made
    once. Legacy records are backfilled explicitly, not guessed."""
    if key in rec:
        return rec[key]
    if key == "thinking_requested" and "thinking" in rec:
        return rec["thinking"]          # pre-rename records
    raise KeyError(f"record missing condition key {key!r}; backfill it explicitly")


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 1.0
    ph = k / n
    d = 1 + z * z / n
    c = ph + z * z / (2 * n)
    s = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n))
    return (c - s) / d, (c + s) / d


def load(paths):
    out = []
    for p in paths:
        with open(p) as fh:
            out += [json.loads(x) for x in fh if x.strip()]
    return out


def chart1(recs, a, b, cond):
    """Running pass rate at one cell, ordered by trial_index (reproducible)."""
    rs = [r for r in recs if r["a"] == a and r["b"] == b
          and r.get("temperature") == cond]
    rs.sort(key=lambda r: (r.get("trial_index", r["instance_id"]),
                           r.get("sample_idx", 0)))
    pts, k = [], 0
    for i, r in enumerate(rs, 1):
        k += 1 if r["correct"] else 0
        lo, hi = wilson(k, i)
        pts.append({"trial": i, "pass": r["correct"], "running": k / i,
                    "lo": lo, "hi": hi})
    return pts


def chart2(recs):
    """Pass rate per cell with interval and trial count."""
    by = defaultdict(list)
    for r in recs:
        by[(r["a"], r["b"], r.get("temperature"))].append(r)
    rows = []
    for (a, b, t), g in sorted(by.items()):
        n = len(g)
        k = sum(x["correct"] for x in g)
        lo, hi = wilson(k, n)
        rows.append({"a": a, "b": b, "temperature": t, "n": n, "k": k,
                     "rate": k / n, "lo": lo, "hi": hi,
                     "label": f"{a}d x {b}d"})
    return rows


if __name__ == "__main__":
    recs = load(sys.argv[1:])
    rows = chart2(recs)
    print(f"{'cell':>10} {'temp':>5} {'trials':>7} {'rate':>7} {'95% CI':>16}")
    for r in rows:
        print(f"{r['label']:>10} {str(r['temperature']):>5} {r['n']:>7} "
              f"{r['rate']:>7.3f} [{r['lo']:.2f},{r['hi']:.2f}]")
    if rows:
        best = max(rows, key=lambda r: r["n"])
        pts = chart1(recs, best["a"], best["b"], best["temperature"])
        print(f"\nrunning pass rate at {best['label']} temp={best['temperature']}")
        print(f"{'trial':>6} {'pass':>5} {'running':>8} {'band':>16}")
        for p in pts:
            mark = "#" if p["pass"] else "."
            print(f"{p['trial']:>6} {mark:>5} {p['running']:>8.3f} "
                  f"[{p['lo']:.2f},{p['hi']:.2f}]")


# --------------------------------------------------------------------------
# The deliverable: x = a digits, y = b digits, z = P(correct)
# --------------------------------------------------------------------------
def grid(recs, temperature=None, model=None, thinking=None):
    """z-surface plus everything needed to grey out an invalid cell."""
    by = defaultdict(list)
    for r in recs:
        if temperature is not None and r.get("temperature") != temperature:
            continue
        if model is not None and r.get("model") != model:
            continue
        if thinking is not None and _cond(r, "thinking_requested") != thinking:
            continue
        by[(r["a"], r["b"])].append(r)

    cells = {}
    for (a, b), g in by.items():
        n = len(g)
        k = sum(x["correct"] for x in g)
        lo, hi = wilson(k, n)
        grind = sum(1 for x in g if x.get("outcome") == "grind")
        quit_ = sum(1 for x in g if x.get("outcome") == "quit")
        cells[(a, b)] = {
            "a": a, "b": b, "n": n, "k": k, "z": k / n, "lo": lo, "hi": hi,
            "N": a * b, "grind": grind, "quit": quit_,
            "trunc_rate": grind / n,
            # a cell whose generations hit the ceiling is measuring the ceiling
            "valid": grind / n <= 0.05,
        }
    return cells


def render_grid(cells, width=6):
    """Terminal heatmap. x across, y down, z as shade."""
    if not cells:
        return "no cells"
    xs = sorted({c["a"] for c in cells.values()})
    ys = sorted({c["b"] for c in cells.values()})
    ramp = " .:-=+*#%@"
    out = ["", "z = P(exactly correct).  x = digits of A across, y = digits of B down",
           "  " + "".join(f"{x:>{width}}" for x in xs)]
    for y in ys:
        row = f"{y:>2}"
        for x in xs:
            c = cells.get((x, y))
            if c is None:
                row += " " * width
            elif not c["valid"]:
                row += f"{'~':>{width}}"          # ceiling-bound, not a capability
            else:
                row += f"{ramp[min(int(c['z'] * 9.999), 9)] * 2:>{width}}"
        out.append(row)
    out.append("  legend  ' '=no data  ~=invalid (hit ceiling)  "
               ".. low -> @@ high")
    return "\n".join(out)


# --------------------------------------------------------------------------
# Streaks: a run of failures is compatible with a high overall rate
# --------------------------------------------------------------------------
def longest_fail_run(seq):
    best = cur = 0
    for ok in seq:
        cur = 0 if ok else cur + 1
        best = max(best, cur)
    return best


def p_run_at_least(n, q, k):
    """P(at least one run of >= k failures in n Bernoulli trials), q = P(fail).

    Exact DP over 'current failure streak length', so no simulation noise.
    """
    if k <= 0:
        return 1.0
    state = [0.0] * k
    state[0] = 1.0
    hit = 0.0
    for _ in range(n):
        nxt = [0.0] * k
        for s, pr in enumerate(state):
            if pr == 0.0:
                continue
            nxt[0] += pr * (1 - q)              # success resets the streak
            if s + 1 >= k:
                hit += pr * q                    # streak reaches k -> absorbed
            else:
                nxt[s + 1] += pr * q
        state = nxt
    return hit


def streak_report(recs, a, b, temperature=None):
    rs = [r for r in recs if r["a"] == a and r["b"] == b
          and (temperature is None or r.get("temperature") == temperature)]
    rs.sort(key=lambda r: (r.get("trial_index", r["instance_id"]),
                           r.get("sample_idx", 0)))
    seq = [bool(r["correct"]) for r in rs]
    n, k = len(seq), sum(seq)
    if n == 0:
        return "no records"
    rate = k / n
    q = 1 - rate
    obs = longest_fail_run(seq)
    lines = [f"\n{a}d x {b}d   {k}/{n} = {rate:.1%} correct",
             "".join("#" if s else "." for s in seq),
             f"longest observed run of failures: {obs}",
             "",
             f"{'run of':>7} {'P(>= this run somewhere in ' + str(n) + ' trials)':>44}"]
    for kk in range(2, 8):
        lines.append(f"{kk:>7} {p_run_at_least(n, q, kk):>44.1%}")
    lines.append("\nA losing streak is not evidence the rate changed. Read the "
                 "table:\nif a run of that length is likely at this rate, the "
                 "streak carries no signal.")
    return "\n".join(lines)
