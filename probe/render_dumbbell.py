#!/usr/bin/env python3
"""Every cell as a pair of dots, sorted by Qwen.

    python probe/render_dumbbell.py -o derived/dumbbell.html

The grid charts show where the cells are. This one shows how far apart the two
models get, cell by cell, with nothing between the reader and the number. Sorted
by Qwen, so the blue trace is monotone by construction and the orange trace's
wandering around it is the entire signal.

A crossing is a segment pointing the wrong way. There are 15, they are countable
here, and every one is short -- which is the honest way to show that they are
what a fifteen-way coin flip looks like rather than a region Phi owns.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paired            # noqa: E402
import chartpage         # noqa: E402

ROW = 6.4
L, T, R = 92, 26, 52
W = 940


def figure(rows):
    HH = T + len(rows) * ROW + 54
    x0, x1 = L, W - R
    X = lambda p: x0 + p * (x1 - x0)
    o = [f'<svg viewBox="0 0 {W} {HH:.0f}" role="img" aria-label="One row per grid '
         f'cell, ordered by Qwen\'s success rate, each row a blue dot and an orange dot '
         f'joined by a line. Orange sits left of blue on most rows and the 15 rows '
         f'where it sits right are all short.">']
    for p in (0, .25, .5, .75, 1):
        o.append(f'<line x1="{X(p):.1f}" y1="{T}" x2="{X(p):.1f}" '
                 f'y2="{T+len(rows)*ROW:.1f}" class="gl"/>')
        o.append(f'<text x="{X(p):.1f}" y="{T-9}" text-anchor="middle" '
                 f'class="tk">{p*100:.0f}%</text>')
    for i, (c, q, p, n) in enumerate(rows):
        y = T + (i + 0.5) * ROW
        flip = p > q
        o.append(f'<line x1="{X(min(q,p)):.1f}" y1="{y:.1f}" x2="{X(max(q,p)):.1f}" '
                 f'y2="{y:.1f}" class="cn{" fl" if flip else ""}"/>')
        o.append(f'<circle cx="{X(q):.1f}" cy="{y:.1f}" r="2.5" class="d qa"/>')
        o.append(f'<circle cx="{X(p):.1f}" cy="{y:.1f}" r="2.5" class="d pb"/>')
        if flip:
            o.append(f'<text x="{X(max(q,p)):.1f}" y="{y+3:.1f}" dx="7" '
                     f'class="fx">{c[0]}&times;{c[1]}</text>')
        if i % 12 == 0:
            o.append(f'<text x="{L-11}" y="{y+3.4:.1f}" text-anchor="end" '
                     f'class="tk">{c[0]}&times;{c[1]}</text>')
    o.append(f'<text x="{(x0+x1)/2:.0f}" y="{HH-18:.0f}" text-anchor="middle" '
             f'class="ax">chance of an exactly correct product</text>')
    o.append(f'<text transform="translate(20,{T+len(rows)*ROW/2:.0f}) rotate(-90)" '
             f'text-anchor="middle" class="ax">144 cells, ordered by Qwen</text>')
    o.append("</svg>")
    return "\n".join(o)


EXTRA = """
.cn{stroke:var(--ink);stroke-width:1.5;opacity:.17}
.cn.fl{stroke:var(--lead-b);stroke-width:2.4;opacity:.8}
.d{stroke:none}
.d.qa{fill:var(--lead-a)} .d.pb{fill:var(--lead-b)}
.fx{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:8.5px;
  fill:var(--lead-b);opacity:.95}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs")
    ap.add_argument("-o", "--out", default="derived/dumbbell.html")
    args = ap.parse_args()
    inst, gens = paired.load(args.runs)
    g = paired.cells(inst)

    rows = sorted(((c, q, p, n) for c, (q, p, n) in g.items()),
                  key=lambda r: (-r[1], -r[2]))
    flips = [r for r in rows if r[2] > r[1]]
    gaps = [r[1] - r[2] for r in rows]
    mean_gap = sum(gaps) / len(gaps)
    worst = max(rows, key=lambda r: r[1] - r[2])
    biggest_flip = max(flips, key=lambda r: r[2] - r[1])

    fig = figure(rows)
    score = "\n".join([
        chartpage.stat(f"{mean_gap*100:+.0f}", "MEAN GAP PER CELL, POINTS", "qc"),
        chartpage.stat(str(len(flips)), "ROWS POINTING THE OTHER WAY", "pc"),
        chartpage.stat(f"{(biggest_flip[2]-biggest_flip[1])*100:.0f}",
                       "BIGGEST FLIP, POINTS"),
        chartpage.stat(f"{(worst[1]-worst[2])*100:.0f}", "BIGGEST QWEN LEAD, POINTS"),
    ])
    key = "\n".join([
        '    <span><span class="dt" style="background:var(--lead-a)"></span>Qwen</span>',
        '    <span><span class="dt" style="background:var(--lead-b)"></span>Phi</span>',
        '    <span>&#183; orange bar = a row where Phi is higher</span>',
        '    <span>&#183; ordered by Qwen, so blue is monotone by construction</span>',
    ])
    notes = (
        chartpage.note(
            "<strong>The orange dot sits left of the blue one almost the whole way "
            f"down.</strong> Mean gap <strong>{mean_gap*100:+.0f} points</strong>, and "
            f"the largest is <strong>{(worst[1]-worst[2])*100:.0f}</strong> at "
            f"{worst[0][0]}&times;{worst[0][1]}. Only "
            f"<strong>{len(flips)} of {len(rows)}</strong> rows point the other way, "
            "and they are marked and named.") +
        chartpage.note(
            "<strong>Every flip is short.</strong> The biggest is "
            f"<strong>{(biggest_flip[2]-biggest_flip[1])*100:.0f} points</strong> at "
            f"{biggest_flip[0][0]}&times;{biggest_flip[0][1]}, against Qwen leads that "
            "reach three or four times that. If Phi genuinely owned a region, its wins "
            "would be as large as its losses somewhere. They are not, anywhere.") +
        chartpage.note(
            "<strong>Sorting by Qwen is doing work, so say so.</strong> It makes the "
            "blue trace monotone by construction, which means blue's smoothness is an "
            "artefact of the sort and carries no information. Everything the chart has "
            "to say is in how far orange strays from blue and in which direction. "
            "Sorting by the other model would look different and mean the same.") +
        chartpage.note(
            "<strong>What this drops.</strong> The grid position is gone except in the "
            "labels, so you cannot see that the flips cluster near the falling edge "
            "&mdash; that is what the surface charts are for. What you get instead is "
            "exactness: 144 rows, 15 marked, each one countable rather than inferred "
            "from an area.")
    )
    html = chartpage.page(
        "every cell, both models",
        f"carrychain &middot; {len(rows)} cells &middot; {len(inst):,} problems",
        "Every cell, both models, sorted",
        "One row per problem size. Blue is Qwen, orange is Phi, and the bar between "
        "them is the gap. Rows where Phi wins point the other way and are marked.",
        fig, key, notes, score, EXTRA, maxw=1020)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    open(args.out, "w").write(html)
    print(f"wrote {args.out}  ({os.path.getsize(args.out)/1024:.0f} KB)")
    print(f"  mean gap {mean_gap*100:+.1f} points, {len(flips)} flips, "
          f"biggest flip {(biggest_flip[2]-biggest_flip[1])*100:.0f} at "
          f"{biggest_flip[0]}, biggest lead {(worst[1]-worst[2])*100:.0f} at {worst[0]}")


if __name__ == "__main__":
    main()
