#!/usr/bin/env python3
"""Six views of one paired comparison: Qwen against Phi, and what a second model
actually buys.

    python probe/render_pair_six.py -o derived/pair-six.html

Sibling to render_blindspots.py, which makes the single summary chart. This one
takes the same comparison apart six ways, because the summary number hides a
band structure that changes what you would do with it.

Every problem is paired on instance_uid under one condition, so both models
answered the same questions. A problem counts as solved if the model got it
right at least once.

The organising fact, which none of the six charts is allowed to soften: Qwen
beats Phi at every chain length, 75.9% against 59.5%. This is not two peers
covering each other's gaps. It is a clearly weaker second model that still
recovers about eight points overall, and fifteen in the band where it matters.

That band is the finding. Below chain length five both models solve nearly
everything, so a second buys nothing. Above ten neither solves anything, so a
second buys nothing. Between, the pair is worth ~15 points over the better model
alone. `min(a,b)` is the chain length -- the number of partial products long
multiplication has to generate and add.
"""
import argparse
import collections
import glob
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reduce_grid import _parser  # noqa: E402

A, B = "Qwen3-4B", "Phi-4-reasoning"
STATES = [("both", "both solved"), ("onlyA", "only Qwen"),
          ("onlyB", "only Phi"), ("neither", "neither")]
LABEL = dict(STATES)


def collect(runs="runs"):
    pa = _parser()
    by, cell = collections.defaultdict(dict), {}
    for f in sorted(glob.glob(os.path.join(runs, "*.jsonl"))):
        for line in open(f):
            if not line.strip():
                continue
            j = json.loads(line)
            if (j.get("temperature") != 0.7 or j.get("top_p") != 1.0
                    or j.get("thinking_observed") is not True):
                continue
            u = j.get("instance_uid")
            if not u:
                continue
            m = (j.get("model") or "").split("/")[-1]
            ans, _ = pa(j.get("raw_text") or "")
            cell[u] = (j["a"], j["b"])
            by[u].setdefault(m, []).append(
                ans is not None and str(ans) == str(j["truth"]))

    grid = collections.defaultdict(lambda: [0, 0, 0, 0])
    chain = collections.defaultdict(lambda: [0, 0, 0, 0])
    for u, d in by.items():
        if A not in d or B not in d:
            continue
        a, b = any(d[A]), any(d[B])
        idx = 0 if (a and b) else 1 if a else 2 if b else 3
        grid[cell[u]][idx] += 1
        chain[min(cell[u])][idx] += 1
    return dict(grid), dict(chain)


def bands(chain, floor=25):
    return [k for k in sorted(chain) if sum(chain[k]) >= floor]


# ------------------------------------------------------------------ 2 · mosaic
def mosaic(chain, W=880, H=340):
    """Column width = problems in that band; height = the four outcomes.

    A plain stacked bar normalises away how much evidence each band carries, so
    a tall only-Phi slice sitting on nine problems looks like the tall slice
    sitting on a hundred. Width proportional to n puts that back.
    """
    ks = bands(chain)
    tot = sum(sum(chain[k]) for k in ks)
    L, R, T, Bm = 46, 16, 14, 48
    pw, ph = W - L - R, H - T - Bm
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Outcome mix by chain length; '
         f'column width is proportional to the number of problems in that band.">']
    for t in (0, .25, .5, .75, 1):
        y = T + t * ph
        o.append(f'<text x="{L-8}" y="{y+4:.1f}" text-anchor="end" class="tk">'
                 f'{int((1-t)*100)}%</text>')
    x = L
    for k in ks:
        n = sum(chain[k])
        w = pw * n / tot
        y = T
        for (key, _), v in zip(STATES, chain[k]):
            h = ph * v / n
            o.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(0,w-1.2):.1f}" '
                     f'height="{h:.1f}" fill="var(--{key})">'
                     f'<title>chain {k} · {LABEL[key]}: {v} of {n}</title></rect>')
            y += h
        o.append(f'<text x="{x+w/2:.1f}" y="{H-28}" text-anchor="middle" class="tk">{k}</text>')
        o.append(f'<text x="{x+w/2:.1f}" y="{H-16}" text-anchor="middle" class="tk" '
                 f'opacity=".6">{n}</text>')
        x += w
    o.append(f'<text x="{L+pw/2:.0f}" y="{H-2}" text-anchor="middle" class="tk">'
             f'chain length &#183; column width = problems in that band</text>')
    o.append("</svg>")
    return "\n".join(o)


