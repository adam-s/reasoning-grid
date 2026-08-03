#!/usr/bin/env python3
"""How spread out the cells are at each chain length.

    python probe/render_spread.py -o derived/spread.html

Every other chart in this set reports a middle. This one reports the spread,
which is the thing a mean hides: whether cells at chain length 8 are uniformly
middling, or split between ones the model always gets and ones it never does.

Drawn as a beeswarm, not a density. A chain length holds between 23 cells and
1, and a kernel density over 3 points draws a smooth curve that says nothing --
worse, it says it confidently. Dots can only claim what is there.

min(a,b) is the chain length: the number of partial products long multiplication
has to generate and add. It is the count, not an estimate of difficulty.
"""
import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paired            # noqa: E402
import chartpage         # noqa: E402

W, HH = 940, 620
L, T, R, Bm = 78, 26, 26, 66
DIM = 12
DOT = 3.1


def beeswarm(vals, span, halfw):
    """Place equal values side by side instead of on top of each other, without
    ever leaving the column.

    The first version spread at a fixed dot-width per neighbour. At chain length
    1, 23 of 23 cells sit at exactly 100%, so the row grew to five columns wide
    and read as data in chain lengths it had nothing to do with. Spacing is now
    solved from the widest stack: whatever fits, fits. A stack too dense to
    separate becomes a solid bar, which is the honest picture of 23 cells all
    landing on the same value.
    """
    lanes = collections.defaultdict(list)
    for v in sorted(vals):
        lanes[round(v / (DOT * 2 / span))].append(v)
    if not lanes:
        return []
    widest = max(len(g) for g in lanes.values())
    gap = min(DOT * 2.05, (2 * halfw) / widest) if widest > 1 else 0
    out = []
    for _, group in sorted(lanes.items()):
        for i, v in enumerate(group):
            k = (i + 1) // 2 * (1 if i % 2 else -1)
            out.append((v, k * gap))
    return out


def figure(rows):
    cw = (W - L - R) / DIM
    y0, y1 = T + 14, HH - Bm
    Y = lambda p: y1 - p * (y1 - y0)
    o = [f'<svg viewBox="0 0 {W} {HH}" role="img" aria-label="For each chain length '
         f'from 1 to 12, one dot per grid cell showing that cell\'s success rate, with '
         f'Qwen and Phi side by side. Both models fall together and both spread widest '
         f'in the middle chain lengths.">']
    for p in (0, .25, .5, .75, 1):
        o.append(f'<line x1="{L}" y1="{Y(p):.1f}" x2="{W-R}" y2="{Y(p):.1f}" class="gl"/>')
        o.append(f'<text x="{L-10}" y="{Y(p)+4:.1f}" text-anchor="end" '
                 f'class="tk">{p*100:.0f}%</text>')
    for k in range(1, DIM + 1):
        cx = L + (k - 0.5) * cw
        qs = [r[0] for r in rows[k]]
        ps = [r[1] for r in rows[k]]
        for vals, cls, side in ((qs, "qa", -1), (ps, "pb", +1)):
            if not vals:
                continue
            m = sum(vals) / len(vals)
            bx = cx + side * cw * 0.21
            o.append(f'<line x1="{bx-cw*0.15:.1f}" y1="{Y(m):.1f}" '
                     f'x2="{bx+cw*0.15:.1f}" y2="{Y(m):.1f}" class="mn {cls}"/>')
            for v, off in beeswarm(vals, y1 - y0, cw * 0.185):
                o.append(f'<circle cx="{bx+off:.1f}" cy="{Y(v):.1f}" r="{DOT}" '
                         f'class="dt {cls}"/>')
        o.append(f'<text x="{cx:.1f}" y="{HH-Bm+20}" text-anchor="middle" '
                 f'class="tk">{k}</text>')
        o.append(f'<text x="{cx:.1f}" y="{HH-Bm+35}" text-anchor="middle" '
                 f'class="nn">{len(qs)}</text>')
    o.append(f'<text x="{(L+W-R)/2:.0f}" y="{HH-Bm+56}" text-anchor="middle" '
             f'class="ax">chain length &mdash; min(digits in A, digits in B)</text>')
    o.append(f'<text transform="translate(19,{(y0+y1)/2:.0f}) rotate(-90)" '
             f'text-anchor="middle" class="ax">cell success rate</text>')
    o.append("</svg>")
    return "\n".join(o)


