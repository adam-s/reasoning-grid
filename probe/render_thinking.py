"""Reasoning on against reasoning off, same model, same problems.

The surface says where Qwen3-4B stops being reliable. It does not say what is
doing the work. Running the identical 196 cells with the chat template's
thinking flag turned off answers that directly: same weights, same instances,
same temperature, same seeds -- the only difference is whether the model is
allowed to work before answering.

  .venv/bin/python probe/render_thinking.py -o derived/thinking.html

Both series are drawn as clouds rather than curves because the point is where
they separate, not where either sits. The separation is the size of the effect,
and it is not constant: it opens at the size where a product stops being
memorable and starts needing a procedure.

Note on what this does NOT show: reasoning-off generations average a few hundred
tokens, which is barely enough to write a twelve-digit product, let alone derive
one. So "reasoning helps" understates it. The honest phrasing is that with
reasoning the model computes and without it the model recalls, and recall runs
out quickly.
"""

import argparse
import glob
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reduce_grid import load, cells, wilson   # noqa: E402
from pick_partner import fit_slope            # noqa: E402

CSS = """
:root{ --paper:#f7f6f3; --ink:#1a1a1a; --muted:#767676; --line:#e4e3e0; --card:#fff;
       --on:#1b2a5e; --off:#c0761a; --gap:#ece7dc; }
@media (prefers-color-scheme:dark){
  :root{ --paper:#12130f; --ink:#eceae4; --muted:#8f8f88; --line:#2a2b26; --card:#191a15;
         --on:#8fa9ee; --off:#e0a048; --gap:#241f16; } }
:root[data-theme="dark"]{ --paper:#12130f; --ink:#eceae4; --muted:#8f8f88; --line:#2a2b26;
  --card:#191a15; --on:#8fa9ee; --off:#e0a048; --gap:#241f16; }
:root[data-theme="light"]{ --paper:#f7f6f3; --ink:#1a1a1a; --muted:#767676; --line:#e4e3e0;
  --card:#fff; --on:#1b2a5e; --off:#c0761a; --gap:#ece7dc; }
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
.lede{max-width:63ch;color:var(--muted);font-size:16.5px;margin:0}
.note{max-width:66ch;color:var(--muted);font-size:13.5px;margin:0}
figure{margin:0;background:var(--card);border:1px solid var(--line);border-radius:4px;
  padding:22px 20px 12px;overflow-x:auto}
svg{display:block;width:100%;height:auto}
text{font-family:ui-monospace,"SF Mono",Menlo,monospace;fill:var(--muted)}
.lab{font-size:12px}.tick{font-size:11px}
.big{font-size:13px;fill:var(--ink)}
.grid{stroke:var(--line);stroke-width:1;stroke-dasharray:2 4}
.axis{stroke:var(--muted);stroke-width:1.2}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:1px;
  background:var(--line);border:1px solid var(--line);border-radius:3px;overflow:hidden}
.stat{background:var(--card);padding:15px 17px}
.stat .k{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:10.5px;
  letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.stat .v{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:23px;
  font-variant-numeric:tabular-nums;margin-top:3px}
.legend{display:flex;gap:18px;flex-wrap:wrap;font-family:ui-monospace,"SF Mono",Menlo,monospace;
  font-size:11px;color:var(--muted);align-items:center;margin-top:12px}
.sw{display:inline-block;width:11px;height:11px;border-radius:50%;vertical-align:-1px;
  margin-right:5px}
table{border-collapse:collapse;font-family:ui-monospace,"SF Mono",Menlo,monospace;
  font-size:12.5px;font-variant-numeric:tabular-nums;width:100%}
th,td{text-align:right;padding:7px 12px;border-bottom:1px solid var(--line)}
th{color:var(--muted);font-weight:400;font-size:10.5px;letter-spacing:.09em;
  text-transform:uppercase}
th:first-child,td:first-child{text-align:left}
.hr{height:1px;background:var(--line);border:0;margin:0}
.tablewrap{overflow-x:auto}
"""


