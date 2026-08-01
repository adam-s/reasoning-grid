"""Raw JSONL -> one small JSON per sweep, for the renderer to fetch.

The middle step of the pipeline the surrounding projects already use: Python
writes raw, a committed script reduces it, the browser draws inline SVG from the
reduction. The browser never sees a raw record.

Everything here is derived and regenerable. Nothing is written back to runs/.

  .venv/bin/python probe/reduce_grid.py --sweep 07-grid12 --out derived/

Validity rule, applied before any rate is computed: a generation that ended
because it hit the token ceiling measured the ceiling, not the model. Those are
counted separately and never folded into the denominator. A cell whose ceiling
bound is reported as invalid rather than as a low score -- the renderer greys
it, because "we cut it off" and "it got the answer wrong" are different facts.
"""

import argparse
import glob
import json
import math
import os
from collections import defaultdict


def wilson(k, n, z=1.96):
    """Wilson score interval. Never the normal approximation: at k=0 or k=n the
    normal interval has zero width, which reads as certainty at exactly the
    cells where we have the least information."""
    if n == 0:
        return (0.0, 0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (p, max(0.0, c - h), min(1.0, c + h))


def _parser():
    """Pull parse_answer out of bakeoff.py without importing modal."""
    import re
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "bakeoff.py")).read()
    m = re.search(r"^def parse_answer\(.*?(?=\n# ---)", src, re.S | re.M)
    ns = {}
    exec(compile(m.group(0), "parse_answer", "exec"), ns)
    return ns["parse_answer"]


def load(paths, model=None, temperature=None, rescore=True):
    """Read raw records, and by default re-derive answer/correct from raw_text.

    The `answer` field on a record is whatever the parser said the day it ran,
    and this parser has shipped broken four times. Trusting the stored field
    silently mixes parser generations inside one surface: records written under
    v2 count a model that answered as a refusal, records written under v4 do
    not, and the difference lands in the rate as if it were a property of the
    model. Raw text is the only thing that does not go stale, so score from it.
    """
    pa = _parser() if rescore else None
    recs = []
    for p in paths:
        with open(p) as fh:
            for line in fh:
                if not line.strip():
                    continue
                r = json.loads(line)
                if model and r.get("model") != model:
                    continue
                if temperature is not None and r.get("temperature") != temperature:
                    continue
                if pa is not None and r.get("raw_text") is not None:
                    ans, method = pa(r["raw_text"])
                    r["answer"], r["parse_method"] = ans, method
                    r["correct"] = ans is not None and ans == r["truth"]
                recs.append(r)
    return recs


def dedupe(recs):
    """Same (model, gpu, temp, top_p, budget_mode, max_len, uid) twice means a
    chunk got written twice. Keep one. Returns (kept, n_dropped)."""
    seen, out = set(), []
    for r in recs:
        key = (r.get("model"), r.get("gpu"), r.get("temperature"), r.get("top_p"),
               r.get("budget_mode"), r.get("engine_max_len"),
               r.get("instance_uid"), r.get("trial_index"), r.get("sweep_id"))
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out, len(recs) - len(out)


def cells(recs):
    by = defaultdict(list)
    for r in recs:
        by[(r["a"], r["b"])].append(r)

    out = {}
    for (a, b), rs in by.items():
        bound = [r for r in rs if r.get("finish_reason") == "length"]
        valid = [r for r in rs if r.get("finish_reason") != "length"]
        k = sum(1 for r in valid if r["correct"])
        n = len(valid)
        p, lo, hi = wilson(k, n)
        counts = defaultdict(int)
        for r in rs:
            counts[r.get("outcome", "?")] += 1
        toks = [r["completion_tokens"] for r in rs]
        out[f"{a}x{b}"] = {
            "a": a, "b": b, "N": a * b,
            "k": k, "n": n, "p": round(p, 4),
            "lo": round(lo, 4), "hi": round(hi, 4),
            "n_ceiling_bound": len(bound),
            # a cell is only trustworthy if the ceiling never bound it
            "valid": len(bound) == 0 and n > 0,
            "outcomes": dict(counts),
            "tok_mean": round(sum(toks) / len(toks)) if toks else 0,
            "tok_max": max(toks) if toks else 0,
        }
    return out


