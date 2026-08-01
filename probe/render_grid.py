"""Reduced JSON -> a self-contained HTML page with inline SVG.

Third step of the pipeline: runners write raw JSONL, reduce_grid.py cuts that
to a small JSON, this draws it. No charting library, no CDN, no canvas -- the
surrounding projects hand-write inline SVG and it is the right call at 144
cells, where SVG stays crisp, themeable and inspectable.

  .venv/bin/python probe/render_grid.py derived/07-grid12.json -o derived/grid.html

Three things the colour has to say at once, and they must not be confusable:

  probability   a single-hue ramp, pale to deep. Sequential data gets one hue;
                a rainbow invents boundaries that are not in the numbers.
  sample size   the cell's inset. n=3 draws smaller than n=12, so a thinly
                sampled cell LOOKS thin. Adaptive n otherwise lies to the eye,
                which reads every tile as equally certain.
  nothing else  deliberately. A run that used the model's whole context without
                answering counts as incorrect, exactly like a wrong digit: it
                did not return the product. No second encoding separates the
                two, because the grid measures one thing. The four-way outcome
                is kept on every record and shown on hover, so the breakdown is
                never lost -- it simply does not get a visual channel it would
                have to earn. Grey means no data at all.

The ramp is computed in CSS via color-mix() from two custom properties, so one
per-cell number (--p) themes correctly in both light and dark.
"""

import argparse
import json
import math
import os

