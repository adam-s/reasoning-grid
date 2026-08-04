"""One chart: do two models from different companies fail in the same places?

The surfaces answer "how good is each model". They cannot answer the question
this project exists for, because two models can share an identical accuracy
curve and still disagree on every individual problem. Only a PAIRED view --
same problem, same seed, both models -- can tell those apart, and pairing
cannot be added after the fact.

  .venv/bin/python probe/render_blindspots.py derived/10-grid12.json -o derived/blindspots.html

Encoding, and why each choice:

  hue        WHO wins the cell. Diverging, two hues with a neutral midpoint,
             because the quantity is signed: blue where only model A solved
             problems the other missed, orange where only model B did. A
             sequential ramp would imply an ordering that does not exist.
  intensity  HOW LOPSIDED that cell is, as the net advantage per problem. A
             cell where both models agree is neutral regardless of whether they
             agreed on right or on wrong -- agreement is not the subject here.
  ring       cells where BOTH models rescued each other at least once. These
             are the strongest evidence for two vendors: not "A is better", but
             "each catches something the other drops", inside a single cell.

The bar underneath is the same data as coverage: what one model gets, what the
other adds, and what neither reaches.
"""

import argparse
import json
import os

CSS = """
:root{
  --paper:#f5f7fa; --ink:#111621; --muted:#5a6478; --line:#d9dfe9; --card:#fff;
  --a:#2a78d6; --b:#eb6834; --neutral:#e9edf3; --dead:#b9c0cc;
}
@media (prefers-color-scheme:dark){
  :root{ --paper:#0e1118; --ink:#e8ecf4; --muted:#8b95a9; --line:#232a38;
         --card:#141926; --a:#3987e5; --b:#d95926; --neutral:#1c2230; --dead:#39414f; }
}
:root[data-theme="dark"]{ --paper:#0e1118; --ink:#e8ecf4; --muted:#8b95a9;
  --line:#232a38; --card:#141926; --a:#3987e5; --b:#d95926; --neutral:#1c2230; --dead:#39414f; }
:root[data-theme="light"]{ --paper:#f5f7fa; --ink:#111621; --muted:#5a6478;
  --line:#d9dfe9; --card:#fff; --a:#2a78d6; --b:#eb6834; --neutral:#e9edf3; --dead:#b9c0cc; }
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:system-ui,-apple-system,"Segoe UI",sans-serif;font-size:15px;line-height:1.65}
.wrap{max-width:940px;margin:0 auto;padding:56px 24px 96px;display:flex;
  flex-direction:column;gap:34px}
h1{font-family:Charter,"Bitstream Charter","Iowan Old Style",Georgia,serif;
  font-weight:600;font-size:clamp(28px,4vw,40px);line-height:1.14;margin:0;
  letter-spacing:-.015em;text-wrap:balance}
h2{font-family:Charter,"Bitstream Charter","Iowan Old Style",Georgia,serif;
  font-weight:600;font-size:19px;margin:0 0 6px;letter-spacing:-.01em}
.eyebrow{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:11px;
  letter-spacing:.13em;text-transform:uppercase;color:var(--muted);margin:0 0 10px}
.lede{max-width:62ch;color:var(--muted);font-size:17px;margin:0}
.note{max-width:64ch;color:var(--muted);font-size:13.5px;margin:0}
figure{margin:0;overflow-x:auto}
svg{display:block;width:100%;height:auto}
.chart{max-width:540px}
text{font-family:ui-monospace,"SF Mono",Menlo,monospace;fill:var(--muted)}
.tick{font-size:9.5px}
.axttl{font-size:10px;letter-spacing:.12em;text-transform:uppercase}
.cell{stroke:var(--paper);stroke-width:.7}
.ring{fill:none;stroke:var(--ink);stroke-width:1.5;opacity:.85}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-family:ui-monospace,"SF Mono",Menlo,monospace;
  font-size:11px;color:var(--muted);align-items:center}
.sw{display:inline-block;width:11px;height:11px;vertical-align:-1px;margin-right:5px;
  border:1px solid var(--line)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;
  background:var(--line);border:1px solid var(--line);border-radius:3px;overflow:hidden}
.stat{background:var(--card);padding:15px 17px}
.stat .k{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:10.5px;
  letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.stat .v{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:24px;
  font-variant-numeric:tabular-nums;margin-top:3px;letter-spacing:-.02em}
.hr{height:1px;background:var(--line);border:0;margin:0}
"""


