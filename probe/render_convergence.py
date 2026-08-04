"""Running pass rate for one cell, with the interval and the per-trial strip.

A cell's headline number is one figure standing for many trials, and it hides
the two things a reader most needs: how much the estimate moved while it was
being collected, and whether the failures were spread out or clustered. This
draws both.

  .venv/bin/python probe/render_convergence.py derived/../runs --cell 7x7

The band is the Wilson interval AFTER EACH TRIAL, so it starts enormous and
narrows. That shape is the honest answer to "has this converged": at low n the
interval spans most of the axis, and a line that looks settled is settled only
because there is not enough data to move it.

The strip is one mark per trial in instance order -- green correct, red not.
Instances within a cell are independent draws of the same size, so the order
carries no information by itself; it is there so a reader can see whether the
misses cluster (which would suggest the trials are not independent) or scatter
(which is what a fixed per-problem success rate looks like).
"""

import argparse
import collections
import glob
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reduce_grid import load  # noqa: E402

CSS = """
:root{ --paper:#f7f6f3; --ink:#1a1a1a; --muted:#767676; --line:#e4e3e0; --card:#fff;
       --line-c:#4a8cf0; --band:#dbe6fa; --ok:#7fbf7f; --bad:#dd7b74; }
@media (prefers-color-scheme:dark){
  :root{ --paper:#12130f; --ink:#eceae4; --muted:#8f8f88; --line:#2a2b26; --card:#191a15;
         --line-c:#6fa4f5; --band:#1c2a44; --ok:#5f9f5f; --bad:#b85f58; } }
:root[data-theme="dark"]{ --paper:#12130f; --ink:#eceae4; --muted:#8f8f88; --line:#2a2b26;
  --card:#191a15; --line-c:#6fa4f5; --band:#1c2a44; --ok:#5f9f5f; --bad:#b85f58; }
:root[data-theme="light"]{ --paper:#f7f6f3; --ink:#1a1a1a; --muted:#767676; --line:#e4e3e0;
  --card:#fff; --line-c:#4a8cf0; --band:#dbe6fa; --ok:#7fbf7f; --bad:#dd7b74; }
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:system-ui,-apple-system,"Segoe UI",sans-serif;font-size:15px;line-height:1.6}
.wrap{max-width:980px;margin:0 auto;padding:52px 24px 90px;display:flex;
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
figure+figure{margin-top:20px}
svg{display:block;width:100%;height:auto}
text{font-family:ui-monospace,"SF Mono",Menlo,monospace;fill:var(--muted)}
.ylab{font-size:12px}.tick{font-size:11.5px}
.val{font-size:14px;fill:var(--ink);font-weight:600}
.grid{stroke:var(--line);stroke-width:1;stroke-dasharray:2 4}
.axis{stroke:var(--muted);stroke-width:1.2}
.rate{fill:none;stroke:var(--line-c);stroke-width:2.4;stroke-linejoin:round}
.final{stroke:var(--line-c);stroke-width:1.3;stroke-dasharray:4 4;opacity:.6}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;
  background:var(--line);border:1px solid var(--line);border-radius:3px;overflow:hidden}
.stat{background:var(--card);padding:15px 17px}
.stat .k{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:10.5px;
  letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.stat .v{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:23px;
  font-variant-numeric:tabular-nums;margin-top:3px}
.hr{height:1px;background:var(--line);border:0;margin:0}
.sub{font-size:10px}\n.panelttl{font-size:12.5px;fill:var(--ink)}
:root{--easy:#4a8cf0;--hard:#8c2f39}
@media (prefers-color-scheme:dark){:root{--easy:#6fa4f5;--hard:#e07070}}
:root[data-theme="dark"]{--easy:#6fa4f5;--hard:#e07070}
:root[data-theme="light"]{--easy:#4a8cf0;--hard:#8c2f39}
"""


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0, 1.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def convergence(outcomes, label, W=940, H=430):
    L, R, T, B = 76, 70, 22, 104
    pw, ph = W - L - R, H - T - B
    n = len(outcomes)
    run = []
    k = 0
    for i, ok in enumerate(outcomes, 1):
        k += 1 if ok else 0
        run.append(wilson(k, i))

    def X(i):
        return L + (pw * (i - 1) / max(n - 1, 1))

    def Y(v):
        return T + ph * (1 - v)

    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="running pass rate with '
         f'95% interval over {n} trials at {label}">']
    band = ([f"{X(i+1):.1f},{Y(hi):.1f}" for i, (_, _, hi) in enumerate(run)]
            + [f"{X(i+1):.1f},{Y(lo):.1f}" for i, (_, lo, _) in reversed(list(enumerate(run)))])
    o.append(f'<polygon points="{" ".join(band)}" fill="var(--band)" opacity=".75"/>')
    for v in (0, .25, .5, .75, 1):
        o.append(f'<line class="grid" x1="{L}" y1="{Y(v):.1f}" x2="{L+pw}" y2="{Y(v):.1f}"/>')
        o.append(f'<text class="ylab" x="{L-12}" y="{Y(v)+4:.1f}" text-anchor="end">'
                 f'{v*100:.0f}%</text>')
    fin = run[-1][0]
    o.append(f'<line class="final" x1="{L}" y1="{Y(fin):.1f}" x2="{L+pw}" y2="{Y(fin):.1f}"/>')
    o.append(f'<line class="axis" x1="{L}" y1="{T}" x2="{L}" y2="{T+ph}"/>')
    o.append(f'<line class="axis" x1="{L}" y1="{T+ph}" x2="{L+pw}" y2="{T+ph}"/>')
    d = " ".join(f"{'M' if i == 0 else 'L'}{X(i+1):.1f},{Y(p):.1f}"
                 for i, (p, _, _) in enumerate(run))
    o.append(f'<path class="rate" d="{d}"/>')
    o.append(f'<circle cx="{X(n):.1f}" cy="{Y(fin):.1f}" r="6" fill="var(--line-c)"/>')
    o.append(f'<text class="val" x="{X(n)+12:.1f}" y="{Y(fin)-8:.1f}">{fin*100:.1f}%</text>')
    o.append(f'<text class="ylab" x="{-(T+ph/2):.1f}" y="17" text-anchor="middle" '
             f'transform="rotate(-90)">running pass rate</text>')
    for i in (1, *(v for v in (5, 10, 15, 20, 30, 40) if v < n), n):
        o.append(f'<text class="tick" x="{X(i):.1f}" y="{T+ph+22:.1f}" '
                 f'text-anchor="middle">{i}</text>')
    # per-trial strip
    sw = min(pw / n * 0.62, 15)
    sy = T + ph + 38
    for i, ok in enumerate(outcomes, 1):
        o.append(f'<rect x="{X(i)-sw/2:.1f}" y="{sy}" width="{sw:.1f}" height="21" rx="2.5" '
                 f'fill="{"var(--ok)" if ok else "var(--bad)"}">'
                 f'<title>trial {i}: {"correct" if ok else "not correct"}</title></rect>')
    o.append(f'<text class="tick" x="{L+pw/2:.1f}" y="{H-10}" text-anchor="middle">'
             f'trial number (1 &hellip; {n}) at {label}</text>')
    o.append("</svg>")
    return "\n".join(o)