CSS = """
:root{
  --paper:#f5f7fa; --ink:#111621; --muted:#5a6478; --line:#d9dfe9;
  --ramp-lo:#e6ebf3; --ramp-hi:#1b2a5e;
  --signal:#c0761a; --void:#9e9992; --card:#ffffff;
  --shadow:0 1px 2px rgba(17,22,33,.06),0 8px 24px rgba(17,22,33,.05);
}
@media (prefers-color-scheme:dark){
  :root{
    --paper:#0e1118; --ink:#e8ecf4; --muted:#8b95a9; --line:#232a38;
    --ramp-lo:#191f2c; --ramp-hi:#8fa9ee;
    --signal:#e0a048; --void:#5a564f; --card:#141926;
    --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.3);
  }
}
:root[data-theme="dark"]{
  --paper:#0e1118; --ink:#e8ecf4; --muted:#8b95a9; --line:#232a38;
  --ramp-lo:#191f2c; --ramp-hi:#8fa9ee;
  --signal:#e0a048; --void:#5a564f; --card:#141926;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.3);
}
:root[data-theme="light"]{
  --paper:#f5f7fa; --ink:#111621; --muted:#5a6478; --line:#d9dfe9;
  --ramp-lo:#e6ebf3; --ramp-hi:#1b2a5e;
  --signal:#c0761a; --void:#9e9992; --card:#ffffff;
  --shadow:0 1px 2px rgba(17,22,33,.06),0 8px 24px rgba(17,22,33,.05);
}
*{box-sizing:border-box}
body{
  margin:0; background:var(--paper); color:var(--ink);
  font-family:system-ui,-apple-system,"Segoe UI",sans-serif;
  font-size:15px; line-height:1.65;
  -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1120px; margin:0 auto; padding:56px 24px 96px; display:flex;
      flex-direction:column; gap:44px}
h1{
  font-family:Charter,"Bitstream Charter","Iowan Old Style",Georgia,serif;
  font-weight:600; font-size:clamp(30px,4.4vw,44px); line-height:1.12;
  letter-spacing:-.015em; margin:0; text-wrap:balance;
}
h2{
  font-family:Charter,"Bitstream Charter","Iowan Old Style",Georgia,serif;
  font-weight:600; font-size:21px; letter-spacing:-.01em; margin:0 0 4px;
}
.lede{max-width:64ch; color:var(--muted); font-size:17px; margin:0}
.eyebrow{
  font-family:ui-monospace,"SF Mono",Menlo,monospace; font-size:11px;
  letter-spacing:.13em; text-transform:uppercase; color:var(--muted); margin:0 0 10px;
}
.rule{height:1px; background:var(--line); border:0; margin:0}
.stats{display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:1px;
       background:var(--line); border:1px solid var(--line); border-radius:3px; overflow:hidden}
.stat{background:var(--card); padding:15px 17px}
.stat .k{font-family:ui-monospace,"SF Mono",Menlo,monospace; font-size:10.5px;
         letter-spacing:.1em; text-transform:uppercase; color:var(--muted)}
.stat .v{font-family:ui-monospace,"SF Mono",Menlo,monospace; font-size:23px;
         font-variant-numeric:tabular-nums; margin-top:3px; letter-spacing:-.02em}
.stat .v small{font-size:13px; color:var(--muted); letter-spacing:0}
.grids{display:grid; grid-template-columns:repeat(auto-fit,minmax(330px,1fr)); gap:34px}
.panel{display:flex; flex-direction:column; gap:12px; min-width:0}
.panel .sub{color:var(--muted); font-size:13.5px; margin:0}
figure{margin:0; overflow-x:auto}
svg{display:block; width:100%; height:auto; max-width:520px}
text{font-family:ui-monospace,"SF Mono",Menlo,monospace; fill:var(--muted)}
.axttl{font-size:10px; letter-spacing:.12em; text-transform:uppercase}
.tick{font-size:9.5px}
.cell{stroke:var(--paper); stroke-width:.6}
.void{fill:var(--void); opacity:.5}
.hatch{stroke:none; pointer-events:none}
.face{stroke:var(--paper); stroke-width:.5; stroke-linejoin:round}
.floor{stroke:var(--line); stroke-width:.6; opacity:.55}
.halfline{fill:none; stroke:var(--signal); stroke-width:2.2; stroke-linecap:round;
          stroke-dasharray:5 4}
.hero{background:var(--card); border:1px solid var(--line); border-radius:3px;
      padding:22px 20px 12px}
.hero svg{max-width:100%}
.legend{display:flex; align-items:center; gap:14px; flex-wrap:wrap;
        font-family:ui-monospace,"SF Mono",Menlo,monospace; font-size:11px; color:var(--muted)}
.swatch{display:inline-block; width:11px; height:11px; vertical-align:-1px; margin-right:5px;
        border:1px solid var(--line)}
table{border-collapse:collapse; font-family:ui-monospace,"SF Mono",Menlo,monospace;
      font-size:12.5px; font-variant-numeric:tabular-nums; width:100%}
th,td{text-align:right; padding:7px 12px; border-bottom:1px solid var(--line)}
th{color:var(--muted); font-weight:400; font-size:10.5px; letter-spacing:.09em;
   text-transform:uppercase}
th:first-child,td:first-child{text-align:left}
.note{color:var(--muted); font-size:13.5px; max-width:64ch; margin:0}
.tablewrap{overflow-x:auto}
"""


def ramp_style(p):
    return (f"fill:color-mix(in oklab, var(--ramp-hi) {p*100:.1f}%, var(--ramp-lo))")


