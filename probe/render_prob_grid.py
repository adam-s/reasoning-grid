#!/usr/bin/env python3
"""The probability grid, both models, one cell per problem size.

    python probe/render_prob_grid.py -o derived/prob-grid.html

Each cell holds two bars: the probability each model returns the exactly
correct product at that size. Not "solved at least once" -- that is not a
probability, it rises with the number of times you ask, and the two models were
not asked the same number of times (1,579 Qwen generations against 1,206 Phi).

A cell's value is the mean over its instances of that instance's success rate,
so every problem counts once regardless of how often it was re-run. Pooling raw
generations instead moves 3 cells of 144 and neither overall rate by more than
half a point.

Bars, not colour, because the question is which of two numbers is larger and
that is what length answers directly. A reader comparing two hues has to hold a
scale in their head; a reader comparing two bars does not.
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

    g = collections.defaultdict(list)          # cell -> [(pA, pB), ...] per instance
    gen = [0, 0, 0, 0]                         # kA, nA, kB, nB
    for u, d in by.items():
        if A not in d or B not in d:
            continue
        g[cell[u]].append((sum(d[A]) / len(d[A]), sum(d[B]) / len(d[B])))
        gen[0] += sum(d[A]); gen[1] += len(d[A])
        gen[2] += sum(d[B]); gen[3] += len(d[B])
    out = {c: (sum(x[0] for x in v) / len(v), sum(x[1] for x in v) / len(v), len(v))
           for c, v in g.items()}
    return out, gen


def wilson(k, n, z=1.96):
    """Interval on a rate. Quoted so nobody reads a 1-of-3 cell as a measurement."""
    if not n:
        return 0.0, 1.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def grid(g, W=960):
    dim = max(max(c) for c in g)
    L, T, R, Bm = 56, 30, 18, 66
    s = (W - L - R) / dim
    H = T + dim * s + Bm
    X = lambda a: L + (a - 1) * s
    Y = lambda b: T + (dim - b) * s
    bw = s * 0.26                              # bar width
    gap = s * 0.07
    pad = s * 0.16                             # room above a full bar
    base = s - pad * 0.55                      # baseline inside the cell

    nq = sum(1 for q, p, _ in g.values() if q > p)
    npb = sum(1 for q, p, _ in g.values() if p > q)
    o = [f'<svg viewBox="0 0 {W} {H:.0f}" role="img" aria-label="A {dim} by {dim} grid '
         f'of problem sizes. Each cell holds two bars, one per model, whose heights are '
         f'the probability that model returns the exactly correct product. Qwen is '
         f'taller in {nq} cells, Phi in {npb}, and the two are level in '
         f'{len(g)-nq-npb}.">']
    for (a, b), (q, p, n) in sorted(g.items()):
        x, y = X(a), Y(b)
        lead = "b" if p > q else ("a" if q > p else "t")
        # A cell earns its ink from evidence, not from effect. n is 3, 6 or 12.
        ev = 0.58 + 0.42 * min(1, n / 12)
        o.append(f'<g class="c {lead}">')
        o.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{s-2:.1f}" height="{s-2:.1f}" '
                 f'class="bg"/>')
        if p > q:
            o.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{s-2:.1f}" '
                     f'height="{s-2:.1f}" class="hi"/>')
        o.append(f'<line x1="{x+pad*0.7:.1f}" y1="{y+base:.1f}" '
                 f'x2="{x+s-2-pad*0.7:.1f}" y2="{y+base:.1f}" class="bl"/>')
        cx = x + (s - 2) / 2
        for k, (v, cls) in enumerate(((q, "qa"), (p, "pb"))):
            h = max(v * (base - pad), 0.9)     # a zero cell still shows a tick
            bx = cx - bw - gap / 2 + k * (bw + gap)
            o.append(f'<rect x="{bx:.1f}" y="{y+base-h:.1f}" width="{bw:.1f}" '
                     f'height="{h:.1f}" class="{cls}" opacity="{ev:.2f}"/>')
        lo_q, hi_q = wilson(round(q * n), n)
        lo_p, hi_p = wilson(round(p * n), n)
        o.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{s-2:.1f}" height="{s-2:.1f}" '
                 f'fill="transparent"><title>{a} x {b} digits &#183; {n} problems\n'
                 f'Qwen {q*100:.0f}%  (95% CI {lo_q*100:.0f}–{hi_q*100:.0f})\n'
                 f'Phi  {p*100:.0f}%  (95% CI {lo_p*100:.0f}–{hi_p*100:.0f})'
                 f'</title></rect>')
        o.append("</g>")
    for i in range(1, dim + 1):
        o.append(f'<text x="{X(i)+(s-2)/2:.1f}" y="{T-11}" text-anchor="middle" '
                 f'class="tk">{i}</text>')
        o.append(f'<text x="{L-11}" y="{Y(i)+(s-2)/2+4:.1f}" text-anchor="end" '
                 f'class="tk">{i}</text>')
    o.append(f'<text x="{L+(W-L-R)/2:.0f}" y="{H-26:.0f}" text-anchor="middle" '
             f'class="ax">digits in A</text>')
    o.append(f'<text transform="translate(15,{T+dim*s/2:.0f}) rotate(-90)" '
             f'text-anchor="middle" class="ax">digits in B</text>')
    o.append("</svg>")
    return "\n".join(o), dim


PAGE = """<title>reasoning-grid &mdash; where each model stops being reliable</title>
<style>
:root{ --paper:#fdfcf9; --panel:#f7f5f0; --line:#e6e2d9; --ink:#191817; --dim:#57544e;
  --faint:#a29d94; --lead-a:#1f3a5f; --lead-b:#c9853a; --hi:#c9853a; }
@media (prefers-color-scheme:dark){:root{ --paper:#131519; --panel:#1a1d23; --line:#2a2f38;
  --ink:#eae7e0; --dim:#a9a49b; --faint:#6c6862; --lead-a:#8fb0dd; --lead-b:#e0a048;
  --hi:#e0a048; }}
:root[data-theme="dark"]{ --paper:#131519; --panel:#1a1d23; --line:#2a2f38; --ink:#eae7e0;
  --dim:#a9a49b; --faint:#6c6862; --lead-a:#8fb0dd; --lead-b:#e0a048; --hi:#e0a048; }
:root[data-theme="light"]{ --paper:#fdfcf9; --panel:#f7f5f0; --line:#e6e2d9; --ink:#191817;
  --dim:#57544e; --faint:#a29d94; --lead-a:#1f3a5f; --lead-b:#c9853a; --hi:#c9853a; }
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
  font-size:17px;line-height:1.62}
.wrap{max-width:1000px;margin:0 auto;padding:56px 22px 90px}
h1{font-size:clamp(27px,4.2vw,38px);line-height:1.12;margin:0 0 14px;letter-spacing:-.016em;
  text-wrap:balance}
.eyebrow{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;
  letter-spacing:.15em;text-transform:uppercase;color:var(--faint);margin:0 0 11px}
.lede{font-size:19.5px;color:var(--dim);margin:0 0 30px;max-width:60ch}
p{margin:0 0 15px;max-width:64ch}
strong{font-weight:650}
.score{display:flex;gap:34px;flex-wrap:wrap;margin:0 0 26px;
  font-family:system-ui,-apple-system,sans-serif}
.score div{display:flex;flex-direction:column;gap:1px}
.score b{font-size:31px;font-weight:600;letter-spacing:-.02em;
  font-variant-numeric:tabular-nums;line-height:1}
.score span{font-size:12px;color:var(--faint);letter-spacing:.03em}
.qc b{color:var(--lead-a)} .pc b{color:var(--lead-b)}
.frame{border:1px solid var(--line);border-radius:5px;background:var(--panel);
  padding:12px 10px 4px;overflow-x:auto}
svg{display:block;width:100%;min-width:660px;height:auto}
.bg{fill:var(--ink);opacity:.028}
.hi{fill:var(--hi);opacity:.11}
.bl{stroke:var(--line);stroke-width:1}
.qa{fill:var(--lead-a)} .pb{fill:var(--lead-b)}
.c:hover .bg{opacity:.09}
.tk{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;fill:var(--faint)}
.ax{font-family:system-ui,-apple-system,sans-serif;font-size:12.5px;fill:var(--dim);
  letter-spacing:.02em}
.key{display:flex;gap:22px;align-items:center;flex-wrap:wrap;margin:16px 0 0;
  font-family:system-ui,-apple-system,sans-serif;font-size:12.5px;color:var(--dim)}
.sw{display:inline-block;width:9px;height:15px;border-radius:1.5px;vertical-align:-3px;
  margin-right:7px}
.tint{display:inline-block;width:15px;height:11px;border-radius:2px;vertical-align:-1px;
  margin-right:7px;background:var(--hi);opacity:.28}
.note{font-family:system-ui,-apple-system,sans-serif;font-size:13.5px;color:var(--faint);
  margin-top:22px;max-width:68ch;line-height:1.62}
.note strong{color:var(--dim)}
</style>
<div class="wrap">
  <p class="eyebrow">reasoning-grid &middot; __INST__ problems &middot; both models, same
  questions</p>
  <h1>Where each model stops being reliable</h1>
  <p class="lede">One cell per problem size. The two bars are the chance each model
  returns the exactly correct product &mdash; blue for Qwen, orange for Phi. Hover a
  cell for the rates and their intervals.</p>
  <div class="score">
    <div class="qc"><b>__PQ__%</b><span>QWEN3-4B</span></div>
    <div class="pc"><b>__PP__%</b><span>PHI-4-REASONING</span></div>
    <div><b>__NP__</b><span>CELLS PHI IS HIGHER</span></div>
    <div><b>__NQO__</b><span>CELLS QWEN IS LEVEL OR HIGHER</span></div>
  </div>
  <div class="frame">__SVG__</div>
  <div class="key">
    <span><span class="sw" style="background:var(--lead-a)"></span>Qwen</span>
    <span><span class="sw" style="background:var(--lead-b)"></span>Phi</span>
    <span><span class="tint"></span>cells where Phi is higher</span>
    <span>&#183; paler bars have fewer problems behind them</span>
  </div>
  <p class="note"><strong>Read the corner first.</strong> Bottom-left is small numbers,
  both bars full, both models right every time. Moving out along either axis the bars
  come down together, and the fall is steep: the reliable region has a hard edge rather
  than a slope. Qwen is the taller bar in <strong>__NQ__</strong> cells, Phi in
  <strong>__NP__</strong>, and the two are level in <strong>__NT__</strong> &mdash; of
  which <strong>__NSAT__</strong> are both models at 100%, where there is nothing left
  to win.</p>
  <p class="note"><strong>The __NP__ orange cells are not a region Phi owns.</strong>
  They are scattered, and every one rests on 12 problems or fewer, where a single
  problem moves a cell 8 to 33 points. The tinted cells mark them so they can be found,
  not so they can be trusted. What is worth trusting is the shape both models share, and
  the __GAP__-point gap between them.</p>
  <p class="note"><strong>These are probabilities, not counts of what was ever
  solved.</strong> A cell is the mean over its problems of how often each model got that
  problem right. The obvious alternative &mdash; did the model ever get it &mdash; is
  not a probability at all: it climbs with the number of times you ask, and the two
  models were not asked equally often (__GA__ Qwen generations against __GB__ Phi).
  Scoring that way flatters whichever model was run more.</p>
</div>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs")
    ap.add_argument("-o", "--out", default="derived/prob-grid.html")
    args = ap.parse_args()
    g, gen = collect(args.runs)
    svg, dim = grid(g)

    nq = sum(1 for q, p, n in g.values() if q > p)
    np_ = sum(1 for q, p, n in g.values() if p > q)
    nt = sum(1 for q, p, n in g.values() if q == p)
    nsat = sum(1 for q, p, n in g.values() if q == p == 1.0)
    inst = sum(n for _, _, n in g.values())
    pq, pp = gen[0] / gen[1] * 100, gen[2] / gen[3] * 100

    html = (PAGE.replace("__SVG__", svg).replace("__INST__", f"{inst:,}")
                .replace("__GENS__", f"{gen[1]+gen[3]:,}")
                .replace("__PQ__", f"{pq:.0f}").replace("__PP__", f"{pp:.0f}")
                .replace("__GAP__", f"{pq-pp:.0f}")
                .replace("__GA__", f"{gen[1]:,}").replace("__GB__", f"{gen[3]:,}")
                .replace("__NQ__", str(nq)).replace("__NP__", str(np_))
                .replace("__NT__", str(nt)).replace("__NSAT__", str(nsat))
                .replace("__NQO__", str(nq + nt)))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    open(args.out, "w").write(html)
    print(f"wrote {args.out}  ({os.path.getsize(args.out)/1024:.0f} KB)")
    print(f"  {inst} problems, {len(g)} cells, Qwen {pq:.1f}% Phi {pp:.1f}%")
    print(f"  Qwen leads {nq}, Phi leads {np_}, level {nt}  ({nq+np_+nt} = {len(g)})")


if __name__ == "__main__":
    main()
