#!/usr/bin/env python3
"""Two surfaces, one for reasoning on and one for off, in the same 3D space.

The published version of this comparison collapses the grid onto one axis --
problem size N = a*b -- and plots two logistic curves. That hides where the
gap is. Two 14x14 sheets in one scene put the effect back on the grid: the
volume between them IS the answer, and it is not uniform.

    python probe/render_onoff_surface.py -o derived/onoff-surface.html

Design matches probe/build_surface.py's chart. Perspective projection with a
real camera (drag to orbit), and back-to-front ordering keyed on the GROUND
plane only -- for a heightfield that is exact, where sorting on a depth key
that mixes in height is only usually right. See
blog/src/lib/viz/surface/project.ts for the full argument.

Pairing is one run per problem per arm, so both sheets answer the same 1,566
problems exactly once. Using every run instead inflates the reasoning arm to
62.8%, because that arm was sampled more.
"""
import argparse
import collections
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reduce_grid import _parser  # noqa: E402

COND = dict(model="Qwen/Qwen3-4B", temperature=0.7, top_p=1.0)


def collect(runs="runs"):
    pa = _parser()
    first, cell = collections.defaultdict(dict), {}
    for f in sorted(glob.glob(os.path.join(runs, "*.jsonl"))):
        for line in open(f):
            if not line.strip():
                continue
            j = json.loads(line)
            if (j.get("model") != COND["model"] or j.get("temperature") != COND["temperature"]
                    or j.get("top_p") != COND["top_p"]):
                continue
            t = j.get("thinking_observed")
            if t not in (True, False):
                continue
            u = j.get("instance_uid")
            if not u:
                continue
            arm = "on" if t else "off"
            if arm in first[u]:
                continue
            cell[u] = (j["a"], j["b"])
            ans, _ = pa(j.get("raw_text") or "")
            first[u][arm] = ans is not None and str(ans) == str(j["truth"])

    paired = {u: v for u, v in first.items() if "on" in v and "off" in v}
    grid = collections.defaultdict(lambda: [0, 0, 0, 0])
    tab = collections.Counter()
    for u, v in paired.items():
        g = grid[cell[u]]
        g[0] += v["on"]; g[1] += 1; g[2] += v["off"]; g[3] += 1
        tab[(v["on"], v["off"])] += 1
    return paired, grid, tab


