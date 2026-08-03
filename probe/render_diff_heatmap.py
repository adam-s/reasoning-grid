#!/usr/bin/env python3
"""Qwen minus Phi, per cell, as a plain 2D heatmap.

    python probe/render_diff_heatmap.py -o derived/diff-heatmap.html

The number is printed in every cell because colour alone cannot carry n, and
n here is 12, 6 or 3. At n=3 a single problem moves a cell by 33 points, so a
reader who only sees hue will read noise as terrain. Cells are faded in
proportion to how little evidence stands behind them.
"""
import argparse
import collections
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reduce_grid import _parser  # noqa: E402

A, B = "Qwen3-4B", "Phi-4-reasoning"


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
            ans, _ = pa(j.get("raw_text") or "")
            cell[u] = (j["a"], j["b"])
            by[u].setdefault((j.get("model") or "").split("/")[-1], []).append(
                ans is not None and str(ans) == str(j["truth"]))
    g = collections.defaultdict(lambda: [0, 0])          # qwen solved, phi solved
    n = collections.Counter()
    only_b = 0
    for u, d in by.items():
        if A not in d or B not in d:
            continue
        qa, pb = any(d[A]), any(d[B])
        g[cell[u]][0] += qa
        g[cell[u]][1] += pb
        n[cell[u]] += 1
        only_b += pb and not qa
    return dict(g), n, only_b


def heatmap(g, n, W=760):
    dim = max(max(c) for c in g)
    L, T, R, Bm = 42, 30, 22, 54
    s = (W - L - R) / dim
    H = T + dim * s + Bm
    X = lambda a: L + (a - 1) * s
    Y = lambda b: T + (dim - b) * s
    mx = 50.0                                            # colour saturates at +-50 points

    o = [f'<svg viewBox="0 0 {W} {H:.0f}" role="img" aria-label="Grid of factor digit '
         f'counts; each cell shows how many percentage points Qwen leads Phi by.">']
    for (a, b), (kq, kp) in sorted(g.items()):
        N = n[(a, b)]
        d = (kq - kp) / N * 100
        t = max(-1, min(1, d / mx))
        col = "var(--lead-a)" if t > 0 else "var(--lead-b)"
        # evidence, not just effect: n=3 cells sit at a third of the ink
        ev = 0.35 + 0.65 * min(1, N / 12)
        o.append(f'<rect x="{X(a):.1f}" y="{Y(b):.1f}" width="{s-1.5:.1f}" '
                 f'height="{s-1.5:.1f}" fill="{col}" opacity="{abs(t)*ev:.3f}"/>')
        o.append(f'<rect x="{X(a):.1f}" y="{Y(b):.1f}" width="{s-1.5:.1f}" '
                 f'height="{s-1.5:.1f}" fill="none" stroke="var(--line)" stroke-width=".7">'
                 f'<title>{a}x{b} · Qwen {kq}/{N} · Phi {kp}/{N} · {d:+.0f} points</title></rect>')
        if abs(d) >= 1:
            o.append(f'<text x="{X(a)+s/2-0.75:.1f}" y="{Y(b)+s/2+3.5:.1f}" '
                     f'text-anchor="middle" class="v">{d:+.0f}</text>')
        else:
            o.append(f'<circle cx="{X(a)+s/2-0.75:.1f}" cy="{Y(b)+s/2-0.75:.1f}" r="1.6" '
                     f'fill="var(--faint)"/>')
    for i in range(1, dim + 1):
        o.append(f'<text x="{X(i)+s/2-0.75:.1f}" y="{T-10}" text-anchor="middle" '
                 f'class="tk">{i}</text>')
        o.append(f'<text x="{L-9}" y="{Y(i)+s/2+3.5:.1f}" text-anchor="end" '
                 f'class="tk">{i}</text>')
    o.append(f'<text x="{L+(W-L-R)/2:.0f}" y="{H-30:.0f}" text-anchor="middle" class="tk">'
             f'digits in A</text>')
    o.append(f'<text transform="translate(12,{T+dim*s/2:.0f}) rotate(-90)" '
             f'text-anchor="middle" class="tk">digits in B</text>')
    o.append("</svg>")
    return "\n".join(o), dim


