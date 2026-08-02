# blog/ — the post

Scaffold. Nothing here is implemented yet; every visualization is a
`<Placeholder>` naming the committed script it ports from.

This is the fourth step of the pipeline. The first three already exist and are
not to be duplicated here:

```text
probe/bakeoff.py       runs generations on Modal    -> runs/*.jsonl   (raw, immutable, tracked)
probe/reduce_grid.py   scores from raw text         -> derived/*.json (small, regenerable)
probe/render_*.py      standalone HTML + inline SVG -> derived/*.html (the working charts)
blog/                  the published post           -> dist/          (copied into the blog repo)
```

The `render_*.py` charts are not throwaway. They are the reference
implementations: each one is a working, validated version of a figure, with the
statistics already checked. Porting means moving a chart into Svelte and
recolouring it, not rediscovering what it should show.

## Where this goes

`~/Projects/blog` is a **deployment manifest, not a source repo**. It holds the
built `dist/` of each sub-app plus a plain-HTML homepage; whatever is on `main`
is what is on the site.

```sh
cd ~/Projects/blog
./scripts/sync-app.sh ~/Projects/carrychain/blog carrychain
# then add a <dt>/<dd> to index.html, commit, push -- CI does s3 sync + invalidation
```

`vite.config.ts` sets `base: './'`, which that script requires: it copies the
same build to an arbitrary subpath, so asset URLs must be relative.

See `~/Projects/blog/.claude/CLAUDE.md` for the AWS side (S3 + CloudFront +
Route53, and the CloudFront Function that rewrites `/carrychain/` to
`/carrychain/index.html`).

## House style — do not re-pick this

`src/app.css` is copied from `~/Projects/grpo/post/src/app.css`. The same tokens
run through **grpo**, **clap** and **separate**, and a post that invents its own
palette reads as a different site.

| | |
|---|---|
| paper | `#fdfcf9` warm, panels `#f7f5f0` |
| ink | `#1a1a1a` / dim `#5a5a5a` / faint `#9a9a9a` |
| accent | navy `#1f3a5f` |
| body | Source Serif 4 |
| mono | JetBrains Mono, `tabular-nums` |
| measure | **`--maxw: 640px`** |

That last row is a real constraint. These are narrow reading columns, and charts
sit **inside** the text measure. The standalone `derived/*.html` charts were
built 940–1120px wide and will need refitting, not just recolouring.

What *is* ours to choose is the semantic mapping, at the bottom of `app.css`.
Each post assigns the shared hues to its own quantities and then holds that
assignment for the whole page:

| token | means | always |
|---|---|---|
| `--ramp-lo` → `--ramp-hi` | reliability | one warm hue, pale to deep. Sequential data gets one hue; a rainbow invents boundaries the numbers do not have |
| `--model-a` | Qwen3-4B | cool |
| `--model-b` | Phi-4-reasoning | warm |
| `--fit` | fitted boundary, UI focus | navy, nothing else |
| `--absent` | no data | faint grey, **never** a low score |

## Structure

```text
blog/
├── index.html
├── vite.config.ts          base: './'
├── scripts/prepare.py      SCAFFOLD -- copies derived/*.json into public/data/
├── public/data/            reduced JSON, fetched at runtime
└── src/
    ├── main.ts
    ├── App.svelte          composes <Section> blocks, one per beat
    ├── app.css             tokens (copied from grpo)
    └── lib/
        ├── components/     Layout, Section, Prose, Placeholder
        ├── data/load.ts    typed fetch of the reduced JSON
        └── viz/            one component per figure -- EMPTY, see below
```

Matches `~/Projects/clap/post` and `~/Projects/grpo/post`. Svelte 5 with runes
(`$state`, `$derived`, `$props`), Vite, no framework beyond that.

## The figures to port

Each is a working chart in `probe/`, published and validated. Order follows the
argument, not the order they were built.

| slot | ports from | what it settles |
|---|---|---|
| `SurfaceCanvas` **(built)** | `probe/build_surface.py` | x = digits of A, y = digits of B, z = P(correct), scrubbable over trial count and orbitable. Breaks at 8.56 digits; 100% → 3% |
| `BlindSpots` | `render_blindspots.py` | **the core argument.** Qwen wins outright (McNemar 58) *and* Phi solves 104 problems it misses — 34% of its failures. Coverage 71% → 81% |
| `Convergence` | `render_convergence.py` | one cell's number as 17 trials; then eight cells as small multiples. No cell converges alone |
| `EffortPrice` | `render_effort.py` | reasoning scales effort 7× with difficulty; without it the line is **flat**. Price per correct answer crosses over at ~30 operations |
| `OrderNull` | `render_order.py` | A×B ≡ B×A (p=0.52), and the apparent effect died under a difficulty-matched control |
| `TemperatureLadder` | `render_temperature.py`, `render_temp0.py` | nothing below T=1.0 is distinguishable; at T=0, **29 of 100 runs loop until the context runs out** against 3 at 0.7 |
| `ThreeTraces` **(built)** | `probe/build_flame.py` | three Qwen traces at N=56/65/77, one per outcome. The run that got it right is not the careful one — it is the one whose checks could fail differently from the arithmetic under test |

Also available and unported: `render_distribution.py` (φ=1.68 — size predicts
difficulty but not completely), `render_ladder.py` (pass rate with Wilson bars).

