"""Every cell as a point, so the grid reads as a distribution and not a curve.

A fitted boundary is a line through a cloud, and printing only the line invites
the reader to believe the cloud is tighter than it is. This draws the cloud:
one dot per cell at its measured rate, the fitted logistic through them, and the
band a pure coin-flip model would produce at the same sample sizes.

  .venv/bin/python probe/render_distribution.py --model Qwen/Qwen3-4B

The band is the question. If the dots sat inside it at the nominal rate, the
surface would be a pure function of N = a*b: every problem of a given size
equally hard, all scatter explained by having only n trials. Dots spilling
outside mean problems at one size genuinely differ, and N is a good predictor
rather than a complete one.

Dispersion phi = Pearson chi-square over cells / degrees of freedom summarises
that in one number. phi = 1 is pure binomial; phi > 1 is extra structure the
size axis does not capture.
"""

import argparse
import glob
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reduce_grid import load, cells          # noqa: E402
from pick_partner import fit_slope           # noqa: E402

CSS = """
:root{ --paper:#f7f6f3; --ink:#1a1a1a; --muted:#767676; --line:#e4e3e0; --card:#fff;
       --dot:#1b2a5e; --curve:#c0761a; --band:#e4e7ee; }
@media (prefers-color-scheme:dark){
  :root{ --paper:#12130f; --ink:#eceae4; --muted:#8f8f88; --line:#2a2b26; --card:#191a15;
         --dot:#8fa9ee; --curve:#e0a048; --band:#1e2434; } }
:root[data-theme="dark"]{ --paper:#12130f; --ink:#eceae4; --muted:#8f8f88; --line:#2a2b26;
  --card:#191a15; --dot:#8fa9ee; --curve:#e0a048; --band:#1e2434; }
:root[data-theme="light"]{ --paper:#f7f6f3; --ink:#1a1a1a; --muted:#767676; --line:#e4e3e0;
  --card:#fff; --dot:#1b2a5e; --curve:#c0761a; --band:#e4e7ee; }
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:system-ui,-apple-system,"Segoe UI",sans-serif;font-size:15px;line-height:1.6}
.wrap{max-width:1000px;margin:0 auto;padding:52px 24px 90px;display:flex;
  flex-direction:column;gap:28px}
h1{font-family:Charter,"Bitstream Charter","Iowan Old Style",Georgia,serif;font-weight:600;
  font-size:clamp(26px,3.6vw,36px);line-height:1.15;margin:0;letter-spacing:-.015em;
  text-wrap:balance}
h2{font-family:Charter,"Bitstream Charter","Iowan Old Style",Georgia,serif;font-weight:600;
  font-size:18px;margin:0 0 4px}
.eyebrow{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:11px;letter-spacing:.13em;
  text-transform:uppercase;color:var(--muted);margin:0 0 9px}
.lede{max-width:62ch;color:var(--muted);font-size:16.5px;margin:0}
.note{max-width:66ch;color:var(--muted);font-size:13.5px;margin:0}
figure{margin:0;background:var(--card);border:1px solid var(--line);border-radius:4px;
  padding:22px 20px 12px;overflow-x:auto}
svg{display:block;width:100%;height:auto}
text{font-family:ui-monospace,"SF Mono",Menlo,monospace;fill:var(--muted)}
.ylab{font-size:12px}.tick{font-size:11px}
.grid{stroke:var(--line);stroke-width:1;stroke-dasharray:2 4}
.axis{stroke:var(--muted);stroke-width:1.2}
.curve{fill:none;stroke:var(--curve);stroke-width:2.6}
.half{stroke:var(--curve);stroke-width:1.2;stroke-dasharray:4 4;opacity:.55}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:1px;
  background:var(--line);border:1px solid var(--line);border-radius:3px;overflow:hidden}
.stat{background:var(--card);padding:15px 17px}
.stat .k{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:10.5px;
  letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.stat .v{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:23px;
  font-variant-numeric:tabular-nums;margin-top:3px}
.legend{display:flex;gap:18px;flex-wrap:wrap;font-family:ui-monospace,"SF Mono",Menlo,monospace;
  font-size:11px;color:var(--muted);align-items:center}
.sw{display:inline-block;width:11px;height:11px;vertical-align:-1px;margin-right:5px}
.hr{height:1px;background:var(--line);border:0;margin:0}
"""


