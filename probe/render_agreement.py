#!/usr/bin/env python3
"""Do the two models disagree by more than sampling noise? (Bland-Altman)

    python probe/render_agreement.py -o derived/agreement.html

Every cell as a point: the average of the two rates across, the difference up.
This is the standard chart for "do two measurements agree", and it answers the
one question the grid charts keep inviting and cannot settle -- whether the
cells where Phi wins are a finding or a coin landing the other way.

The envelope is the answer. For a cell of n problems at average rate m, two
independent binomial estimates differ with SD sqrt(2m(1-m)/n), which is largest
at m = 0.5 and vanishes at both ends. Plotting +-1.96 of that alongside the
points shows directly whether the scatter is bigger than the sampling floor.

The envelope is drawn from INDEPENDENT sampling although the design is paired.
Pairing makes the true SD smaller, so this envelope is wider than it should be
and the test is conservative: a point outside it is outside under an assumption
that was already being generous.
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paired            # noqa: E402
import chartpage         # noqa: E402

W, HH = 940, 620
L, T, R, Bm = 74, 30, 152, 62


def figure(pts, bands, bias, loa, YMAX, ticks):
    x0, x1 = L, W - R
    y0, y1 = T, HH - Bm
    X = lambda m: x0 + m * (x1 - x0)
    Y = lambda d: (y0 + y1) / 2 - d / YMAX * (y1 - y0) / 2
    o = [f'<svg viewBox="0 0 {W} {HH}" role="img" aria-label="Bland-Altman plot. Each '
         f'grid cell is a point: the two models\' average rate across, their difference '
         f'up. Nearly every point lies inside the envelope that binomial sampling noise '
         f'alone would produce.">']
    for d in ticks:
        o.append(f'<line x1="{x0}" y1="{Y(d):.1f}" x2="{x1}" y2="{Y(d):.1f}" '
                 f'class="gl{" zero" if d==0 else ""}"/>')
        o.append(f'<text x="{x0-10}" y="{Y(d)+4:.1f}" text-anchor="end" '
                 f'class="tk">{d*100:+.0f}</text>')
    for m in (0, .25, .5, .75, 1):
        o.append(f'<text x="{X(m):.1f}" y="{y1+20:.1f}" text-anchor="middle" '
                 f'class="tk">{m*100:.0f}%</text>')
    # the sampling-noise envelope, one band per distinct n
    for n, col in bands:
        up, dn = [], []
        m = 0.0
        while m <= 1.0001:
            s = 1.96 * math.sqrt(max(2 * m * (1 - m) / n, 0))
            up.append(f"{X(m):.1f} {Y(min(s,YMAX)):.1f}")
            dn.append(f"{X(m):.1f} {Y(max(-s,-YMAX)):.1f}")
            m += 0.02
        o.append(f'<path d="M{up[0]}L{"L".join(up[1:])}" class="env n{n}" fill="none"/>')
        o.append(f'<path d="M{dn[0]}L{"L".join(dn[1:])}" class="env n{n}" fill="none"/>')
        ly = min(Y(min(1.96*math.sqrt(0.5/n), YMAX)) - 6, y1 - 4)
        o.append(f'<text x="{X(0.5):.1f}" y="{ly:.1f}" '
                 f'text-anchor="middle" class="en">n={n}</text>')
    o.append(f'<line x1="{x0}" y1="{Y(bias):.1f}" x2="{x1}" y2="{Y(bias):.1f}" '
             f'class="bias"/>')
    for (a, b), m, d, n in pts:
        r = 2.4 + 1.9 * min(1, n / 12)
        s = 1.96 * math.sqrt(max(2 * m * (1 - m) / n, 1e-9))
        cls = "pt out" if abs(d) > s else "pt"
        o.append(f'<circle cx="{X(m):.1f}" cy="{Y(d):.1f}" r="{r:.1f}" class="{cls}">'
                 f'<title>{a} x {b} &#183; mean {m*100:.0f}% &#183; Phi minus Qwen '
                 f'{d*100:+.0f} &#183; {n} problems</title></circle>')
    o.append(f'<text x="{(x0+x1)/2:.0f}" y="{y1+44:.0f}" text-anchor="middle" '
             f'class="ax">average of the two rates</text>')
    o.append(f'<text transform="translate(18,{(y0+y1)/2:.0f}) rotate(-90)" '
             f'text-anchor="middle" class="ax">Phi minus Qwen, points</text>')
    o.append(f'<text x="{x1+18}" y="{Y(bias)+4:.0f}" class="lb">mean '
             f'{bias*100:+.1f}</text>')
    o.append(f'<text x="{x1+18}" y="{T+18}" class="sub">above the line:</text>')
    o.append(f'<text x="{x1+18}" y="{T+33}" class="sub">Phi did better</text>')
    o.append(f'<text x="{x1+18}" y="{y1-30}" class="sub">dot size = how many</text>')
    o.append(f'<text x="{x1+18}" y="{y1-15}" class="sub">problems in the cell</text>')
    o.append("</svg>")
    return "\n".join(o)


EXTRA = """
.gl.zero{stroke:var(--line-2);stroke-width:1.4}
.pt{fill:var(--ink);opacity:.34;stroke:none}
.pt.out{fill:var(--lead-b);opacity:.92}
.env{stroke:var(--lead-a);stroke-dasharray:3 4;opacity:.5;stroke-width:1.2}
.env.n3{opacity:.28} .env.n6{opacity:.38}
.en{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:9px;
  fill:var(--lead-a);opacity:.7}
.bias{stroke:var(--lead-a);stroke-width:1.8;opacity:.75}
.lb{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:10.5px;
  fill:var(--lead-a)}