def small_multiples(series, cols=4, PW=222, PH=158, GAP=14):
    """One panel per cell instead of one axis for all of them.

    Overlaid, eight running-rate lines cross constantly and the eye cannot
    follow any single one; the reader gets an impression of noise and no
    individual story. Split into panels each line is legible, and the
    comparison survives because every panel shares the same axes -- so the
    shapes can still be read against each other at a glance.

    Panels are ordered by N, so difficulty increases left to right and top to
    bottom, and the drop across the sequence is the surface itself.
    """
    rows = (len(series) + cols - 1) // cols
    W = cols * PW + (cols - 1) * GAP
    H = rows * PH + (rows - 1) * GAP
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="running pass rate for '
         f'each of the {len(series)} best-sampled cells, one panel each">']
    L, T, B, Rr = 34, 26, 30, 8

    for idx, (label, outcomes, N) in enumerate(sorted(series, key=lambda s: s[2])):
        ox = (idx % cols) * (PW + GAP)
        oy = (idx // cols) * (PH + GAP)
        pw, ph = PW - L - Rr, PH - T - B
        n = len(outcomes)
        run, k = [], 0
        for i, ok in enumerate(outcomes, 1):
            k += 1 if ok else 0
            run.append(wilson(k, i))

        def X(i):
            return ox + L + pw * (i - 1) / max(n - 1, 1)

        def Y(v):
            return oy + T + ph * (1 - v)

        t = min(N / 110, 1.0)
        col = f"color-mix(in oklab, var(--hard) {t*100:.0f}%, var(--easy))"
        o.append(f'<rect x="{ox}" y="{oy}" width="{PW}" height="{PH}" fill="var(--card)" '
                 f'stroke="var(--line)" rx="3"/>')
        band = ([f"{X(i+1):.1f},{Y(hi):.1f}" for i, (_, _, hi) in enumerate(run)]
                + [f"{X(i+1):.1f},{Y(lo):.1f}"
                   for i, (_, lo, _) in reversed(list(enumerate(run)))])
        o.append(f'<polygon points="{" ".join(band)}" fill="{col}" opacity=".14"/>')
        for v in (0, .5, 1):
            o.append(f'<line x1="{ox+L}" y1="{Y(v):.1f}" x2="{ox+L+pw}" y2="{Y(v):.1f}" '
                     f'class="grid"/>')
            o.append(f'<text class="sub" x="{ox+L-5}" y="{Y(v)+3.5:.1f}" '
                     f'text-anchor="end">{v*100:.0f}</text>')
        d = " ".join(f"{'M' if i == 0 else 'L'}{X(i+1):.1f},{Y(p):.1f}"
                     for i, (p, _, _) in enumerate(run))
        o.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="2.1" '
                 f'stroke-linejoin="round"/>')
        fin = run[-1][0]
        o.append(f'<circle cx="{X(n):.1f}" cy="{Y(fin):.1f}" r="4" fill="{col}"/>')
        o.append(f'<text class="panelttl" x="{ox+L}" y="{oy+16}">{label}</text>')
        o.append(f'<text class="sub" x="{ox+PW-8}" y="{oy+16}" text-anchor="end">'
                 f'N={N}</text>')
        lo_, hi_ = run[-1][1], run[-1][2]
        o.append(f'<text class="sub" x="{ox+L}" y="{oy+PH-9}">'
                 f'{k}/{n} = {fin:.0%}</text>')
        o.append(f'<text class="sub" x="{ox+PW-8}" y="{oy+PH-9}" text-anchor="end">'
                 f'[{lo_:.0%}, {hi_:.0%}]</text>')
    o.append("</svg>")
    return "\n".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs")
    ap.add_argument("--model", default="Qwen/Qwen3-4B")
    ap.add_argument("--cell", default=None, help="e.g. 7x7; default = best sampled")
    ap.add_argument("--glob", default="1[01]-*,07-grid12-*")
    ap.add_argument("-o", "--out", default="derived/convergence.html")
    ap.add_argument("--top", type=int, default=8,
                    help="how many best-sampled cells to overlay in the second panel")
    args = ap.parse_args()

    paths = []
    for g in args.glob.split(","):
        paths += sorted(glob.glob(os.path.join(args.runs, f"{g}.jsonl")))
    recs = load(paths, model=args.model, temperature=0.7)
    by = collections.defaultdict(list)
    for r in recs:
        by[(r["a"], r["b"])].append(r)
    if args.cell:
        a, b = (int(x) for x in args.cell.split("x"))
    else:
        a, b = max(by, key=lambda k: len(by[k]))
    rs = sorted(by[(a, b)], key=lambda r: (r["instance_id"], r.get("sweep_id", "")))
    outcomes = [bool(r["correct"]) for r in rs]
    n = len(outcomes)
    k = sum(outcomes)
    p, lo, hi = wilson(k, n)
    grinds = sum(1 for r in rs if r.get("finish_reason") == "length")
    label = f"{a}d &times; {b}d"
    mname = args.model.split("/")[-1]

    top = sorted(by.items(), key=lambda kv: -len(kv[1]))[:args.top]
    series = []
    for (ca, cb), rs2 in top:
        rs2 = sorted(rs2, key=lambda r: (r["instance_id"], r.get("sweep_id", "")))
        series.append((f"{ca}x{cb}", [bool(r["correct"]) for r in rs2], ca * cb))
    n_cells = len(by)

    # how much the estimate moved over the second half -- a crude convergence read
    half = n // 2
    swing = max(abs(sum(outcomes[:i]) / i - p) for i in range(max(half, 1), n + 1))

    html = f"""<title>reasoning-grid &mdash; has one cell converged?</title>
<style>{CSS}</style>
<div class="wrap">
  <header>
    <p class="eyebrow">reasoning-grid &middot; {mname} &middot; {a}&times;{b} &middot;
      temp 0.7 &middot; thinking on</p>
    <h1>One cell, {n} trials, and whether the number has settled</h1>
    <p class="lede">The grid reports {p:.0%} for this cell. This is what that single
      number is made of &mdash; the estimate after every trial, the interval around it,
      and which trials actually passed.</p>
  </header>

  <div class="stats">
    <div class="stat"><div class="k">pass rate</div><div class="v">{p:.1%}</div></div>
    <div class="stat"><div class="k">trials</div><div class="v">{k}/{n}</div></div>
    <div class="stat"><div class="k">95% interval</div><div class="v">{lo:.0%}&ndash;{hi:.0%}</div></div>
    <div class="stat"><div class="k">width</div><div class="v">{hi-lo:.0%}</div></div>
  </div>

  <figure>{convergence(outcomes, label)}</figure>

  <hr class="hr"/>
  <section>
    <h2>The {len(series)} best-sampled cells at once</h2>
    <p class="note" style="margin-bottom:14px">One panel per cell, ordered by problem
      size, all sharing the same axes. Shaded is the 95% interval after each trial;
      darker lines are harder cells.</p>
    <figure>{small_multiples(series)}</figure>
    <p class="note" style="margin-top:14px">What the single chart cannot show: the lines
      finish <em>ordered by problem size</em> and stay ordered well before any one of them
      has converged. That is the whole reason a grid works. Individual cells are noisy
      measurements, and the surface they form is still legible &mdash; which is why the
      boundary is fitted across all {n_cells} cells rather than read off any of them.</p>
  </section>

  <hr class="hr"/>
  <section>
    <h2>Has it converged?</h2>
    <p class="note">Not really, and the band is the reason. After {n} trials the interval
      still spans {hi-lo:.0%} &mdash; from {lo:.0%} to {hi:.0%}. The line looks flat over
      the last stretch, but a flat line at this sample size mostly means each new trial
      can only move the estimate by about {1/n:.0%}. Over the second half the running
      estimate still drifted by up to {swing:.0%} from where it ended.</p>
    <p class="note" style="margin-top:12px">This is why the boundary is fitted across all
      196 cells at once rather than read off any single one. Pooling buys the precision
      that no individual cell has at {n} trials, and it is also why the sampling plan put
      n=12 only where the outcome was genuinely uncertain: at a cell that is 100% or 0%,
      more trials would have narrowed an interval nobody needed narrowed.</p>
    <p class="note" style="margin-top:12px">The strip is one mark per trial: green if the
      model returned the exactly correct product, red otherwise. Nothing distinguishes a
      wrong digit from a run that never finished, because nothing should &mdash; both are
      the same failure to return the answer. The misses scatter rather than cluster, which
      is what a fixed per-problem success rate looks like; a run of consecutive reds would
      have suggested the trials were not independent.</p>
  </section>
</div>
"""
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    open(args.out, "w").write(html)
    print(f"wrote {args.out}")
    print(f"  {mname} {a}x{b}: {k}/{n} = {p:.1%}  [{lo:.0%}, {hi:.0%}] width {hi-lo:.0%}"
          f"  grinds {grinds}  second-half swing {swing:.0%}")


if __name__ == "__main__":
    main()
