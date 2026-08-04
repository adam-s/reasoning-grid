"""Greedy decoding against sampling, on the same hard problems.

Temperature 0 is the obvious thing to try when a model keeps changing its
answer: remove the randomness and the answer stops moving. This tests whether
that buys anything, on 100 problems hard enough that the model is wrong most of
the time either way.

  .venv/bin/python probe/render_temp0.py -o derived/temp0.html

The test needs a control, and it is the same control the operand-order
experiment needed. Two runs of the same problem will disagree some of the time
purely because the model is unreliable there -- so "temperature 0 changed the
answer on 27% of problems" means nothing until you know how often simply asking
twice changes it. Here that baseline is 37%, which is higher.

Written after two predictions failed. The page says so, because a prediction
that missed is the cheapest information in the run.
"""

import argparse
import collections
import glob
import math
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reduce_grid import load, wilson  # noqa: E402

CSS = """
:root{ --paper:#f7f6f3; --ink:#1a1a1a; --muted:#767676; --line:#e2e2e0; --card:#fff;
       --cold:#2a78d6; --hot:#eb6834; --both:#3f4a5a; --none:#b9c0cc; }
@media (prefers-color-scheme:dark){
  :root{ --paper:#12130f; --ink:#eceae4; --muted:#8f8f88; --line:#2a2b26; --card:#191a15;
         --cold:#3987e5; --hot:#d95926; --both:#9aa6b8; --none:#3b4350; } }
:root[data-theme="dark"]{ --paper:#12130f; --ink:#eceae4; --muted:#8f8f88; --line:#2a2b26;
  --card:#191a15; --cold:#3987e5; --hot:#d95926; --both:#9aa6b8; --none:#3b4350; }
:root[data-theme="light"]{ --paper:#f7f6f3; --ink:#1a1a1a; --muted:#767676; --line:#e2e2e0;
  --card:#fff; --cold:#2a78d6; --hot:#eb6834; --both:#3f4a5a; --none:#b9c0cc; }
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
.lede{max-width:63ch;color:var(--muted);font-size:16.5px;margin:0}
.note{max-width:66ch;color:var(--muted);font-size:13.5px;margin:0}
figure{margin:0;background:var(--card);border:1px solid var(--line);border-radius:4px;
  padding:22px 20px 14px;overflow-x:auto}
svg{display:block;width:100%;height:auto}
text{font-family:ui-monospace,"SF Mono",Menlo,monospace;fill:var(--muted)}
.big{font-size:15px}.lab{font-size:12px}.tick{font-size:11px}
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
.legend{display:flex;gap:16px;flex-wrap:wrap;font-family:ui-monospace,"SF Mono",Menlo,monospace;
  font-size:11px;color:var(--muted);align-items:center;margin-top:12px}
.sw{display:inline-block;width:11px;height:11px;vertical-align:-1px;margin-right:5px}
.pred{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--hot);
  border-radius:3px;padding:16px 18px}
.hr{height:1px;background:var(--line);border:0;margin:0}
"""


def mosaic(t, n, W=880, H=170):
    segs = [(t["both"], "var(--both)", "correct both ways"),
            (t["only07"], "var(--hot)", "only at T=0.7"),
            (t["only00"], "var(--cold)", "only at T=0"),
            (t["neither"], "var(--none)", "wrong both ways")]
    L, T = 10, 24
    pw = W - 2 * L
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="paired outcomes at the two '
         f'temperatures">']
    x = L
    for v, col, lab in segs:
        w = pw * v / n
        o.append(f'<rect x="{x:.1f}" y="{T}" width="{w:.1f}" height="52" fill="{col}">'
                 f'<title>{lab}: {v} ({v/n:.0%})</title></rect>')
        if w > 70:
            o.append(f'<text class="big" x="{x+w/2:.1f}" y="{T+32:.1f}" '
                     f'text-anchor="middle" fill="var(--paper)">{v}</text>')
            o.append(f'<text class="lab" x="{x+w/2:.1f}" y="{T+72:.1f}" '
                     f'text-anchor="middle">{lab}</text>')
        x += w
    x0 = L + pw * t["both"] / n
    x1 = x0 + pw * (t["only07"] + t["only00"]) / n
    o.append(f'<line class="bar" x1="{x0:.1f}" y1="{T-10}" x2="{x1:.1f}" y2="{T-10}" '
             f'stroke="var(--muted)"/>')
    o.append(f'<text class="tick" x="{(x0+x1)/2:.1f}" y="{T-16}" text-anchor="middle">'
             f'{t["only07"]+t["only00"]} problems changed verdict</text>')
    o.append(f'<text class="lab" x="{L}" y="{H-8}">{n} problems, run once at each '
             f'temperature</text>')
    o.append("</svg>")
    return "\n".join(o)


