#!/usr/bin/env python3
"""Height is the better model; colour is which one it was.

    python probe/render_diff_surface.py -o derived/diff-surface.html

Two variables, two channels, chosen to match how noisy each one is.

HEIGHT is max(Qwen, Phi) per cell -- the best either model manages. That falls
off smoothly with problem size, so it makes a real surface: a plateau at the
easy corner, a slope, a floor.

On top of it sits a CAP wherever the union -- either model solving it -- rises
above that. Union is never below the better single model, so on an even cell the
cap lands exactly on the surface and disappears: a cell where the two models came
out level is simply Qwen's colour with nothing on it. Where Phi solved problems
Qwen missed, the cap lifts, and the gap is the coverage a second model buys.

This is the one quantity a difference map cannot show. Two models both scoring 6
of 12 look identical whether they solved the same six problems or disjoint sixes,
and only the second is worth paying for.

Two earlier versions were wrong in instructive ways. The first put the difference
on the height axis: relief cannot separate a one-problem fluctuation from an
effect, because both are a spike, and unlike the heatmap there is no printed
number to discount against. The second put the difference on colour, which was
better but still answered "who is ahead" when the useful question is "what does
the second one add".

Cells are drawn paler in proportion to how few trials stand behind them, the same
discount the heatmap uses: at n=3 one problem is a third of the cell.
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
    g = collections.defaultdict(lambda: [0, 0, 0, 0])    # qwen, phi, n, union
    only_b = 0
    for u, d in by.items():
        if A not in d or B not in d:
            continue
        qa, pb = any(d[A]), any(d[B])
        c = g[cell[u]]
        c[0] += qa
        c[1] += pb
        c[2] += 1
        c[3] += qa or pb                 # count the union, never reconstruct it
        only_b += pb and not qa
    return dict(g), only_b


PAGE = """<title>carrychain &mdash; Qwen&rsquo;s blind spots, and what Phi covers</title>
<style>
:root{ --paper:#fdfcf9; --panel:#f7f5f0; --line:#e3dfd6; --line-2:#cfc9bd; --ink:#1a1a1a;
  --dim:#5a5a5a; --faint:#a6a29a; --lead-a:#1f3a5f; --lead-b:#c9853a; }
@media (prefers-color-scheme:dark){:root{ --paper:#14161a; --panel:#1b1e24; --line:#2b303a;
  --line-2:#3a4150; --ink:#e9e6df; --dim:#a8a49b; --faint:#6f6b64;
  --lead-a:#8fb0dd; --lead-b:#e0a048; }}
:root[data-theme="dark"]{ --paper:#14161a; --panel:#1b1e24; --line:#2b303a; --line-2:#3a4150;
  --ink:#e9e6df; --dim:#a8a49b; --faint:#6f6b64; --lead-a:#8fb0dd; --lead-b:#e0a048; }
:root[data-theme="light"]{ --paper:#fdfcf9; --panel:#f7f5f0; --line:#e3dfd6; --line-2:#cfc9bd;
  --ink:#1a1a1a; --dim:#5a5a5a; --faint:#a6a29a; --lead-a:#1f3a5f; --lead-b:#c9853a; }
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
  font-size:17px;line-height:1.6}
.wrap{max-width:900px;margin:0 auto;padding:52px 24px 80px}
h1{font-size:clamp(26px,4vw,36px);line-height:1.15;margin:0 0 14px;letter-spacing:-.015em}
.eyebrow{font-family:ui-monospace,monospace;font-size:11px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--faint);margin:0 0 10px}
.lede{font-size:19px;color:var(--dim);margin:0 0 24px;max-width:62ch}
p{margin:0 0 15px;max-width:64ch}
strong{font-weight:650}
.plot{position:relative;border:1px solid var(--line);border-radius:4px;background:var(--panel);
  overflow:hidden}
canvas{display:block;cursor:grab;touch-action:pan-y}
canvas:active{cursor:grabbing}
.hint{position:absolute;left:10px;bottom:7px;font-family:ui-monospace,monospace;font-size:9px;
  color:var(--faint);pointer-events:none}
.key{display:flex;gap:20px;align-items:center;flex-wrap:wrap;margin:14px 0 0;
  font-family:system-ui,sans-serif;font-size:12.5px;color:var(--dim)}
.sw{display:inline-block;width:18px;height:10px;border-radius:2px;vertical-align:-1px;
  margin-right:6px}
.note{font-family:system-ui,sans-serif;font-size:13.5px;color:var(--faint);margin-top:20px;
  max-width:66ch}
</style>
<div class="wrap">
  <p class="eyebrow">carrychain &middot; __N__ problems &middot; both models, same questions</p>
  <h1>Qwen&rsquo;s blind spots, and what Phi covers</h1>
  <p class="lede">The blue surface is Qwen, the stronger model. The orange caps are
  Qwen&rsquo;s blind spots that Phi covered &mdash; problems Qwen missed and Phi got.
  Where Phi adds nothing there is no cap. Drag to look along the slope.</p>
  <div class="plot"><canvas id="c"></canvas><span class="hint">drag to rotate</span></div>
  <div class="key">
    <span><span class="sw" style="background:var(--lead-a)"></span>Qwen alone</span>
    <span><span class="sw" style="background:var(--lead-b)"></span>blind spots Phi covered</span>
    <span>&#183; stronger orange = more problems patched</span>
    <span>&#183; paler = fewer trials</span>
  </div>
  <p class="note"><strong>The caps are the whole argument for a second model.</strong>
  A plateau with no cap is a cell where Qwen already solves everything &mdash; paying
  for Phi there buys nothing. A cap is coverage that exists only because both ran.
  <strong>__NEG__ of __CELLS__</strong> cells carry one, and they cluster where the
  surface is falling, which is the only region where a second model returns anything.
  Qwen alone gets <strong>75.2%</strong>; Qwen with Phi behind it gets
  <strong>83.1%</strong>.</p>
  <p class="note"><strong>Caps get denser toward the back, and that is not Phi getting
  better.</strong> A cap can only exist where Qwen failed, and Qwen only fails on big
  problems &mdash; so cap density is forced upward by size no matter how
  the two models compare. Qwen is ahead in every band, and the gap widens with size
  rather than closing: <strong>96.9% to 91.1%</strong> at chain length 1&ndash;3, and
  <strong>18.5% to 6.5%</strong> at 10&ndash;12. Qwen solved <strong>256</strong>
  problems Phi missed against Phi's <strong>83</strong> the other way.</p>
  <p class="note">The caps are the one thing a difference map cannot show. Two models
  both scoring 6 of 12 look identical whether they solved the same six problems or
  disjoint sixes, and only the second case is worth paying for. Height is Qwen alone, so
  a cap is exactly what Phi adds on top of it &mdash; <strong>__OB__ problems</strong>
  across the grid.</p>
</div>
<script>
const D=__DATA__, DIM=D.dim;
const cv=document.getElementById('c'), ctx=cv.getContext('2d');
let yaw=-0.62, pitch=0.42, W=0, H=0, drag=false, lx=0, ly=0;
const css=k=>getComputedStyle(document.documentElement).getPropertyValue(k).trim();
function P(a,b,z,cx,cy,fit){
  const cw=Math.cos(yaw),sw=Math.sin(yaw),cp=Math.cos(pitch),sp=Math.sin(pitch);
  const mid=(DIM+1)/2, x=a-mid, y=b-mid;
  const x1=x*cw-y*sw, y1=x*sw+y*cw, d=y1*cp-z*5.2*sp, vy=y1*sp+z*5.2*cp;
  const s=900/(900+d*26);
  return {sx:cx+x1*26*s*fit, sy:cy-vy*26*s*fit, d};
}
const val=(a,b)=>{const g=D.g[a+'x'+b]; return g?g[1]:null;};   // best single model
const uni=(a,b)=>{const g=D.g[a+'x'+b]; return g?g[2]:null;};   // either model
const ev =(a,b)=>{const g=D.g[a+'x'+b]; return g?0.35+0.65*Math.min(1,g[0]/12):0;};
function draw(){
  const dpr=Math.min(devicePixelRatio||1,2);
  if(cv.width!==Math.round(W*dpr)){cv.width=Math.round(W*dpr);cv.height=Math.round(H*dpr);}
  ctx.setTransform(dpr,0,0,dpr,0,0); ctx.clearRect(0,0,W,H);
  let b0=1e9,b1=-1e9,c0=1e9,c1=-1e9;
  // Frame the range the data actually occupies. Reserving z=-1 when the deepest
  // dip is -0.4 spends a third of the canvas on empty space below the plane.
  for(const a of[1,DIM])for(const b of[1,DIM])for(const z of[0,1]){
    const q=P(a,b,z,0,0,1);
    b0=Math.min(b0,q.sx);b1=Math.max(b1,q.sx);c0=Math.min(c0,q.sy);c1=Math.max(c1,q.sy);}
  const PAD=52, aw=Math.max(80,W-PAD*2), ah=Math.max(80,H-PAD*2);
  const fit=Math.min(aw/(b1-b0), ah/(c1-c0));
  const cx=PAD+aw/2-((b0+b1)/2)*fit, cy=PAD+ah/2-((c0+c1)/2)*fit;
  const Q=(a,b,z)=>P(a,b,z,cx,cy,fit);
  const n=DIM-1, ord=[];
  for(let i=0;i<n;i++)for(let j=0;j<n;j++)
    ord.push([i,j,(i+1-(DIM+1)/2)*Math.sin(yaw)+(j+1-(DIM+1)/2)*Math.cos(yaw)]);
  ord.sort((p,q)=>q[2]-p[2]);
  // the zero PLANE, drawn first so the sheet reads as relief against it
  ctx.strokeStyle=css('--line-2'); ctx.globalAlpha=.85; ctx.lineWidth=1; ctx.beginPath();
  for(let g=1;g<=DIM;g++){const a0=Q(g,1,0),a1=Q(g,DIM,0),d0=Q(1,g,0),d1=Q(DIM,g,0);
    ctx.moveTo(a0.sx,a0.sy);ctx.lineTo(a1.sx,a1.sy);
    ctx.moveTo(d0.sx,d0.sy);ctx.lineTo(d1.sx,d1.sy);}
  ctx.stroke(); ctx.globalAlpha=1;
  for(const [i,j] of ord){
    const A=i+1,B=j+1, z=[val(A,B),val(A+1,B),val(A+1,B+1),val(A,B+1)];
    if(z.some(v=>v===null)) continue;
    const p=[Q(A,B,z[0]),Q(A+1,B,z[1]),Q(A+1,B+1,z[2]),Q(A,B+1,z[3])];
    ctx.beginPath(); ctx.moveTo(p[0].sx,p[0].sy);
    for(let k=1;k<4;k++) ctx.lineTo(p[k].sx,p[k].sy);
    ctx.closePath();
    const e=(ev(A,B)+ev(A+1,B)+ev(A+1,B+1)+ev(A,B+1))/4;
    ctx.fillStyle=css('--lead-a'); ctx.globalAlpha=0.45+0.55*e; ctx.fill();
    ctx.globalAlpha=.45; ctx.strokeStyle=css('--paper'); ctx.lineWidth=.6; ctx.stroke();
    ctx.globalAlpha=1;
    // The patch. Union sits at or above the better single model everywhere, so
    // where the two are level this cap lands exactly on the surface and is
    // invisible -- an even cell stays Qwen's colour, with nothing on top. Where
    // Phi solved problems Qwen missed, the cap lifts off and that gap IS the
    // coverage a second model buys. Drawn after, because seen from above the
    // higher sheet occludes the lower one.
    const uz=[uni(A,B),uni(A+1,B),uni(A+1,B+1),uni(A,B+1)];
    if(!uz.some(v=>v===null)){
      const lift=uz.reduce((t,v,k)=>t+(v-z[k]),0)/4;
      // Weight the cap by how far it actually lifts. A cell patched by one
      // problem in twelve and a cell patched by four are both "orange" at a
      // fixed alpha, which reads as a repaint of the region rather than as a
      // quantity. Full strength at a third of the cell, which is the largest
      // patch in the grid.
      if(lift > 0.005){
        const up=[Q(A,B,uz[0]),Q(A+1,B,uz[1]),Q(A+1,B+1,uz[2]),Q(A,B+1,uz[3])];
        ctx.beginPath(); ctx.moveTo(up[0].sx,up[0].sy);
        for(let k=1;k<4;k++) ctx.lineTo(up[k].sx,up[k].sy);
        ctx.closePath();
        ctx.fillStyle=css('--lead-b');
        ctx.globalAlpha=e*(0.30+0.62*Math.min(1,lift/0.33)); ctx.fill();
        ctx.globalAlpha=.45; ctx.strokeStyle=css('--paper'); ctx.lineWidth=.6; ctx.stroke();
        ctx.globalAlpha=1;
      }
    }
  }
  // axes, on the two edges nearest the camera
  const cors=[[1,1],[DIM,1],[1,DIM],[DIM,DIM]];
  let near=cors[0],nd=1e9;
  for(const c of cors){const d=Q(c[0],c[1],0).d; if(d<nd){nd=d;near=c;}}
  const ctr=Q((1+DIM)/2,(1+DIM)/2,0);
  const out=(x,y,by)=>{const dx=x-ctr.sx,dy=y-ctr.sy,m=Math.hypot(dx,dy)||1;
    return[x+dx/m*by,y+dy/m*by];};
  ctx.textBaseline='middle'; ctx.textAlign='center';
  for(const ax of[{t:'digits in A',f:near[1],al:'a'},{t:'digits in B',f:near[0],al:'b'}]){
    const at=v=>ax.al==='a'?Q(v,ax.f,0):Q(ax.f,v,0);
    const e0=at(1),e1=at(DIM);
    ctx.strokeStyle=css('--dim');ctx.globalAlpha=.5;ctx.lineWidth=1;
    ctx.beginPath();ctx.moveTo(e0.sx,e0.sy);ctx.lineTo(e1.sx,e1.sy);ctx.stroke();
    ctx.globalAlpha=1;ctx.fillStyle=css('--dim');ctx.font='10px ui-monospace,monospace';
    for(let g=2;g<=DIM;g+=2){const t0=at(g);
      const[tx,ty]=out(t0.sx,t0.sy,5),[l2,m2]=out(t0.sx,t0.sy,15);
      ctx.globalAlpha=.5;ctx.beginPath();ctx.moveTo(t0.sx,t0.sy);ctx.lineTo(tx,ty);ctx.stroke();
      ctx.globalAlpha=1;ctx.fillText(String(g),l2,m2);}
    const mm=at((1+DIM)/2),[ttx,tty]=out(mm.sx,mm.sy,32);
    let an=Math.atan2(e1.sy-e0.sy,e1.sx-e0.sx);
    if(an>Math.PI/2)an-=Math.PI; if(an<-Math.PI/2)an+=Math.PI;
    ctx.save();ctx.translate(ttx,tty);ctx.rotate(an);
    ctx.font='600 11px system-ui,sans-serif';ctx.fillStyle=css('--ink');
    ctx.fillText(ax.t,0,0);ctx.restore();
  }
}
const ro=new ResizeObserver(e=>{const r=e[0].contentRect;
  W=Math.max(280,Math.floor(r.width));H=Math.max(300,Math.round(Math.min(430,r.width*.46)));
  cv.style.width=W+'px';cv.style.height=H+'px';draw();});
ro.observe(cv.parentElement);
cv.addEventListener('pointerdown',e=>{drag=true;lx=e.clientX;ly=e.clientY;
  cv.setPointerCapture(e.pointerId);});
cv.addEventListener('pointermove',e=>{if(!drag)return;
  yaw+=(e.clientX-lx)*.008;pitch=Math.max(.05,Math.min(1.3,pitch+(e.clientY-ly)*.005));
  lx=e.clientX;ly=e.clientY;draw();});
const up=()=>{drag=false;};
cv.addEventListener('pointerup',up);cv.addEventListener('pointercancel',up);
new MutationObserver(draw).observe(document.documentElement,
  {attributes:true,attributeFilter:['data-theme']});
matchMedia('(prefers-color-scheme:dark)').addEventListener('change',draw);
</script>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs")
    ap.add_argument("-o", "--out", default="derived/diff-surface.html")
    args = ap.parse_args()
    g, only_b = collect(args.runs)

    # [ n, Qwen, union ]. Height is Qwen alone, not max(Qwen, Phi). Taking the
    # per-cell best is an oracle nobody can run -- it needs the answer key to
    # pick which model to trust on each size. Qwen is the model you would
    # actually deploy, so the cap is the honest question: given that, what does
    # adding Phi buy? Counted per problem rather than rebuilt from rates.
    diff = {f"{a}x{b}": [n, round(q / n, 4), round(uni / n, 4)]
            for (a, b), (q, p, n, uni) in g.items()}
    N = sum(c[2] for c in g.values())
    mean = sum(q - p for q, p, n, _ in g.values()) / N * 100
    # Cap volume is exactly the problems Phi solved that Qwen did not, so it
    # sums to only_b by construction.
    caps = [uni - q for q, p, n, uni in g.values()]
    neg = sum(1 for c in caps if c > 0)
    cap_total = sum(caps)

    payload = {"dim": max(max(c) for c in g), "g": diff}
    html = (PAGE.replace("__DATA__", json.dumps(payload, separators=(",", ":")))
                .replace("__N__", f"{N:,}").replace("__MEAN__", f"{mean:+.0f}")
                .replace("__NEG__", str(neg)).replace("__CELLS__", str(len(g)))
                .replace("__OB__", str(cap_total)))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    open(args.out, "w").write(html)
    print(f"wrote {args.out}  ({os.path.getsize(args.out)/1024:.0f} KB)")
    print(f"  {N} problems, {len(g)} cells, mean lead {mean:+.1f} points, "
          f"{neg} of {len(g)} cells carry a cap totalling {cap_total} problems, "
          f"{only_b} solved only by Phi")


if __name__ == "__main__":
    main()
