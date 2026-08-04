"""What the model spends, and what it gets for it.

"Reasoning improves accuracy" is the boring version of this comparison. The
interesting part is in the token counts, and it is two facts that only show up
side by side:

  effort   with reasoning on, output length scales with problem size -- the
           model works longer on harder problems. With reasoning off it is
           FLAT. Roughly the same number of tokens for a 1-digit product as for
           a 14-digit one, including sizes it never once gets right. It is not
           computing and failing; it is emitting an answer-shaped string at
           constant cost.
  price    tokens per exactly-correct answer, which is the number anyone
           deploying this actually pays. Below about 30 single-digit operations
           reasoning-off is an order of magnitude cheaper per correct answer AND
           nearly as accurate, so paying for reasoning is waste. Past ~57 it is
           barely cheaper, and then it never produces a correct answer at any
           price.

  .venv/bin/python probe/render_effort.py -o derived/effort.html

The floor line on the first panel is the length of the answer itself. A run that
lands near it did not have room to do arithmetic even in principle.
"""

import argparse
import glob
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reduce_grid import load  # noqa: E402

CSS = """
:root{ --paper:#f7f6f3; --ink:#1a1a1a; --muted:#767676; --line:#e2e2e0; --card:#fff;
       --on:#1b2a5e; --off:#c0761a; --floor:#9aa0aa; --band:#efeee9; }
@media (prefers-color-scheme:dark){
  :root{ --paper:#12130f; --ink:#eceae4; --muted:#8f8f88; --line:#2a2b26; --card:#191a15;
         --on:#8fa9ee; --off:#e0a048; --floor:#5d636d; --band:#1d1e19; } }
:root[data-theme="dark"]{ --paper:#12130f; --ink:#eceae4; --muted:#8f8f88; --line:#2a2b26;
  --card:#191a15; --on:#8fa9ee; --off:#e0a048; --floor:#5d636d; --band:#1d1e19; }
:root[data-theme="light"]{ --paper:#f7f6f3; --ink:#1a1a1a; --muted:#767676; --line:#e2e2e0;
  --card:#fff; --on:#1b2a5e; --off:#c0761a; --floor:#9aa0aa; --band:#efeee9; }
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:system-ui,-apple-system,"Segoe UI",sans-serif;font-size:15px;line-height:1.6}
.wrap{max-width:1000px;margin:0 auto;padding:52px 24px 90px;display:flex;
  flex-direction:column;gap:26px}
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
.ylab{font-size:11.5px}.tick{font-size:11px}.ann{font-size:12px;fill:var(--ink)}
.grid{stroke:var(--line);stroke-width:1;stroke-dasharray:2 4}
.axis{stroke:var(--muted);stroke-width:1.2}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:1px;
  background:var(--line);border:1px solid var(--line);border-radius:3px;overflow:hidden}
.stat{background:var(--card);padding:15px 17px}
.stat .k{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:10.5px;
  letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.stat .v{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:22px;
  font-variant-numeric:tabular-nums;margin-top:3px}
.legend{display:flex;gap:18px;flex-wrap:wrap;font-family:ui-monospace,"SF Mono",Menlo,monospace;
  font-size:11px;color:var(--muted);align-items:center;margin-top:12px}
.sw{display:inline-block;width:14px;height:3px;vertical-align:3px;margin-right:6px}
table{border-collapse:collapse;font-family:ui-monospace,"SF Mono",Menlo,monospace;
  font-size:12.5px;font-variant-numeric:tabular-nums;width:100%}
th,td{text-align:right;padding:7px 12px;border-bottom:1px solid var(--line)}
th{color:var(--muted);font-weight:400;font-size:10.5px;letter-spacing:.09em;
  text-transform:uppercase}
th:first-child,td:first-child{text-align:left}
.hr{height:1px;background:var(--line);border:0;margin:0}
.tablewrap{overflow-x:auto}
"""