def mix(side, t):
    """t in 0..1 -> from neutral toward the winning model's hue."""
    v = "var(--a)" if side == "a" else "var(--b)"
    return f"color-mix(in oklab, {v} {min(t,1)*100:.0f}%, var(--neutral))"


def chart(per_cell, dim, na, nb):
    S, PAD_L, PAD_T, PAD_B = 36, 36, 10, 36
    W, H = PAD_L + dim * S + 10, PAD_T + dim * S + PAD_B
    o = [f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="which model '
         f'solves what the other misses, by problem size">']
    for a in range(1, dim + 1):
        for b in range(1, dim + 1):
            c = per_cell.get(f"{a}x{b}")
            x, y = PAD_L + (b - 1) * S, PAD_T + (a - 1) * S
            if not c:
                continue
            oa, ob = c["only_a"], c["only_b"]
            n = sum(c.values())
            dead = c["both_wrong"] == n
            net = (oa - ob) / n if n else 0
            # scale so a cell where a third of problems are one-sided is saturated
            t = min(abs(net) / 0.34, 1.0)
            fill = ("var(--dead)" if dead else
                    "var(--neutral)" if oa == ob == 0 else
                    mix("a" if net > 0 else "b", t))
            tip = (f"{a}x{b}  n={n}   both right {c['both_right']}, "
                   f"only {na} {oa}, only {nb} {ob}, neither {c['both_wrong']}")
            o.append(f'<rect class="cell" x="{x+.6:.1f}" y="{y+.6:.1f}" '
                     f'width="{S-1.2}" height="{S-1.2}" style="fill:{fill}">'
                     f'<title>{tip}</title></rect>')
            # both models rescued each other here at least once
            if oa and ob:
                o.append(f'<circle class="ring" cx="{x+S/2:.1f}" cy="{y+S/2:.1f}" r="4.2"/>')
    for i in range(1, dim + 1):
        o.append(f'<text class="tick" x="{PAD_L+(i-1)*S+S/2:.1f}" y="{PAD_T+dim*S+13:.1f}" '
                 f'text-anchor="middle">{i}</text>')
        o.append(f'<text class="tick" x="{PAD_L-8:.1f}" y="{PAD_T+(i-1)*S+S/2+3.4:.1f}" '
                 f'text-anchor="end">{i}</text>')
    o.append(f'<text class="axttl" x="{PAD_L+dim*S/2:.1f}" y="{H-4}" '
             f'text-anchor="middle">digits of B</text>')
    o.append(f'<text class="axttl" x="{-(PAD_T+dim*S/2):.1f}" y="10" text-anchor="middle" '
             f'transform="rotate(-90)">digits of A</text>')
    o.append("</svg>")
    return "\n".join(o)


