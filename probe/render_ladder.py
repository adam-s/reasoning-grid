"""Pass rate with intervals along a difficulty ladder, in the essay's format.

The heatmap shows the whole surface but hides precision: every tile looks
equally certain. This is the other half -- one axis of increasing difficulty,
every point carrying its Wilson interval and its trial count, so a reader can
see where the measurement is converged and where it is still noise.

  .venv/bin/python probe/render_ladder.py derived/10-grid12.json -o derived/ladder.html

The shaded band is where a cell is worth sampling at all. Above it a cell is
saturated and below it dead: in both cases the outcome was known in advance and
the trials bought nothing. Spending belongs in the band, which is also where the
intervals need to be tightest -- so the band doubles as a budget map.

Filled points are cells sampled at the full live-band n. Hollow points are the
thin ones, whose intervals are wide by construction rather than by disagreement.
"""

import argparse
import json
import math
import os

CSS = """
:root{ --paper:#f7f6f3; --ink:#1a1a1a; --muted:#767676; --line:#e2e2e0;
       --a:#4a8cf0; --b:#eb6834; --band:#ececea; --card:#fff; }
@media (prefers-color-scheme:dark){
  :root{ --paper:#12130f; --ink:#eceae4; --muted:#8f8f88; --line:#2a2b26;
         --a:#4a8cf0; --b:#e07a4a; --band:#1e1f1a; --card:#191a15; } }
:root[data-theme="dark"]{ --paper:#12130f; --ink:#eceae4; --muted:#8f8f88;
  --line:#2a2b26; --a:#4a8cf0; --b:#e07a4a; --band:#1e1f1a; --card:#191a15; }
:root[data-theme="light"]{ --paper:#f7f6f3; --ink:#1a1a1a; --muted:#767676;
  --line:#e2e2e0; --a:#4a8cf0; --b:#eb6834; --band:#ececea; --card:#fff; }
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:system-ui,-apple-system,"Segoe UI",sans-serif;font-size:15px;line-height:1.6}
.wrap{max-width:1000px;margin:0 auto;padding:52px 24px 90px;display:flex;
  flex-direction:column;gap:30px}
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
  padding:20px 18px 10px;overflow-x:auto}
svg{display:block;width:100%;height:auto}
text{font-family:ui-monospace,"SF Mono",Menlo,monospace;fill:var(--muted)}
.ylab{font-size:12px}.xlab{font-size:12.5px;fill:var(--ink)}
.sub{font-size:11px}.val{font-size:12.5px;fill:var(--ink)}
.grid{stroke:var(--line);stroke-width:1;stroke-dasharray:2 4}
.axis{stroke:var(--muted);stroke-width:1.2}
.bar{stroke:var(--muted);stroke-width:1.6;stroke-linecap:round}
.conn{fill:none;stroke-width:1.6;stroke-dasharray:5 4;opacity:.6}
.bandlab{font-size:12px}
.legend{display:flex;gap:18px;flex-wrap:wrap;font-family:ui-monospace,"SF Mono",Menlo,monospace;
  font-size:11px;color:var(--muted);align-items:center}
.sw{display:inline-block;width:10px;height:10px;border-radius:50%;vertical-align:-1px;
  margin-right:5px}
.hr{height:1px;background:var(--line);border:0;margin:0}
"""