PAGE = """<title>carrychain &mdash; Qwen minus Phi</title>
<style>
:root{ --paper:#fdfcf9; --panel:#f7f5f0; --line:#e3dfd6; --ink:#1a1a1a; --dim:#5a5a5a;
  --faint:#a6a29a; --lead-a:#1f3a5f; --lead-b:#c9853a; }
@media (prefers-color-scheme:dark){:root{ --paper:#14161a; --panel:#1b1e24; --line:#2b303a;
  --ink:#e9e6df; --dim:#a8a49b; --faint:#6f6b64; --lead-a:#8fb0dd; --lead-b:#e0a048; }}
:root[data-theme="dark"]{ --paper:#14161a; --panel:#1b1e24; --line:#2b303a; --ink:#e9e6df;
  --dim:#a8a49b; --faint:#6f6b64; --lead-a:#8fb0dd; --lead-b:#e0a048; }
:root[data-theme="light"]{ --paper:#fdfcf9; --panel:#f7f5f0; --line:#e3dfd6; --ink:#1a1a1a;
  --dim:#5a5a5a; --faint:#a6a29a; --lead-a:#1f3a5f; --lead-b:#c9853a; }
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
  font-size:17px;line-height:1.6}
.wrap{max-width:820px;margin:0 auto;padding:52px 24px 80px}
h1{font-size:clamp(26px,4vw,36px);line-height:1.15;margin:0 0 14px;letter-spacing:-.015em}
.eyebrow{font-family:ui-monospace,monospace;font-size:11px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--faint);margin:0 0 10px}
.lede{font-size:19px;color:var(--dim);margin:0 0 26px;max-width:62ch}
p{margin:0 0 15px;max-width:62ch}
strong{font-weight:650}
svg{display:block;width:100%;height:auto}
.tk{font-family:ui-monospace,monospace;font-size:11px;fill:var(--faint)}
.v{font-family:ui-monospace,monospace;font-size:11.5px;fill:var(--ink);opacity:.85}
.key{display:flex;gap:20px;align-items:center;flex-wrap:wrap;margin:14px 0 0;
  font-family:system-ui,sans-serif;font-size:12.5px;color:var(--dim)}
.sw{display:inline-block;width:18px;height:10px;border-radius:2px;vertical-align:-1px;
  margin-right:6px}
.note{font-family:system-ui,sans-serif;font-size:13.5px;color:var(--faint);
  margin-top:22px;max-width:66ch}
</style>
<div class="wrap">
  <p class="eyebrow">carrychain &middot; __N__ problems &middot; both models, same questions</p>
  <h1>Qwen minus Phi</h1>
  <p class="lede">One cell per problem size. The number is how many percentage points
  Qwen leads by. Blue is Qwen ahead, orange is Phi ahead.</p>
  __SVG__
  <div class="key">
    <span><span class="sw" style="background:var(--lead-a)"></span>Qwen ahead</span>
    <span><span class="sw" style="background:var(--lead-b)"></span>Phi ahead</span>
    <span>&#183; a dot means the two tied</span>
    <span>&#183; paler cells have fewer trials behind them</span>
  </div>
  <p class="note"><strong>Read the bottom-left first.</strong> It is all ties, because
  both models solve everything there. The lead only appears once problems get big enough
  for either model to fail, and it is almost entirely blue: Qwen is ahead nearly
  everywhere, by __MEAN__ points on average.</p>
  <p class="note">__NEG__ of __CELLS__ cells are orange. Every one of them sits on
  12 trials or fewer, where a single problem moves a cell by 8 to 33 points &mdash; so
  none of them is evidence that Phi leads anywhere. The case for running Phi is not
  that it wins regions; it is the __ONLYB__ individual problems it solved that Qwen
  missed, which this chart does not show.</p>
</div>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs")
    ap.add_argument("-o", "--out", default="derived/diff-heatmap.html")
    args = ap.parse_args()
    g, n, only_b = collect(args.runs)
    svg, dim = heatmap(g, n)

    N = sum(n.values())
    diffs = [(kq - kp) / n[c] for c, (kq, kp) in g.items()]
    neg = sum(1 for d in diffs if d < 0)
    mean = sum((kq - kp) for kq, kp in g.values()) / N * 100

    html = (PAGE.replace("__SVG__", svg).replace("__N__", f"{N:,}")
                .replace("__MEAN__", f"{mean:+.0f}").replace("__NEG__", str(neg))
                .replace("__CELLS__", str(len(g))).replace("__ONLYB__", str(only_b)))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    open(args.out, "w").write(html)
    print(f"wrote {args.out}  ({os.path.getsize(args.out)/1024:.0f} KB)")
    print(f"  {N} problems, {len(g)} cells, mean lead {mean:+.1f} points, {neg} cells orange")


if __name__ == "__main__":
    main()