Published versions of all of them, with their URLs and findings, are in
[../docs/ARTIFACTS.md](../docs/ARTIFACTS.md).

## The flame stack is shared, and takes its categories as a prop

`viz/flame/` came from the λ-bench post importing `design/categories.ts`
directly, so it could only ever render λ's nine. carrychain has a different nine
(`design/carrychain-categories.ts`), so `design/scheme.ts` now carries the set as
a value and the components take it as a `scheme` prop.

The λ scheme is the default, so `FlamePanel` renders the reference figure exactly
as before and no existing call site changed. Rows are typed structurally
(`AnyFlameRow`) rather than by a literal union: a chart needs a colour for the
string it was handed, and a category the scheme is missing is a data bug, not
something to catch by narrowing a component.

| | |
|---|---|
| `FlamePanel` | the λ reference figure. λ-specific chrome (model badge, algorithm id, wall-clock) |
| `CarryFlamePanel` | one carrychain trace. Percent axis, no minimap, annotation markers |
| `ThreeTraces` | the figure: shared key, three panels, the crosscheck:recheck strip |

Two things the carrychain panel does differently, both deliberate:

- **The x-axis is share of the trace, not absolute offset.** The three traces are
  16k, 18k and 57k characters; on a shared absolute axis the two that finished
  would be slivers. Real lengths stay in each header.
- **Container rows are muted.** A container's colour is the dominant category
  among its children, and that dominance can be a plurality as low as 34%. At
  full strength it reads as a claim about the whole phase; at half it reads as
  the hint it is, and the leaves below carry the signal.

Review a figure without opening a browser:

```sh
npm run dev &
node scripts/shot.mjs /tmp/fig.png 390     # phone
node scripts/viewports.mjs                 # overflow check, five sizes
```

## 3D: two techniques, and they are not interchangeable

Both exist in the neighbouring projects. Pick deliberately.

**Perspective, on canvas** — `~/Projects/grpo/post/src/lib/components/viz/ModelDiagram.svelte`
(1,046 lines), documented across nine files in **`~/Projects/grpo/docs/3d-on-2d/`**:

1. why pseudo-3D and not WebGL — what was tried and what failed
2. projection math — similar triangles, `scale = CAM_DIST/(CAM_DIST + z)`
3. coordinates and rotations — world/camera/screen, yaw/pitch/roll, sign conventions
4. painter's algorithm vs z-buffer, and when back-to-front sorting breaks
5. hit-testing under perspective — inverse bilinear interpolation on a projected quad
6. plane thickness via cuboids
7. advanced techniques not yet used — lighting, fog, perspective-correct texturing
8. implementation map — which concept lives on which line
9. sources

Real foreshortening (quads, not transformed rects), tunable `CAM_DIST`, `ROT_X`,
`ROT_Y`, and working hit-testing. **Read this before building the surface.**

**Isometric, in SVG** — `~/Projects/agent-capability-threshold/web/src/lib/rubiks/Cube.svelte`:
`px = (x−y)/√2`, `py = (x+y−2z)/√6`. No perspective divide, no camera. Equal
foreshortening on all three axes. Cheaper, themeable through CSS custom
properties, crisp at any zoom.

`probe/render_animation.py` currently uses the isometric one, with painter's
algorithm over 169 quads. It is the right default at this size — but if the
surface needs rotation or click-to-inspect, the grpo pipeline already has both
and the isometric one has neither.

Broader survey of what the surrounding projects use:
[../.agents/reference/dataviz/](../.agents/reference/dataviz/).

## The data path

Data reaches the page as **generated TypeScript modules**, not as JSON fetched
at runtime. `probe/build_flame.py` and `probe/build_surface.py` read the reduced
artifacts and write `src/lib/data/*.ts`, which Vite bundles and tree-shakes. An
earlier scaffold fetched `public/data/*.json` instead; it was deleted along with
`scripts/prepare.py` and `lib/data/load.ts` once nothing imported them. **The
browser never sees a raw generation** either way.

That reducer does three things this post depends on, and none should be
reimplemented here:

- **scores from `raw_text`**, not the stored `correct` field — the parser has
  shipped broken four times, and stored scores are whatever it said that day
- **pools by condition, not filename** — two runs are comparable when
  temperature, `top_p`, thinking and context ceiling match
- **counts a non-terminating run as incorrect** — sound only because every model
  was granted its own native context, so running out is the model's limit

```sh
python probe/reduce_grid.py --sweep 10-grid12 --pool 11-ext14 --out derived
python probe/segment_trace.py --uid <uid> -o derived/segments-X.json
python probe/label_grind.py        # regenerates trace C's labels
python probe/build_flame.py        # labels/ + derived/segments-*.json -> src/lib/data/
python probe/build_surface.py      # runs/ -> src/lib/data/surface.ts
```

## Writing

`../AGENTS.md` governs prose, and points at
`../.agents/reference/anti-slop.md`. The blog projects carry their own copy of
the same rules at `~/Projects/clap/.agent/rules/anti-slop.md`.

State results plainly, negative ones included. Two of three pre-registered
predictions in this project missed, three findings are null, and every cost
estimate came in low — all of which is written down in
[../sweeps/10-grid14-pair/RESULTS.md](../sweeps/10-grid14-pair/RESULTS.md). A
post that quietly drops them is worth less than one that leads with them.

## Getting started

```sh
cd blog
npm install
npm run dev        # http://localhost:5175
```