# The band the SAMPLING PLAN used: a cell between these got n=12, outside got
# 6 or 3. It must match the allocation or the chart labels cells "useful" that
# the run never treated as such. (The essay's own charts use 60-90%, a stricter
# band suited to a different question.)
LO, HI = 0.20, 0.80


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0, 1.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def ladder(series, labels, subs, W=980, H=520):
    L, R, T, B = 74, 26, 26, 92
    pw, ph = W - L - R, H - T - B
    n = len(labels)
    step = pw / n

    def X(i):
        return L + step * (i + 0.5)

    def Y(v):
        return T + ph * (1 - v)

    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="pass rate with 95% '
         f'intervals along a difficulty ladder">']
    # the band first, so everything else sits on top of it
    o.append(f'<rect x="{L}" y="{Y(HI):.1f}" width="{pw}" height="{Y(LO)-Y(HI):.1f}" '
             f'fill="var(--band)"/>')
    o.append(f'<text class="bandlab" x="{L+pw-6}" y="{Y(HI)+16:.1f}" text-anchor="end" '
             f'fill="var(--a)">live band {LO*100:.0f}&ndash;{HI*100:.0f}% &mdash; where n=12 was spent</text>')
    for v in (0, .25, .5, .75, 1):
        o.append(f'<line class="grid" x1="{L}" y1="{Y(v):.1f}" x2="{L+pw}" y2="{Y(v):.1f}"/>')
        o.append(f'<text class="ylab" x="{L-12}" y="{Y(v)+4:.1f}" text-anchor="end">'
                 f'{v*100:.0f}%</text>')
    o.append(f'<line class="axis" x1="{L}" y1="{T}" x2="{L}" y2="{T+ph}"/>')
    o.append(f'<line class="axis" x1="{L}" y1="{T+ph}" x2="{L+pw}" y2="{T+ph}"/>')
    o.append(f'<text class="ylab" x="{-(T+ph/2):.1f}" y="18" text-anchor="middle" '
             f'transform="rotate(-90)">pass rate</text>')

    for si, (name, colour, pts) in enumerate(series):
        d = " ".join(f"{'M' if i == 0 else 'L'}{X(i):.1f},{Y(p):.1f}"
                     for i, (p, _, _, _) in enumerate(pts))
        o.append(f'<path class="conn" d="{d}" stroke="{colour}"/>')
        for i, (p, lo, hi, k) in enumerate(pts):
            x = X(i) + (si - (len(series) - 1) / 2) * 9
            o.append(f'<line class="bar" x1="{x:.1f}" y1="{Y(lo):.1f}" x2="{x:.1f}" '
                     f'y2="{Y(hi):.1f}"/>')
            for e in (lo, hi):
                o.append(f'<line class="bar" x1="{x-4.5:.1f}" y1="{Y(e):.1f}" '
                         f'x2="{x+4.5:.1f}" y2="{Y(e):.1f}"/>')
            full = k >= 12
            o.append(f'<circle cx="{x:.1f}" cy="{Y(p):.1f}" r="6.5" fill="'
                     + (colour if full else "var(--card)")
                     + f'" stroke="{colour}" stroke-width="2.4">'
                     f'<title>{name} {labels[i]}: {p:.1%} [{lo:.0%}, {hi:.0%}], n={k}</title>'
                     f'</circle>')
    for i, lab in enumerate(labels):
        o.append(f'<text class="xlab" x="{X(i):.1f}" y="{T+ph+26:.1f}" '
                 f'text-anchor="middle">{lab}</text>')
        o.append(f'<text class="sub" x="{X(i):.1f}" y="{T+ph+44:.1f}" '
                 f'text-anchor="middle">{subs[i]}</text>')
    o.append(f'<text class="ylab" x="{L+pw/2:.1f}" y="{H-8}" text-anchor="middle">'
             f'operand sizes (A digits &times; B digits) &mdash; harder &rarr;</text>')
    o.append("</svg>")
    return "\n".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("-o", "--out", default="derived/ladder.html")
    ap.add_argument("--max-dim", type=int, default=14)
    args = ap.parse_args()
    doc = json.load(open(args.src))

    models = list(doc["models"])
    colours = {0: "var(--a)", 1: "var(--b)"}
    # the diagonal is the natural difficulty ladder: N grows as d^2
    dims = [d for d in range(2, args.max_dim + 1)]
    series, labels, subs = [], [f"{d}d &times; {d}d" for d in dims], None
    for mi, m in enumerate(models):
        cs = doc["models"][m]["cells"]
        pts = []
        for d in dims:
            c = cs.get(f"{d}x{d}")
            if not c:
                pts.append((0, 0, 1, 0)); continue
            p, lo, hi = wilson(c["k"], c["n"])
            pts.append((p, lo, hi, c["n"]))
        series.append((m.split("/")[-1], colours.get(mi, "var(--a)"), pts))
    ref = doc["models"][models[0]]["cells"]
    subs = [f"{ref.get(f'{d}x{d}',{}).get('n',0)} trials" for d in dims]

    inband = sum(1 for _, _, pts in series for p, _, _, _ in pts if LO <= p <= HI)
    total = sum(len(pts) for _, _, pts in series)
    widest = max((hi - lo, nm, dims[i])
                 for nm, _, pts in series for i, (p, lo, hi, k) in enumerate(pts))

    html = f"""<title>reasoning-grid &mdash; where the measurement converges</title>
<style>{CSS}</style>
<div class="wrap">
  <header>
    <p class="eyebrow">reasoning-grid &middot; diagonal ladder &middot; temp 0.7 &middot; thinking on</p>
    <h1>Where the measurement converges, and where it is still noise</h1>
    <p class="lede">Each point is one cell of the grid with its 95% Wilson interval and
      its trial count. The heatmap shows the whole surface but makes every tile look
      equally certain; this shows what each number is actually worth.</p>
  </header>
  <figure>{ladder(series, labels, subs)}</figure>
  <div class="legend">
    {''.join(f'<span><span class="sw" style="background:{c}"></span>{n}</span>'
             for n, c, _ in series)}
    <span>&#9679; filled = full sample (n&ge;12)</span>
    <span>&#9675; hollow = thin sample, wide by construction</span>
  </div>
  <hr class="hr"/>
  <section>
    <h2>Reading it</h2>
    <p class="note">The shaded band is where a trial was worth its GPU time, and it is
      the same band the sampling plan used: cells inside it got n=12, cells outside got
      6 or 3. Above it a cell is saturated, below it dead &mdash; in both cases the answer
      was known before the run and more samples would have bought nothing.</p>
    <p class="note" style="margin-top:12px">Only {inband} of {total} points on this
      diagonal land inside the band, and that is the shape of the result rather than a
      flaw in the plan: <strong>the transition is steep.</strong> Qwen goes from 100% at
      6d&times;6d to 50% at 9d&times;9d to 0% at 13d&times;13d. Along the diagonal N grows
      as d&sup2;, so three steps cross the entire useful range. Most of the genuinely
      uncertain cells are off-diagonal, at lopsided sizes like 7&times;12, which is where
      the n=12 budget actually went.</p>
    <p class="note" style="margin-top:12px">Intervals widen toward the middle of the
      curve and at the thin points, and that is the honest picture &mdash; the widest here
      spans {widest[0]:.0%} ({widest[1]} at {widest[2]}d&times;{widest[2]}d). No single
      cell settles a claim at this sample size. The boundary estimate is fitted across all
      196 cells jointly, which is why it carries a tighter interval than any point on this
      chart.</p>
  </section>
</div>
"""
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    open(args.out, "w").write(html)
    print(f"wrote {args.out}")
    for nm, _, pts in series:
        band = sum(1 for p, _, _, _ in pts if LO <= p <= HI)
        print(f"  {nm:<20} {band}/{len(pts)} diagonal cells inside the {LO:.0%}-{HI:.0%} band")


if __name__ == "__main__":
    main()
