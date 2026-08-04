"""Does A x B behave differently from B x A? The paired test, and its control.

For a language model "3 x 12" and "12 x 3" are different token sequences that
invite different procedures, so operand order is a real thing to test. It is
also easy to test WRONG: comparing grid cell (a,b) against cell (b,a) compares
different numbers, so any difference confounds order with which instances were
drawn. This uses the same product presented both ways, paired on instance_uid.

  .venv/bin/python probe/render_order.py -o derived/order.html

Two panels, because one is not enough to reach a conclusion:

  direction   the paired 2x2. If one order were better, the two single-order
              bars would differ. McNemar tests exactly that.
  dispersion  swapping might change WHICH problems are solved without favouring
              either order, which would show up as more disagreement than plain
              resampling produces. That needs a control -- the same problem
              asked twice in the SAME order -- and it must be matched on
              difficulty, because harder problems disagree more regardless.

The uncontrolled version of the second panel showed 36% against 21% and looked
like a strong effect. Matched on N it is 36% against 28%, p=0.157. The control
is the entire finding.
"""

import argparse
import collections
import glob
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reduce_grid import load, wilson  # noqa: E402

CSS = """
:root{ --paper:#f7f6f3; --ink:#1a1a1a; --muted:#767676; --line:#e4e3e0; --card:#fff;
       --a:#2a78d6; --b:#eb6834; --both:#3f4a5a; --none:#b9c0cc; --ctl:#8b93a3; }
@media (prefers-color-scheme:dark){
  :root{ --paper:#12130f; --ink:#eceae4; --muted:#8f8f88; --line:#2a2b26; --card:#191a15;
         --a:#3987e5; --b:#d95926; --both:#9aa6b8; --none:#3b4350; --ctl:#6d7482; } }
:root[data-theme="dark"]{ --paper:#12130f; --ink:#eceae4; --muted:#8f8f88; --line:#2a2b26;
  --card:#191a15; --a:#3987e5; --b:#d95926; --both:#9aa6b8; --none:#3b4350; --ctl:#6d7482; }
:root[data-theme="light"]{ --paper:#f7f6f3; --ink:#1a1a1a; --muted:#767676; --line:#e4e3e0;
  --card:#fff; --a:#2a78d6; --b:#eb6834; --both:#3f4a5a; --none:#b9c0cc; --ctl:#8b93a3; }
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
  padding:22px 20px 14px;overflow-x:auto}
svg{display:block;width:100%;height:auto}
text{font-family:ui-monospace,"SF Mono",Menlo,monospace;fill:var(--muted)}
.big{font-size:15px;fill:var(--ink)}
.lab{font-size:12px}.tick{font-size:11px}
.grid{stroke:var(--line);stroke-width:1;stroke-dasharray:2 4}
.axis{stroke:var(--muted);stroke-width:1.2}
.bar{stroke:var(--muted);stroke-width:1.7;stroke-linecap:round}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:1px;
  background:var(--line);border:1px solid var(--line);border-radius:3px;overflow:hidden}
.stat{background:var(--card);padding:15px 17px}
.stat .k{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:10.5px;
  letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.stat .v{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:23px;
  font-variant-numeric:tabular-nums;margin-top:3px}
.legend{display:flex;gap:18px;flex-wrap:wrap;font-family:ui-monospace,"SF Mono",Menlo,monospace;
  font-size:11px;color:var(--muted);align-items:center;margin-top:12px}
.sw{display:inline-block;width:11px;height:11px;vertical-align:-1px;margin-right:5px}
.hr{height:1px;background:var(--line);border:0;margin:0}
"""


def mosaic(t, n, W=900, H=190):
    """The paired 2x2 as one proportional bar. If order mattered, the two
    middle segments would differ."""
    segs = [("both", t["both"], "var(--both)", "correct both ways"),
            ("orig", t["orig_only"], "var(--a)", "only A &times; B"),
            ("swap", t["swap_only"], "var(--b)", "only B &times; A"),
            ("none", t["neither"], "var(--none)", "wrong both ways")]
    L, R, T = 10, 10, 22
    pw = W - L - R
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="paired outcomes when the '
         f'same product is presented in both operand orders">']
    x = L
    for key, v, col, lab in segs:
        w = pw * v / n
        o.append(f'<rect x="{x:.1f}" y="{T}" width="{w:.1f}" height="54" fill="{col}">'
                 f'<title>{lab}: {v} ({v/n:.1%})</title></rect>')
        if w > 74:
            o.append(f'<text class="big" x="{x+w/2:.1f}" y="{T+33:.1f}" '
                     f'text-anchor="middle" fill="var(--paper)">{v}</text>')
            o.append(f'<text class="lab" x="{x+w/2:.1f}" y="{T+74:.1f}" '
                     f'text-anchor="middle">{lab}</text>')
            o.append(f'<text class="tick" x="{x+w/2:.1f}" y="{T+91:.1f}" '
                     f'text-anchor="middle">{v/n:.0%}</text>')
        x += w
    # bracket the two discordant segments -- these are what McNemar compares
    x0 = L + pw * t["both"] / n
    x1 = x0 + pw * (t["orig_only"] + t["swap_only"]) / n
    o.append(f'<line class="bar" x1="{x0:.1f}" y1="{T-9}" x2="{x1:.1f}" y2="{T-9}"/>')
    o.append(f'<text class="tick" x="{(x0+x1)/2:.1f}" y="{T-15}" text-anchor="middle">'
             f'the {t["orig_only"]+t["swap_only"]} problems where order changed the '
             f'outcome</text>')
    o.append(f'<text class="lab" x="{L}" y="{H-8}">'
             f'{n} problems, each run once in each order</text>')
    o.append("</svg>")
    return "\n".join(o)