def binom_interval(n, p, lo=0.025, hi=0.975):
    """Returns COUNTS, not fractions.

    Comparing a stored rate against fraction bounds looked equivalent and was
    not: `p` is rounded to four places, so a cell sitting exactly on the edge
    (k=11 of 12 against a band ending at 11) compares as 0.9167 > 0.916666 and
    reads as an outlier. That one line doubled the apparent overdispersion,
    from 6% of cells outside the band to 12%. Compare integers.
    """
    cum, l, h = 0.0, None, None
    for k in range(n + 1):
        cum += math.comb(n, k) * p ** k * (1 - p) ** (n - k)
        if l is None and cum > lo:
            l = k
        if h is None and cum > hi:
            h = k
    return (0 if l is None else l), (n if h is None else h)


def scatter(cs, A, B, W=960, H=520):
    L, R, T, Bo = 74, 26, 24, 62
    pw, ph = W - L - R, H - T - Bo
    Ns = [c["N"] for c in cs.values()]
    lo_n, hi_n = math.log(min(Ns)), math.log(max(Ns))

    def X(N):
        return L + pw * (math.log(N) - lo_n) / (hi_n - lo_n)

    def Y(v):
        return T + ph * (1 - v)

    def pred(N):
        return 1 / (1 + math.exp(-max(-30, min(30, A + B * math.log(N)))))

    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="every cell\'s measured '
         f'rate against problem size, with the fitted curve and the binomial band">']
    # binomial band at the typical live-band n
    up, dn = [], []
    steps = 160
    for i in range(steps + 1):
        N = math.exp(lo_n + (hi_n - lo_n) * i / steps)
        p = pred(N)
        l, h = binom_interval(12, p)
        up.append(f"{X(N):.1f},{Y(h/12):.1f}")
        dn.append(f"{X(N):.1f},{Y(l/12):.1f}")
    o.append(f'<polygon points="{" ".join(up + dn[::-1])}" fill="var(--band)"/>')
    for v in (0, .25, .5, .75, 1):
        o.append(f'<line class="grid" x1="{L}" y1="{Y(v):.1f}" x2="{L+pw}" y2="{Y(v):.1f}"/>')
        o.append(f'<text class="ylab" x="{L-12}" y="{Y(v)+4:.1f}" text-anchor="end">'
                 f'{v*100:.0f}%</text>')
    o.append(f'<line class="axis" x1="{L}" y1="{T}" x2="{L}" y2="{T+ph}"/>')
    o.append(f'<line class="axis" x1="{L}" y1="{T+ph}" x2="{L+pw}" y2="{T+ph}"/>')
    d = " ".join(f"{'M' if i == 0 else 'L'}{X(math.exp(lo_n+(hi_n-lo_n)*i/steps)):.1f},"
                 f"{Y(pred(math.exp(lo_n+(hi_n-lo_n)*i/steps))):.1f}"
                 for i in range(steps + 1))
    o.append(f'<path class="curve" d="{d}"/>')
    o.append(f'<line class="half" x1="{L}" y1="{Y(.5):.1f}" x2="{L+pw}" y2="{Y(.5):.1f}"/>')
    for c in sorted(cs.values(), key=lambda c: -c["n"]):
        r = 2.6 + 2.4 * math.sqrt(c["n"] / 12)
        o.append(f'<circle cx="{X(c["N"]):.1f}" cy="{Y(c["p"]):.1f}" r="{r:.1f}" '
                 f'fill="var(--dot)" opacity=".5">'
                 f'<title>{c["a"]}x{c["b"]}  N={c["N"]}  {c["k"]}/{c["n"]} = '
                 f'{c["p"]:.0%}</title></circle>')
    for N in (1, 4, 12, 30, 60, 120, 196):
        if not (min(Ns) <= N <= max(Ns)):
            continue
        o.append(f'<text class="tick" x="{X(N):.1f}" y="{T+ph+20:.1f}" '
                 f'text-anchor="middle">{N}</text>')
    o.append(f'<text class="ylab" x="{-(T+ph/2):.1f}" y="17" text-anchor="middle" '
             f'transform="rotate(-90)">share of runs exactly correct</text>')
    o.append(f'<text class="ylab" x="{L+pw/2:.1f}" y="{H-14}" text-anchor="middle">'
             f'N = digits of A &times; digits of B &nbsp;(log scale)</text>')
    o.append("</svg>")
    return "\n".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs")
    ap.add_argument("--model", default="Qwen/Qwen3-4B")
    ap.add_argument("--glob", default="10-grid12-qwen-*,11-ext14-qwen-*")
    ap.add_argument("-o", "--out", default="derived/distribution.html")
    args = ap.parse_args()
    paths = []
    for g in args.glob.split(","):
        paths += sorted(glob.glob(os.path.join(args.runs, f"{g}.jsonl")))
    cs = cells(load(paths, model=args.model, temperature=0.7))
    A, B = fit_slope(cs)

    def pred(N):
        return 1 / (1 + math.exp(-max(-30, min(30, A + B * math.log(N)))))

    chi2 = df = out = tot = 0
    for c in cs.values():
        if c["n"] < 6:
            continue
        p = pred(c["N"])
        if not (0 < p < 1):
            continue
        chi2 += (c["k"] - c["n"] * p) ** 2 / (c["n"] * p * (1 - p))
        df += 1
        l, h = binom_interval(c["n"], p)
        tot += 1
        if not (l <= c["k"] <= h):
            out += 1
    phi = chi2 / df
    dstar = math.sqrt(math.exp(-A / B))
    mname = args.model.split("/")[-1]

    html = f"""<title>reasoning-grid &mdash; the grid is a distribution, not a curve</title>
<style>{CSS}</style>
<div class="wrap">
  <header>
    <p class="eyebrow">reasoning-grid &middot; {mname} &middot; {len(cs)} cells &middot;
      {sum(c['n'] for c in cs.values()):,} runs</p>
    <h1>The grid is a distribution, not a curve</h1>
    <p class="lede">One dot per cell, at the share of its runs that returned the exactly
      correct product. The curve is the fitted boundary. The shaded band is the scatter
      you would get if every problem of a given size were equally hard and all the spread
      came from having only twelve trials.</p>
  </header>

  <div class="stats">
    <div class="stat"><div class="k">cells</div><div class="v">{len(cs)}</div></div>
    <div class="stat"><div class="k">boundary d*</div><div class="v">{dstar:.2f}</div></div>
    <div class="stat"><div class="k">dispersion &phi;</div><div class="v">{phi:.2f}</div></div>
    <div class="stat"><div class="k">outside the band</div><div class="v">{out/tot:.0%}</div></div>
  </div>

  <figure>{scatter(cs, A, B)}</figure>
  <div class="legend">
    <span><span class="sw" style="background:var(--dot);opacity:.5;border-radius:50%"></span>
      one cell &mdash; bigger dot means more runs</span>
    <span><span class="sw" style="background:var(--curve)"></span>fitted boundary</span>
    <span><span class="sw" style="background:var(--band)"></span>coin-flip band at n=12</span>
  </div>

  <hr class="hr"/>
  <section>
    <h2>What the spread means</h2>
    <p class="note">Two things could produce a cloud this wide. Either every problem of a
      given size is equally hard and the scatter is just twelve coin flips per cell, or
      problems of the same size genuinely differ and the size axis is an incomplete
      description. The band separates them: it is what the first story predicts.</p>
    <p class="note" style="margin-top:12px"><strong>&phi; = {phi:.2f}.</strong> Cells
      scatter about {(phi-1)*100:.0f}% wider than coin flipping alone would produce, so
      the second story has something in it &mdash; N = a&times;b is a good predictor of
      difficulty, not a complete one. But only {out/tot:.0%} of cells fall outside their
      95% interval against the 5% expected, so this is mild extra variance spread across
      many cells rather than a few genuinely anomalous sizes.</p>
    <p class="note" style="margin-top:12px">This is why the boundary is fitted across
      every cell at once. No single dot on this chart pins the curve, and several sit far
      from it; the estimate is trustworthy because {len(cs)} of them agree on where it
      goes, not because any one of them is precise.</p>
  </section>
</div>
"""
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    open(args.out, "w").write(html)
    print(f"wrote {args.out}")
    print(f"  {len(cs)} cells, d*={dstar:.2f}, phi={phi:.2f}, "
          f"{out}/{tot} outside the 95% binomial band ({out/tot:.0%})")


if __name__ == "__main__":
    main()