# ---------------------------------------------------------------- 6 · squares
def squares(chain, per=98, gap=14):
    """One area-proportional contingency square per band. Rows split on whether
    Qwen solved it, columns on whether Phi did."""
    ks = bands(chain)
    W = len(ks) * per + (len(ks) - 1) * gap
    H = per + 42
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="One contingency square per '
         f'chain length; quadrant area is the share of problems in that outcome.">']
    for i, k in enumerate(ks):
        b_, q, p, n = chain[k]
        N = b_ + q + p + n
        x0 = i * (per + gap)
        top = (b_ + q) / N
        lw = b_ / (b_ + q) if (b_ + q) else 0
        bw = p / (p + n) if (p + n) else 0
        for cx, cy, cw, ch, key in [
                (x0, 0, per * lw, per * top, "both"),
                (x0 + per * lw, 0, per * (1 - lw), per * top, "onlyA"),
                (x0, per * top, per * bw, per * (1 - top), "onlyB"),
                (x0 + per * bw, per * top, per * (1 - bw), per * (1 - top), "neither")]:
            if cw > .5 and ch > .5:
                o.append(f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{cw:.1f}" '
                         f'height="{ch:.1f}" fill="var(--{key})"/>')
        o.append(f'<rect x="{x0}" y="0" width="{per}" height="{per}" fill="none" '
                 f'stroke="var(--line-2)"/>')
        o.append(f'<text x="{x0+per/2:.0f}" y="{per+15}" text-anchor="middle" class="tk">'
                 f'chain {k}</text>')
        o.append(f'<text x="{x0+per/2:.0f}" y="{per+29}" text-anchor="middle" class="tk" '
                 f'opacity=".6">{p} only Phi</text>')
    o.append("</svg>")
    return "\n".join(o)


# --------------------------------------------------------------- 3 · alluvial
def alluvial(chain, W=880, H=330):
    """Problems flow from what Qwen did to what Phi did. Four ribbons.

    The band crossing upward -- Qwen failed, Phi solved -- is the blind spot as
    an object. The band crossing down is the same size argument in reverse and
    is three times bigger, which the figure has to show at the same weight.
    """
    b_ = sum(chain[k][0] for k in chain); q = sum(chain[k][1] for k in chain)
    p = sum(chain[k][2] for k in chain); n = sum(chain[k][3] for k in chain)
    N = b_ + q + p + n
    L, R, T, Bm = 162, 162, 22, 26   # wide enough for the end labels
    ph = H - T - Bm
    xl, xr = L, W - R
    h = lambda v: ph * v / N

    qs, qf = b_ + q, p + n          # left: Qwen solved / failed
    ps, pf = b_ + p, q + n          # right: Phi solved / failed
    GAP = 26
    ly0, ly1 = T, T + h(qs) + GAP
    ry0, ry1 = T, T + h(ps) + GAP

    def ribbon(y0, y1, v, key):
        t = h(v)
        c = (xl + xr) / 2
        d = (f"M{xl},{y0:.1f} C{c},{y0:.1f} {c},{y1:.1f} {xr},{y1:.1f} "
             f"L{xr},{y1+t:.1f} C{c},{y1+t:.1f} {c},{y0+t:.1f} {xl},{y0+t:.1f} Z")
        return (f'<path d="{d}" fill="var(--{key})" opacity=".85">'
                f'<title>{LABEL[key]}: {v}</title></path>')

    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Flow of {N} problems from '
         f'Qwen solved or failed into Phi solved or failed.">']
    # order within each column so ribbons do not cross unnecessarily
    o.append(ribbon(ly0, ry0, b_, "both"))
    o.append(ribbon(ly0 + h(b_), ry1 + h(p), q, "onlyA"))
    o.append(ribbon(ly1, ry0 + h(b_), p, "onlyB"))
    o.append(ribbon(ly1 + h(p), ry1, n, "neither"))
    for x, y, v, lab, anc in [
            (xl, ly0, qs, f"Qwen solved &#183; {qs}", "end"),
            (xl, ly1, qf, f"Qwen failed &#183; {qf}", "end"),
            (xr, ry0, ps, f"Phi solved &#183; {ps}", "start"),
            (xr, ry1, pf, f"Phi failed &#183; {pf}", "start")]:
        o.append(f'<rect x="{x-4 if anc=="end" else x}" y="{y:.1f}" width="4" '
                 f'height="{h(v):.1f}" fill="var(--ink)" opacity=".5"/>')
        o.append(f'<text x="{x-12 if anc=="end" else x+12}" y="{y+h(v)/2+4:.1f}" '
                 f'text-anchor="{anc}" class="tk" fill="var(--ink)">{lab}</text>')
    o.append(f'<text x="{(xl+xr)/2:.0f}" y="{H-6}" text-anchor="middle" class="tk">'
             f'{p} problems cross up &#183; {q} cross down</text>')
    o.append("</svg>")
    return "\n".join(o)