def logplot(seriesd, floor, W=940, H=420, ymin=100, ymax=40000, ylab="", note=""):
    L, R, T, B = 76, 26, 24, 56
    pw, ph = W - L - R, H - T - B
    lx0, lx1 = math.log(1), math.log(196)
    ly0, ly1 = math.log(ymin), math.log(ymax)

    def X(N):
        return L + pw * (math.log(N) - lx0) / (lx1 - lx0)

    def Y(v):
        v = max(v, ymin)
        return T + ph * (1 - (math.log(v) - ly0) / (ly1 - ly0))

    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{ylab} against problem size">']
    ticks = [t for t in (100, 300, 1000, 3000, 10000, 30000) if ymin <= t <= ymax]
    for v in ticks:
        o.append(f'<line class="grid" x1="{L}" y1="{Y(v):.1f}" x2="{L+pw}" y2="{Y(v):.1f}"/>')
        lab = f"{v//1000}k" if v >= 1000 else str(v)
        o.append(f'<text class="ylab" x="{L-10}" y="{Y(v)+4:.1f}" text-anchor="end">{lab}</text>')
    o.append(f'<line class="axis" x1="{L}" y1="{T}" x2="{L}" y2="{T+ph}"/>')
    o.append(f'<line class="axis" x1="{L}" y1="{T+ph}" x2="{L+pw}" y2="{T+ph}"/>')
    if floor:
        d = " ".join(f"{'M' if i == 0 else 'L'}{X(N):.1f},{Y(v):.1f}"
                     for i, (N, v) in enumerate(floor))
        o.append(f'<path d="{d}" fill="none" stroke="var(--floor)" stroke-width="1.6" '
                 f'stroke-dasharray="3 3"/>')
        N, v = floor[-1]
        o.append(f'<text class="tick" x="{X(N)-6:.1f}" y="{Y(v)+16:.1f}" '
                 f'text-anchor="end" fill="var(--floor)">just writing the answer</text>')
    for name, col, pts in seriesd:
        d = " ".join(f"{'M' if i == 0 else 'L'}{X(N):.1f},{Y(v):.1f}"
                     for i, (N, v) in enumerate(pts))
        o.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="2.8" '
                 f'stroke-linejoin="round"/>')
        for N, v in pts:
            o.append(f'<circle cx="{X(N):.1f}" cy="{Y(v):.1f}" r="5" fill="{col}">'
                     f'<title>{name}, N&asymp;{N}: {v:,.0f}</title></circle>')
    for N in (1, 4, 12, 30, 60, 120, 196):
        o.append(f'<text class="tick" x="{X(N):.1f}" y="{T+ph+20:.1f}" '
                 f'text-anchor="middle">{N}</text>')
    o.append(f'<text class="ylab" x="{-(T+ph/2):.1f}" y="16" text-anchor="middle" '
             f'transform="rotate(-90)">{ylab}</text>')
    o.append(f'<text class="ylab" x="{L+pw/2:.1f}" y="{H-10}" text-anchor="middle">'
             f'N = digits of A &times; digits of B &nbsp;(log scale)</text>')
    if note:
        o.append(f'<text class="ann" x="{L+12}" y="{T+18}">{note}</text>')
    o.append("</svg>")
    return "\n".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs")
    ap.add_argument("-o", "--out", default="derived/effort.html")
    args = ap.parse_args()
    M = "Qwen/Qwen3-4B"

    def L(pat):
        return load(sorted(glob.glob(os.path.join(args.runs, pat))),
                    model=M, temperature=0.7)
    ON = L("10-grid12-qwen-*.jsonl") + L("11-ext14-qwen-*.jsonl")
    OFF = L("13-nothink-qwen-*.jsonl")

    BANDS = ((1, 12), (13, 30), (31, 56), (57, 90), (91, 196))
    rows, eff_on, eff_off, price_on, price_off, floor = [], [], [], [], [], []
    for lo, hi in BANDS:
        mid = math.exp((math.log(lo) + math.log(hi)) / 2)
        a = [r for r in ON if lo <= r["a"] * r["b"] <= hi]
        b = [r for r in OFF if lo <= r["a"] * r["b"] <= hi]
        ka, ta = sum(r["correct"] for r in a), sum(r["completion_tokens"] for r in a)
        kb, tb = sum(r["correct"] for r in b), sum(r["completion_tokens"] for r in b)
        eff_on.append((mid, ta / len(a)))
        eff_off.append((mid, tb / len(b)))
        price_on.append((mid, ta / ka if ka else 0))
        if kb:
            price_off.append((mid, tb / kb))
        floor.append((mid, sum(len(r["truth"]) for r in b) / len(b)))
        rows.append((lo, hi, ka, len(a), ta / len(a), ta / ka if ka else None,
                     kb, len(b), tb / len(b), tb / kb if kb else None))

    tok_on = sum(r["completion_tokens"] for r in ON) / len(ON)
    tok_off = sum(r["completion_tokens"] for r in OFF) / len(OFF)
    ratio_lo = rows[0][5] / rows[0][9]
    # the band where reasoning-off stops being the cheaper way to a correct answer
    cross = "57&ndash;90"
    for lo, hi, ka, na, ea, pa, kb, nb, eb, pb in rows:
        if pb and pa and pb > pa:
            cross = f"{lo}&ndash;{hi}"
            break

    html = f"""<title>reasoning-grid &mdash; what the model spends, and what it gets</title>
<style>{CSS}</style>
<div class="wrap">
  <header>
    <p class="eyebrow">reasoning-grid &middot; Qwen3-4B &middot; 3,132 runs &middot;
      temp 0.7 &middot; identical problems</p>
    <h1>Without reasoning, it doesn&rsquo;t try harder on harder problems</h1>
    <p class="lede">Same model, same 196 cells, same seeded problems. One difference:
      whether the chat template lets it work before answering. The accuracy gap is the
      obvious result. The token counts are the interesting one.</p>
  </header>

  <div class="stats">
    <div class="stat"><div class="k">tokens, reasoning on</div>
      <div class="v">{tok_on:,.0f}</div></div>
    <div class="stat"><div class="k">tokens, reasoning off</div>
      <div class="v">{tok_off:,.0f}</div></div>
    <div class="stat"><div class="k">effort scaling, on</div>
      <div class="v">{eff_on[-1][1]/eff_on[0][1]:.1f}&times;</div></div>
    <div class="stat"><div class="k">effort scaling, off</div>
      <div class="v">{eff_off[-1][1]/eff_off[0][1]:.1f}&times;</div></div>
  </div>

  <section>
    <h2>Effort against difficulty</h2>
    <p class="note" style="margin-bottom:12px">How many tokens the model produces per
      attempt, as problems get harder.</p>
    <figure>{logplot([("reasoning on", "var(--on)", eff_on),
                      ("reasoning off", "var(--off)", eff_off)], floor,
                     ylab="output tokens per attempt")}</figure>
    <div class="legend">
      <span><span class="sw" style="background:var(--on)"></span>reasoning on</span>
      <span><span class="sw" style="background:var(--off)"></span>reasoning off</span>
      <span><span class="sw" style="background:var(--floor)"></span>length of the answer itself</span>
    </div>
    <p class="note" style="margin-top:14px">With reasoning the line climbs
      {eff_on[-1][1]/eff_on[0][1]:.0f}&times; &mdash; the model works longer on harder
      problems, which is what working means. <strong>Without reasoning it is flat.</strong>
      About {eff_off[-1][1]:,.0f} tokens whether the product needs seven digits or
      twenty-two, including every size it never once gets right. It is not computing and
      failing. It is emitting an answer-shaped string at constant cost, and the
      grey line shows how little of that budget is even left over after writing the
      digits out.</p>
  </section>

  <hr class="hr"/>

  <section>
    <h2>Tokens per <em>correct</em> answer</h2>
    <p class="note" style="margin-bottom:12px">The number anyone deploying this pays:
      total tokens divided by answers that were exactly right.</p>
    <figure>{logplot([("reasoning on", "var(--on)", price_on),
                      ("reasoning off", "var(--off)", price_off)], None,
                     ymax=200000,
                     ylab="tokens per correct answer")}</figure>
    <div class="tablewrap" style="margin-top:16px"><table>
      <tr><th>N = a&times;b</th><th>on: correct</th><th>on: tok/correct</th>
          <th>off: correct</th><th>off: tok/correct</th></tr>
      {''.join(f'<tr><td>{lo}&ndash;{hi}</td><td>{ka}/{na}</td>'
               f'<td>{pa:,.0f}</td><td>{kb}/{nb}</td>'
               f'<td>{(f"{pb:,.0f}" if pb else "never")}</td></tr>'
               for lo, hi, ka, na, ea, pa, kb, nb, eb, pb in rows)}
    </table></div>
    <p class="note" style="margin-top:16px">The lines cross. Below about thirty
      single-digit operations, turning reasoning <em>off</em> is roughly
      {ratio_lo:.0f}&times; cheaper per correct answer and barely less accurate &mdash;
      paying for reasoning there is waste. Past that it stops being a bargain, and past
      N=90 it never returns a correct answer at any price.</p>
    <p class="note" style="margin-top:12px">So the useful question is not whether
      reasoning helps. It is where the crossover sits, because on either side of it the
      right choice is the opposite one.</p>
  </section>
</div>
"""
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    open(args.out, "w").write(html)
    print(f"wrote {args.out}")
    print(f"  effort scaling: on {eff_on[-1][1]/eff_on[0][1]:.1f}x, "
          f"off {eff_off[-1][1]/eff_off[0][1]:.1f}x")
    for lo, hi, ka, na, ea, pa, kb, nb, eb, pb in rows:
        print(f"  N {lo:>3}-{hi:<4} on {ka:>3}/{na:<4} {ea:>7,.0f} tok "
              f"({pa:>8,.0f}/correct)   off {kb:>3}/{nb:<4} {eb:>6,.0f} tok "
              f"({(f'{pb:,.0f}' if pb else 'never'):>9}/correct)")


if __name__ == "__main__":
    main()
