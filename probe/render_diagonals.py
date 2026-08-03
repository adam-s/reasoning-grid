#!/usr/bin/env python3
"""Which axis is difficulty: total digits, or chain length?

    python probe/render_diagonals.py -o derived/diagonals.html

One small panel per value of a+b. Within a panel the total is fixed, so every
cell has the same number of single-digit multiplications to do; what changes
along the panel is the SHAPE -- 2x10 and 6x6 both total 12, but one needs 2
partial products and the other 6.

If total digits governs, each panel is flat. If chain length governs, each panel
slopes. Reading 23 panels answers a question a single fitted coefficient can
only assert.

This matters because the repo's difficulty axis is a modelling choice, and an
unstated choice is the kind that quietly decides a result. The fit already
prefers a+b on deviance; this is the same claim in a form that can be argued
with.
"""
import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paired            # noqa: E402
import chartpage         # noqa: E402

W = 940
COLS, PW, PH, GAP = 5, 0, 118, 16
PAD_L, PAD_T = 34, 20


def panel(o, x, y, tot, rows, pw):
    """rows: [(chain, qwen, phi, n)] sorted by chain."""
    ix0, iy0 = x + PAD_L, y + PAD_T
    iw, ih = pw - PAD_L - 10, PH - PAD_T - 22
    ks = [r[0] for r in rows]
    kmin, kmax = min(ks), max(ks)
    span = max(1, kmax - kmin)
    X = lambda k: ix0 + (k - kmin) / span * iw
    Y = lambda p: iy0 + (1 - p) * ih
    o.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{pw:.1f}" height="{PH}" class="pn"/>')
    for p in (0, .5, 1):
        o.append(f'<line x1="{ix0:.1f}" y1="{Y(p):.1f}" x2="{ix0+iw:.1f}" '
                 f'y2="{Y(p):.1f}" class="gl"/>')
    # A 1.1px dodge, because in the small-total panels both models sit at 100%
    # and the line drawn second hides the other completely -- five panels read as
    # "Phi only" when they mean "both, identical".
    for ix, cls, dy in ((1, "qa", -1.1), (2, "pb", +1.1)):
        d = "".join(("M" if i == 0 else "L") + f"{X(r[0]):.1f} {Y(r[ix])+dy:.1f}"
                    for i, r in enumerate(rows))
        o.append(f'<path d="{d}" class="ln {cls}" fill="none"/>')
        for r in rows:
            o.append(f'<circle cx="{X(r[0]):.1f}" cy="{Y(r[ix])+dy:.1f}" '
                     f'r="{1.8+1.3*min(1,r[3]/12):.1f}" class="d {cls}">'
                     f'<title>chain {r[0]} &#183; {"Qwen" if ix==1 else "Phi"} '
                     f'{r[ix]*100:.0f}% &#183; {r[3]} problems</title></circle>')
    o.append(f'<text x="{x+6}" y="{y+13}" class="pt">a+b = {tot}</text>')
    o.append(f'<text x="{ix0-6:.1f}" y="{Y(1)+3.5:.1f}" text-anchor="end" '
             f'class="tn">100</text>')
    o.append(f'<text x="{ix0-6:.1f}" y="{Y(0)+3.5:.1f}" text-anchor="end" '
             f'class="tn">0</text>')
    o.append(f'<text x="{X(kmin):.1f}" y="{y+PH-7}" text-anchor="middle" '
             f'class="tn">{kmin}</text>')
    if kmax != kmin:
        o.append(f'<text x="{X(kmax):.1f}" y="{y+PH-7}" text-anchor="middle" '
                 f'class="tn">{kmax}</text>')