# ------------------------------------------------------- 4 · boundaries/wedge
def boundaries(grid, W=880, H=430):
    """Each model's 50% contour on the (a,b) plane, and the wedge between them.

    Extracted per row: walk b upward at fixed a and linearly interpolate where
    the solve rate crosses 0.5. Marching squares would be smoother, but a
    per-row crossing is exactly what the reader is asked to compare, and it
    cannot invent a contour where a row has no crossing.

    The question this settles is not who is better -- Qwen is, everywhere. It is
    whether the two contours differ in SHAPE. Two curves of the same shape at
    different offsets means one model is a scaled copy of the other; different
    shapes mean the blind spots are structural.
    """
    dim = max(max(c) for c in grid)
    L, R, T, Bm = 52, 82, 16, 44     # right margin holds the curve labels
    pw, ph = W - L - R, H - T - Bm
    X = lambda a: L + (a - 1) / (dim - 1) * pw
    Y = lambda b: T + ph - (b - 1) / (dim - 1) * ph

    def rate(a, b, who):
        g = grid.get((a, b))
        if not g:
            return None
        n = sum(g)
        return (g[0] + g[1]) / n if who == "A" else (g[0] + g[2]) / n

    def contour(who):
        pts = []
        for a in range(1, dim + 1):
            prev = None
            for b in range(1, dim + 1):
                r = rate(a, b, who)
                if r is None:
                    continue
                if prev is not None and prev[1] >= .5 > r:
                    b0, r0 = prev
                    t = (r0 - .5) / (r0 - r) if r0 != r else 0
                    pts.append((a, b0 + t * (b - b0)))
                    break
                prev = (b, r)
        return pts

    ca, cb = contour("A"), contour("B")
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Each model\'s fifty percent '
         f'contour on the grid of factor digits, with the region where only one model '
         f'works shaded between them.">']
    for g in range(2, dim + 1, 2):
        o.append(f'<line x1="{X(g):.1f}" y1="{T}" x2="{X(g):.1f}" y2="{T+ph}" '
                 f'stroke="var(--line)" stroke-dasharray="2 4"/>')
        o.append(f'<line x1="{L}" y1="{Y(g):.1f}" x2="{L+pw}" y2="{Y(g):.1f}" '
                 f'stroke="var(--line)" stroke-dasharray="2 4"/>')
        o.append(f'<text x="{X(g):.1f}" y="{T+ph+16}" text-anchor="middle" class="tk">{g}</text>')
        o.append(f'<text x="{L-8}" y="{Y(g)+4:.1f}" text-anchor="end" class="tk">{g}</text>')

    if ca and cb:
        wedge = ("M" + " L".join(f"{X(a):.1f},{Y(b):.1f}" for a, b in ca) + " L"
                 + " L".join(f"{X(a):.1f},{Y(b):.1f}" for a, b in reversed(cb)) + " Z")
        o.append(f'<path d="{wedge}" fill="var(--onlyA)" opacity=".13"/>')
    for pts, key, lab in [(cb, "onlyB", "Phi 50%"), (ca, "onlyA", "Qwen 50%")]:
        if not pts:
            continue
        d = "M" + " L".join(f"{X(a):.1f},{Y(b):.1f}" for a, b in pts)
        o.append(f'<path d="{d}" fill="none" stroke="var(--{key})" stroke-width="2.6" '
                 f'stroke-linejoin="round"/>')
        a, b = pts[-1]
        o.append(f'<text x="{X(a)+8:.1f}" y="{Y(b)+4:.1f}" class="tk" '
                 f'fill="var(--{key})">{lab}</text>')
    o.append(f'<text x="{L+pw/2:.0f}" y="{H-6}" text-anchor="middle" class="tk">'
             f'digits in A &#183; vertical axis is digits in B &#183; '
             f'shaded = only one model clears 50%</text>')
    o.append("</svg>")
    return "\n".join(o)