def heatmap(cells, dim, dstar=None, title_x="digits of B", title_y="digits of A"):
    """One square grid. Inset encodes n; grey encodes ceiling-bound."""
    S, PAD_L, PAD_T, PAD_B = 34, 34, 8, 34
    W = PAD_L + dim * S + 8
    H = PAD_T + dim * S + PAD_B
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" '
         f'aria-label="probability of an exactly correct product by operand size">',
         '<defs><pattern id="grind" width="4" height="4" patternUnits="userSpaceOnUse" '
         'patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="4" '
         'stroke="var(--paper)" stroke-width="1.4" opacity=".85"/></pattern></defs>']

    nmax = max((c["n"] for c in cells.values()), default=1) or 1
    for a in range(1, dim + 1):
        for b in range(1, dim + 1):
            c = cells.get(f"{a}x{b}")
            x, y = PAD_L + (b - 1) * S, PAD_T + (a - 1) * S
            if not c:
                continue
            # inset: a thinly sampled cell is drawn smaller, so it looks thinner
            frac = math.sqrt(c["n"] / nmax) if nmax else 1
            ins = (S - 1.2) * (1 - max(0.42, frac)) / 2
            w = S - 1.2 - 2 * ins
            tip = (f"{a}x{b}  N={c['N']}  {c['k']}/{c['n']}"
                   f"  p={c['p']:.2f} [{c['lo']:.2f}, {c['hi']:.2f}]")
            gr = c.get("n_ceiling_bound", 0) / max(c["n"], 1)
            if gr:
                tip += f"  ({c['n_ceiling_bound']} ran out of context)"
            if not c["valid"]:
                tip += "  NOT MEASURED"
                o.append(f'<rect class="cell void" x="{x+ins:.1f}" y="{y+ins:.1f}" '
                         f'width="{w:.1f}" height="{w:.1f}"><title>{tip}</title></rect>')
            else:
                o.append(f'<rect class="cell" x="{x+ins:.1f}" y="{y+ins:.1f}" '
                         f'width="{w:.1f}" height="{w:.1f}" style="{ramp_style(c["p"])}">'
                         f'<title>{tip}</title></rect>')
                # No hatch, no second encoding. A wrong answer is a wrong
                # answer whether the model computed it wrongly or never finished
                # computing it -- in both cases it failed to return the product,
                # which is the only thing this grid measures. The mechanism is
                # still on every record and in the tooltip for anyone who wants
                # it; it just does not get to complicate the chart.

    for i in range(1, dim + 1):
        o.append(f'<text class="tick" x="{PAD_L+(i-1)*S+S/2:.1f}" '
                 f'y="{PAD_T+dim*S+13:.1f}" text-anchor="middle">{i}</text>')
        o.append(f'<text class="tick" x="{PAD_L-8:.1f}" '
                 f'y="{PAD_T+(i-1)*S+S/2+3.4:.1f}" text-anchor="end">{i}</text>')

    # the fitted 50% boundary, N = d*^2, drawn as the hyperbola a*b = N
    if dstar:
        N = dstar * dstar
        pts = []
        for j in range(0, 241):
            av = 1 + j * (dim - 1) / 240
            bv = N / av
            if 1 <= bv <= dim:
                pts.append(f"{PAD_L+(bv-0.5)*S:.1f},{PAD_T+(av-0.5)*S:.1f}")
        if len(pts) > 1:
            o.append(f'<polyline points="{" ".join(pts)}" fill="none" '
                     f'stroke="var(--signal)" stroke-width="1.7" stroke-linecap="round" '
                     f'stroke-dasharray="4 3" opacity=".95"/>')

    o.append(f'<text class="axttl" x="{PAD_L+dim*S/2:.1f}" y="{H-4}" '
             f'text-anchor="middle">{title_x}</text>')
    o.append(f'<text class="axttl" x="{-(PAD_T+dim*S/2):.1f}" y="10" '
             f'text-anchor="middle" transform="rotate(-90)">{title_y}</text>')
    o.append("</svg>")
    return "\n".join(o)


