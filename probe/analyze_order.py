#!/usr/bin/env python3
"""Does operand order change the answer? Two readings, both tested.

Regenerates every number in the commutativity artifact. Run it before citing
any of them.

    python probe/analyze_order.py

DIRECTION -- is one order better? A grid cannot answer this. Cell (a,b) and
cell (b,a) hold independently drawn integers, so a gap between them mixes an
order effect with "those were harder numbers". Tested anyway across every
mirror-pair in the project, because a null over 4,985 generations bounds the
effect even with the confound working against us.

DISAGREEMENT -- does reversing flip the outcome more often than re-asking? This
needs the swap design: the SAME integers presented both ways, paired on
instance_uid. And it needs a control, because at temperature 0.7 the model
flips on its own. The control is the same problem, same order, run twice.

The control must be drawn from the same cells as the swap. Taking it from
whichever cells happened to be re-run gives 17.5% and a fake near-doubling,
because the sweep re-ran easy cells (see sweeps/10-grid14-pair/RESULTS.md on
allocation). Restricted to the swap's own 14 cells it is 36.0%, and the effect
disappears.
"""
import collections
import glob
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reduce_grid import _parser  # noqa: E402

COND = dict(model="Qwen/Qwen3-4B", temperature=0.7, top_p=1.0)


def wilson(k, n, z=1.96):
    if not n:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - m) / d, (c + m) / d)


def sign_test(a, b):
    n = a + b
    if not n:
        return 1.0
    return min(1.0, sum(math.comb(n, i) for i in range(min(a, b) + 1)) / 2 ** n * 2)


def load_all(runs="runs"):
    pa = _parser()
    out = []
    for f in sorted(glob.glob(os.path.join(runs, "*.jsonl"))):
        for line in open(f):
            if not line.strip():
                continue
            j = json.loads(line)
            ans, _ = pa(j.get("raw_text") or "")
            j["_ok"] = ans is not None and str(ans) == str(j["truth"])
            out.append(j)
    return out


def direction(recs):
    """Mirror cells, paired within condition. Independently drawn problems."""
    cond = lambda r: (r.get("model"), r.get("temperature"), r.get("top_p"),
                      r.get("thinking_observed"))
    G = collections.defaultdict(lambda: [0, 0])
    for r in recs:
        a, b = r.get("a"), r.get("b")
        if not a or not b or a == b:
            continue
        g = G[(cond(r), a, b)]
        g[0] += r["_ok"]
        g[1] += 1

    hi = lo = tie = 0
    K1 = N1 = K2 = N2 = 0
    for (c, a, b), (k1, n1) in list(G.items()):
        if a <= b:
            continue
        m = G.get((c, b, a))
        if not m:
            continue
        k2, n2 = m
        if n1 < 3 or n2 < 3:
            continue
        d = k1 / n1 - k2 / n2
        hi += d > 0
        lo += d < 0
        tie += d == 0
        K1 += k1; N1 += n1; K2 += k2; N2 += n2

    gap = K1 / N1 - K2 / N2
    se = math.sqrt(K1/N1*(1-K1/N1)/N1 + K2/N2*(1-K2/N2)/N2)
    return dict(pairs=hi + lo + tie, first_higher=hi, second_higher=lo, tied=tie,
                sign_p=sign_test(hi, lo), generations=N1 + N2, gap=gap,
                gap_ci=(gap - 1.96 * se, gap + 1.96 * se))


def disagreement(recs):
    """Same integers both ways, against a same-order control from the same cells."""
    xy = collections.defaultdict(list)
    yx = collections.defaultdict(list)
    cell = {}
    for r in recs:
        if (r.get("model") != COND["model"] or r.get("temperature") != COND["temperature"]
                or r.get("top_p") != COND["top_p"] or r.get("thinking_observed") is not True):
            continue
        u = r.get("instance_uid")
        if not u:
            continue
        cell[u] = (r["a"], r["b"])
        (yx if r.get("presented_as") == "yx" else xy)[u].append(r)

    shared = sorted(set(xy) & set(yx))
    cells = {cell[u] for u in shared}

    rr = rw = wr = ww = 0
    for u in shared:
        o, v = xy[u][0]["_ok"], yx[u][0]["_ok"]
        rr += o and v
        rw += o and not v
        wr += v and not o
        ww += not o and not v
    flips = rw + wr

    bf = bn = 0
    for u, v in xy.items():
        if cell[u] not in cells or len(v) < 2:
            continue
        rs = [j["_ok"] for j in v]
        for i in range(len(rs) - 1):
            bn += 1
            bf += rs[i] != rs[i + 1]

    p1, p2 = flips / len(shared), (bf / bn if bn else float("nan"))
    pp = (flips + bf) / (len(shared) + bn)
    se = math.sqrt(pp * (1 - pp) * (1 / len(shared) + 1 / bn))
    z = (p1 - p2) / se
    return dict(paired=len(shared), cells=len(cells),
                both_right=rr, orig_only=rw, rev_only=wr, both_wrong=ww,
                direction_p=sign_test(rw, wr),
                rev_flip=p1, rev_flip_ci=wilson(flips, len(shared)), rev_n=len(shared),
                base_flip=p2, base_flip_ci=wilson(bf, bn), base_n=bn,
                diff=p1 - p2, z=z, p=math.erfc(abs(z) / math.sqrt(2)))


def main():
    recs = load_all()
    print(f"{len(recs):,} records\n")

    d = direction(recs)
    print("DIRECTION -- is one order better?")
    print(f"  {d['pairs']} mirror-pairs, {d['generations']:,} generations")
    print(f"  first longer higher {d['first_higher']}   second higher {d['second_higher']}"
          f"   tied {d['tied']}")
    print(f"  sign test p = {d['sign_p']:.3f}")
    print(f"  pooled gap {d['gap']:+.4f}  95% CI [{d['gap_ci'][0]:+.3f}, {d['gap_ci'][1]:+.3f}]")

    a = disagreement(recs)
    print(f"\nDISAGREEMENT -- does reversing flip more than re-asking?")
    print(f"  {a['paired']} problems shown both ways, {a['cells']} cells")
    print(f"  both right {a['both_right']}   orig only {a['orig_only']}"
          f"   rev only {a['rev_only']}   both wrong {a['both_wrong']}")
    print(f"  direction among flips: sign test p = {a['direction_p']:.3f}")
    print(f"  reversed   {a['rev_flip']:.1%}  CI [{a['rev_flip_ci'][0]:.1%}, {a['rev_flip_ci'][1]:.1%}]"
          f"   n={a['rev_n']}")
    print(f"  same order {a['base_flip']:.1%}  CI [{a['base_flip_ci'][0]:.1%}, {a['base_flip_ci'][1]:.1%}]"
          f"   n={a['base_n']}")
    print(f"  difference {a['diff']:+.1%}   z = {a['z']:+.2f}   p = {a['p']:.3f}")
    print(f"\n  The control has {a['base_n']} comparisons. It rules out a large effect,")
    print(f"  not a modest one. The headline number is the control itself:")
    print(f"  re-asking the same question flips the verdict {a['base_flip']:.0%} of the time.")


if __name__ == "__main__":
    main()