def chart(on, off, W=960, H=520):
    L, R, T, B = 74, 26, 24, 60
    pw, ph = W - L - R, H - T - B
    Ns = [c["N"] for c in on.values()]
    lo_n, hi_n = math.log(min(Ns)), math.log(max(Ns))

    def X(N):
        return L + pw * (math.log(N) - lo_n) / (hi_n - lo_n)

    def Y(v):
        return T + ph * (1 - v)

    fits = {}
    for key, cs in (("on", on), ("off", off)):
        fits[key] = fit_slope(cs)

    def pred(key, N):
        a, b = fits[key]
        return 1 / (1 + math.exp(-max(-30, min(30, a + b * math.log(N)))))

    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="share of runs exactly '
         f'correct with reasoning on and off, against problem size">']
    # the gap between the two fitted curves is the effect
    steps = 150
    top = [f"{X(math.exp(lo_n+(hi_n-lo_n)*i/steps)):.1f},"
           f"{Y(pred('on', math.exp(lo_n+(hi_n-lo_n)*i/steps))):.1f}" for i in range(steps + 1)]
    bot = [f"{X(math.exp(lo_n+(hi_n-lo_n)*i/steps)):.1f},"
           f"{Y(pred('off', math.exp(lo_n+(hi_n-lo_n)*i/steps))):.1f}"
           for i in range(steps, -1, -1)]
    o.append(f'<polygon points="{" ".join(top + bot)}" fill="var(--gap)"/>')
    for v in (0, .25, .5, .75, 1):
        o.append(f'<line class="grid" x1="{L}" y1="{Y(v):.1f}" x2="{L+pw}" y2="{Y(v):.1f}"/>')
        o.append(f'<text class="lab" x="{L-12}" y="{Y(v)+4:.1f}" text-anchor="end">'
                 f'{v*100:.0f}%</text>')
    o.append(f'<line class="axis" x1="{L}" y1="{T}" x2="{L}" y2="{T+ph}"/>')
    o.append(f'<line class="axis" x1="{L}" y1="{T+ph}" x2="{L+pw}" y2="{T+ph}"/>')
    for key, cs, col in (("off", off, "var(--off)"), ("on", on, "var(--on)")):
        for c in cs.values():
            r = 2.4 + 2.2 * math.sqrt(c["n"] / 12)
            o.append(f'<circle cx="{X(c["N"]):.1f}" cy="{Y(c["p"]):.1f}" r="{r:.1f}" '
                     f'fill="{col}" opacity=".42">'
                     f'<title>{c["a"]}x{c["b"]} N={c["N"]} {c["k"]}/{c["n"]}='
                     f'{c["p"]:.0%} ({key})</title></circle>')
        d = " ".join(f"{'M' if i == 0 else 'L'}"
                     f"{X(math.exp(lo_n+(hi_n-lo_n)*i/steps)):.1f},"
                     f"{Y(pred(key, math.exp(lo_n+(hi_n-lo_n)*i/steps))):.1f}"
                     for i in range(steps + 1))
        o.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="2.8"/>')
    for N in (1, 4, 12, 30, 60, 120, 196):
        if min(Ns) <= N <= max(Ns):
            o.append(f'<text class="tick" x="{X(N):.1f}" y="{T+ph+20:.1f}" '
                     f'text-anchor="middle">{N}</text>')
    # label the widest gap
    best = max(range(steps + 1),
               key=lambda i: pred("on", math.exp(lo_n + (hi_n - lo_n) * i / steps))
               - pred("off", math.exp(lo_n + (hi_n - lo_n) * i / steps)))
    Nb = math.exp(lo_n + (hi_n - lo_n) * best / steps)
    g = pred("on", Nb) - pred("off", Nb)
    o.append(f'<text class="big" x="{X(Nb)+10:.1f}" y="{Y((pred("on",Nb)+pred("off",Nb))/2):.1f}">'
             f'{g:.0%} gap</text>')
    o.append(f'<text class="lab" x="{-(T+ph/2):.1f}" y="17" text-anchor="middle" '
             f'transform="rotate(-90)">share of runs exactly correct</text>')
    o.append(f'<text class="lab" x="{L+pw/2:.1f}" y="{H-12}" text-anchor="middle">'
             f'N = digits of A &times; digits of B &nbsp;(log scale)</text>')
    o.append("</svg>")
    return "\n".join(o), fits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs")
    ap.add_argument("-o", "--out", default="derived/thinking.html")
    args = ap.parse_args()
    M = "Qwen/Qwen3-4B"

    def L(pat):
        return load(sorted(glob.glob(os.path.join(args.runs, pat))),
                    model=M, temperature=0.7)

    ON = L("10-grid12-qwen-*.jsonl") + L("11-ext14-qwen-*.jsonl")
    OFF = L("13-nothink-qwen-*.jsonl")
    on, off = cells(ON), cells(OFF)
    svg, fits = chart(on, off)

    def tot(cs):
        k = sum(c["k"] for c in cs.values()); n = sum(c["n"] for c in cs.values())
        return k, n, wilson(k, n)
    ko, no, (po, lo_, ho_) = tot(on)
    kf, nf, (pf, lf, hf) = tot(off)
    don = math.sqrt(math.exp(-fits["on"][0] / fits["on"][1]))
    dof = math.sqrt(math.exp(-fits["off"][0] / fits["off"][1]))
    tok_on = sum(r["completion_tokens"] for r in ON) / len(ON)
    tok_off = sum(r["completion_tokens"] for r in OFF) / len(OFF)

    rows = []
    for lo, hi in ((1, 12), (13, 30), (31, 56), (57, 90), (91, 196)):
        a = [c for c in on.values() if lo <= c["N"] <= hi]
        b = [c for c in off.values() if lo <= c["N"] <= hi]
        ka, na = sum(c["k"] for c in a), sum(c["n"] for c in a)
        kb, nb = sum(c["k"] for c in b), sum(c["n"] for c in b)
        rows.append((f"{lo}&ndash;{hi}", ka, na, kb, nb))

    html = f"""<title>reasoning-grid &mdash; is the reasoning doing the arithmetic?</title>
<style>{CSS}</style>
<div class="wrap">
  <header>
    <p class="eyebrow">reasoning-grid &middot; Qwen3-4B &middot; 196 cells &times; 2 &middot;
      temp 0.7 &middot; identical problems</p>
    <h1>Is the reasoning doing the arithmetic, or the weights?</h1>
    <p class="lede">Same model, same {len(on)} cells, same seeded problems, same
      temperature. The only difference is whether the chat template lets the model work
      before it answers.</p>
  </header>

  <div class="stats">
    <div class="stat"><div class="k">reasoning on</div><div class="v">{po:.1%}</div></div>
    <div class="stat"><div class="k">reasoning off</div><div class="v">{pf:.1%}</div></div>
    <div class="stat"><div class="k">boundary, on</div><div class="v">{don:.2f}</div></div>
    <div class="stat"><div class="k">boundary, off</div><div class="v">{dof:.2f}</div></div>
  </div>

  <figure>{svg}</figure>
  <div class="legend">
    <span><span class="sw" style="background:var(--on)"></span>reasoning on
      &mdash; {tok_on:,.0f} tokens per attempt</span>
    <span><span class="sw" style="background:var(--off)"></span>reasoning off
      &mdash; {tok_off:,.0f} tokens per attempt</span>
    <span>dot size = runs in that cell</span>
  </div>

  <hr class="hr"/>
  <section>
    <h2>Where the gap opens</h2>
    <div class="tablewrap"><table>
      <tr><th>N = a&times;b</th><th>reasoning on</th><th>reasoning off</th><th>gap</th></tr>
      {''.join(f'<tr><td>{lab}</td><td>{ka}/{na} = {ka/na:.0%}</td>'
               f'<td>{kb}/{nb} = {kb/nb:.0%}</td><td>{ka/na - kb/nb:+.0%}</td></tr>'
               for lab, ka, na, kb, nb in rows)}
    </table></div>
    <p class="note" style="margin-top:16px">Through N=30 the two are close: small products
      are answerable without working them out. Past that the lines part, and by N=57 the
      model without reasoning is at a few percent while the model with it is still over
      half right. The boundary moves from {don:.2f} digits to {dof:.2f}.</p>
    <p class="note" style="margin-top:12px">One honest qualification. Reasoning-off
      averages {tok_off:,.0f} tokens &mdash; barely enough to write a twelve-digit product,
      let alone derive one. So this is not really &ldquo;reasoning helps by X%&rdquo;. With
      reasoning the model <em>computes</em>; without it the model <em>recalls</em>, and
      recall runs out at about the size where a product stops being a fact and starts
      being a procedure.</p>
  </section>
</div>
"""
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    open(args.out, "w").write(html)
    print(f"wrote {args.out}")
    print(f"  reasoning ON  {ko}/{no} = {po:.1%}  d*={don:.2f}  {tok_on:,.0f} tok/gen")
    print(f"  reasoning OFF {kf}/{nf} = {pf:.1%}  d*={dof:.2f}  {tok_off:,.0f} tok/gen")


if __name__ == "__main__":
    main()
