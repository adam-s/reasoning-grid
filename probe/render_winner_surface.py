#!/usr/bin/env python3
"""The winning model, as a surface, coloured by which model that is.

    python probe/render_winner_surface.py -o derived/winner-surface.html

Height is max(Qwen, Phi) -- the best either model manages at that size, as a
probability. Colour is which one it was: blue where Qwen is level or higher,
orange where Phi is higher.

The surface is drawn as ONE TILE PER CELL, not as quads between cells. Colour
here is categorical per cell, and quads interpolate: painting a quad orange
whenever any of its four corners is orange turns 15 cells into 40 of 121 quads,
and taking the mean of the corners instead turns them into 7. Neither is the
answer. Each cell gets its own tile spanning [a-0.5,a+0.5] x [b-0.5,b+0.5], and
the tile's corner heights are the mean of the cells meeting at that corner --
so adjacent tiles share corner values exactly, the sheet stays continuous with
no cracks, and exactly 15 tiles are orange.

Rates are P(correct), the mean over a cell's problems of that problem's success
rate. Scoring by whether a model ever solved a problem is not a probability: it
climbs with the number of times you ask, and the two models were not asked the
same number of times.
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
    g, gen = collections.defaultdict(list), [0, 0, 0, 0]
    for u, d in by.items():
        if A not in d or B not in d:
            continue
        g[cell[u]].append((sum(d[A]) / len(d[A]), sum(d[B]) / len(d[B])))
        gen[0] += sum(d[A]); gen[1] += len(d[A])
        gen[2] += sum(d[B]); gen[3] += len(d[B])
    out = {c: (sum(x[0] for x in v) / len(v), sum(x[1] for x in v) / len(v), len(v))
           for c, v in g.items()}
    return out, gen


PAGE = """<title>carrychain &mdash; the better model at every size</title>
<style>
:root{ --paper:#fdfcf9; --panel:#f7f5f0; --line:#e6e2d9; --line-2:#cdc7bb; --ink:#191817;
  --dim:#57544e; --faint:#a29d94; --lead-a:#1f3a5f; --lead-b:#c9853a; }
@media (prefers-color-scheme:dark){:root{ --paper:#131519; --panel:#1a1d23; --line:#2a2f38;
  --line-2:#3b4250; --ink:#eae7e0; --dim:#a9a49b; --faint:#6c6862;
  --lead-a:#8fb0dd; --lead-b:#e0a048; }}
:root[data-theme="dark"]{ --paper:#131519; --panel:#1a1d23; --line:#2a2f38; --line-2:#3b4250;
  --ink:#eae7e0; --dim:#a9a49b; --faint:#6c6862; --lead-a:#8fb0dd; --lead-b:#e0a048; }
:root[data-theme="light"]{ --paper:#fdfcf9; --panel:#f7f5f0; --line:#e6e2d9; --line-2:#cdc7bb;
  --ink:#191817; --dim:#57544e; --faint:#a29d94; --lead-a:#1f3a5f; --lead-b:#c9853a; }
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
  font-size:17px;line-height:1.62}
.wrap{max-width:980px;margin:0 auto;padding:56px 22px 90px}
h1{font-size:clamp(27px,4.2vw,38px);line-height:1.12;margin:0 0 14px;letter-spacing:-.016em;
  text-wrap:balance}
.eyebrow{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;
  letter-spacing:.15em;text-transform:uppercase;color:var(--faint);margin:0 0 11px}
.lede{font-size:19.5px;color:var(--dim);margin:0 0 28px;max-width:60ch}
p{margin:0 0 15px;max-width:64ch}
strong{font-weight:650}
.score{display:flex;gap:34px;flex-wrap:wrap;margin:0 0 24px;
  font-family:system-ui,-apple-system,sans-serif}
.score div{display:flex;flex-direction:column;gap:1px}
.score b{font-size:31px;font-weight:600;letter-spacing:-.02em;
  font-variant-numeric:tabular-nums;line-height:1}
.score span{font-size:12px;color:var(--faint);letter-spacing:.03em}
.qc b{color:var(--lead-a)} .pc b{color:var(--lead-b)}
.plot{position:relative;border:1px solid var(--line);border-radius:5px;
  background:var(--panel);overflow:hidden}
canvas{display:block;cursor:grab;touch-action:pan-y}
canvas:active{cursor:grabbing}
.hint{position:absolute;left:11px;bottom:8px;font-family:ui-monospace,monospace;
  font-size:9px;letter-spacing:.08em;color:var(--faint);pointer-events:none}
.key{display:flex;gap:22px;align-items:center;flex-wrap:wrap;margin:16px 0 0;
  font-family:system-ui,-apple-system,sans-serif;font-size:12.5px;color:var(--dim)}
.sw{display:inline-block;width:40px;height:11px;border-radius:2px;vertical-align:-1px;
  margin-right:7px}
.ra{background:linear-gradient(90deg,rgb(232,236,243),rgb(27,42,94))}
.rb{background:linear-gradient(90deg,rgb(247,237,224),rgb(138,74,18))}
@media (prefers-color-scheme:dark){
  .ra{background:linear-gradient(90deg,rgb(38,46,60),rgb(150,182,224))}
  .rb{background:linear-gradient(90deg,rgb(56,45,32),rgb(232,170,86))}}
:root[data-theme="dark"] .ra{background:linear-gradient(90deg,rgb(38,46,60),rgb(150,182,224))}
:root[data-theme="dark"] .rb{background:linear-gradient(90deg,rgb(56,45,32),rgb(232,170,86))}
:root[data-theme="light"] .ra{background:linear-gradient(90deg,rgb(232,236,243),rgb(27,42,94))}
:root[data-theme="light"] .rb{background:linear-gradient(90deg,rgb(247,237,224),rgb(138,74,18))}
.note{font-family:system-ui,-apple-system,sans-serif;font-size:13.5px;color:var(--faint);
  margin-top:22px;max-width:68ch;line-height:1.62}
.note strong{color:var(--dim)}
</style>
<div class="wrap">
  <p class="eyebrow">carrychain &middot; __INST__ problems &middot; both models, same
  questions</p>
  <h1>The better model at every size</h1>
  <p class="lede">Height is the best either model manages &mdash; the chance of an
  exactly correct product. Colour is which model that was. Drag to look along the
  slope.</p>
  <div class="score">
    <div class="qc"><b>__NQO__</b><span>CELLS QWEN IS LEVEL OR HIGHER</span></div>
    <div class="pc"><b>__NP__</b><span>CELLS PHI IS HIGHER</span></div>
    <div><b>__PQ__%</b><span>QWEN OVERALL</span></div>
    <div><b>__PP__%</b><span>PHI OVERALL</span></div>
  </div>
  <div class="plot"><canvas id="c"></canvas><span class="hint">drag to rotate</span></div>
  <div class="key">
    <span><span class="sw ra"></span>Qwen level or higher</span>
    <span><span class="sw rb"></span>Phi higher</span>
    <span>&#183; pale to deep = 0 to 100% correct</span>
    <span>&#183; greyer = fewer problems behind it</span>
  </div>
  <p class="note"><strong>The shape is the finding; the colour is nearly all one.</strong>
  Both models hold a plateau over the small sizes and then fall off a cliff in the same
  place, so the surface would look much the same if either model had drawn it alone.
  Qwen is level or higher in <strong>__NQO__ of __CELLS__</strong> cells &mdash; and of
  the <strong>__NLEVEL__</strong> level ones, <strong>__NSAT__</strong> are both models
  at 100%, where there is nothing left to win.</p>
  <p class="note"><strong>The __NP__ orange tiles are not a region Phi owns.</strong>
  They are scattered rather than clustered, and every one rests on 12 problems or fewer,
  where a single problem moves a cell 8 to 33 points. They mark where to look, not what
  to conclude.</p>
  <p class="note"><strong>One tile per cell, not quads between cells.</strong> Colour
  here is a category attached to a cell, and quads interpolate between four of them.
  Painting a quad orange whenever any corner is orange would turn 15 cells into 40 of
  121 quads; averaging the corners instead turns them into 7. So each cell owns a tile
  spanning half a step in every direction, with corner heights averaged from the cells
  meeting there &mdash; adjacent tiles share those values exactly, so the sheet stays
  continuous, and exactly __NP__ tiles are orange.</p>
  <p class="note"><strong>These are probabilities.</strong> A cell is the mean over its
  problems of how often each model got that problem right. Scoring by whether a model
  ever solved a problem is not a probability: it climbs with the number of times you
  ask, and the two models were not asked equally often (__GA__ Qwen generations against
  __GB__ Phi), so it flatters whichever was run more.</p>
</div>
<script>
const D=__DATA__, DIM=D.dim;
const cv=document.getElementById('c'), ctx=cv.getContext('2d');
let yaw=-0.62, pitch=0.46, W=0, H=0, drag=false, lx=0, ly=0;
const css=k=>getComputedStyle(document.documentElement).getPropertyValue(k).trim();
// yaw, then pitch, then the perspective divide. cx/cy are added AFTER the
// divide, so framing is a pure translation and cannot skew the projection.
function P(a,b,z,cx,cy,fit){
  const cw=Math.cos(yaw),sw=Math.sin(yaw),cp=Math.cos(pitch),sp=Math.sin(pitch);
  const mid=(DIM+1)/2, x=a-mid, y=b-mid;
  const x1=x*cw-y*sw, y1=x*sw+y*cw, d=y1*cp-z*5.0*sp, vy=y1*sp+z*5.0*cp;
  const s=900/(900+d*26);
  return {sx:cx+x1*26*s*fit, sy:cy-vy*26*s*fit, d};
}
const at =(a,b)=>D.g[a+'x'+b]||null;            // [n, qwen, phi]
const best=(a,b)=>{const g=at(a,b); return g?Math.max(g[1],g[2]):null;};
const win=(a,b)=>{const g=at(a,b); return g?(g[2]>g[1]?1:0):0;};
const ev =(a,b)=>{const g=at(a,b); return g?0.55+0.45*Math.min(1,g[0]/12):0;};
// A tile corner sits between cells, so its height is the mean of the cells that
// meet there. Adjacent tiles compute the same corner from the same neighbours,
// which is what keeps the sheet continuous instead of cracked.
function corner(u,v){
  let t=0,k=0;
  for(const a of[u-0.5,u+0.5])for(const b of[v-0.5,v+0.5]){
    const z=best(a,b); if(z!==null){t+=z;k++;}
  }
  return k?t/k:null;
}
// The blog's surface ramp: pale at a low rate, deep at a high one, one hue,
// because the rate is ordered rather than categorical. Here there are two hues
// -- the ramp runs inside whichever model won the cell -- so lightness carries
// how well and hue carries which. The blue endpoints are the blog's exactly;
// the orange is built to match their luminance so neither family reads as
// heavier than the other at the same rate.
//
// Dark theme inverts the direction. A pale-to-deep ramp on a dark panel puts
// the plateau -- almost every cell -- at its least visible, which is backwards:
// there, a high rate is the bright end.
const RAMP={
  light:{a:[[232,236,243],[27,42,94]],   b:[[247,237,224],[138,74,18]]},
  dark: {a:[[38,46,60],  [150,182,224]], b:[[56,45,32],  [232,170,86]]},
};
function tone(rate,phi,e){
  // Ask the ground how bright it is rather than matching a hex string, which
  // breaks the moment a token is retuned.
  const bg=css('--paper'), h=[1,3,5].map(i=>parseInt(bg.slice(i,i+2),16));
  const dark=0.2126*h[0]+0.7152*h[1]+0.0722*h[2] < 128;
  const [lo,hi]=RAMP[dark?'dark':'light'][phi?'b':'a'];
  const t=Math.max(0,Math.min(1,rate));
  const c=lo.map((v,i)=>v+(hi[i]-v)*t);
  // Evidence rides on SATURATION, not lightness, so it cannot be mistaken for
  // the rate. A cell standing on 3 problems is visibly greyer than one standing
  // on 12 at the same height.
  const l=0.2126*c[0]+0.7152*c[1]+0.0722*c[2];
  return `rgb(${c.map(v=>Math.round(v+(l-v)*(1-e))).join(',')})`;
}
function draw(){
  const dpr=Math.min(devicePixelRatio||1,2);
  if(cv.width!==Math.round(W*dpr)){cv.width=Math.round(W*dpr);cv.height=Math.round(H*dpr);}
  ctx.setTransform(dpr,0,0,dpr,0,0); ctx.clearRect(0,0,W,H);
  // Frame what the data actually occupies rather than a fixed box.
  let b0=1e9,b1=-1e9,c0=1e9,c1=-1e9;
  for(const a of[0.5,DIM+0.5])for(const b of[0.5,DIM+0.5])for(const z of[0,1]){
    const q=P(a,b,z,0,0,1);
    b0=Math.min(b0,q.sx);b1=Math.max(b1,q.sx);c0=Math.min(c0,q.sy);c1=Math.max(c1,q.sy);}
  const PAD=54, aw=Math.max(80,W-PAD*2), ah=Math.max(80,H-PAD*2);
  const fit=Math.min(aw/(b1-b0), ah/(c1-c0));
  const cx=PAD+aw/2-((b0+b1)/2)*fit, cy=PAD+ah/2-((c0+c1)/2)*fit;
  const Q=(a,b,z)=>P(a,b,z,cx,cy,fit);
  const mid=(DIM+1)/2;
  const key=(a,b)=>(a-mid)*Math.sin(yaw)+(b-mid)*Math.cos(yaw);
  // the zero plane, so the sheet reads as relief against something
  ctx.strokeStyle=css('--line-2'); ctx.globalAlpha=.8; ctx.lineWidth=1; ctx.beginPath();
  for(let g=1;g<=DIM;g++){const p0=Q(g,1,0),p1=Q(g,DIM,0),r0=Q(1,g,0),r1=Q(DIM,g,0);
    ctx.moveTo(p0.sx,p0.sy);ctx.lineTo(p1.sx,p1.sy);
    ctx.moveTo(r0.sx,r0.sy);ctx.lineTo(r1.sx,r1.sy);}
  ctx.stroke(); ctx.globalAlpha=1;
  const tiles=[];
  for(let a=1;a<=DIM;a++)for(let b=1;b<=DIM;b++)
    if(best(a,b)!==null) tiles.push({a,b,d:key(a,b)});
  tiles.sort((p,q)=>q.d-p.d);                      // far to near
  for(const t of tiles){
    const a=t.a,b=t.b;
    const cs=[[-0.5,-0.5],[0.5,-0.5],[0.5,0.5],[-0.5,0.5]]
      .map(([u,v])=>Q(a+u,b+v,corner(a+u,b+v)));
    ctx.beginPath(); ctx.moveTo(cs[0].sx,cs[0].sy);
    for(let k=1;k<4;k++) ctx.lineTo(cs[k].sx,cs[k].sy);
    ctx.closePath();
    ctx.fillStyle=tone(best(a,b),win(a,b),ev(a,b));
    ctx.fill();
    ctx.globalAlpha=.34; ctx.strokeStyle=css('--panel'); ctx.lineWidth=.7; ctx.stroke();
    ctx.globalAlpha=1;
  }
  // axes, on the two ground edges nearest the camera
  const cors=[[1,1],[DIM,1],[1,DIM],[DIM,DIM]];
  let near=cors[0],nd=1e9;
  for(const c of cors){const d=Q(c[0],c[1],0).d; if(d<nd){nd=d;near=c;}}
  const ctr=Q(mid,mid,0);
  const out=(x,y,by)=>{const dx=x-ctr.sx,dy=y-ctr.sy,m=Math.hypot(dx,dy)||1;
    return[x+dx/m*by,y+dy/m*by];};
  ctx.textBaseline='middle'; ctx.textAlign='center';
  for(const ax of[{t:'digits in A',f:near[1],al:'a'},{t:'digits in B',f:near[0],al:'b'}]){
    const pt=v=>ax.al==='a'?Q(v,ax.f,0):Q(ax.f,v,0);
    const e0=pt(1),e1=pt(DIM);
    ctx.strokeStyle=css('--dim');ctx.globalAlpha=.45;ctx.lineWidth=1;
    ctx.beginPath();ctx.moveTo(e0.sx,e0.sy);ctx.lineTo(e1.sx,e1.sy);ctx.stroke();
    ctx.globalAlpha=1;ctx.fillStyle=css('--dim');ctx.font='10px ui-monospace,monospace';
    for(let g=2;g<=DIM;g+=2){const t0=pt(g);
      const[tx,ty]=out(t0.sx,t0.sy,5),[lx2,ly2]=out(t0.sx,t0.sy,15);
      ctx.globalAlpha=.45;ctx.beginPath();ctx.moveTo(t0.sx,t0.sy);ctx.lineTo(tx,ty);
      ctx.stroke();
      ctx.globalAlpha=1;ctx.fillText(String(g),lx2,ly2);}
    const mm=pt(mid),[ttx,tty]=out(mm.sx,mm.sy,33);
    let an=Math.atan2(e1.sy-e0.sy,e1.sx-e0.sx);
    if(an>Math.PI/2)an-=Math.PI; if(an<-Math.PI/2)an+=Math.PI;
    ctx.save();ctx.translate(ttx,tty);ctx.rotate(an);
    ctx.font='600 11px system-ui,sans-serif';ctx.fillStyle=css('--ink');
    ctx.fillText(ax.t,0,0);ctx.restore();
  }
}
const ro=new ResizeObserver(e=>{const r=e[0].contentRect;
  W=Math.max(280,Math.floor(r.width));
  H=Math.max(320,Math.round(Math.min(470,r.width*.52)));
  cv.style.width=W+'px';cv.style.height=H+'px';draw();});
ro.observe(cv.parentElement);
cv.addEventListener('pointerdown',e=>{drag=true;lx=e.clientX;ly=e.clientY;
  cv.setPointerCapture(e.pointerId);});
cv.addEventListener('pointermove',e=>{if(!drag)return;
  yaw+=(e.clientX-lx)*.008;
  // .05 flattened the ground to a line and stopped being a chart
  pitch=Math.max(.16,Math.min(1.3,pitch+(e.clientY-ly)*.005));
  lx=e.clientX;ly=e.clientY;draw();});
for(const t of['pointerup','pointercancel'])cv.addEventListener(t,()=>{drag=false;});
matchMedia('(prefers-color-scheme:dark)').addEventListener('change',draw);
new MutationObserver(draw).observe(document.documentElement,
  {attributes:true,attributeFilter:['data-theme']});
</script>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs")
    ap.add_argument("-o", "--out", default="derived/winner-surface.html")
    args = ap.parse_args()
    g, gen = collect(args.runs)

    payload = {"dim": max(max(c) for c in g),
               "g": {f"{a}x{b}": [n, round(q, 4), round(p, 4)]
                     for (a, b), (q, p, n) in g.items()}}
    np_ = sum(1 for q, p, n in g.values() if p > q)
    nlev = sum(1 for q, p, n in g.values() if q == p)
    nsat = sum(1 for q, p, n in g.values() if q == p == 1.0)
    inst = sum(n for _, _, n in g.values())
    pq, pp = gen[0] / gen[1] * 100, gen[2] / gen[3] * 100

    html = (PAGE.replace("__DATA__", json.dumps(payload, separators=(",", ":")))
                .replace("__INST__", f"{inst:,}").replace("__CELLS__", str(len(g)))
                .replace("__NP__", str(np_)).replace("__NQO__", str(len(g) - np_))
                .replace("__NLEVEL__", str(nlev)).replace("__NSAT__", str(nsat))
                .replace("__PQ__", f"{pq:.0f}").replace("__PP__", f"{pp:.0f}")
                .replace("__GA__", f"{gen[1]:,}").replace("__GB__", f"{gen[3]:,}"))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    open(args.out, "w").write(html)
    print(f"wrote {args.out}  ({os.path.getsize(args.out)/1024:.0f} KB)")
    print(f"  {inst} problems, {len(g)} cells, Qwen {pq:.1f}% Phi {pp:.1f}%")
    print(f"  Qwen level or higher {len(g)-np_}, Phi higher {np_}  "
          f"({len(g)-np_}+{np_} = {len(g)})")


if __name__ == "__main__":
    main()
