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
./scripts/sync-app.sh ~/Projects/reasoning-grid/blog reasoning-grid
# then add a <dt>/<dd> to index.html, commit, push -- CI does s3 sync + invalidation
```

`vite.config.ts` sets `base: './'`, which that script requires: it copies the
same build to an arbitrary subpath, so asset URLs must be relative.

See `~/Projects/blog/.claude/CLAUDE.md` for the AWS side (S3 + CloudFront +
Route53, and the CloudFront Function that rewrites `/reasoning-grid/` to
`/reasoning-grid/index.html`).

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

An earlier version of this table promised the blind-spot slot would show Phi
solving 104 problems Qwen missed, 34% of its failures, lifting coverage from 71%
to 81%. Those numbers came from scoring a cell by whether a model *ever* solved
each problem, which is not a probability -- it rises with the number of times you
ask, and the two models were not asked equally often. On P(correct) the finding
reverses: the two models fail in the same places, about a digit apart. The slot
still exists and still carries the argument; the argument now has the other
sign.

| slot | ports from | what it settles |
|---|---|---|
| `Dogfight` **(built, not ported)** | nothing — `scripts/dogfight-curve.mjs` checks it | **the opener's second figure, and the only modelled one on the page.** Two point-mass aircraft fly Boyd's own energy-manoeuvrability physics, each on its own OODA loop, with the MiG given the better aeroplane and its pilot a compounding per-cycle loop tax. **It now shows the fight and nothing else** — the win-rate curve, the slider, the readouts and the caption were all cut for simplicity, so the figure illustrates the mechanism and no longer evidences it. What the ensemble found, and what the figure used to display: the mechanism is real and rising, 12% to 67% of merges across the tax range, and **weak** — tripling the MiG pilot's loop still leaves the Sabre at 37%, and nothing in reach gets near the parable's nine-out-of-ten. Rerun the script to re-derive it |
| `ThinkingMath` **(built)** | `probe/build_opener.py` | **the opener.** A run's thinking streams on the left; every closed arithmetic claim lands on the right, checked as it is made. 160 claims across three runs and exactly **one** is false -- an addition. Every multiplication in every run is correct, and the prose reads the same either way |
| `SurfaceCanvas` **(built)** | `probe/build_surface.py` | x = digits of A, y = digits of B, z = P(correct), scrubbable over trial count and orbitable. Breaks at 8.56 digits; 100% → 3% |
| `WinnerSurface` **(built)** | `probe/build_winner.py` | **the core argument, and it came back negative.** Toggle Qwen alone against the better of the two: 15 tiles of 144 move. Fitted, Qwen is still right half the time at 9.24 digits square and Phi at 8.39 — the same curve shifted 0.8 digits, never crossing. 10 cells are further apart than sampling noise explains and **none** favour Phi |
| `Convergence` | `render_convergence.py` | one cell's number as 17 trials; then eight cells as small multiples. No cell converges alone |
| `EffortPrice` | `render_effort.py` | reasoning scales effort 7× with difficulty; without it the line is **flat**. Price per correct answer crosses over at ~30 operations |
| `OrderNull` | `render_order.py` | A×B ≡ B×A (p=0.52), and the apparent effect died under a difficulty-matched control |
| `TemperatureLadder` | `render_temperature.py`, `render_temp0.py` | nothing below T=1.0 is distinguishable; at T=0, **29 of 100 runs loop until the context runs out** against 3 at 0.7 |

Also available and unported: `render_distribution.py` (φ=1.68 — size predicts
difficulty but not completely), `render_ladder.py` (pass rate with Wilson bars).

Published versions of all of them, with their URLs and findings, are in
[../docs/ARTIFACTS.md](../docs/ARTIFACTS.md).

## The flame stack is shared, and takes its categories as a prop

`viz/flame/` came from the λ-bench post importing `design/categories.ts`
directly, so it could only ever render λ's nine. reasoning-grid now has **sixteen of
its own** (`design/reasoning-grid-categories.ts`), derived from its own traces rather
than adapted from a study of a different model on a different task, so
`design/scheme.ts` carries the set as a value and the components take it as a
`scheme` prop.

The categories, the decision rules, the blind pass and its **72% reproduction
agreement — lower than the 84% of the scheme they replace, with the cause
diagnosed and unfixed** — are in
[../.agents/reference/label-rubric-qwen-multiplication.md](../.agents/reference/label-rubric-qwen-multiplication.md).
Every figure below inherits that number.

`scheme` and `header` are both required, and neither used to be. Each defaulted
to what the λ reference figure wanted, and that figure is gone. A default scheme
would colour a reasoning-grid trace with the wrong nine labels rather than failing,
and the λ header is model-specific chrome — a model badge, an algorithm id, a
wall-clock — built from fields reasoning-grid traces do not carry, so it rendered
empty. Rows are typed structurally (`AnyFlameRow`) rather than by a literal
union: a chart needs a colour for the string it was handed, and a category the
scheme is missing is a data bug, not something to catch by narrowing a component.

One caller is left. `SyncedTrace` renders a `FlamePanel` as the top third of the
opener and drives its playhead from the same character offsets the panes below it
are streaming. The stack stays factored because the flame is worth its own file,
not because a second figure is coming back.

**Two rows, and both are earned.** The container band is the OODA phase, the leaf
is the move, and the band is computed from the leaves rather than supplied — a
run of consecutive segments in one phase. Nothing hand-drawn sits between them.

Two things that panel does differently, both deliberate:

- **The x-axis is share of the trace, not absolute offset.** It is a timeline for
  the run beside it, and a character count is not something a reader converts in
  their head. The real length stays in the header.
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

`viz/surface/project.ts` is this repo's version, and it has one trap worth
knowing before the third caller hits it. Its divide is

```ts
scale = cam.dist / (cam.dist + depth * cam.zoom)
```

so **`dist` is compared against `depth * zoom` and is therefore in pixels, not
in world units.** `SurfaceCanvas` uses `dist: 900` against `zoom: 26`; `Dogfight`
uses `1300` against `~230`. Passing a camera distance that looks reasonable in
normalized world coordinates — 3.4, say — puts the singular plane inside the
scene, and every primitive crossing it is flung off the canvas. It does not look
like a divide by zero. It looks like a broken transform, which is the wrong
thing to go hunting for.

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

node --experimental-strip-types scripts/dogfight-curve.mjs   # prints, writes nothing
```