def surface3d(cells, dim, zs=9.0, label="", dstar=None):
    """x = digits of A, y = digits of B, z = P(exactly correct), as SVG.

    Same isometric projection the Rubik's cube renderer in the neighbouring
    project uses -- equal foreshortening on all three axes, no perspective
    divide, no camera matrix:

        px = (x - y) / sqrt(2)
        py = (x + y - 2z) / sqrt(6)

    and the same hidden-surface method: give every quad a depth along the view
    axis (1,1,1), sort, draw back to front. A z-buffer would be overkill for
    169 quads, and staying in SVG keeps the fill themeable through the same
    custom properties the flat heatmap uses.

    The surface is drawn from cell CENTRES, so each quad spans four adjacent
    cells and is shaded by their mean. Reading a single cell's value off this
    is not the point -- the shape is. The flat grid beside it carries the
    numbers.
    """
    R2, R6 = math.sqrt(2), math.sqrt(6)

    def proj(x, y, z):
        return ((x - y) / R2, (x + y - 2 * z * zs) / R6)

    def p_at(a, b):
        c = cells.get(f"{a}x{b}")
        return c["p"] if c else None

    quads = []
    for a in range(1, dim):
        for b in range(1, dim):
            pts = [(a, b), (a + 1, b), (a + 1, b + 1), (a, b + 1)]
            zz = [p_at(u, v) for u, v in pts]
            if any(z is None for z in zz):
                continue
            xy = [proj(u, v, z) for (u, v), z in zip(pts, zz)]
            mean = sum(zz) / 4
            depth = sum(u + v + z * zs for (u, v), z in zip(pts, zz)) / 4
            quads.append((depth, xy, mean))
    quads.sort(key=lambda q: q[0])

    allpts = [p for _, xy, _ in quads for p in xy]
    xs = [p[0] for p in allpts]; ys = [p[1] for p in allpts]
    # room for the floor grid and the axis labels
    pad = 1.1
    minx, maxx = min(xs) - pad, max(xs) + pad
    miny, maxy = min(ys) - pad * 1.4, max(ys) + pad
    W, H = maxx - minx, maxy - miny
    S = 46  # scale to a comfortable viewBox
    o = [f'<svg viewBox="{minx*S:.1f} {miny*S:.1f} {W*S:.1f} {H*S:.1f}" role="img" '
         f'aria-label="{label} surface: probability of an exactly correct product '
         f'against the two operand sizes">']

    # floor at z=0, so the height of the surface is readable against something
    for a in range(1, dim + 1):
        p0, p1 = proj(a, 1, 0), proj(a, dim, 0)
        o.append(f'<line x1="{p0[0]*S:.1f}" y1="{p0[1]*S:.1f}" x2="{p1[0]*S:.1f}" '
                 f'y2="{p1[1]*S:.1f}" class="floor"/>')
    for b in range(1, dim + 1):
        p0, p1 = proj(1, b, 0), proj(dim, b, 0)
        o.append(f'<line x1="{p0[0]*S:.1f}" y1="{p0[1]*S:.1f}" x2="{p1[0]*S:.1f}" '
                 f'y2="{p1[1]*S:.1f}" class="floor"/>')

    for _, xy, mean in quads:
        pts = " ".join(f"{x*S:.1f},{y*S:.1f}" for x, y in xy)
        o.append(f'<polygon points="{pts}" class="face" style="{ramp_style(mean)}"/>')

    # the 50% plane where the fitted boundary sits, drawn as a hyperbola on the surface
    if dstar:
        N = dstar * dstar
        pts = []
        for i in range(0, 241):
            a = 1 + i * (dim - 1) / 240
            b = N / a
            if 1 <= b <= dim:
                x, y = proj(a, b, 0.5)
                pts.append(f"{x*S:.1f},{y*S:.1f}")
        if len(pts) > 1:
            o.append(f'<polyline points="{" ".join(pts)}" class="halfline"/>')

    for a, b, t, dx in ((dim, 1, "digits of A", 0.9), (1, dim, "digits of B", -0.9)):
        x, y = proj(a + (dx > 0) * 0.9, b + (dx < 0) * 0.9, 0)
        o.append(f'<text class="axttl" x="{x*S:.1f}" y="{y*S:.1f}" '
                 f'text-anchor="middle">{t}</text>')
    for v in (1, dim):
        x, y = proj(v, 0.1, 0)
        o.append(f'<text class="tick" x="{x*S:.1f}" y="{y*S:.1f}" text-anchor="middle">{v}</text>')
        x, y = proj(0.1, v, 0)
        o.append(f'<text class="tick" x="{x*S:.1f}" y="{y*S:.1f}" text-anchor="middle">{v}</text>')
    o.append("</svg>")
    return "\n".join(o)