def compare(rows, W=880, H=290):
    L, R, T, B = 66, 20, 24, 74
    pw, ph = W - L - R, H - T - B
    step = pw / len(rows)

    def X(i):
        return L + step * (i + 0.5)

    def Y(v):
        return T + ph * (1 - v / 0.6)

    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="how often the verdict '
         f'changes, greedy versus resampling">']
    for v in (0, .15, .30, .45, .60):
        o.append(f'<line class="grid" x1="{L}" y1="{Y(v):.1f}" x2="{L+pw}" y2="{Y(v):.1f}"/>')
        o.append(f'<text class="lab" x="{L-10}" y="{Y(v)+4:.1f}" text-anchor="end">'
                 f'{v*100:.0f}%</text>')
    o.append(f'<line class="axis" x1="{L}" y1="{T}" x2="{L}" y2="{T+ph}"/>')
    o.append(f'<line class="axis" x1="{L}" y1="{T+ph}" x2="{L+pw}" y2="{T+ph}"/>')
    for i, (lab, k, n, col, sub) in enumerate(rows):
        p, lo, hi = wilson(k, n)
        x = X(i)
        o.append(f'<line class="bar" x1="{x:.1f}" y1="{Y(lo):.1f}" x2="{x:.1f}" '
                 f'y2="{Y(hi):.1f}" stroke="{col}"/>')
        for e in (lo, hi):
            o.append(f'<line class="bar" x1="{x-6:.1f}" y1="{Y(e):.1f}" '
                     f'x2="{x+6:.1f}" y2="{Y(e):.1f}" stroke="{col}"/>')
        o.append(f'<circle cx="{x:.1f}" cy="{Y(p):.1f}" r="8" fill="{col}">'
                 f'<title>{lab}: {k}/{n} = {p:.0%} [{lo:.0%}, {hi:.0%}]</title></circle>')
        o.append(f'<text class="big" x="{x+16:.1f}" y="{Y(p)+5:.1f}" fill="var(--ink)">'
                 f'{p:.0%}</text>')
        o.append(f'<text class="lab" x="{x:.1f}" y="{T+ph+24:.1f}" '
                 f'text-anchor="middle">{lab}</text>')
        o.append(f'<text class="tick" x="{x:.1f}" y="{T+ph+42:.1f}" '
                 f'text-anchor="middle">{sub}</text>')
        o.append(f'<text class="tick" x="{x:.1f}" y="{T+ph+58:.1f}" '
                 f'text-anchor="middle">{k}/{n}</text>')
    o.append(f'<text class="lab" x="{-(T+ph/2):.1f}" y="15" text-anchor="middle" '
             f'transform="rotate(-90)">verdict changed</text>')
    o.append("</svg>")
    return "\n".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs")
    ap.add_argument("-o", "--out", default="derived/temp0.html")
    args = ap.parse_args()
    M = "Qwen/Qwen3-4B"

    def L(pat, temp):
        return load(sorted(glob.glob(os.path.join(args.runs, pat))), model=M, temperature=temp)

    T0 = load(sorted(glob.glob(os.path.join(args.runs, "14-temp0-qwen-*.jsonl"))),
              temperature=0.0)
    T7 = L("10-grid12-qwen-*.jsonl", 0.7) + L("11-ext14-qwen-*.jsonl", 0.7)
    d7 = {r["instance_uid"]: r for r in T7}
    pairs = [(d7[r["instance_uid"]], r) for r in T0 if r["instance_uid"] in d7]
    n = len(pairs)

    t = collections.Counter()
    for a, b in pairs:
        t["both" if a["correct"] and b["correct"] else
          "only07" if a["correct"] else
          "only00" if b["correct"] else "neither"] += 1
    n01, n10 = t["only07"], t["only00"]
    disc = n01 + n10
    chi = (abs(n01 - n10) - 1) ** 2 / disc if disc else 0
    pv = (sum(math.comb(disc, i) for i in range(min(n01, n10) + 1)) * 2 / 2 ** disc) \
        if disc else 1.0

    A = L("07-grid12-qwen-*.jsonl", 0.7)
    B = L("10-grid12-qwen-*.jsonl", 0.7)
    dA, dB = {r["instance_uid"]: r for r in A}, {r["instance_uid"]: r for r in B}
    ctl = [(dA[u], dB[u]) for u in set(dA) & set(dB)
           if dA[u]["a"] * dA[u]["b"] >= 56]
    cf = sum(1 for a, b in ctl if a["correct"] != b["correct"])

    pool = (disc + cf) / (n + len(ctl))
    se = math.sqrt(pool * (1 - pool) * (1 / n + 1 / len(ctl)))
    z = (disc / n - cf / len(ctl)) / se
    pz = math.erfc(abs(z) / math.sqrt(2))

    p7 = (t["both"] + n01) / n
    p0 = (t["both"] + n10) / n
    tok7 = statistics.mean(a["completion_tokens"] for a, _ in pairs)
    tok0 = statistics.mean(b["completion_tokens"] for _, b in pairs)
    W = re.compile(r"\bwait\b", re.I)
    w7 = statistics.median([len(W.findall(a["raw_text"])) for a, _ in pairs if not a["correct"]])
    w0 = statistics.median([len(W.findall(b["raw_text"])) for _, b in pairs if not b["correct"]])

    sd7 = statistics.stdev(a["completion_tokens"] for a, _ in pairs)
    sd0 = statistics.stdev(b["completion_tokens"] for _, b in pairs)
    g0 = sum(1 for _, b in pairs if b["finish_reason"] == "length")
    g7 = sum(1 for a, _ in pairs if a["finish_reason"] == "length")

    rows = [("temperature 0", disc, n, "var(--cold)", "vs T=0.7"),
            ("asked twice", cf, len(ctl), "var(--hot)", "T=0.7 vs T=0.7")]

    html = f"""<title>reasoning-grid &mdash; does greedy decoding help?</title>
<style>{CSS}</style>
<div class="wrap">
  <header>
    <p class="eyebrow">reasoning-grid &middot; Qwen3-4B &middot; {n} hard problems &middot;
      reasoning on &middot; run once at each temperature</p>
    <h1>Turning the randomness off changes the answer, but not for the better</h1>
    <p class="lede">If a model keeps changing its mind, the obvious fix is to stop it
      sampling. These are {n} problems hard enough that it is wrong most of the time
      either way, each run once at temperature 0.7 and once at temperature 0.</p>
  </header>

  <div class="stats">
    <div class="stat"><div class="k">at T=0.7</div><div class="v">{p7:.0%}</div></div>
    <div class="stat"><div class="k">at T=0</div><div class="v">{p0:.0%}</div></div>
    <div class="stat"><div class="k">McNemar p</div><div class="v">{min(pv,1):.2f}</div></div>
    <div class="stat"><div class="k">tokens at T=0</div>
      <div class="v">{tok0/tok7:.0%}</div></div>
  </div>

  <section>
    <h2>Neither temperature is better</h2>
    <figure>{mosaic(t, n)}</figure>
    <p class="note" style="margin-top:14px">{n01} problems were solved only at 0.7,
      {n10} only at 0 &mdash; McNemar &chi;&sup2; = {chi:.2f}, exact p = {min(pv,1):.3f}.
      As close to a dead heat as {n} problems can produce.</p>
  </section>

  <hr class="hr"/>

  <section>
    <h2>But {disc} problems changed verdict &mdash; is that the temperature?</h2>
    <p class="note" style="margin-bottom:12px">{disc/n:.0%} of these problems came out
      differently. That sounds like an effect until you ask how often the model changes
      its answer when you simply ask it the same question twice.</p>
    <figure>{compare(rows)}</figure>
    <div class="legend">
      <span><span class="sw" style="background:var(--cold)"></span>greedy vs sampling</span>
      <span><span class="sw" style="background:var(--hot)"></span>sampling vs itself,
        same problems, matched difficulty</span>
    </div>
    <p class="note" style="margin-top:14px"><strong>No.</strong> Asking twice at the same
      temperature changes the verdict {cf/len(ctl):.0%} of the time &mdash; more often
      than switching to greedy does, and the difference is not significant
      (z = {abs(z):.2f}, p = {pz:.3f}). Turning the randomness off is
      statistically indistinguishable from asking again.</p>
  </section>

  <hr class="hr"/>

  <section>
    <h2>Where the extra tokens went: it gets stuck</h2>
    <p class="note">Temperature 0 spent <strong>{tok0/tok7-1:.0%} more tokens</strong> for
      the same score, and the spread widened too &mdash; a standard deviation of
      {sd0:,.0f} tokens against {sd7:,.0f}. Both come from one thing.</p>
    <p class="note" style="margin-top:12px"><strong>{g0} of {n} runs at temperature 0 used
      up the entire context without answering, against {g7} at 0.7.</strong> Twenty of
      those {g0} end in a plain repetition loop &mdash; the same line, over and over, until
      the room runs out:</p>
    <pre style="overflow-x:auto;background:var(--card);border:1px solid var(--line);
      border-radius:3px;padding:14px 16px;font-family:ui-monospace,Menlo,monospace;
      font-size:11.5px;color:var(--muted);line-height:1.5;margin:12px 0 0"><code>...Let me add 42,177,834,871,396 to 31,633,376,153,547,000:
   Let me add 42,177,834,871,396 to 31,633,376,153,547,000:
   Let me add 42,177,834,871,396 to 31,633,376,153,547,000: ...</code></pre>
    <p class="note" style="margin-top:14px">The reason is the whole point of greedy
      decoding. Each next token is a fixed function of everything before it, so once the
      model enters a repeating state <strong>it cannot leave</strong> &mdash; the thing
      that would break the loop is exactly the randomness that was switched off. At 0.7 a
      sampled token eventually differs and the model escapes, which is why only {g7} in
      {n} grind there.</p>
    <p class="note" style="margin-top:12px">So the randomness is not just noise to be
      cleaned up. It is what stops the model getting stuck.</p>
  </section>

  <hr class="hr"/>

  <div class="pred">
    <p class="note" style="margin:0"><strong>Two predictions, written before the run, both
      wrong.</strong> Greedy decoding was going to help slightly by avoiding a derailing
      token &mdash; it did not ({p0:.0%} against {p7:.0%}). And self-correction was going
      to collapse, since redoing the same arithmetic deterministically cannot land
      anywhere new &mdash; instead the model backtracked a median of {w0:.0f} times on
      wrong answers against {w7:.0f}, and the failure took a form nothing in the plan
      anticipated: not worse answers, but no answer at all.</p>
  </div>
</div>
"""
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    open(args.out, "w").write(html)
    print(f"wrote {args.out}")
    print(f"  T=0.7 {p7:.0%}  T=0 {p0:.0%}  McNemar p={min(pv,1):.3f}")
    print(f"  changed verdict {disc}/{n} = {disc/n:.0%}; control {cf}/{len(ctl)} = "
          f"{cf/len(ctl):.0%}; z={z:.2f} p={pz:.3f}")
    print(f"  tokens {tok7:,.0f} -> {tok0:,.0f} ({tok0/tok7-1:+.0%})")
    print(f"  ran out of context: {g7} at T=0.7 -> {g0} at T=0")


if __name__ == "__main__":
    main()