That last one is the exception to the sentence above it, and it is worth naming
rather than leaving to be discovered: **nothing in it comes from `runs/`.** It is
a simulation, not a reduction of a generation, and it no longer feeds the page
at all — it prints a table. The figure it belongs to draws one fight, and the
only thing it still inherits from the ensemble is `TAX`, pinned at the even-odds
crossing.

**The page does not say any of this.** The caption marking the figure as a model
rather than a measurement was cut when the figure was simplified, so a reader
meets a simulated dogfight among figures that are otherwise all measurements
with nothing distinguishing it. That is a known gap, recorded here because
nothing on the page records it.

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

## The page is prerendered, and the figures are not

`npm run build` runs three steps: the client build, an SSR build of
`src/entry-server.ts`, then `scripts/prerender.mjs`, which renders the page to
HTML and writes it into `dist/index.html`. That file goes from 2.7KB to ~24KB
and carries the whole essay as text.

The reason is the deploy target. This ships to S3 behind CloudFront as static
files, so without the prerender step the HTML is an empty `<div id="app">` and
every word lives inside ~220KB of gzipped JavaScript. Crawlers that do not run
JS, reader-mode tools and `curl` all get nothing, and a reader on a slow
connection watches a blank screen until the bundle executes.

**The figures still mount on the client.** They are canvas, rAF and matchMedia,
so they cannot render on a server. Each one is wrapped in
`lib/components/Figure.svelte`, which gives it a `data-fig` name, a reserved
height, and a `<noscript>` block holding a picture of the figure and a sentence
saying what it shows.