def paired(recs_a, recs_b):
    """Per-instance agreement between two models. Only instances BOTH ran.

    The four counts are the whole two-vendor argument: `only_a` and `only_b`
    are the cells one model rescues the other on. If they are lopsided, the
    honest reading is "one model is better", not "different blind spots".
    """
    # Key on temperature too. Keying on uid alone silently lets a model's T=0.7
    # record overwrite its T=0.0 record for the same problem, so the pairing
    # compares one model at one temperature against the other at another.
    def key(r):
        return (r["instance_uid"], r.get("temperature"), r.get("trial_index", 0))

    da = {key(r): r for r in recs_a if r.get("finish_reason") != "length"}
    db = {key(r): r for r in recs_b if r.get("finish_reason") != "length"}
    both = set(da) & set(db)
    t = {"both_right": 0, "only_a": 0, "only_b": 0, "both_wrong": 0}
    per_cell = defaultdict(lambda: dict(t))
    for u in both:
        ra, rb = da[u], db[u]
        key = ("both_right" if ra["correct"] and rb["correct"] else
               "only_a" if ra["correct"] else
               "only_b" if rb["correct"] else "both_wrong")
        t[key] += 1
        per_cell[f"{ra['a']}x{ra['b']}"][key] += 1
    # McNemar, the test for whether the off-diagonal is lopsided beyond chance
    n01, n10 = t["only_a"], t["only_b"]
    chi2 = ((abs(n01 - n10) - 1) ** 2 / (n01 + n10)) if (n01 + n10) > 0 else 0.0
    return {"totals": t, "n_paired": len(both),
            "mcnemar_chi2": round(chi2, 3),
            "mcnemar_note": "1 df; >3.84 means the off-diagonal is lopsided at p<0.05",
            "per_cell": {k: v for k, v in per_cell.items()}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", required=True, help="sweep id prefix, e.g. 07-grid12")
    ap.add_argument("--runs", default="runs")
    ap.add_argument("--out", default="derived")
    ap.add_argument("--temperature", type=float, default=None)
    args = ap.parse_args()

    paths = sorted(glob.glob(os.path.join(args.runs, f"{args.sweep}*.jsonl")))
    if not paths:
        raise SystemExit(f"no files matching {args.sweep}* in {args.runs}/")
    recs = load(paths, temperature=args.temperature)
    recs, dropped = dedupe(recs)

    models = sorted({r["model"] for r in recs})
    doc = {"sweep": args.sweep, "files": len(paths), "records": len(recs),
           "duplicates_dropped": dropped, "models": {}}

    for m in models:
        mr = [r for r in recs if r["model"] == m]
        c = cells(mr)
        doc["models"][m] = {
            "n_records": len(mr),
            "n_cells": len(c),
            "temperature": sorted({r["temperature"] for r in mr}),
            "top_p": sorted({r["top_p"] for r in mr}),
            "engine_max_len": sorted({r.get("engine_max_len") for r in mr}),
            "thinking_observed": sum(1 for r in mr if r.get("thinking_observed")),
            "total_tokens": sum(r["completion_tokens"] for r in mr),
            "cells_ceiling_bound": sum(1 for v in c.values() if not v["valid"]),
            "cells": c,
        }

    if len(models) == 2:
        a, b = models
        doc["paired"] = {"model_a": a, "model_b": b,
                         **paired([r for r in recs if r["model"] == a],
                                  [r for r in recs if r["model"] == b])}

    os.makedirs(args.out, exist_ok=True)
    dest = os.path.join(args.out, f"{args.sweep}.json")
    with open(dest, "w") as fh:
        json.dump(doc, fh, indent=1)

    print(f"wrote {dest}")
    print(f"  {len(paths)} files, {len(recs)} records, {dropped} duplicates dropped")
    for m, v in doc["models"].items():
        print(f"  {m}: {v['n_cells']} cells, {v['n_records']} recs, "
              f"{v['cells_ceiling_bound']} ceiling-bound, "
              f"max_len={v['engine_max_len']}")
    if "paired" in doc:
        t = doc["paired"]["totals"]
        print(f"  paired {doc['paired']['n_paired']}: both_right={t['both_right']} "
              f"only_a={t['only_a']} only_b={t['only_b']} both_wrong={t['both_wrong']} "
              f"McNemar chi2={doc['paired']['mcnemar_chi2']}")


if __name__ == "__main__":
    main()
