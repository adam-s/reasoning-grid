"""The surface assembling itself, one trial at a time.

Every static chart here shows the finished measurement. None of them shows the
thing that most needs showing: how much of the shape was already there after two
trials, and how long the rest took to settle. Scrubbing through trial count
answers that directly -- the terrain heaves early and then stops moving, and
where it stops moving is where the number can be trusted.

  .venv/bin/python probe/render_animation.py -o derived/animation.html

Same isometric projection and painter's algorithm as the static surface, moved
into inline JavaScript so the geometry can be recomputed per frame. No library,
no CDN -- the page carries a small array of pass/fail per cell and rebuilds 169
quads on each redraw, which is nothing for a browser.

A cell with n=3 stops updating at trial 3 while a cell with n=12 keeps going.
That is honest rather than tidy: the adaptive allocation really did spend more
on uncertain cells, and the animation shows which parts of the surface froze
early because nobody was still measuring them.
"""

import argparse
import collections
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reduce_grid import load  # noqa: E402

PAGE = """<title>carrychain &mdash; watching the surface settle</title>
<style>
:root{ --paper:#f5f7fa; --ink:#111621; --muted:#5a6478; --line:#d9dfe9; --card:#fff;
       --ramp-lo:#e6ebf3; --ramp-hi:#1b2a5e; --signal:#c0761a; }
@media (prefers-color-scheme:dark){
  :root{ --paper:#0e1118; --ink:#e8ecf4; --muted:#8b95a9; --line:#232a38; --card:#141926;
         --ramp-lo:#191f2c; --ramp-hi:#8fa9ee; --signal:#e0a048; } }
:root[data-theme="dark"]{ --paper:#0e1118; --ink:#e8ecf4; --muted:#8b95a9; --line:#232a38;
  --card:#141926; --ramp-lo:#191f2c; --ramp-hi:#8fa9ee; --signal:#e0a048; }
:root[data-theme="light"]{ --paper:#f5f7fa; --ink:#111621; --muted:#5a6478; --line:#d9dfe9;
  --card:#fff; --ramp-lo:#e6ebf3; --ramp-hi:#1b2a5e; --signal:#c0761a; }
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
.stage{background:var(--card);border:1px solid var(--line);border-radius:4px;
  padding:18px 18px 8px}
svg{display:block;width:100%;height:auto}
.controls{display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-top:6px;
  font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:12px;color:var(--muted)}
button{font:inherit;font-size:13px;padding:7px 16px;border-radius:3px;cursor:pointer;
  background:var(--ramp-hi);color:var(--paper);border:1px solid var(--ramp-hi)}
button:hover{opacity:.88}
button:focus-visible,input:focus-visible{outline:2px solid var(--signal);outline-offset:2px}
input[type=range]{flex:1;min-width:200px;accent-color:var(--ramp-hi)}
.readout{font-variant-numeric:tabular-nums;color:var(--ink);min-width:150px}
.hr{height:1px;background:var(--line);border:0;margin:0}
@media (prefers-reduced-motion:reduce){ button.auto{display:none} }
</style>
<div class="wrap">
  <header>
    <p class="eyebrow">carrychain &middot; __MODEL__ &middot; __CELLS__ cells &middot;
      temp 0.7 &middot; thinking on</p>
    <h1>Watching the surface settle</h1>
    <p class="lede">x is the digits of A, y the digits of B, height is the share of runs
      returning the exactly correct product. Drag the slider to add trials one at a time
      and watch the terrain stop moving.</p>
  </header>

  <div class="stage">
    <svg id="surf" viewBox="__VB__" role="img"
         aria-label="reliability surface, redrawn as trials accumulate"></svg>
    <div class="controls">
      <button id="play" class="auto" type="button">Play</button>
      <input id="t" type="range" min="1" max="__MAXN__" value="__MAXN__"
             aria-label="trials per cell"/>
      <span class="readout" id="ro"></span>
    </div>
  </div>

  <hr class="hr"/>
  <section>
    <h2>What to watch for</h2>
    <p class="note">At one trial per cell the surface is already roughly the right shape
      &mdash; high at the back, low at the front &mdash; but every cell is 0% or 100%, so
      it reads as a cliff rather than a slope. The middle fills in over the next few
      trials, and by about eight the terrain stops changing shape and only jitters.</p>
    <p class="note" style="margin-top:12px"><strong>Cells run out of trials at different
      points, and each one keeps its last value rather than being dropped.</strong> A cell
      with __MINN__ trials freezes early; one with __MAXN__ keeps moving to the end. So a
      late frame is not a uniform snapshot &mdash; it is every cell showing everything
      that was ever measured for it, which is also how the grid itself is scored. Trimming
      every cell to a common count would throw away most of the data to buy a tidiness
      nothing depends on.</p>
    <p class="note" style="margin-top:12px">The counter tracks how many cells are still
      moving. It falls fast at first, because the sampling plan gave saturated corners
      only enough runs to confirm a bound. What is still shifting near the end is the
      transition band &mdash; exactly where the budget went, and exactly where the answer
      was genuinely uncertain.</p>
  </section>
</div>
<script>
(function(){
  var D = __DATA__, DIM = __DIM__, ZS = 9.0, S = 46;
  var R2 = Math.SQRT2, R6 = Math.sqrt(6);
  var svg = document.getElementById('surf'), rng = document.getElementById('t'),
      ro = document.getElementById('ro'), play = document.getElementById('play');
  var NS = 'http://www.w3.org/2000/svg';

  function proj(x, y, z){ return [(x - y) / R2, (x + y - 2 * z * ZS) / R6]; }

  function rateAt(cell, t){
    var o = D[cell]; if(!o) return null;
    var m = Math.min(t, o.length), k = 0;
    for(var i = 0; i < m; i++) k += o[i];
    return {p: k / m, n: m, full: o.length};
  }

  function draw(t){
    while(svg.firstChild) svg.removeChild(svg.firstChild);
    var quads = [], moved = 0, frozen = 0;
    for(var a = 1; a < DIM; a++){
      for(var b = 1; b < DIM; b++){
        var pts = [[a,b],[a+1,b],[a+1,b+1],[a,b+1]], zz = [], ok = true;
        for(var i = 0; i < 4; i++){
          var r = rateAt(pts[i][0] + 'x' + pts[i][1], t);
          if(!r){ ok = false; break; }
          zz.push(r.p);
        }
        if(!ok) continue;
        var xy = [], depth = 0, mean = 0;
        for(var j = 0; j < 4; j++){
          xy.push(proj(pts[j][0], pts[j][1], zz[j]));
          depth += pts[j][0] + pts[j][1] + zz[j] * ZS;
          mean += zz[j];
        }
        quads.push({d: depth / 4, xy: xy, m: mean / 4});
      }
    }
    quads.sort(function(p, q){ return p.d - q.d; });
    // floor grid, drawn first so the surface sits on it
    for(var g = 1; g <= DIM; g++){
      [[[g,1],[g,DIM]], [[1,g],[DIM,g]]].forEach(function(seg){
        var p0 = proj(seg[0][0], seg[0][1], 0), p1 = proj(seg[1][0], seg[1][1], 0);
        var ln = document.createElementNS(NS, 'line');
        ln.setAttribute('x1', (p0[0]*S).toFixed(1)); ln.setAttribute('y1', (p0[1]*S).toFixed(1));
        ln.setAttribute('x2', (p1[0]*S).toFixed(1)); ln.setAttribute('y2', (p1[1]*S).toFixed(1));
        ln.setAttribute('stroke', 'var(--line)'); ln.setAttribute('stroke-width', '.6');
        ln.setAttribute('opacity', '.5');
        svg.appendChild(ln);
      });
    }
    quads.forEach(function(q){
      var pg = document.createElementNS(NS, 'polygon');
      pg.setAttribute('points', q.xy.map(function(p){
        return (p[0]*S).toFixed(1) + ',' + (p[1]*S).toFixed(1); }).join(' '));
      pg.setAttribute('style', 'fill:color-mix(in oklab, var(--ramp-hi) ' +
        (q.m*100).toFixed(1) + '%, var(--ramp-lo))');
      pg.setAttribute('stroke', 'var(--paper)'); pg.setAttribute('stroke-width', '.5');
      pg.setAttribute('stroke-linejoin', 'round');
      svg.appendChild(pg);
    });
    var still = 0, total = 0;
    for(var c in D){ total++; if(D[c].length > t) still++; }
    ro.textContent = t + ' trial' + (t === 1 ? '' : 's') + ' per cell — ' +
                     still + ' of ' + total + ' still measuring';
  }

  var timer = null;
  function stop(){ clearInterval(timer); timer = null; play.textContent = 'Play'; }
  play.addEventListener('click', function(){
    if(timer){ stop(); return; }
    if(+rng.value >= +rng.max) rng.value = 1;
    play.textContent = 'Pause';
    timer = setInterval(function(){
      var v = +rng.value + 1;
      if(v > +rng.max){ stop(); return; }
      rng.value = v; draw(v);
    }, 420);
  });
  rng.addEventListener('input', function(){ stop(); draw(+rng.value); });
  draw(+rng.value);
})();
</script>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs")
    ap.add_argument("--model", default="Qwen/Qwen3-4B")
    ap.add_argument("--glob", default="10-grid12-qwen-*,11-ext14-qwen-*")
    ap.add_argument("-o", "--out", default="derived/animation.html")
    args = ap.parse_args()

    # Pool every record at matching temperature, top_p and thinking, regardless
    # of which sweep wrote it. The context ceiling is allowed to differ ONLY
    # where it provably could not have mattered: if some records in a cell ran
    # under a smaller ceiling, they are kept only when no record in that cell
    # came near it. A generation that finished in 5k tokens is the same
    # measurement whether the cap was 32k or 40k; one that ran to 30k is not.
    # This is worth the care -- it adds 22% more trials, and the small cells
    # that gain most are the ones with the longest histories on disk.
    SAFE = 0.80
    recs = []
    for f in sorted(glob.glob(os.path.join(args.runs, "*.jsonl"))):
        for r in load([f], model=args.model, temperature=0.7):
            if r.get("top_p") != 1.0 or r.get("thinking_observed") is not True:
                continue
            recs.append(r)
    by = collections.defaultdict(list)
    for r in recs:
        by[(r["a"], r["b"])].append(r)
    dropped = 0
    for k, rs in list(by.items()):
        ceils = {r.get("engine_max_len") for r in rs if r.get("engine_max_len")}
        if len(ceils) > 1:
            mn = min(ceils)
            if any(r["completion_tokens"] > SAFE * mn for r in rs):
                keep = [r for r in rs if r.get("engine_max_len") == max(ceils)]
                dropped += len(rs) - len(keep)
                by[k] = keep

    data, dim, maxn = {}, 0, 0
    for (a, b), rs in by.items():
        rs = sorted(rs, key=lambda r: (r["instance_id"], r.get("sweep_id", "")))
        data[f"{a}x{b}"] = [1 if r["correct"] else 0 for r in rs]
        dim = max(dim, a, b)
        maxn = max(maxn, len(rs))

    # viewBox from the extremes of the projection, with room for the floor
    import math
    R2, R6, ZS, S = math.sqrt(2), math.sqrt(6), 9.0, 46
    xs, ys = [], []
    for a in (1, dim):
        for b in (1, dim):
            for z in (0.0, 1.0):
                xs.append((a - b) / R2)
                ys.append((a + b - 2 * z * ZS) / R6)
    pad = 1.0
    minx, maxx = min(xs) - pad, max(xs) + pad
    miny, maxy = min(ys) - pad, max(ys) + pad
    vb = (f"{minx*S:.1f} {miny*S:.1f} {(maxx-minx)*S:.1f} {(maxy-miny)*S:.1f}")

    lens = [len(v) for v in data.values()]
    html = (PAGE.replace("__DATA__", json.dumps(data, separators=(",", ":")))
                .replace("__MINN__", str(min(lens)))
                .replace("__DIM__", str(dim))
                .replace("__MAXN__", str(maxn))
                .replace("__CELLS__", str(len(data)))
                .replace("__MODEL__", args.model.split("/")[-1])
                .replace("__VB__", vb))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    open(args.out, "w").write(html)
    print(f"wrote {args.out}")
    print(f"  {len(data)} cells, {dim}x{dim}, up to {maxn} trials, "
          f"{sum(len(v) for v in data.values()):,} outcomes embedded")
    print(f"  {dropped} records dropped: a smaller ceiling could have bound them")


if __name__ == "__main__":
    main()