PAGE = """<title>reasoning-grid &mdash; six views of one pair</title>
<style>
:root{ --paper:#fdfcf9; --panel:#f7f5f0; --line:#e8e4dc; --line-2:#d8d2c4;
  --ink:#1a1a1a; --dim:#5a5a5a; --faint:#9a9a9a;
  --both:#c6cdd8; --onlyA:#1f3a5f; --onlyB:#c9853a; --neither:#efece5;
  --gain-lo:#f2ede3; --gain-hi:#8a4d12; }
@media (prefers-color-scheme:dark){:root{ --paper:#14161a; --panel:#1b1e24; --line:#2b303a;
  --line-2:#3a4150; --ink:#e9e6df; --dim:#a8a49b; --faint:#77736c;
  --both:#3d4653; --onlyA:#8fb0dd; --onlyB:#e0a048; --neither:#22262e;
  --gain-lo:#1e2129; --gain-hi:#f0b45f; }}
:root[data-theme="dark"]{ --paper:#14161a; --panel:#1b1e24; --line:#2b303a; --line-2:#3a4150;
  --ink:#e9e6df; --dim:#a8a49b; --faint:#77736c; --both:#3d4653; --onlyA:#8fb0dd;
  --onlyB:#e0a048; --neither:#22262e; --gain-lo:#1e2129; --gain-hi:#f0b45f; }
:root[data-theme="light"]{ --paper:#fdfcf9; --panel:#f7f5f0; --line:#e8e4dc; --line-2:#d8d2c4;
  --ink:#1a1a1a; --dim:#5a5a5a; --faint:#9a9a9a; --both:#c6cdd8; --onlyA:#1f3a5f;
  --onlyB:#c9853a; --neither:#efece5; --gain-lo:#f2ede3; --gain-hi:#8a4d12; }
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
  font-size:17px;line-height:1.62}
.wrap{max-width:1000px;margin:0 auto;padding:52px 24px 96px}
.col{max-width:640px}
.eyebrow{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:11px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--faint);margin:0 0 10px}
h1{font-size:clamp(28px,4.2vw,42px);line-height:1.12;letter-spacing:-.015em;margin:0 0 16px;
  text-wrap:balance}
h2{font-family:system-ui,sans-serif;font-size:12.5px;font-weight:650;letter-spacing:.08em;
  text-transform:uppercase;color:var(--dim);margin:52px 0 6px;padding-bottom:7px;
  border-bottom:1px solid var(--line);max-width:920px}
h2 .n{color:var(--faint);margin-right:8px}
p{margin:0 0 16px}
.lede{font-size:19.5px;line-height:1.55;color:var(--dim)}
strong{font-weight:650;color:var(--ink)}
.mono{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-variant-numeric:tabular-nums}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:1px;
  background:var(--line);border:1px solid var(--line);border-radius:4px;overflow:hidden;
  margin:28px 0 4px;max-width:920px}
.stat{background:var(--panel);padding:14px 16px}
.stat .k{font-family:ui-monospace,monospace;font-size:10.5px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--faint)}
.stat .v{font-family:ui-monospace,monospace;font-size:23px;font-variant-numeric:tabular-nums;
  margin-top:3px}
figure{margin:20px 0 8px;max-width:920px}
figcaption{font-family:system-ui,sans-serif;font-size:13px;line-height:1.55;color:var(--faint);
  margin-top:12px}
.scroll{overflow-x:auto}
svg{display:block;width:100%;height:auto;overflow:visible}
.tk{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:10.5px;fill:var(--faint)}
.plot{position:relative;border:1px solid var(--line);border-radius:4px;background:var(--panel);
  overflow:hidden}
canvas{display:block;cursor:grab;touch-action:pan-y}
canvas:active{cursor:grabbing}
.hint{position:absolute;left:10px;bottom:7px;font-family:ui-monospace,monospace;font-size:9px;
  color:var(--faint);pointer-events:none}
.key{display:flex;gap:16px;flex-wrap:wrap;align-items:center;margin-top:12px;
  font-family:system-ui,sans-serif;font-size:12px;color:var(--dim)}
.sw{display:inline-block;width:20px;height:9px;border-radius:2px;vertical-align:-1px;
  margin-right:6px}
.foot{margin-top:60px;padding-top:18px;border-top:1px solid var(--line);
  font-family:system-ui,sans-serif;font-size:13px;line-height:1.6;color:var(--faint);
  max-width:920px}
</style>
<div class="wrap">
  <p class="eyebrow">reasoning-grid &middot; __N__ problems &middot; both models, same questions</p>
  <h1>Six views of one pair</h1>
  <p class="lede col">Qwen and Phi answered the same __N__ multiplications. Qwen is the
  better model at every difficulty. The question is not which to pick &mdash; it is
  whether the weaker one is worth running anyway, and where.</p>

  <div class="stats">
    <div class="stat"><div class="k">Qwen alone</div><div class="v">__QA__</div></div>
    <div class="stat"><div class="k">Phi alone</div><div class="v">__PA__</div></div>
    <div class="stat"><div class="k">either one</div><div class="v">__UN__</div></div>
    <div class="stat"><div class="k">only Phi solved</div><div class="v">__OB__</div></div>
  </div>

  <h2><span class="n">1</span> Where the pair pays</h2>
  <div class="col"><p>Height is what running both buys <em>over the better model alone</em>
  &mdash; not over the worse one, which nobody would choose. Axes are the shorter and
  longer factor, so lines of constant chain length run straight.</p></div>
  <figure>
    <div class="plot"><canvas id="c1"></canvas><span class="hint">drag to rotate</span></div>
    <figcaption>A hill, not a slope. It peaks at <strong>+__PEAK__ points around chain
    length __PEAKK__</strong> and falls to nothing at both ends: below, both models already
    solve everything; above, neither solves anything. Outside that band a second model is
    money for no coverage.</figcaption>
  </figure>

  <h2><span class="n">2</span> The mix, weighted by evidence</h2>
  <figure class="scroll">__MOSAIC__
    <div class="key">__KEY__</div>
    <figcaption>Column width is how many problems that band holds, so a tall slice sitting
    on few problems cannot pretend to be a tall slice sitting on many. Watch
    <span style="color:var(--onlyB)">only&nbsp;Phi</span> swell through the middle and
    vanish at both ends, while <span style="color:var(--neither)">neither</span> takes
    over the right.</figcaption>
  </figure>

  <h2><span class="n">3</span> Every problem, from Qwen to Phi</h2>
  <figure class="scroll">__ALLUVIAL__
    <figcaption>The upward ribbon is the blind spot as an object: problems Qwen failed and
    Phi solved. The downward ribbon is three times thicker, and is drawn at the same weight
    on purpose &mdash; this is a weaker model recovering some of a better one's failures,
    not two equals trading.</figcaption>
  </figure>

  <h2><span class="n">4</span> Two boundaries, and the wedge between</h2>
  <figure class="scroll">__BOUNDS__
    <figcaption>Each line is where that model drops through 50%. The shaded wedge is the
    region only one of them clears. If the two curves had the same shape at different
    offsets, Phi would be a scaled-down Qwen and the wedge would be decorative; where they
    differ in shape, the gap is structural.</figcaption>
  </figure>

  <h2><span class="n">5</span> Both surfaces, and where they cross</h2>
  <figure>
    <div class="plot"><canvas id="c5"></canvas><span class="hint">drag to rotate</span></div>
    <div class="key">
      <span><span class="sw" style="background:var(--onlyA)"></span>Qwen</span>
      <span><span class="sw" style="background:var(--onlyB);opacity:.55"></span>Phi</span>
      <span class="mono" style="color:var(--faint)">height = share of problems solved</span>
    </div>
    <figcaption>The same two models as terrain. Qwen sits above Phi everywhere, which is
    the honest shape of this comparison &mdash; there is no region where the weaker model
    leads on average. The blind spots in chart 3 live <em>inside</em> this gap, at the
    level of individual problems, not as a place where the surfaces swap.</figcaption>
  </figure>

  <h2><span class="n">6</span> The same 2&times;2, eleven times</h2>
  <figure class="scroll">__SQUARES__
    <figcaption>One contingency square per band, quadrants sized by share. Read left to
    right and the whole finding is a shape change: <span style="color:var(--both)">both</span>
    collapsing, <span style="color:var(--neither)">neither</span> swelling, and
    <span style="color:var(--onlyB)">only&nbsp;Phi</span> bulging only in between.</figcaption>
  </figure>

  <div class="foot">
    <p><strong>Method.</strong> Temperature 0.7, top_p 1.0, reasoning on, native context.
    Problems paired on <span class="mono">instance_uid</span>, so both models saw the same
    integers; a problem counts as solved if the model got it right at least once. Scoring
    is exact string match re-derived from raw text. __N__ problems, __CELLS__ cells. Bands
    with fewer than 25 problems are dropped from the by-band charts.</p>
    <p><strong>What this is not.</strong> Not a claim that the models are peers. Qwen wins
    at every chain length, __QA__ against __PA__. The case for running both rests entirely
    on the __OB__ problems in chart 3's upward ribbon, and those are concentrated in one
    band &mdash; which is what charts 1, 2 and 6 exist to show.</p>
    <p><strong>Regenerate.</strong> <span class="mono">probe/render_pair_six.py</span></p>
  </div>
</div>
<script>
const D=__DATA__;
function mk(id, cfg){
  const cv=document.getElementById(id), ctx=cv.getContext('2d');
  let yaw=-0.62, pitch=0.52, W=0, H=0, drag=false, lx=0, ly=0;
  const css=k=>getComputedStyle(document.documentElement).getPropertyValue(k).trim();
  const hex=h=>[1,3,5].map(i=>parseInt(h.slice(i,i+2),16));
  const DIM=cfg.dim;
  function P(a,b,z,cx,cy,fit){
    const cw=Math.cos(yaw),sw=Math.sin(yaw),cp=Math.cos(pitch),sp=Math.sin(pitch);
    const mid=(DIM+1)/2, x=a-mid, y=b-mid;
    const x1=x*cw-y*sw, y1=x*sw+y*cw, d=y1*cp-z*cfg.zs*sp, vy=y1*sp+z*cfg.zs*cp;
    const s=900/(900+d*26);
    return {sx:cx+x1*26*s*fit, sy:cy-vy*26*s*fit, d};
  }
  function draw(){
    const dpr=Math.min(devicePixelRatio||1,2);
    if(cv.width!==Math.round(W*dpr)){cv.width=Math.round(W*dpr);cv.height=Math.round(H*dpr);}
    ctx.setTransform(dpr,0,0,dpr,0,0); ctx.clearRect(0,0,W,H);
    let b0=1e9,b1=-1e9,c0=1e9,c1=-1e9;
    for(const a of[1,DIM])for(const b of[1,DIM])for(const z of[0,1]){
      const q=P(a,b,z,0,0,1);
      b0=Math.min(b0,q.sx);b1=Math.max(b1,q.sx);c0=Math.min(c0,q.sy);c1=Math.max(c1,q.sy);}
    const PAD=54, aw=Math.max(80,W-PAD*2), ah=Math.max(80,H-PAD*2);
    const fit=Math.min(aw/(b1-b0), ah/(c1-c0));
    const cx=PAD+aw/2-((b0+b1)/2)*fit, cy=PAD+ah/2-((c0+c1)/2)*fit;
    const Q=(a,b,z)=>P(a,b,z,cx,cy,fit);
    const n=DIM-1, ord=[];
    for(let i=0;i<n;i++)for(let j=0;j<n;j++)
      ord.push([i,j,(i+1-(DIM+1)/2)*Math.sin(yaw)+(j+1-(DIM+1)/2)*Math.cos(yaw)]);
    ord.sort((p,q)=>q[2]-p[2]);
    ctx.strokeStyle=css('--line-2'); ctx.globalAlpha=.5; ctx.lineWidth=1; ctx.beginPath();
    for(let g=1;g<=DIM;g++){const a0=Q(g,1,0),a1=Q(g,DIM,0),d0=Q(1,g,0),d1=Q(DIM,g,0);
      ctx.moveTo(a0.sx,a0.sy);ctx.lineTo(a1.sx,a1.sy);
      ctx.moveTo(d0.sx,d0.sy);ctx.lineTo(d1.sx,d1.sy);}
    ctx.stroke(); ctx.globalAlpha=1;
    cfg.paint(ctx,Q,ord,css,hex,DIM);
    // axes on the two edges nearest the camera
    const cors=[[1,1],[DIM,1],[1,DIM],[DIM,DIM]];
    let near=cors[0],nd=1e9;
    for(const c of cors){const d=Q(c[0],c[1],0).d; if(d<nd){nd=d;near=c;}}
    const ctr=Q((1+DIM)/2,(1+DIM)/2,0);
    const out=(x,y,by)=>{const dx=x-ctr.sx,dy=y-ctr.sy,m=Math.hypot(dx,dy)||1;
      return[x+dx/m*by,y+dy/m*by];};
    ctx.textBaseline='middle'; ctx.textAlign='center';
    for(const ax of[{t:cfg.ax[0],f:near[1],al:'a'},{t:cfg.ax[1],f:near[0],al:'b'}]){
      const at=v=>ax.al==='a'?Q(v,ax.f,0):Q(ax.f,v,0);
      const e0=at(1),e1=at(DIM);
      ctx.strokeStyle=css('--dim');ctx.globalAlpha=.5;ctx.lineWidth=1;
      ctx.beginPath();ctx.moveTo(e0.sx,e0.sy);ctx.lineTo(e1.sx,e1.sy);ctx.stroke();
      ctx.globalAlpha=1;ctx.fillStyle=css('--dim');ctx.font='10px ui-monospace,monospace';
      for(let g=2;g<=DIM;g+=2){const t0=at(g);
        const[tx,ty]=out(t0.sx,t0.sy,5),[lx2,ly2]=out(t0.sx,t0.sy,15);
        ctx.globalAlpha=.5;ctx.beginPath();ctx.moveTo(t0.sx,t0.sy);ctx.lineTo(tx,ty);ctx.stroke();
        ctx.globalAlpha=1;ctx.fillText(String(g),lx2,ly2);}
      const m=at((1+DIM)/2),[ttx,tty]=out(m.sx,m.sy,34);
      let an=Math.atan2(e1.sy-e0.sy,e1.sx-e0.sx);
      if(an>Math.PI/2)an-=Math.PI; if(an<-Math.PI/2)an+=Math.PI;
      ctx.save();ctx.translate(ttx,tty);ctx.rotate(an);
      ctx.font='600 11px system-ui,sans-serif';ctx.fillStyle=css('--ink');
      ctx.fillText(ax.t,0,0);ctx.restore();
    }
  }
  const ro=new ResizeObserver(e=>{const r=e[0].contentRect;
    W=Math.max(280,Math.floor(r.width));H=Math.max(320,Math.round(Math.min(500,r.width*.58)));
    cv.style.width=W+'px';cv.style.height=H+'px';draw();});
  ro.observe(cv.parentElement);
  cv.addEventListener('pointerdown',e=>{drag=true;lx=e.clientX;ly=e.clientY;
    cv.setPointerCapture(e.pointerId);});
  cv.addEventListener('pointermove',e=>{if(!drag)return;
    yaw+=(e.clientX-lx)*.008;pitch=Math.max(.08,Math.min(1.3,pitch+(e.clientY-ly)*.005));
    lx=e.clientX;ly=e.clientY;draw();});
  const up=()=>{drag=false;};
  cv.addEventListener('pointerup',up);cv.addEventListener('pointercancel',up);
  new MutationObserver(draw).observe(document.documentElement,
    {attributes:true,attributeFilter:['data-theme']});
  matchMedia('(prefers-color-scheme:dark)').addEventListener('change',draw);
}
const quad=(ctx,Q,i,j,f,fill,stroke,alpha)=>{
  const A=i+1,B=j+1, z=[f(A,B),f(A+1,B),f(A+1,B+1),f(A,B+1)];
  if(z.some(v=>v===null))return;
  const p=[Q(A,B,z[0]),Q(A+1,B,z[1]),Q(A+1,B+1,z[2]),Q(A,B+1,z[3])];
  ctx.beginPath();ctx.moveTo(p[0].sx,p[0].sy);
  for(let k=1;k<4;k++)ctx.lineTo(p[k].sx,p[k].sy);
  ctx.closePath();
  ctx.globalAlpha=alpha;ctx.fillStyle=fill((z[0]+z[1]+z[2]+z[3])/4);ctx.fill();
  ctx.globalAlpha=alpha*.5;ctx.strokeStyle=stroke;ctx.lineWidth=.6;ctx.stroke();
  ctx.globalAlpha=1;
};
// 1 -- gain over the better single model, folded onto (shorter, longer)
mk('c1',{dim:D.dim, zs:5.2, ax:['shorter factor','longer factor'],
  paint(ctx,Q,ord,css,hex){
    const lo=hex(css('--gain-lo')),hi=hex(css('--gain-hi'));
    const g=a=>D.gain[a]===undefined?null:D.gain[a];
    const f=(a,b)=>g(a+'x'+b);
    for(const[i,j]of ord)
      quad(ctx,Q,i,j,f,m=>`rgb(${lo.map((v,k)=>Math.round(v+(hi[k]-v)*Math.min(1,m/0.18))).join(',')})`,
           css('--paper'),1);
  }});
// 5 -- both surfaces
mk('c5',{dim:D.dim, zs:5.2, ax:['digits in A','digits in B'],
  paint(ctx,Q,ord,css){
    const q=(a,b)=>D.qwen[a+'x'+b]===undefined?null:D.qwen[a+'x'+b];
    const p=(a,b)=>D.phi[a+'x'+b]===undefined?null:D.phi[a+'x'+b];
    for(const[i,j]of ord){
      quad(ctx,Q,i,j,p,()=>css('--onlyB'),css('--paper'),.55);
      quad(ctx,Q,i,j,q,()=>css('--onlyA'),css('--paper'),.9);
    }
  }});
</script>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs")
    ap.add_argument("-o", "--out", default="derived/pair-six.html")
    args = ap.parse_args()

    grid, chain = collect(args.runs)
    tot = [sum(g[i] for g in grid.values()) for i in range(4)]
    N = sum(tot)
    qa, pa_, un = (tot[0] + tot[1]) / N, (tot[0] + tot[2]) / N, (tot[0] + tot[1] + tot[2]) / N

    # gain over the BETTER single model, folded onto (shorter, longer)
    fold = collections.defaultdict(lambda: [0, 0, 0, 0])
    for (a, b), g in grid.items():
        f = fold[(min(a, b), max(a, b))]
        for i in range(4):
            f[i] += g[i]
    gain, qsurf, psurf = {}, {}, {}
    for (a, b), g in fold.items():
        n = sum(g)
        if not n:
            continue
        q, p = (g[0] + g[1]) / n, (g[0] + g[2]) / n
        gain[f"{a}x{b}"] = round((g[0] + g[1] + g[2]) / n - max(q, p), 4)
    for (a, b), g in grid.items():
        n = sum(g)
        if n:
            qsurf[f"{a}x{b}"] = round((g[0] + g[1]) / n, 4)
            psurf[f"{a}x{b}"] = round((g[0] + g[2]) / n, 4)

    peak_k, peak_v = 0, 0.0
    for k in bands(chain):
        b_, q, p, n = chain[k]
        t = b_ + q + p + n
        v = (b_ + q + p) / t - max((b_ + q) / t, (b_ + p) / t)
        if v > peak_v:
            peak_k, peak_v = k, v

    key = " ".join(
        f'<span><span class="sw" style="background:var(--{k})"></span>{lab}</span>'
        for k, lab in STATES)
    data = {"dim": max(max(c) for c in grid), "gain": gain, "qwen": qsurf, "phi": psurf}

    html = (PAGE.replace("__DATA__", json.dumps(data, separators=(",", ":")))
                .replace("__MOSAIC__", mosaic(chain))
                .replace("__SQUARES__", squares(chain))
                .replace("__ALLUVIAL__", alluvial(chain))
                .replace("__BOUNDS__", boundaries(grid))
                .replace("__KEY__", key)
                .replace("__N__", f"{N:,}").replace("__CELLS__", str(len(grid)))
                .replace("__QA__", f"{qa:.1%}").replace("__PA__", f"{pa_:.1%}")
                .replace("__UN__", f"{un:.1%}").replace("__OB__", str(tot[2]))
                .replace("__PEAK__", f"{peak_v*100:.1f}").replace("__PEAKK__", str(peak_k)))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    open(args.out, "w").write(html)
    print(f"wrote {args.out}  ({os.path.getsize(args.out)/1024:.0f} KB)")
    print(f"  {N} problems, {len(grid)} cells")
    print(f"  Qwen {qa:.1%}  Phi {pa_:.1%}  union {un:.1%}  onlyPhi {tot[2]}")
    print(f"  pair peaks at +{peak_v:.1%} on chain length {peak_k}")


if __name__ == "__main__":
    main()
