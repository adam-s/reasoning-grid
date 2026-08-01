"""Read the bake-off jsonl and report what Stage 1 was for.

  .venv/bin/python probe/analyze.py runs/*.jsonl

Reports per (model, gpu, temperature):
  - pass rate by digit size, with Wilson intervals
  - the boundary: largest size still above 70%, smallest size at or below 10%
  - observed output tokens vs a*b, which is what makes the Stage 2 budget real
  - truncation rate, so a token ceiling is never mistaken for a capability limit
  - digit-level error width, which the tokenizer hypothesis predicts differs
"""

import json
import math
import sys
from collections import defaultdict


def infer_budget_mode(rec):
    """Records predating the `budget_mode` field are still distinguishable.

    Max mode grants the same ceiling to every cell (context minus a margin);
    formula mode grants 2000 + 200*a*b. Two runs of the same cell under
    different modes are different conditions, and without this they collide on
    every key -- 48 such collisions existed across the boundary runs.
    """
    if "budget_mode" in rec:
        return rec["budget_mode"]
    formula = 2000 + 200 * rec["a"] * rec["b"]
    # Use tokens_wanted, not max_tokens. At cells where the formula exceeds the
    # context it is CLIPPED to the same ceiling max mode grants, so the granted
    # value cannot tell them apart -- that was true for every 14x14 record.
    # tokens_wanted keeps the formula's ask before clipping.
    if rec.get("tokens_wanted") is not None:
        return "formula" if rec["tokens_wanted"] == formula else "max"
    return "formula" if rec.get("max_tokens") == formula else "max"


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
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    s = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - s) / d, (c + s) / d)


def digit_error_width(answer, truth):
    """How many digit positions differ. The tokenizer hypothesis says gpt-oss
    should corrupt digits in runs of ~3 while Qwen corrupts single digits."""
    if answer is None:
        return None
    a, t = answer.rjust(len(truth), "_"), truth
    if len(a) != len(t):
        return abs(len(a) - len(t)) + sum(1 for x, y in zip(a, t) if x != y)
    return sum(1 for x, y in zip(a, t) if x != y)


def load(paths):
    recs = []
    for p in paths:
        with open(p) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    recs.append(json.loads(line))
    return recs


def main(paths):
    recs = load(paths)
    if not recs:
        print("no records")
        return
    groups = defaultdict(list)
    for r in recs:
        groups[(r["model"], r["gpu"], r["temperature"],
                _cond(r, "thinking_requested"), r.get("top_p"),
                infer_budget_mode(r), r.get("sweep_id"))].append(r)

    for key in sorted(groups, key=str):
        model, gpu, temp, think, topp, bmode, sweep = key
        rs = groups[key]
        print(f"\n{'=' * 74}")
        print(f"{model}  gpu={gpu}  T={temp}  top_p={topp}  thinking={think}  "
              f"budget={bmode}  sweep={sweep}   n={len(rs)}")
        print(f"{'=' * 74}")
        print(f"{'size':>7} {'pass':>7} {'95% CI':>16} {'avg tok':>9} "
              f"{'tok/N':>7} {'trunc':>6} {'errwidth':>9}")

        by_size = defaultdict(list)
        for r in rs:
            by_size[(r["a"], r["b"])].append(r)

        boundary_hi, boundary_lo = None, None
        for (a, b) in sorted(by_size):
            g = by_size[(a, b)]
            n = len(g)
            k = sum(x["correct"] for x in g)
            lo, hi = wilson(k, n)
            avg_tok = sum(x["completion_tokens"] for x in g) / n
            trunc = sum(x["finish_reason"] == "length" for x in g)
            widths = [
                digit_error_width(x["answer"], x["truth"])
                for x in g
                if not x["correct"] and x["answer"] is not None
            ]
            aw = f"{sum(widths) / len(widths):.1f}" if widths else "-"
            rate = k / n
            if rate > 0.7:
                boundary_hi = (a, b)
            if rate <= 0.1 and boundary_lo is None:
                boundary_lo = (a, b)
            bar = "#" * k + "." * (n - k)
            print(f"{a:>3}x{b:<3} {k:>3}/{n:<3} [{lo:.2f},{hi:.2f}] {avg_tok:>9.0f} "
                  f"{avg_tok / (a * b):>7.1f} {trunc:>6} {aw:>9}  {bar}")

        print(f"  last size above 70%: {boundary_hi}   first size at/below 10%: {boundary_lo}")

        # token cost model for budgeting Stage 2
        pts = [
            (a * b, sum(x["completion_tokens"] for x in g) / len(g))
            for (a, b), g in by_size.items()
        ]
        if len(pts) > 2:
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
            den = sum((x - mx) ** 2 for x in xs)
            slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den if den else 0
            print(f"  token cost fit: tokens ~ {my - slope * mx:.0f} + {slope:.1f} * (a*b)")

    # cross-model pairing, only where the same instances were run
    print(f"\n{'=' * 74}\npaired disagreement (same seeded instances)\n{'=' * 74}")
    byinst = defaultdict(dict)
    for r in recs:
        # key on every condition AND on instance_uid where present: two records
        # are the same trial only if all of these agree. Omitting gpu or
        # budget_mode silently merged a formula-mode run with a max-mode one.
        pk = (r["a"], r["b"], r.get("instance_uid") or r["instance_id"],
              r.get("sample_idx", 0), r["temperature"], r.get("top_p"),
              _cond(r, "thinking_requested"), infer_budget_mode(r),
              r["gpu"])
        byinst[pk][r["model"]] = r["correct"]
    models = sorted({r["model"] for r in recs})
    for i, m1 in enumerate(models):
        for m2 in models[i + 1:]:
            n11 = n10 = n01 = n00 = 0
            for _, d in byinst.items():
                if m1 in d and m2 in d:
                    a, b = d[m1], d[m2]
                    n11 += a and b
                    n10 += a and not b
                    n01 += (not a) and b
                    n00 += (not a) and (not b)
            tot = n11 + n10 + n01 + n00
            if tot:
                print(f"  {m1.split('/')[-1]} vs {m2.split('/')[-1]}  n={tot}")
                print(f"    both right {n11}  only-1st {n10}  only-2nd {n01}  both wrong {n00}")
                union = (n11 + n10 + n01) / tot
                best = max(n11 + n10, n11 + n01) / tot
                print(f"    union {union:.2f}  best single {best:.2f}  "
                      f"complementarity gain {union - best:+.2f}")


if __name__ == "__main__":
    main(sys.argv[1:])