def bands(rows, W=900, H=330):
    """Disagreement rate by difficulty: swapped order vs the same-order control."""
    L, R, T, B = 66, 18, 20, 64
    pw, ph = W - L - R, H - T - B
    n = len(rows)
    step = pw / n
    ymax = 0.6

    def X(i, off=0):
        return L + step * (i + 0.5) + off

    def Y(v):
        return T + ph * (1 - v / ymax)

    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="disagreement rate by '
         f'problem size, swapped order against the same-order control">']
    for v in (0, .15, .30, .45, .60):
        o.append(f'<line class="grid" x1="{L}" y1="{Y(v):.1f}" x2="{L+pw}" y2="{Y(v):.1f}"/>')
        o.append(f'<text class="lab" x="{L-10}" y="{Y(v)+4:.1f}" text-anchor="end">'
                 f'{v*100:.0f}%</text>')
    o.append(f'<line class="axis" x1="{L}" y1="{T}" x2="{L}" y2="{T+ph}"/>')
    o.append(f'<line class="axis" x1="{L}" y1="{T+ph}" x2="{L+pw}" y2="{T+ph}"/>')
    for i, (lab, c, t) in enumerate(rows):
        for (d, tot, col, off, nm) in ((c[0], c[1], "var(--ctl)", -11, "same order"),
                                       (t[0], t[1], "var(--b)", 11, "swapped")):
            if not tot:
                continue
            p, lo, hi = wilson(d, tot)
            x = X(i, off)
            o.append(f'<line class="bar" x1="{x:.1f}" y1="{Y(lo):.1f}" x2="{x:.1f}" '
                     f'y2="{Y(hi):.1f}" stroke="{col}"/>')
            for e in (lo, hi):
                o.append(f'<line class="bar" x1="{x-4:.1f}" y1="{Y(e):.1f}" '
                         f'x2="{x+4:.1f}" y2="{Y(e):.1f}" stroke="{col}"/>')
            o.append(f'<circle cx="{x:.1f}" cy="{Y(p):.1f}" r="6" fill="{col}">'
                     f'<title>{nm}, N {lab}: {d}/{tot} = {p:.0%} [{lo:.0%},{hi:.0%}]</title>'
                     f'</circle>')
        o.append(f'<text class="lab" x="{X(i):.1f}" y="{T+ph+24:.1f}" '
                 f'text-anchor="middle">N {lab}</text>')
        o.append(f'<text class="tick" x="{X(i):.1f}" y="{T+ph+41:.1f}" '
                 f'text-anchor="middle">{c[1]} vs {t[1]} pairs</text>')
    o.append(f'<text class="lab" x="{-(T+ph/2):.1f}" y="15" text-anchor="middle" '
             f'transform="rotate(-90)">pairs that disagree</text>')
    o.append("</svg>")
    return "\n".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs")
    ap.add_argument("-o", "--out", default="derived/order.html")
    args = ap.parse_args()
    R = args.runs

    def L(pat, **kw):
        return load(sorted(glob.glob(os.path.join(R, pat))), temperature=0.7, **kw)

    M = "Qwen/Qwen3-4B"
    SW = L("12-swap-qwen-*.jsonl")
    OR = L("10-grid12-qwen-*.jsonl", model=M) + L("11-ext14-qwen-*.jsonl", model=M)
    A = L("07-grid12-qwen-*.jsonl", model=M)
    B = L("10-grid12-qwen-*.jsonl", model=M)

    o = {x["instance_uid"]: x for x in OR}
    test = [(o[x["instance_uid"]], x) for x in SW if x["instance_uid"] in o]
    dA, dB = {x["instance_uid"]: x for x in A}, {x["instance_uid"]: x for x in B}
    ctl = [(dA[u], dB[u]) for u in set(dA) & set(dB)]

    t = collections.Counter()
    for a, b in test:
        t["both" if a["correct"] and b["correct"] else
          "orig_only" if a["correct"] else
          "swap_only" if b["correct"] else "neither"] += 1
    n = len(test)
    n01, n10 = t["orig_only"], t["swap_only"]
    d = n01 + n10
    chi = (abs(n01 - n10) - 1) ** 2 / d if d else 0
    pv = (sum(math.comb(d, k) for k in range(min(n01, n10) + 1)) * 2 / 2 ** d) if d else 1

    def dis(pp):
        return sum(1 for a, b in pp if a["correct"] != b["correct"]), len(pp)

    rows, pc, pn, tc, tn = [], 0, 0, 0, 0
    for lo, hi, lab in ((1, 30, "1-30"), (31, 60, "31-60"),
                        (61, 100, "61-100"), (101, 196, "101+")):
        c = dis([p for p in ctl if lo <= p[0]["a"] * p[0]["b"] <= hi])
        s = dis([p for p in test if lo <= p[0]["a"] * p[0]["b"] <= hi])
        rows.append((lab, c, s))
        if c[1] >= 15 and s[1] >= 15:
            pc += c[0]; pn += c[1]; tc += s[0]; tn += s[1]
    pp = (tc + pc) / (tn + pn)
    se = math.sqrt(pp * (1 - pp) * (1 / tn + 1 / pn))
    z = (tc / tn - pc / pn) / se
    pz = math.erfc(abs(z) / math.sqrt(2))

    html = f"""<title>reasoning-grid &mdash; does A&times;B differ from B&times;A?</title>
<style>{CSS}</style>
<div class="wrap">
  <header>
    <p class="eyebrow">reasoning-grid &middot; Qwen3-4B &middot; {n} products, each run in
      both orders</p>
    <h1>For a language model, is 3&times;12 the same problem as 12&times;3?</h1>
    <p class="lede">They are different token sequences and invite different procedures,
      so there is a real question here. Testing it needs <em>the same product</em>
      presented both ways &mdash; comparing grid cell (a,b) against cell (b,a) compares
      different numbers and answers nothing.</p>
  </header>

  <div class="stats">
    <div class="stat"><div class="k">A&times;B correct</div>
      <div class="v">{(t['both']+n01)/n:.1%}</div></div>
    <div class="stat"><div class="k">B&times;A correct</div>
      <div class="v">{(t['both']+n10)/n:.1%}</div></div>
    <div class="stat"><div class="k">McNemar p</div><div class="v">{min(pv,1):.2f}</div></div>
    <div class="stat"><div class="k">verdict</div>
      <div class="v" style="font-size:19px">no effect</div></div>
  </div>

  <section>
    <h2>Does either order win?</h2>
    <p class="note" style="margin-bottom:12px">Each of the {n} products was run once as
      A&times;B and once as B&times;A. If order mattered, the two middle segments would
      differ.</p>
    <figure>{mosaic(t, n)}</figure>
    <p class="note" style="margin-top:14px"><strong>No.</strong> {n01} problems were
      solved only in the original order, {n10} only reversed &mdash; McNemar
      &chi;&sup2; = {chi:.2f}, exact p = {min(pv,1):.3f}. Neither presentation is better.</p>
  </section>

  <hr class="hr"/>

  <section>
    <h2>Does swapping change <em>which</em> problems it solves?</h2>
    <p class="note" style="margin-bottom:12px">Order could still matter without favouring
      either direction, by changing which problems land. That would show as more
      disagreement than simply asking twice produces &mdash; so it needs a control: the
      same problem, the <em>same</em> order, two independent draws.</p>
    <figure>{bands(rows)}</figure>
    <div class="legend">
      <span><span class="sw" style="background:var(--ctl);border-radius:50%"></span>
        control &mdash; same order, asked twice</span>
      <span><span class="sw" style="background:var(--b);border-radius:50%"></span>
        swapped order</span>
    </div>
    <p class="note" style="margin-top:14px"><strong>Also no.</strong> Matched on problem
      size the two are {tc/tn:.0%} against {pc/pn:.0%}, z = {z:.2f}, p = {pz:.3f}. At
      N=61&ndash;100, where both have plenty of pairs, they are 42% and 41%.</p>
    <p class="note" style="margin-top:12px">Matching matters more than it sounds. Compared
      without it, swapped ran 36% against the control's 21% and looked like a strong
      effect &mdash; but the control pairs happened to be easier problems, and harder
      problems disagree more however they are asked. The apparent finding was difficulty
      wearing a costume.</p>
  </section>

  <hr class="hr"/>

  <section>
    <h2>What the disagreement actually is</h2>
    <p class="note">Around a third of these products get a different verdict on a second
      attempt. That is not operand order &mdash; it is temperature 0.7. Near the boundary
      the model's answer is a coin weighted by problem size, and asking twice gets two
      draws. It is the same fact the convergence chart shows from the other side, and it
      is why a cell needs many trials before its number means anything.</p>
  </section>
</div>
"""
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    open(args.out, "w").write(html)
    print(f"wrote {args.out}")
    print(f"  {n} paired products: both {t['both']}, only AxB {n01}, only BxA {n10}, "
          f"neither {t['neither']}")
    print(f"  McNemar chi2={chi:.2f} exact p={min(pv,1):.3f}")
    print(f"  disagreement matched on N: swapped {tc}/{tn}={tc/tn:.0%} vs "
          f"control {pc}/{pn}={pc/pn:.0%}, z={z:.2f} p={pz:.3f}")


if __name__ == "__main__":
    main()