def fit_dstar(cells):
    """Logistic in log N, ridge-damped. Same estimator as boundary_fit.py."""
    pts = [(c["N"], c["k"], c["n"]) for c in cells.values() if c["valid"] and c["n"] > 0]
    if len(pts) < 3:
        return None
    a, b, ridge = 5.0, -1.5, 1e-3

    def ll(a, b):
        t = 0.0
        for N, k, n in pts:
            z = max(-30.0, min(30.0, a + b * math.log(N)))
            p = min(max(1 / (1 + math.exp(-z)), 1e-12), 1 - 1e-12)
            t += k * math.log(p) + (n - k) * math.log(1 - p)
        return t - ridge * (a * a + b * b)

    cur = ll(a, b)
    for _ in range(300):
        g0 = g1 = h00 = h01 = h11 = 0.0
        for N, k, n in pts:
            x = math.log(N)
            p = 1 / (1 + math.exp(-max(-30.0, min(30.0, a + b * x))))
            r, w = k - n * p, n * p * (1 - p)
            g0 += r; g1 += r * x
            h00 += w; h01 += w * x; h11 += w * x * x
        g0 -= 2 * ridge * a; g1 -= 2 * ridge * b
        h00 += 2 * ridge; h11 += 2 * ridge
        det = h00 * h11 - h01 * h01
        if abs(det) < 1e-12:
            break
        da, db = (h11 * g0 - h01 * g1) / det, (h00 * g1 - h01 * g0) / det
        m = max(abs(da), abs(db))
        if m > 1.0:
            da, db = da / m, db / m
        step = 1.0
        for _ in range(30):
            if ll(a + step * da, b + step * db) >= cur:
                a, b = a + step * da, b + step * db
                cur = ll(a, b)
                break
            step /= 2
        else:
            break
    if b >= -1e-6:
        return None
    N = math.exp(-a / b)
    return math.sqrt(N) if N > 0 else None