EXTRA = """
.dt{stroke:none;opacity:.72}
.dt.qa{fill:var(--lead-a)} .dt.pb{fill:var(--lead-b)}
.mn{stroke-width:2.2;opacity:.9}
.mn.qa{stroke:var(--lead-a)} .mn.pb{stroke:var(--lead-b)}
.nn{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:9px;
  fill:var(--faint);opacity:.8}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs")
    ap.add_argument("-o", "--out", default="derived/spread.html")
    args = ap.parse_args()
    inst, gens = paired.load(args.runs)
    g = paired.cells(inst)

    rows = collections.defaultdict(list)
    for (a, b), (q, p, n) in g.items():
        rows[min(a, b)].append((q, p))

    def sd(v):
        if len(v) < 2:
            return 0.0
        m = sum(v) / len(v)
        return (sum((x - m) ** 2 for x in v) / (len(v) - 1)) ** 0.5

    widest = max(range(1, DIM + 1),
                 key=lambda k: sd([r[0] for r in rows[k]]) if rows[k] else -1)
    wsd = sd([r[0] for r in rows[widest]])

    fig = figure(rows)
    score = "\n".join([
        chartpage.stat(str(widest), "CHAIN LENGTH WITH THE WIDEST SPREAD"),
        chartpage.stat(f"{wsd*100:.0f}", "POINTS OF SPREAD THERE (SD)"),
        chartpage.stat(f"{sd([r[0] for r in rows[3]])*100:.0f}", "POINTS AT CHAIN LENGTH 3"),
    ])
    key = "\n".join([
        '    <span><span class="dt" style="background:var(--lead-a)"></span>Qwen</span>',
        '    <span><span class="dt" style="background:var(--lead-b)"></span>Phi</span>',
        '    <span>&#183; one dot per grid cell</span>',
        '    <span>&#183; bar is the mean</span>',
        '    <span>&#183; small number under the axis is how many cells</span>',
    ])
    notes = (
        chartpage.note(
            "<strong>Difficulty is not a step, and it is not a smooth slope "
            "either.</strong> Cells cluster hard at the top for short chains, spread "
            f"out through the middle, and re-cluster at the bottom. The spread is "
            f"widest at chain length <strong>{widest}</strong>, at "
            f"<strong>{wsd*100:.0f} points</strong> of standard deviation against "
            f"<strong>{sd([r[0] for r in rows[3]])*100:.0f}</strong> at chain length 3. "
            "That middle band is where a model is neither reliable nor hopeless, and "
            "it is the only band where extra trials buy much.") +
        chartpage.note(
            "<strong>The two colours move together.</strong> Wherever Qwen's dots "
            "spread, Phi's spread with them, and neither has a chain length where it "
            "is tight while the other is loose. Two models with genuinely different "
            "blind spots would disagree about which sizes are the uncertain ones. "
            "These do not.") +
        chartpage.note(
            "<strong>Dots, not a density curve.</strong> A chain length holds between "
            "23 cells and 1. A kernel density over three points draws a smooth shape "
            "that says nothing, and says it confidently. The count under each axis "
            "label is how many cells stand behind that column, so a thin column is "
            "visibly thin rather than quietly so.") +
        chartpage.note(
            "<strong>Chain length is counted, not estimated.</strong> "
            "<code>min(a,b)</code> is exactly how many partial products long "
            "multiplication has to generate and add. That is why this axis exists: "
            "the difficulty of a problem here is arithmetic, known before the model "
            "sees it, which is the whole reason long multiplication is the instrument.")
    )
    html = chartpage.page(
        "spread by chain length",
        f"carrychain &middot; {len(g)} cells &middot; {len(inst):,} problems",
        "How wide the uncertain band is",
        "One dot per grid cell, grouped by how many partial products the problem "
        "needs. Means hide whether a middling column is uniformly middling or split.",
        fig, key, notes, score, EXTRA, maxw=1020)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    open(args.out, "w").write(html)
    print(f"wrote {args.out}  ({os.path.getsize(args.out)/1024:.0f} KB)")
    for k in range(1, DIM + 1):
        q = [r[0] for r in rows[k]]
        p = [r[1] for r in rows[k]]
        if q:
            print(f"  chain {k:2d}  cells {len(q):2d}  Qwen {sum(q)/len(q):.2f}"
                  f" sd {sd(q):.2f}   Phi {sum(p)/len(p):.2f} sd {sd(p):.2f}")


if __name__ == "__main__":
    main()