PAGE = """<title>carrychain &mdash; where reasoning earns its tokens</title>
<style>
:root{ --paper:#fdfcf9; --panel:#f7f5f0; --line:#e8e4dc; --line-2:#d8d2c4;
  --ink:#1a1a1a; --dim:#5a5a5a; --faint:#9a9a9a; --navy:#1f3a5f;
  --on-lo:#e8ecf3; --on-hi:#1b2a5e; --off:#c9853a; }
@media (prefers-color-scheme:dark){ :root{ --paper:#14161a; --panel:#1b1e24; --line:#2b303a;
  --line-2:#3a4150; --ink:#e9e6df; --dim:#a8a49b; --faint:#77736c; --navy:#8fb0dd;
  --on-lo:#1a2130; --on-hi:#96b0f0; --off:#e0a048; } }
:root[data-theme="dark"]{ --paper:#14161a; --panel:#1b1e24; --line:#2b303a; --line-2:#3a4150;
  --ink:#e9e6df; --dim:#a8a49b; --faint:#77736c; --navy:#8fb0dd;
  --on-lo:#1a2130; --on-hi:#96b0f0; --off:#e0a048; }
:root[data-theme="light"]{ --paper:#fdfcf9; --panel:#f7f5f0; --line:#e8e4dc; --line-2:#d8d2c4;
  --ink:#1a1a1a; --dim:#5a5a5a; --faint:#9a9a9a; --navy:#1f3a5f;
  --on-lo:#e8ecf3; --on-hi:#1b2a5e; --off:#c9853a; }
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
  font-size:17px;line-height:1.62}
.wrap{max-width:1000px;margin:0 auto;padding:52px 24px 90px}
.col{max-width:640px}
.eyebrow{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:11px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--faint);margin:0 0 10px}
h1{font-size:clamp(28px,4.2vw,42px);line-height:1.12;letter-spacing:-.015em;margin:0 0 16px;
  text-wrap:balance}
h2{font-family:system-ui,sans-serif;font-size:13px;font-weight:650;letter-spacing:.08em;
  text-transform:uppercase;color:var(--dim);margin:48px 0 14px;padding-bottom:7px;
  border-bottom:1px solid var(--line);max-width:920px}
p{margin:0 0 16px}
.lede{font-size:19.5px;line-height:1.55;color:var(--dim)}
strong{font-weight:650;color:var(--ink)}
.mono{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-variant-numeric:tabular-nums}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;
  background:var(--line);border:1px solid var(--line);border-radius:4px;overflow:hidden;
  margin:28px 0 4px;max-width:920px}
.stat{background:var(--panel);padding:15px 17px}
.stat .k{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:10.5px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--faint)}
.stat .v{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:24px;
  font-variant-numeric:tabular-nums;margin-top:3px}
figure{margin:26px 0 8px;max-width:920px}
figcaption{font-family:system-ui,sans-serif;font-size:13px;line-height:1.55;color:var(--faint);
  margin-top:12px}
.plot{position:relative;border:1px solid var(--line);border-radius:4px;background:var(--panel);
  overflow:hidden}
canvas{display:block;cursor:grab;touch-action:pan-y}
canvas:active{cursor:grabbing}
.hint{position:absolute;left:10px;bottom:7px;font-family:ui-monospace,monospace;font-size:9px;
  color:var(--faint);pointer-events:none}
.key{display:flex;gap:18px;flex-wrap:wrap;align-items:center;margin-top:12px;
  font-family:system-ui,sans-serif;font-size:12px;color:var(--dim)}
.sw{display:inline-block;width:22px;height:9px;border-radius:2px;vertical-align:-1px;
  margin-right:6px}
.foot{margin-top:56px;padding-top:18px;border-top:1px solid var(--line);
  font-family:system-ui,sans-serif;font-size:13px;line-height:1.6;color:var(--faint);
  max-width:920px}
</style>
<div class="wrap">
  <p class="eyebrow">carrychain &middot; Qwen3-4B &middot; __PROBS__ identical problems</p>
  <h1>Where reasoning earns its tokens</h1>
  <p class="lede col">Same model, same problems, same temperature. The only difference is
  whether the chat template lets it work before answering. The gap between these two
  sheets is what the thinking buys &mdash; and it is not spread evenly.</p>

  <div class="stats">
    <div class="stat"><div class="k">reasoning on</div><div class="v">__ON__</div></div>
    <div class="stat"><div class="k">reasoning off</div><div class="v">__OFF__</div></div>
    <div class="stat"><div class="k">on solves, off misses</div><div class="v">__ONLYON__</div></div>
    <div class="stat"><div class="k">off solves, on misses</div><div class="v">__ONLYOFF__</div></div>
  </div>

  <figure>
    <div class="plot"><canvas id="c"></canvas><span class="hint">drag to rotate</span></div>
    <div class="key">
      <span><span class="sw" style="background:linear-gradient(90deg,var(--on-lo),var(--on-hi))"></span>reasoning on</span>
      <span><span class="sw" style="background:var(--off);opacity:.85"></span>reasoning off</span>
      <span class="mono" style="color:var(--faint)">x, y = digits in each factor &middot; height = P(exactly correct)</span>
    </div>
    <figcaption>Two 14&times;14 sheets over the same grid. The lower one is the model
    answering immediately; the upper one is the same model allowed to think first. Drag to
    look along the ridge &mdash; the sheets meet at both ends and separate most in the
    middle.</figcaption>
  </figure>

  <h2>What the shape says</h2>
  <div class="col">
    <p>On easy problems the sheets touch: both arms get them right, and the thinking is
    spent confirming what the weights already knew. On the hardest problems they touch
    again at the floor &mdash; reasoning does not rescue a problem that is out of reach,
    it just fails more expensively.</p>
    <p>Everything reasoning buys is in the band between. That is the shape the
    one-dimensional version of this chart cannot show, because collapsing the grid onto
    <span class="mono">N = a&times;b</span> averages the ridge away.</p>
    <p>The asymmetry is the other half. Reasoning solves <strong>__ONLYON__</strong>
    problems that the immediate answer misses. The immediate answer solves
    <strong>__ONLYOFF__</strong> that reasoning misses &mdash; a ratio of about
    <strong>17 to 1</strong>. Thinking is close to free of downside here; it is only a
    question of whether the problem is in the band where it helps.</p>
  </div>

  <div class="foot">
    <p><strong>Method.</strong> Qwen3-4B, temperature 0.7, top_p 1.0, native context.
    __PROBS__ problems appear in both arms and each is counted once per arm, so both
    sheets answer the same questions the same number of times. Pooling every run instead
    lifts the reasoning arm to 62.8%, because that arm was sampled more &mdash; a real
    trap, since it looks like a bigger effect. Scoring is exact string match, re-derived
    from raw text. Cells with no data in an arm are dropped from both.</p>
    <p><strong>Rendering.</strong> Perspective projection with a real camera, so it
    orbits; back-to-front ordering keyed on the ground plane only, which is exact for a
    heightfield rather than the usual approximation. Regenerated by
    <span class="mono">probe/render_onoff_surface.py</span>.</p>
  </div>
</div>
<script>
const D = __DATA__, DIM = D.dim;
const cv = document.getElementById('c'), ctx = cv.getContext('2d');
let yaw = -0.62, pitch = 0.50, W = 0, H = 0;
const css = k => getComputedStyle(document.documentElement).getPropertyValue(k).trim();
const hex = h => [1,3,5].map(i => parseInt(h.slice(i,i+2),16));

function proj(x,y,z,cx,cy,fit){
  const cy_=Math.cos(yaw), sy=Math.sin(yaw), cp=Math.cos(pitch), sp=Math.sin(pitch);
  const x1=x*cy_-y*sy, y1=x*sy+y*cy_;
  const d=y1*cp-z*sp, vy=y1*sp+z*cp;
  const s=900/(900+d*26);
  return {sx:cx+x1*26*s*fit, sy:cy-vy*26*s*fit, d};
}
function rate(k,a,b){ const g=D.grid[a+'x'+b]; if(!g) return null;
  return k==='on' ? (g[1]?g[0]/g[1]:null) : (g[3]?g[2]/g[3]:null); }

function draw(){
  const dpr=Math.min(devicePixelRatio||1,2);
  if(cv.width!==Math.round(W*dpr)||cv.height!==Math.round(H*dpr)){
    cv.width=Math.round(W*dpr); cv.height=Math.round(H*dpr); }
  ctx.setTransform(dpr,0,0,dpr,0,0); ctx.clearRect(0,0,W,H);
  const mid=(DIM+1)/2, Z=5.2, PAD=54;
  let bx0=1e9,bx1=-1e9,by0=1e9,by1=-1e9;
  for(const a of [1,DIM]) for(const b of [1,DIM]) for(const z of [0,1]){
    const q=proj(a-mid,b-mid,z*Z,0,0,1);
    bx0=Math.min(bx0,q.sx);bx1=Math.max(bx1,q.sx);by0=Math.min(by0,q.sy);by1=Math.max(by1,q.sy); }
  const aw=Math.max(80,W-PAD*2), ah=Math.max(80,H-PAD*2);
  const fit=Math.min(aw/(bx1-bx0), ah/(by1-by0));
  const cx=PAD+aw/2-((bx0+bx1)/2)*fit, cy=PAD+ah/2-((by0+by1)/2)*fit;
  const P=(a,b,z)=>proj(a-mid,b-mid,z*Z,cx,cy,fit);

  // ground order: exact for a heightfield, height stays out of the key
  const n=DIM-1, ord=[];
  for(let i=0;i<n;i++) for(let j=0;j<n;j++)
    ord.push([i,j,(i+1-mid)*Math.sin(yaw)+(j+1-mid)*Math.cos(yaw)]);
  ord.sort((p,q)=>q[2]-p[2]);

  ctx.strokeStyle=css('--line-2'); ctx.lineWidth=1; ctx.globalAlpha=.55; ctx.beginPath();
  for(let g=1;g<=DIM;g++){ const a0=P(g,1,0),a1=P(g,DIM,0),b0=P(1,g,0),b1=P(DIM,g,0);
    ctx.moveTo(a0.sx,a0.sy);ctx.lineTo(a1.sx,a1.sy);
    ctx.moveTo(b0.sx,b0.sy);ctx.lineTo(b1.sx,b1.sy); }
  ctx.stroke(); ctx.globalAlpha=1;

  const lo=hex(css('--on-lo')), hi=hex(css('--on-hi')), off=css('--off');
  const ramp=t=>`rgb(${lo.map((v,i)=>Math.round(v+(hi[i]-v)*t)).join(',')})`;
  // both sheets share one traversal, so the far cell of BOTH is painted before
  // the near cell of either -- drawing one whole sheet then the other would put
  // the near half of the lower sheet under the far half of the upper one.
  for(const [i,j] of ord){
    const A=i+1,B=j+1;
    for(const arm of ['off','on']){
      const z=[rate(arm,A,B),rate(arm,A+1,B),rate(arm,A+1,B+1),rate(arm,A,B+1)];
      if(z.some(v=>v===null)) continue;
      const p=[P(A,B,z[0]),P(A+1,B,z[1]),P(A+1,B+1,z[2]),P(A,B+1,z[3])];
      ctx.beginPath(); ctx.moveTo(p[0].sx,p[0].sy);
      for(let q=1;q<4;q++) ctx.lineTo(p[q].sx,p[q].sy);
      ctx.closePath();
      const m=(z[0]+z[1]+z[2]+z[3])/4;
      if(arm==='on'){ ctx.fillStyle=ramp(m); ctx.globalAlpha=1; }
      else { ctx.fillStyle=off; ctx.globalAlpha=.85; }
      ctx.fill();
      ctx.globalAlpha=arm==='on'?.55:.35; ctx.strokeStyle=css('--paper');
      ctx.lineWidth=.6; ctx.stroke(); ctx.globalAlpha=1;
    }
  }
  // axes on the two edges nearest the camera, labels pushed outward
  const corners=[[1,1],[DIM,1],[1,DIM],[DIM,DIM]];
  let near=corners[0], nd=1e9;
  for(const c of corners){ const d=P(c[0],c[1],0).d; if(d<nd){nd=d;near=c;} }
  const ctr=P((1+DIM)/2,(1+DIM)/2,0);
  const out=(x,y,by)=>{const dx=x-ctr.sx,dy=y-ctr.sy,m=Math.hypot(dx,dy)||1;
    return [x+dx/m*by, y+dy/m*by];};
  ctx.textBaseline='middle'; ctx.textAlign='center';
  for(const ax of [{t:'digits in A',f:near[1],al:'a'},{t:'digits in B',f:near[0],al:'b'}]){
    const at=v=>ax.al==='a'?P(v,ax.f,0):P(ax.f,v,0);
    const e0=at(1), e1=at(DIM);
    ctx.strokeStyle=css('--dim'); ctx.globalAlpha=.5; ctx.lineWidth=1;
    ctx.beginPath(); ctx.moveTo(e0.sx,e0.sy); ctx.lineTo(e1.sx,e1.sy); ctx.stroke();
    ctx.globalAlpha=1; ctx.fillStyle=css('--dim');
    ctx.font='10px ui-monospace,monospace';
    for(let g=2;g<=DIM;g+=2){ const t0=at(g);
      const [tx,ty]=out(t0.sx,t0.sy,5), [lx,ly]=out(t0.sx,t0.sy,15);
      ctx.globalAlpha=.5; ctx.beginPath(); ctx.moveTo(t0.sx,t0.sy); ctx.lineTo(tx,ty); ctx.stroke();
      ctx.globalAlpha=1; ctx.fillText(String(g),lx,ly); }
    const m=at((1+DIM)/2), [ttx,tty]=out(m.sx,m.sy,34);
    let ang=Math.atan2(e1.sy-e0.sy,e1.sx-e0.sx);
    if(ang>Math.PI/2) ang-=Math.PI; if(ang<-Math.PI/2) ang+=Math.PI;
    ctx.save(); ctx.translate(ttx,tty); ctx.rotate(ang);
    ctx.font='600 11px system-ui,sans-serif'; ctx.fillStyle=css('--ink');
    ctx.fillText(ax.t,0,0); ctx.restore();
  }
}
const ro=new ResizeObserver(e=>{const r=e[0].contentRect;
  W=Math.max(280,Math.floor(r.width)); H=Math.max(320,Math.round(Math.min(520,r.width*.6)));
  cv.style.width=W+'px'; cv.style.height=H+'px'; draw();});
ro.observe(cv.parentElement);
let drag=false,lx=0,ly=0;
cv.addEventListener('pointerdown',e=>{drag=true;lx=e.clientX;ly=e.clientY;
  cv.setPointerCapture(e.pointerId);});
cv.addEventListener('pointermove',e=>{if(!drag)return;
  yaw+=(e.clientX-lx)*.008; pitch=Math.max(.08,Math.min(1.3,pitch+(e.clientY-ly)*.005));
  lx=e.clientX;ly=e.clientY;draw();});
const up=e=>{drag=false;};
cv.addEventListener('pointerup',up); cv.addEventListener('pointercancel',up);
new MutationObserver(draw).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
matchMedia('(prefers-color-scheme:dark)').addEventListener('change',draw);
</script>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs")
    ap.add_argument("-o", "--out", default="derived/onoff-surface.html")
    args = ap.parse_args()

    paired, grid, tab = collect(args.runs)
    kon = sum(g[0] for g in grid.values()); non = sum(g[1] for g in grid.values())
    kof = sum(g[2] for g in grid.values()); nof = sum(g[3] for g in grid.values())
    data = {"dim": max(max(c) for c in grid),
            "grid": {f"{a}x{b}": grid[(a, b)] for (a, b) in sorted(grid)}}

    html = (PAGE.replace("__DATA__", json.dumps(data, separators=(",", ":")))
                .replace("__PROBS__", f"{len(paired):,}")
                .replace("__ON__", f"{kon/non:.1%}")
                .replace("__OFF__", f"{kof/nof:.1%}")
                .replace("__ONLYON__", str(tab[(True, False)]))
                .replace("__ONLYOFF__", str(tab[(False, True)])))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    open(args.out, "w").write(html)

    print(f"wrote {args.out}  ({os.path.getsize(args.out)/1024:.0f} KB)")
    print(f"  {len(paired):,} paired problems, {len(grid)} cells")
    print(f"  on {kon}/{non} = {kon/non:.1%}   off {kof}/{nof} = {kof/nof:.1%}")
    print(f"  both {tab[(True, True)]}   on only {tab[(True, False)]}"
          f"   off only {tab[(False, True)]}   neither {tab[(False, False)]}")


if __name__ == "__main__":
    main()