```sh
npm run figures    # rebuild public/figures/ from the preview
```

`scripts/build-figure-stills.mjs` captures ten frames of each figure and
compares them: identical means a PNG, different means a GIF built through
ffmpeg. Nothing decides which from a list, so a figure that gains or loses
motion is handled without anyone remembering. About a megabyte in total, and
nobody but a reader with JavaScript off ever fetches it — markup inside
`<noscript>` is not parsed when scripting is on, so the images are never
requested.

`prerender.mjs` fails the build if the rendered body does not contain a known
sentence. That check is not optional: a page that prerendered nothing still
looks perfect in a browser, so nothing else would catch it.

### Reserved heights are measured, never guessed

```sh
node scripts/measure-figures.mjs http://localhost:5175/           # rewrite
node scripts/measure-figures.mjs http://localhost:5175/ --check   # fail if stale
```

This sweeps the real page across 26 widths, bisects to find every reflow to the
pixel, fits each figure's height as straight segments, and writes
`src/lib/viz/figure-heights.css`. Rerun it after changing any figure's layout.

Guessing does not work here. These figures do not share breakpoints and do not
scale by aspect ratio: the opener is 510px tall on a phone and 517px on a
desktop three times as wide, while the trace figure gets *shorter* as the screen
widens. One of them picks its column count in JavaScript, so its breakpoint
appears in no stylesheet — which is why the script bisects rather than reading
the CSS.

`--check` earns its place. Adding `display: flex` to the figure wrapper resized
GridKey from 229px to 293px, and that is the only thing that noticed.

### Verifying a deploy

```sh
npm run preview
node scripts/verify-deploy.mjs http://localhost:4173/
node scripts/verify-deploy.mjs https://adamsohn.com/reasoning-grid/   # after deploy
```

Six groups of checks: the essay is in the raw HTML (a canary from the opening,
one from the closing, and a length floor, because one canary near the top passed
happily on a page that dropped the other 93%); the og tags sit under the URL
being served; the no-trailing-slash form redirects; every reserved box is
compared against its figure measured with the reservation forced off, across 28
widths the fitter never sampled; every figure mounts, draws something, keeps the
console clean and stays under 0.1 CLS at three widths; and the whole page is
loaded once with JavaScript disabled.

**Every check in here must be able to fail, and that is not automatic.** The
first version compared each box's height at `domcontentloaded` against its
height after load. Module scripts are deferred, so both readings were the same
post-hydration DOM: the delta was exactly zero for all nine figures at all three
widths, and deleting the entire stylesheet it existed to guard still printed
`ok`. Two independent reviews caught it, both by trying to make it fail rather
than by reading it. The fixed version, run against that same broken page,
reports nine short boxes and triple the CLS budget.

Run it against a local preview before shipping and against the live URL after,
because a production build differs from dev in ways that matter — idle rAF on
this page is 117/sec in dev and 0/sec built.

When CLS fails, `scripts/cls-blame.mjs <url> [width]` names the element that
moved and by how much.

### Does anything freeze on reload

```sh
node scripts/check-reload-freeze.mjs http://localhost:4173/
```

Fourteen reloads that land scrolled down, at a 6x CPU throttle, checking that
the opener still animates after scrolling back up. It exists because that broke
and nothing else could see it: `onscreen.svelte.ts` read `entries[0]` from its
IntersectionObserver, and one delivery can carry two records for the same
element. Reloading scrolled down produced exactly that — 205px and off screen,
then 508px and on screen — so the stale record won and the figure sat frozen at
two percent of its first lap, about one reload in three.

The tell is requestAnimationFrame throughput rather than a screenshot, because a
frozen figure looks the same as one that has not started. Four loops is ~360/sec;
one dead loop is ~240.