def bar(t, n, na, nb):
    W, H = 560, 66
    segs = [("both_right", "var(--a)", .95, f"both correct"),
            ("only_a", "var(--a)", .45, f"only {na}"),
            ("only_b", "var(--b)", .95, f"only {nb}"),
            ("both_wrong", "var(--dead)", 1, "neither")]
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="coverage from one model '
         f'versus both">']
    x = 0
    for k, col, op, lab in segs:
        w = t[k] / n * W
        o.append(f'<rect x="{x:.1f}" y="0" width="{w:.1f}" height="26" fill="{col}" '
                 f'opacity="{op}"><title>{lab}: {t[k]} ({t[k]/n:.1%})</title></rect>')
        if w > 46:
            o.append(f'<text class="tick" x="{x+w/2:.1f}" y="42" text-anchor="middle">'
                     f'{t[k]/n:.0%}</text>')
        x += w
    solo = (t["both_right"] + t["only_a"]) / n * W
    o.append(f'<line x1="{solo:.1f}" y1="-2" x2="{solo:.1f}" y2="30" stroke="var(--ink)" '
             f'stroke-width="2"/>')
    o.append(f'<text class="tick" x="{solo:.1f}" y="58" text-anchor="middle">'
             f'{na} alone stops here</text>')
    o.append("</svg>")
    return "\n".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("-o", "--out", default="derived/blindspots.html")
    args = ap.parse_args()
    doc = json.load(open(args.src))
    pr = doc["paired"]
    na = pr["model_a"].split("/")[-1]
    nb = pr["model_b"].split("/")[-1]
    t, n = pr["totals"], pr["n_paired"]
    pc = pr["per_cell"]
    dim = max(max(int(k.split("x")[0]), int(k.split("x")[1])) for k in pc)

    rescue_b = t["only_b"] / (t["only_b"] + t["both_wrong"])
    both_cells = sum(1 for c in pc.values() if c["only_a"] and c["only_b"])
    solo = (t["both_right"] + t["only_a"]) / n
    either = (n - t["both_wrong"]) / n

    cards = [("problems", f"{n:,}"),
             (f"{na} alone", f"{solo:.1%}"),
             ("either model", f"{either:.1%}"),
             ("coverage gained", f"+{either-solo:.1%}")]

    html = f"""<title>reasoning-grid &mdash; do two models fail in the same places?</title>
<style>{CSS}</style>
<div class="wrap">
  <header>
    <p class="eyebrow">reasoning-grid &middot; {n:,} paired problems &middot; {dim}&times;{dim}</p>
    <h1>Two models, two companies, and the problems only one of them can do</h1>
    <p class="lede">Every problem below was given to both models &mdash; same digits, same
      seed, same settings. That pairing is what makes the question answerable: two models
      can share an accuracy curve and still disagree on every individual problem.</p>
  </header>

  <div class="stats">
    {''.join(f'<div class="stat"><div class="k">{k}</div><div class="v">{v}</div></div>'
             for k, v in cards)}
  </div>

  <hr class="hr"/>

  <section>
    <h2>Where each model rescues the other</h2>
    <p class="note" style="margin-bottom:14px">Blue where only {na} solved problems
      {nb} missed; orange where only {nb} did. Stronger colour means more one-sided.
      Grey cells are beyond both models. A ring marks a cell where <em>each</em> model
      rescued the other at least once &mdash; {both_cells} of them.</p>
    <figure>{chart(pc, dim, na, nb)}</figure>
    <div class="legend" style="margin-top:12px">
      <span><span class="sw" style="background:var(--a)"></span>only {na}</span>
      <span><span class="sw" style="background:var(--b)"></span>only {nb}</span>
      <span><span class="sw" style="background:var(--neutral)"></span>they agree</span>
      <span><span class="sw" style="background:var(--dead)"></span>neither ever correct</span>
      <span>&#9711; both rescued the other</span>
    </div>
  </section>

  <hr class="hr"/>

  <section>
    <h2>What the second model buys</h2>
    <figure style="max-width:600px">{bar(t, n, na, nb)}</figure>
    <p class="note" style="margin-top:14px">{na} is the stronger model and wins outright:
      it solves {solo:.1%} of these problems against {(t['both_right']+t['only_b'])/n:.1%}
      for {nb}. But <strong>{t['only_b']} problems &mdash; {rescue_b:.0%} of everything
      {na} got wrong &mdash; were solved by {nb} alone.</strong> Running both lifts
      coverage from {solo:.1%} to {either:.1%}.</p>
    <p class="note" style="margin-top:12px">So the two questions come apart. <em>Which
      model is better</em> has a clear answer. <em>Is a second vendor worth it</em> has a
      different one, and it is not derivable from the first: the failures are not nested.
      Past the point where problems defeat both models the redundancy stops paying &mdash;
      the grey region buys nothing, and no amount of vendor diversity reaches it.</p>
  </section>
</div>
"""
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    open(args.out, "w").write(html)
    print(f"wrote {args.out}")
    print(f"  {na} alone {solo:.1%}   either {either:.1%}   gain +{either-solo:.1%}")
    print(f"  {nb} rescued {t['only_b']} of {t['only_b']+t['both_wrong']} "
          f"{na} failures = {rescue_b:.0%}")
    print(f"  cells where both rescued each other: {both_cells}")


if __name__ == "__main__":
    main()