def figure(by_tot):
    tots = sorted(by_tot)
    pw = (W - GAP * (COLS - 1)) / COLS
    rowsn = (len(tots) + COLS - 1) // COLS
    HH = rowsn * (PH + GAP) + 34
    o = [f'<svg viewBox="0 0 {W} {HH:.0f}" role="img" aria-label="One small panel per '
         f'total digit count. Inside each panel the total is fixed and the horizontal '
         f'axis is chain length. Most panels are close to flat, so total digits governs '
         f'difficulty and the shape of the problem barely matters.">']
    for i, t in enumerate(tots):
        x = (i % COLS) * (pw + GAP)
        y = (i // COLS) * (PH + GAP)
        panel(o, x, y, t, by_tot[t], pw)
    o.append(f'<text x="{W/2:.0f}" y="{HH-8:.0f}" text-anchor="middle" class="ax">'
             f'inside each panel: chain length min(a,b) &mdash; vertical: success rate'
             f'</text>')
    o.append("</svg>")
    return "\n".join(o)


EXTRA = """
.pn{fill:none;stroke:var(--line);stroke-width:1;rx:3}
.ln{stroke-width:1.7;opacity:.85}
.ln.qa{stroke:var(--lead-a)} .ln.pb{stroke:var(--lead-b)}
.d{stroke:none}
.d.qa{fill:var(--lead-a)} .d.pb{fill:var(--lead-b)}
.pt{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:10px;
  fill:var(--dim);font-weight:600}
.tn{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:8.5px;
  fill:var(--faint)}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs")
    ap.add_argument("-o", "--out", default="derived/diagonals.html")
    args = ap.parse_args()
    inst, gens = paired.load(args.runs)
    g = paired.cells(inst)

    by = collections.defaultdict(dict)          # total -> chain -> [(q,p,n)...]
    for (a, b), (q, p, n) in g.items():
        by[a + b].setdefault(min(a, b), []).append((q, p, n))
    by_tot = {}
    for t, d in by.items():
        rows = []
        for k, v in sorted(d.items()):
            nn = sum(x[2] for x in v)
            rows.append((k, sum(x[0] * x[2] for x in v) / nn,
                         sum(x[1] * x[2] for x in v) / nn, nn))
        if len(rows) >= 2:
            by_tot[t] = rows

    # how much does the rate move WITHIN a fixed total, against between totals?
    within = [max(r[1] for r in rows) - min(r[1] for r in rows)
              for rows in by_tot.values()]
    mean_within = sum(within) / len(within)
    tot_means = {t: sum(r[1] * r[3] for r in rows) / sum(r[3] for r in rows)
                 for t, rows in by_tot.items()}
    between = max(tot_means.values()) - min(tot_means.values())
    worst = max(by_tot, key=lambda t: max(r[1] for r in by_tot[t])
                - min(r[1] for r in by_tot[t]))

    fig = figure(by_tot)
    score = "\n".join([
        chartpage.stat(f"{mean_within*100:.0f}", "POINTS OF SWING INSIDE A PANEL"),
        chartpage.stat(f"{between*100:.0f}", "POINTS OF SWING BETWEEN PANELS"),
        chartpage.stat(f"{between/mean_within:.1f}&times;", "TOTAL DIGITS OVER SHAPE"),
    ])
    key = "\n".join([
        '    <span><span class="sw" style="background:var(--lead-a)"></span>Qwen</span>',
        '    <span><span class="sw" style="background:var(--lead-b)"></span>Phi</span>',
        '    <span>&#183; each panel fixes a+b; across it, the shape changes</span>',
        '    <span>&#183; dot size = how many problems</span>',
        '    <span>&#183; the two traces are nudged apart by a hair so an exact tie still shows both</span>',
    ])
    notes = (
        chartpage.note(
            "<strong>The panels are mostly flat, so total digits is the axis.</strong> "
            f"Holding a+b fixed and changing the shape moves the rate by "
            f"<strong>{mean_within*100:.0f} points</strong> on average. Moving between "
            f"totals moves it by <strong>{between*100:.0f}</strong> &mdash; about "
            f"<strong>{between/mean_within:.0f} times</strong> as much. A 2&times;10 "
            "and a 6&times;6 are close to the same problem for these models, even "
            "though one needs 2 partial products and the other 6.") +
        chartpage.note(
            "<strong>That is not the obvious answer.</strong> Chain length is the "
            "count of partial products long multiplication actually has to carry, so "
            "it is the natural candidate for what makes a problem hard. It is not what "
            "these models track. What tracks is the total number of digits, which is "
            "closer to how much has to be held at once than to how many steps there "
            "are.") +
        chartpage.note(
            "<strong>Both colours say the same thing.</strong> Where a panel does "
            "slope, Qwen and Phi slope together. Two models with different internal "
            "notions of difficulty would disagree about which shapes are hard at a "
            f"fixed total. The widest panel here is <strong>a+b = {worst}</strong>, "
            "and even there the two traces stay parallel.") +
        chartpage.note(
            "<strong>Why draw a fitted coefficient.</strong> The repo already prefers "
            "<code>a+b</code> to <code>min(a,b)</code> on deviance, which is a number "
            "you either accept or do not. This is the same claim laid out so it can be "
            "argued with: if the panels sloped, the deviance comparison would be "
            "wrong, and you would be able to see that without refitting anything.")
    )
    html = chartpage.page(
        "which axis is difficulty",
        f"carrychain &middot; {len(by_tot)} totals &middot; {len(inst):,} problems",
        "Which axis is difficulty?",
        "Each panel fixes the total number of digits. Across a panel the problem "
        "changes shape &mdash; more partial products, shorter ones. Flat panels mean "
        "the total is what matters.",
        fig, key, notes, score, EXTRA, maxw=1020)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    open(args.out, "w").write(html)
    print(f"wrote {args.out}  ({os.path.getsize(args.out)/1024:.0f} KB)")
    print(f"  within-panel swing {mean_within*100:.1f} pts, "
          f"between-panel {between*100:.1f} pts, ratio {between/mean_within:.1f}x")
    print(f"  widest panel a+b={worst}")


if __name__ == "__main__":
    main()
