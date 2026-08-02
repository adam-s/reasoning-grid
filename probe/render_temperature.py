"""Does sampling temperature change how often the answer is right?

The grid was run at one temperature, so it cannot answer this. An earlier
variance sweep can: a single cell, ~100 trials at each of five temperatures,
which is far more depth per condition than the grid ever spends.

  .venv/bin/python probe/render_temperature.py -o derived/temperature.html

Two limits stated on the page rather than buried, because they bound the claim
completely:

  one cell   4x4, which is 16 single-digit operations -- easy enough that the
             model is not near its boundary. Temperature could matter more, or
             differently, where the problem is hard.
  no thinking  every one of these records has reasoning off. The grid's own
             sweeps show reasoning is worth 2.8 digits of boundary, so this
             measures temperature on a model that is recalling rather than
             computing. Whether the same curve holds while it reasons is
             untested and would need a fresh run.

The reason this is still worth drawing: n is ~100 per point, so the intervals
are tighter than anything else in the project, and the endpoints are far enough
apart that no reading of the noise closes the gap.
"""

import argparse
import collections
import glob
import json
import math
import os

MARK = ("<think>", "</think>", "<|channel|>analysis", "<|start|>assistant<|channel|>")

CSS = """
:root{ --paper:#f7f6f3; --ink:#1a1a1a; --muted:#767676; --line:#e2e2e0; --card:#fff;
       --dot:#2a78d6; --warm:#eb6834; --band:#ececea; }
@media (prefers-color-scheme:dark){
  :root{ --paper:#12130f; --ink:#eceae4; --muted:#8f8f88; --line:#2a2b26; --card:#191a15;
         --dot:#4a8cf0; --warm:#e07a4a; --band:#1e1f1a; } }
:root[data-theme="dark"]{ --paper:#12130f; --ink:#eceae4; --muted:#8f8f88; --line:#2a2b26;
  --card:#191a15; --dot:#4a8cf0; --warm:#e07a4a; --band:#1e1f1a; }
:root[data-theme="light"]{ --paper:#f7f6f3; --ink:#1a1a1a; --muted:#767676; --line:#e2e2e0;
  --card:#fff; --dot:#2a78d6; --warm:#eb6834; --band:#ececea; }
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:system-ui,-apple-system,"Segoe UI",sans-serif;font-size:15px;line-height:1.6}
.wrap{max-width:960px;margin:0 auto;padding:52px 24px 90px;display:flex;
  flex-direction:column;gap:26px}
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
.ylab{font-size:12px}.xlab{font-size:13px;fill:var(--ink)}.sub{font-size:11px}
.val{font-size:12.5px;fill:var(--ink)}
.grid{stroke:var(--line);stroke-width:1;stroke-dasharray:2 4}
.axis{stroke:var(--muted);stroke-width:1.2}
.bar{stroke-width:1.7;stroke-linecap:round}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:1px;
  background:var(--line);border:1px solid var(--line);border-radius:3px;overflow:hidden}
.stat{background:var(--card);padding:15px 17px}
.stat .k{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:10.5px;
  letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.stat .v{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:23px;
  font-variant-numeric:tabular-nums;margin-top:3px}
.warn{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--warm);
  border-radius:3px;padding:16px 18px}
.hr{height:1px;background:var(--line);border:0;margin:0}
"""


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0, 1.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def ladder(pts, W=900, H=440):
    L, R, T, B = 70, 26, 24, 78
    pw, ph = W - L - R, H - T - B
    n = len(pts)
    step = pw / n

    def X(i):
        return L + step * (i + 0.5)

    def Y(v):
        return T + ph * (1 - v)

    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="pass rate against sampling '
         f'temperature with 95% intervals">']
    for v in (0, .25, .5, .75, 1):
        o.append(f'<line class="grid" x1="{L}" y1="{Y(v):.1f}" x2="{L+pw}" y2="{Y(v):.1f}"/>')
        o.append(f'<text class="ylab" x="{L-12}" y="{Y(v)+4:.1f}" text-anchor="end">'
                 f'{v*100:.0f}%</text>')
    o.append(f'<line class="axis" x1="{L}" y1="{T}" x2="{L}" y2="{T+ph}"/>')
    o.append(f'<line class="axis" x1="{L}" y1="{T+ph}" x2="{L+pw}" y2="{T+ph}"/>')
    d = " ".join(f"{'M' if i == 0 else 'L'}{X(i):.1f},{Y(p):.1f}"
                 for i, (t, k, nn, p, lo, hi) in enumerate(pts))
    o.append(f'<path d="{d}" fill="none" stroke="var(--dot)" stroke-width="1.8" '
             f'stroke-dasharray="5 4" opacity=".5"/>')
    for i, (t, k, nn, p, lo, hi) in enumerate(pts):
        x = X(i)
        # warm the dot as temperature rises -- the axis is the subject
        frac = i / max(len(pts) - 1, 1)
        col = f"color-mix(in oklab, var(--warm) {frac*100:.0f}%, var(--dot))"
        o.append(f'<line class="bar" x1="{x:.1f}" y1="{Y(lo):.1f}" x2="{x:.1f}" '
                 f'y2="{Y(hi):.1f}" stroke="{col}"/>')
        for e in (lo, hi):
            o.append(f'<line class="bar" x1="{x-5:.1f}" y1="{Y(e):.1f}" '
                     f'x2="{x+5:.1f}" y2="{Y(e):.1f}" stroke="{col}"/>')
        o.append(f'<circle cx="{x:.1f}" cy="{Y(p):.1f}" r="7" fill="{col}">'
                 f'<title>T={t}: {k}/{nn} = {p:.1%} [{lo:.0%}, {hi:.0%}]</title></circle>')
        o.append(f'<text class="val" x="{x+13:.1f}" y="{Y(p)-9:.1f}">{p:.0%}</text>')
        o.append(f'<text class="xlab" x="{x:.1f}" y="{T+ph+26:.1f}" '
                 f'text-anchor="middle">{t}</text>')
        o.append(f'<text class="sub" x="{x:.1f}" y="{T+ph+44:.1f}" '
                 f'text-anchor="middle">{nn} trials</text>')
    o.append(f'<text class="ylab" x="{-(T+ph/2):.1f}" y="16" text-anchor="middle" '
             f'transform="rotate(-90)">share of runs exactly correct</text>')
    o.append(f'<text class="xlab" x="{L+pw/2:.1f}" y="{H-12}" text-anchor="middle">'
             f'sampling temperature &mdash; more random &rarr;</text>')
    o.append("</svg>")
    return "\n".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs")
    ap.add_argument("--cell", default="4x4")
    ap.add_argument("--min-n", type=int, default=40)
    ap.add_argument("-o", "--out", default="derived/temperature.html")
    args = ap.parse_args()
    ca, cb = (int(v) for v in args.cell.split("x"))

    by = collections.defaultdict(list)
    for f in sorted(glob.glob(os.path.join(args.runs, "*.jsonl"))):
        for line in open(f):
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("model") != "Qwen/Qwen3-4B" or r.get("top_p") != 1.0:
                continue
            if (r["a"], r["b"]) != (ca, cb):
                continue
            obs = r.get("thinking_observed")
            if obs is None and r.get("raw_text"):
                obs = any(m in r["raw_text"] for m in MARK)
            if obs:
                continue
            by[r["temperature"]].append(r)

    pts = []
    for t in sorted(by):
        rs = by[t]
        if len(rs) < args.min_n:
            continue
        k, n = sum(1 for r in rs if r["correct"]), len(rs)
        p, lo, hi = wilson(k, n)
        pts.append((t, k, n, p, lo, hi))

    (t0, k0, n0, p0, _, _) = pts[0]
    (t1, k1, n1, p1, _, _) = pts[-1]
    pool = (k0 + k1) / (n0 + n1)
    se = math.sqrt(pool * (1 - pool) * (1 / n0 + 1 / n1))
    z = (p0 - p1) / se
    pv = math.erfc(abs(z) / math.sqrt(2))

    html = f"""<title>carrychain &mdash; does temperature change the answer?</title>
<style>{CSS}</style>
<div class="wrap">
  <header>
    <p class="eyebrow">carrychain &middot; Qwen3-4B &middot; {ca}&times;{cb} &middot;
      reasoning OFF &middot; top_p 1.0</p>
    <h1>Turning the randomness up makes it worse</h1>
    <p class="lede">The grid runs at one temperature, so it cannot answer this. An earlier
      variance sweep can: one cell, about a hundred trials at each of
      {len(pts)} temperatures &mdash; far more depth per point than the grid ever spends.</p>
  </header>

  <div class="stats">
    <div class="stat"><div class="k">at T={t0}</div><div class="v">{p0:.0%}</div></div>
    <div class="stat"><div class="k">at T={t1}</div><div class="v">{p1:.0%}</div></div>
    <div class="stat"><div class="k">difference</div><div class="v">{p0-p1:+.0%}</div></div>
    <div class="stat"><div class="k">p-value</div>
      <div class="v">{'&lt;0.001' if pv < 0.001 else f'{pv:.3f}'}</div></div>
  </div>

  <figure>{ladder(pts)}</figure>

  <hr class="hr"/>
  <section>
    <h2>Reading it</h2>
    <p class="note">Greedy decoding wins. At T={t0} the model returns the exactly correct
      product {p0:.0%} of the time; at T={t1} it manages {p1:.0%} &mdash; a
      {abs(p0-p1)*100:.0f}-point drop, z = {abs(z):.1f}. The middle of the range is flat
      within noise, so this is not a smooth penalty for randomness so much as a cliff once
      sampling gets loose enough to derail a digit.</p>
    <p class="note" style="margin-top:12px">That makes sense mechanically. A long
      multiplication is a chain where every step must be right; one unlucky token early
      poisons everything after it. Temperature is exactly the knob that controls how often
      an unlucky token gets picked.</p>
  </section>

  <div class="warn">
    <p class="note" style="margin:0"><strong>Two limits that bound this completely.</strong>
      It is <strong>one cell</strong> &mdash; {ca}&times;{cb}, sixteen single-digit
      operations, easy enough that the model is nowhere near its boundary. And every
      record here has <strong>reasoning off</strong>, so this measures temperature on a
      model that is recalling rather than computing. The project's own sweeps show
      reasoning is worth 2.8 digits of boundary, so whether this curve survives with
      reasoning on is untested. Both would need a fresh run.</p>
  </div>
</div>
"""
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    open(args.out, "w").write(html)
    print(f"wrote {args.out}")
    for t, k, n, p, lo, hi in pts:
        print(f"  T={t:<4} {k:>3}/{n:<4} {p:>5.0%}  [{lo:.0%}, {hi:.0%}]")
    print(f"  T={t0} vs T={t1}: {p0-p1:+.0%}, z={z:.2f}, p={pv:.2e}")


if __name__ == "__main__":
    main()