def short(m):
    return m.split("/")[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("-o", "--out", default="derived/grid.html")
    ap.add_argument("--title", default="Where two models stop being reliable")
    args = ap.parse_args()

    doc = json.load(open(args.src))
    models = list(doc["models"])
    dim = max(max(c["a"], c["b"]) for m in models for c in doc["models"][m]["cells"].values())

    panels, stats = [], []
    for m in models:
        md = doc["models"][m]
        d = fit_dstar(md["cells"])
        valid = [c for c in md["cells"].values() if c["valid"]]
        k = sum(c["k"] for c in valid); n = sum(c["n"] for c in valid)
        stats.append((short(m), d, k, n, md))
        panels.append(f"""
      <div class="panel">
        <div>
          <p class="eyebrow">{short(m)}</p>
          <h2>{'breaks at %.2f digits' % d if d else 'no boundary in range'}</h2>
          <p class="sub">{k:,} of {n:,} products exactly correct &middot;
             {md['cells_ceiling_bound']} cells ceiling-bound</p>
        </div>
        <figure>{heatmap(md['cells'], dim, d)}</figure>
      </div>""")

    # the 3D surface leads: x = digits of A, y = digits of B, z = P(correct).
    # Built for whichever model covers the most cells, since that is the one
    # with a complete surface to show.
    top = max(stats, key=lambda s: s[4]["n_cells"])
    tdim = max(max(c["a"], c["b"]) for c in top[4]["cells"].values())
    hero = f'''<div class="hero">
    <p class="eyebrow">{top[0]} &middot; {tdim}&times;{tdim} &middot; z = P(exactly correct)</p>
    <h2>The surface</h2>
    <p class="note" style="margin:0 0 10px">Height is the share of runs returning the
      exactly correct product. The plateau at the back is where the model is reliable;
      the floor at the front is where it has stopped working. The dashed line traces the
      50% crossing, at {top[1]:.2f} digits on the diagonal.</p>
    {surface3d(top[4]["cells"], tdim, label=top[0], dstar=top[1])}
  </div>'''

    tot_gen = sum(s[4]["n_records"] for s in stats)
    tot_tok = sum(s[4]["total_tokens"] for s in stats)
    cards = [
        ("grid", f"{dim}&times;{dim}", "full square"),
        ("generations", f"{tot_gen:,}", "both models"),
        ("output tokens", f"{tot_tok/1e6:.1f}<small>M</small>", "reasoning included"),
    ]
    for nm, d, k, n, md in stats:
        cards.append((f"{nm} boundary", f"{d:.2f}" if d else "&mdash;", "digits at 50%"))

    paired_block = ""
    if "paired" in doc:
        p = doc["paired"]
        t = p["totals"]
        a, b = short(p["model_a"]), short(p["model_b"])
        lop = t["only_a"] + t["only_b"]
        verdict = ("The off-diagonal is one-sided: one model covers almost everything "
                   "the other misses, so a second vendor buys little here."
                   if lop and min(t["only_a"], t["only_b"]) / max(lop, 1) < 0.2 else
                   "Each model rescues problems the other misses, which is what a "
                   "two-vendor setup has to show to be worth its cost.")
        paired_block = f"""
    <hr class="rule"/>
    <section>
      <p class="eyebrow">paired outcomes &middot; {p['n_paired']:,} problems both models solved</p>
      <h2>Do they fail in the same places?</h2>
      <p class="note">{verdict} McNemar &chi;&sup2; = {p['mcnemar_chi2']}
         &mdash; above 3.84 the imbalance is beyond chance.</p>
      <div class="tablewrap"><table>
        <tr><th>outcome</th><th>problems</th><th>share</th></tr>
        <tr><td>both correct</td><td>{t['both_right']:,}</td>
            <td>{t['both_right']/max(p['n_paired'],1):.1%}</td></tr>
        <tr><td>only {a}</td><td>{t['only_a']:,}</td>
            <td>{t['only_a']/max(p['n_paired'],1):.1%}</td></tr>
        <tr><td>only {b}</td><td>{t['only_b']:,}</td>
            <td>{t['only_b']/max(p['n_paired'],1):.1%}</td></tr>
        <tr><td>both wrong</td><td>{t['both_wrong']:,}</td>
            <td>{t['both_wrong']/max(p['n_paired'],1):.1%}</td></tr>
      </table></div>
    </section>"""

    html = f"""<title>carrychain &mdash; {dim}&times;{dim} reliability grid</title>
<style>{CSS}</style>
<div class="wrap">
  <header>
    <p class="eyebrow">carrychain &middot; sweep {doc['sweep']}</p>
    <h1>{args.title}</h1>
    <p class="lede">Every cell is a multiplication size. Each is run many times, and its
      shade is the share of runs that returned the exactly correct product &mdash; deep
      means reliable, pale means broken. The dashed line is the fitted 50% boundary.</p>
  </header>

  <div class="stats">
    {''.join(f'<div class="stat"><div class="k">{k}</div><div class="v">{v}</div>'
             f'<div class="k">{s}</div></div>' for k, v, s in cards)}
  </div>

  <hr class="rule"/>
  {hero}
  <div class="grids">{''.join(panels)}</div>

  <div class="legend">
    <span><span class="swatch" style="background:var(--ramp-lo)"></span>0%</span>
    <span><span class="swatch"
       style="background:color-mix(in oklab,var(--ramp-hi) 50%,var(--ramp-lo))"></span>50%</span>
    <span><span class="swatch" style="background:var(--ramp-hi)"></span>100%</span>
    <span>smaller tile = fewer runs</span>
  </div>
  <p class="note">Cells are drawn smaller where fewer runs were spent on them. Samples
    are concentrated where the outcome is genuinely uncertain; a cell pinned at 0% or 100%
    gets only enough runs to confirm the bound. A run that consumed the model&rsquo;s entire
    context without answering counts as incorrect, the same as a wrong digit &mdash; either
    way the model did not return the product. That is fair here because every model was
    granted its own full context, so running out is the model&rsquo;s own limit and not a
    budget we imposed on it.</p>
  {paired_block}
</div>
"""
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as fh:
        fh.write(html)
    print(f"wrote {args.out}")
    for nm, d, k, n, md in stats:
        print(f"  {nm}: d*={d:.2f} digits, {k}/{n} correct, "
              f"{md['cells_ceiling_bound']} ceiling-bound cells"
              if d else f"  {nm}: no boundary")


if __name__ == "__main__":
    main()
