# Data visualization reference

Survey of what is actually used across `~/Projects`, so a later session does not
re-derive it. **Nothing here is in use by reasoning-grid yet.** This is a pointer
file for when the grid needs rendering.

Surveyed 2026-07-30.

---

## The short version

Charts in these projects are **hand-written inline SVG**, not a charting
library. d3 is present but only three small modules are imported — no `d3.axis`,
no `d3.line`, no selections driving rendering. Nothing uses Canvas or WebGL,
including the 3D cube, which is projected to SVG polygons.

That is a deliberate-looking pattern and it is worth keeping: inline SVG in a
component, with `viewBox` for scaling, theme colours via CSS custom properties,
and a couple of `d3-scale` calls for the axis math.

---

## What each project uses

### `agent-capability-threshold/web` — the essay site

The reference implementation. Svelte 5 (runes: `$props`, `$derived.by`), Vite.

- **11 files contain inline `<svg>`.** Every chart in the published essay is
  hand-built. No Recharts / Chart.js / Plotly / Observable Plot.
- **d3, used sparingly.** Only `d3-scale` (`scaleLinear`), `d3-brush`
  (`brushX`), and `d3-selection` (`select`, only where brush needs it).
  Everything else — paths, axes, ticks, labels — is written out.
- **katex** for the `P = p_step^N` formula rendering.
- **@melt-ui/svelte** for interactive primitives.
- Design tokens live in `src/lib/design/tokens.ts` and `categories.ts`.

Chart sections worth reading before building anything similar:
`src/sections/Consistency.svelte` (the convergence chart — running rate,
Wilson band, per-trial strip), `CapabilityCurves.svelte` (log-x accuracy curves
with a reference line), `Reliability.svelte`, `ThinkingOps.svelte` (annotated
trace segments).

### The Rubik's cube renderer — 3D to 2D

`agent-capability-threshold/web/src/lib/rubiks/Cube.svelte`

**SVG, not canvas.** A cubie-based isometric renderer. The projection is two
lines:

```ts
function project(p: [number,number,number]): [number,number] {
  return [(p[0] - p[1]) / Math.SQRT2,
          (p[0] + p[1] - 2 * p[2]) / Math.sqrt(6)];
}
```

That is the academic isometric projection — equal foreshortening on all three
axes, no perspective divide, no camera matrix. For a small object with axis
aligned geometry it is enough, and it keeps everything as SVG polygons that
inherit CSS theming and stay crisp at any zoom.

The rest of the approach, which is the part worth copying:

- **26 cubie objects each carry their own sticker colours.** During a rotation
  the colours travel with the geometry, so there is no per-frame lookup back
  into cube state. Cubies are rebuilt only when state changes.
- **Painter's algorithm** for hidden-surface removal: each projected polygon
  gets a `depth`, they are sorted, and drawn back to front. No z-buffer needed.
- **`cross2D`** on the projected vertices does back-face culling — a face whose
  winding is reversed after projection is pointing away.
- Related files: `cube.ts` (state and moves), `CubeGridSimple.svelte`,
  `lab/Cube2x2.svelte`, `ThoughtTicker.svelte`, and `ALGORITHM.md`.

**When SVG stops being the right choice:** roughly a few thousand elements.
Below that, SVG wins on theming, accessibility, crispness and debuggability.
Above it — dense scatter plots, particle fields, per-pixel work — switch to
Canvas 2D, and to WebGL only when the geometry genuinely needs a GPU.

### Other projects

- `rubiks-cube/dashboard` — Svelte + Vite, separate cube dashboard.
- `rubiks-cube-mcp/web` — SvelteKit.
- Two projects carry `chart.js`, two carry `d3`, one `d3-geo`. None of them is
  the essay site, and none is load-bearing for this work.
- **No Python plotting anywhere.** No matplotlib, seaborn, plotly, altair or
  bokeh in any `requirements.txt` or `pyproject.toml`. Charts are built in the
  browser from JSON, not rendered server-side.

---

## The pipeline that is actually used

Worth stating because it is not obvious from any single file:

1. Python runners write raw JSONL.
2. A script under `web/scripts/` (`port-chart-data.mjs`,
   `extract-mul-traces.mjs`, `extract-modexp-opus.mjs`, and similar) reduces
   raw to a small JSON file in `web/public/`.
3. A Svelte component fetches that JSON and draws inline SVG.

So the browser never sees raw records, and the reduction step is a committed,
re-runnable script rather than a notebook. That is the same separation
reasoning-grid uses between `runs/` and `derived/`.

---

## The dataviz skill

A bundled `dataviz` skill exists and carries a **validated categorical palette**
plus a runnable checker (`scripts/validate_palette.js`) that tests lightness
band, chroma floor, colour-blind separation and contrast. It was used for the
reasoning-grid artifacts; both light and dark palettes passed.

Values that passed, for reuse:

```text
light:  #2a78d6  #eb6834  #1baf7a  #eda100  #e87ba4  #008300  #4a3aa7  #e34948
dark:   #3987e5  #d95926  #199e70  #c98500  #d55181  #008300  #9085e9  #e66767
```

Two rules from it that bit during this session and are easy to forget: assign
categorical hues in **fixed order, never cycled**, and a contrast warning is not
dismissable — it obliges a visible label or a table view.

---

## For the reasoning-grid grid, when we come back to it

The deliverable is `x` = digits of A, `y` = digits of B, `z` = probability. That
is a **heatmap**, which means a sequential ramp (one hue, light to dark), not a
categorical palette and never a rainbow.

Open questions to settle then, not now:

- The live band is a hyperbola (`N = a·b`), so most of a square grid is
  saturated. Does the plot stay square, or use a log-log axis where the band
  becomes a straight diagonal?
- Cells differ in sample size under adaptive n. Encode that — opacity, or a
  hatch on low-n cells — or the reader assumes uniform confidence.
- Cells failing the truncation validity rule must be visibly distinct from
  cells measured at zero. Greyed, not dark.
- The difference map (model A minus model B, and the grid minus its own
  transpose for the order question) is diverging data: two hues with a neutral
  midpoint.
- The per-cell outcome strip carries information the colour does not. Some
  cells may deserve the `Consistency.svelte` treatment rather than a single
  swatch.