.sub{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:10px;
  fill:var(--faint)}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs")
    ap.add_argument("-o", "--out", default="derived/agreement.html")
    args = ap.parse_args()
    inst, gens = paired.load(args.runs)
    g = paired.cells(inst)

    pts = [(c, (q + p) / 2, p - q, n) for c, (q, p, n) in g.items()]
    ds = [d for _, _, d, _ in pts]
    bias = sum(ds) / len(ds)
    sd = (sum((d - bias) ** 2 for d in ds) / (len(ds) - 1)) ** 0.5
    loa = (bias - 1.96 * sd, bias + 1.96 * sd)
    out = [x for x in pts
           if abs(x[2]) > 1.96 * math.sqrt(max(2 * x[1] * (1 - x[1]) / x[3], 1e-9))]
    out_hi = [x for x in out if x[2] > 0]
    ns = sorted({n for _, _, _, n in pts})
    bands = [(n, None) for n in ns]
    # Scale to the data. A fixed +-55 clipped 4x10 -- a 92-point gap, the single
    # largest thing on the chart -- straight off the bottom of the frame, which
    # is the one point a reader most needs to see.
    YMAX = max(0.30, max(abs(d) for d in ds) * 1.06)
    step = 0.25 if YMAX <= 0.62 else 0.5
    ticks, t = [], -round(YMAX / step) * step
    while t <= YMAX + 1e-9:
        ticks.append(round(t, 4)); t += step
    if 0 not in ticks:
        ticks.append(0.0)

    fig = figure(pts, bands, bias, loa, YMAX, sorted(ticks))
    score = "\n".join([
        chartpage.stat(f"{bias*100:+.1f}", "MEAN DIFFERENCE, POINTS", "qc"),
        chartpage.stat(f"{len(out)}", f"CELLS OUTSIDE THE NOISE ENVELOPE"),
        chartpage.stat(f"{len(out_hi)}", "OF THOSE, IN PHI&rsquo;S FAVOUR", "pc"),
        chartpage.stat(f"{len(pts)}", "CELLS PLOTTED"),
    ])
    key = "\n".join([
        '    <span><span class="dt" style="background:var(--ink);opacity:.34"></span>'
        'a grid cell</span>',
        '    <span><span class="dt" style="background:var(--lead-b)"></span>'
        'outside the envelope</span>',
        '    <span>&#183; dashed curves = &plusmn;1.96 SD of pure sampling noise, '
        'one per n</span>',
    ])
    notes = (
        chartpage.note(
            "<strong>Almost every point sits inside the envelope.</strong> The dashed "
            "curves are how far apart two rates would drift from sampling alone, with "
            "no difference between the models at all: widest in the middle where a "
            "coin flip has the most room, pinched to nothing at both ends. "
            f"<strong>{len(out)} of {len(pts)}</strong> cells fall outside it, and "
            f"<strong>{len(out_hi)}</strong> of those are in Phi&rsquo;s favour. Not "
            "one of the 15 cells where Phi came out higher survives its own sampling "
            "floor, while ten of Qwen&rsquo;s do.") +
        chartpage.note(
            f"<strong>The mean difference is {bias*100:+.1f} points.</strong> That is "
            "the real, reproducible finding &mdash; Qwen is better overall, by a "
            "margin no amount of resampling will erase. What the envelope kills is the "
            "other reading: that individual cells are telling you where each model is "
            "strong. They are not; they are telling you about 12 problems each. The "
            "largest surviving gaps are all Qwen&rsquo;s &mdash; 4&times;10, where "
            "Qwen got all six problems and Phi got none, and 7&times;10 close behind. "
            "Those were checked against the raw records rather than believed.") +
        chartpage.note(
            "<strong>The envelope is deliberately too wide.</strong> It comes from two "
            "<em>independent</em> binomial samples, but the design is paired &mdash; "
            "both models answered the same problems, so their errors are correlated "
            "and the true spread is narrower. Being generous is the right way round: a "
            "point outside this envelope is outside under an assumption that was "
            "already helping it.") +
        chartpage.note(
            "<strong>Why this shape.</strong> Plotting difference against average, "
            "rather than one model against the other, keeps the disagreement off the "
            "diagonal where the eye cannot judge it, and puts it on an axis where zero "
            "is a line. The funnel is the point: a fixed &plusmn;10-point band would "
            "flag the middle cells as fine and the end cells as broken, which is "
            "exactly backwards.")
    )
    html = chartpage.page(
        "do the two models disagree by more than noise?",
        f"reasoning-grid &middot; {len(pts)} cells &middot; {len(inst):,} problems",
        "Is the disagreement bigger than the noise?",
        "Each cell is a point: the two models&rsquo; average rate across, how far "
        "apart they landed up. The dashed funnel is how far apart pure sampling noise "
        "would put them.",
        fig, key, notes, score, EXTRA, maxw=1020)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    open(args.out, "w").write(html)
    print(f"wrote {args.out}  ({os.path.getsize(args.out)/1024:.0f} KB)")
    print(f"  bias {bias*100:+.2f} pts, SD {sd*100:.2f}, "
          f"limits of agreement {loa[0]*100:+.0f}..{loa[1]*100:+.0f}")
    print(f"  {len(out)} of {len(pts)} outside the per-n sampling envelope "
          f"({len(out_hi)} favouring Phi)")
    for c, m, d, n in sorted(out, key=lambda x: -abs(x[2])):
        print(f"    {c[0]:>2}x{c[1]:<2} mean {m:.2f} diff {d*100:+.0f} n={n}")


if __name__ == "__main__":
    main()
