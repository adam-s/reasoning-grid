#!/usr/bin/env python3
"""Where each model's reliability crosses 50%, as one line per model.

    python probe/render_boundary.py -o derived/boundary.html

144 cells collapse to two curves. The question this repo exists to answer --
do two models from different companies stop being reliable in the same places
or different ones -- is a question about two curves, and this is the chart that
states it in the form the question is asked.

The curves come from a logistic fit, not from marching squares over the raw
cells. A contour drawn through 12 or fewer trials per cell is a staircase of
islands, and a reader takes the staircase for structure. The raw crossings are
drawn underneath as small marks so the fit can be checked against them.

logit(p) = B0 + B1*(a+b) + B2*min(a,b)

Both terms are identifiable here: 6x6 and 11x1 share a+b=12 with chain lengths
6 and 1, so the grid varies them independently. That is checked before fitting.
A design that cannot separate two terms does not give imprecise estimates, it
gives unrecoverable ones.
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paired            # noqa: E402
import chartpage         # noqa: E402

W, HH = 940, 560
L, T, R, Bm = 62, 26, 210, 62
DIM = 12


def sx(a):
    return L + (a - 0.5) / DIM * (W - L - R)


def sy(b):
    return T + (DIM - b + 0.5) / DIM * (HH - T - Bm)


def curve(beta, level, cls, dash=""):
    lo = math.log(level / (1 - level))
    f = lambda x, y: beta[0] + beta[1] * (x + y) + beta[2] * min(x, y) - lo
    segs = paired.marching_squares(f, 1.0, float(DIM), 0.0, step=0.2)
    d = "".join(f"M{sx(p[0]):.1f} {sy(p[1]):.1f}L{sx(q[0]):.1f} {sy(q[1]):.1f}"
                for p, q in segs)
    return (f'<path d="{d}" class="{cls}" fill="none"{dash}/>' if d else "")


def figure(g, fits):
    o = [f'<svg viewBox="0 0 {W} {HH}" role="img" aria-label="Two curves on a grid '
         f'of factor digit counts, marking where each model\'s chance of an exactly '
         f'correct product falls through 50 percent. The two curves run parallel about '
         f'one digit apart, Phi inside Qwen.">']
    for i in range(1, DIM + 1):
        o.append(f'<line x1="{sx(i):.1f}" y1="{sy(0.5):.1f}" x2="{sx(i):.1f}" '
                 f'y2="{sy(DIM+0.5):.1f}" class="gl"/>')
        o.append(f'<line x1="{sx(0.5):.1f}" y1="{sy(i):.1f}" x2="{sx(DIM+0.5):.1f}" '
                 f'y2="{sy(i):.1f}" class="gl"/>')
    # every cell as a dot: filled once BOTH models are under half, so the reader
    # can see the fitted lines land where the data actually turns over
    for (a, b), (q, p, n) in sorted(g.items()):
        both_lo = q < 0.5 and p < 0.5
        both_hi = q >= 0.5 and p >= 0.5
        cls = "cd lo" if both_lo else ("cd hi" if both_hi else "cd sp")
        o.append(f'<circle cx="{sx(a):.1f}" cy="{sy(b):.1f}" r="{2.6 if both_hi else 3.4:.1f}" '
                 f'class="{cls}"><title>{a} x {b} &#183; Qwen {q*100:.0f}% &#183; '
                 f'Phi {p*100:.0f}% &#183; {n} problems</title></circle>')
    for nm, beta, cls in fits:
        o.append(curve(beta, 0.9, f"bd {cls} faint", ' stroke-dasharray="2 4"'))
        o.append(curve(beta, 0.1, f"bd {cls} faint", ' stroke-dasharray="2 4"'))
        o.append(curve(beta, 0.5, f"bd {cls}"))
    for i in range(1, DIM + 1):
        o.append(f'<text x="{sx(i):.1f}" y="{HH-Bm+20}" text-anchor="middle" '
                 f'class="tk">{i}</text>')
        o.append(f'<text x="{L-12}" y="{sy(i)+4:.1f}" text-anchor="end" class="tk">{i}</text>')
    o.append(f'<text x="{(sx(1)+sx(DIM))/2:.0f}" y="{HH-Bm+43}" text-anchor="middle" '
             f'class="ax">digits in A</text>')
    o.append(f'<text transform="translate(17,{(sy(1)+sy(DIM))/2:.0f}) rotate(-90)" '
             f'text-anchor="middle" class="ax">digits in B</text>')
    # labels in the free space to the right, on the curve's own row
    for nm, beta, cls, yy in ((fits[0][0], fits[0][1], fits[0][2], sy(10.6)),
                              (fits[1][0], fits[1][1], fits[1][2], sy(8.2))):
        o.append(f'<text x="{W-R+16}" y="{yy:.0f}" class="lb {cls}">{nm}</text>')
    o.append(f'<text x="{W-R+16}" y="{sy(10.6)+17:.0f}" class="sub">50% at '
             f'{diag(fits[0][1]):.1f} &times; {diag(fits[0][1]):.1f}</text>')
    o.append(f'<text x="{W-R+16}" y="{sy(8.2)+17:.0f}" class="sub">50% at '
             f'{diag(fits[1][1]):.1f} &times; {diag(fits[1][1]):.1f}</text>')
    o.append(f'<text x="{W-R+16}" y="{sy(4.6):.0f}" class="sub">dashed: 90% and 10%</text>')
    o.append(f'<text x="{W-R+16}" y="{sy(4.6)+17:.0f}" class="sub">dots: measured cells</text>')
    o.append("</svg>")
    return "\n".join(o)


def diag(beta):
    """The square problem size where the fit crosses 50%: solve B0+2dB1+dB2=0."""
    return -beta[0] / (2 * beta[1] + beta[2])


EXTRA = """
.cd{stroke:none}
.cd.hi{fill:var(--faint);opacity:.32}
.cd.sp{fill:var(--lead-b);opacity:.55}
.cd.lo{fill:var(--ink);opacity:.26}
.bd{stroke-width:2.4;stroke-linecap:round}
.bd.faint{stroke-width:1.3;opacity:.45}
.qa{stroke:var(--lead-a)} .pb{stroke:var(--lead-b)}
.lb{font-family:system-ui,-apple-system,sans-serif;font-size:14px;font-weight:600}
.lb.qa{fill:var(--lead-a);stroke:none} .lb.pb{fill:var(--lead-b);stroke:none}
.sub{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:10.5px;
  fill:var(--faint)}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs")
    ap.add_argument("-o", "--out", default="derived/boundary.html")
    args = ap.parse_args()
    inst, gens = paired.load(args.runs)
    g = paired.cells(inst)

    # identifiability, checked rather than assumed
    tot = {c[0] + c[1] for c in g}
    ok = any(len({min(c) for c in g if c[0] + c[1] == t}) > 1 for t in tot)
    if not ok:
        sys.exit("a+b and min(a,b) do not vary independently in this grid; "
                 "the two terms are unrecoverable, not merely imprecise")

    fits = []
    for nm, ix, cls in (("Qwen3-4B", 0, "qa"), ("Phi-4-reasoning", 1, "pb")):
        rows = [(c[0], c[1], v[ix] * v[2], v[2]) for c, v in g.items()]
        fits.append((nm, paired.logistic_fit(rows), cls))
    dq, dp = diag(fits[0][1]), diag(fits[1][1])

    fig = figure(g, fits)
    score = "\n".join([
        chartpage.stat(f"{dq:.1f}&times;{dq:.1f}", "QWEN HALF-RIGHT AT", "qc"),
        chartpage.stat(f"{dp:.1f}&times;{dp:.1f}", "PHI HALF-RIGHT AT", "pc"),
        chartpage.stat(f"{dq-dp:.1f}", "DIGITS BETWEEN THEM"),
    ])
    key = "\n".join([
        '    <span><span class="sw" style="background:var(--lead-a)"></span>Qwen</span>',
        '    <span><span class="sw" style="background:var(--lead-b)"></span>Phi</span>',
        '    <span>&#183; solid = 50%, dashed = 90% and 10%</span>',
        '    <span>&#183; orange dots are cells where the two straddle a half</span>',
    ])
    notes = (
        chartpage.note(
            "<strong>The two curves are the same shape, about a digit apart.</strong> "
            f"Qwen holds half its problems out to <strong>{dq:.1f}&times;{dq:.1f}</strong> "
            f"digits and Phi to <strong>{dp:.1f}&times;{dp:.1f}</strong>. Neither curve "
            "cuts across the other, and neither has a kink the other lacks &mdash; so "
            "on this instrument the two models do not fail in different places, they "
            "fail at different distances along the same road.") +
        chartpage.note(
            "<strong>That is the negative result this repo was built to be able to "
            "get.</strong> If the curves had crossed, running two models from different "
            "vendors would buy coverage a single better model could not. They do not "
            "cross, so on long multiplication the honest recommendation is one model, "
            "and the only question is which.") +
        chartpage.note(
            "<strong>Read the gap, not the lines' exact position.</strong> The curves "
            "come from a logistic fit in <code>a+b</code> and <code>min(a,b)</code>, "
            "which is a smooth summary of a noisy grid, not a measurement. Both terms "
            "are identifiable &mdash; 6&times;6 and 11&times;1 share a total of 12 with "
            "chain lengths 6 and 1 &mdash; and the script refuses to fit if that stops "
            "being true. The dots are the measured cells, drawn so the fit can be "
            "checked against them rather than believed.") +
        chartpage.note(
            "<strong>The contour is fitted, not traced.</strong> Marching squares over "
            "the raw 12&times;12 grid gives a staircase of islands at 3 to 12 problems "
            "a cell, and a reader takes the staircase for structure. The lattice under "
            "the fit is sampled at a fifth of a digit, so the curve is the model's, and "
            "the model's assumptions are stated above rather than hidden in a smoother.")
    )
    html = chartpage.page(
        "where each model crosses 50%",
        f"reasoning-grid &middot; {len(inst):,} problems &middot; both models, same questions",
        "Where each model stops being right half the time",
        "One line per model: the problem sizes where its chance of an exactly correct "
        "product falls through a half. The question is whether the two lines cross.",
        fig, key, notes, score, EXTRA, maxw=1020)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    open(args.out, "w").write(html)
    print(f"wrote {args.out}  ({os.path.getsize(args.out)/1024:.0f} KB)")
    for nm, beta, _ in fits:
        print(f"  {nm:18s} B0={beta[0]:+.3f} B1(a+b)={beta[1]:+.4f} "
              f"B2(min)={beta[2]:+.4f}   50% at {diag(beta):.2f}^2")
    print(f"  gap {dq-dp:.2f} digits on the diagonal")


if __name__ == "__main__":
    main()
