# Sweep 10 + 11 — results

Run 2026-08-01. Pre-registration in [PREFLIGHT.md](PREFLIGHT.md), committed as
`5a777e9` before the first generation.

Two of three pre-registered predictions **missed**. The cause is a defect in how
the partner was screened, described below, and it is the most useful thing this
sweep produced.

## What ran

| | Qwen3-4B (Alibaba) | Phi-4-reasoning (Microsoft) |
|---|---|---|
| grid | 14×14, 196 cells | 12×12, 144 cells |
| generations | 1,566 | 1,062 |
| context granted | 40,960 (native) | 32,768 (native) |
| tokens produced | 23.2M | 12.2M |

temperature 0.7, top_p 1.0, thinking requested **and observed on every record**,
`budget_mode=max`, seed 20260730, shared `order_seed` so both models met
identical problems in identical submission positions. H200 throughout.

Rows 13–14 were run for Qwen only, so the paired analysis is confined to the
12×12 core where both models have data.

## Scoring rule

**A run that consumed the model's entire context without answering counts as
incorrect.** It is not excluded and not distinguished in any chart from a wrong
digit: in both cases the model failed to return the exactly correct product,
which is the only thing the grid measures.

This is sound *here* specifically because each model was granted its own native
context, so exhausting it is the model's limit rather than a budget imposed on
it. Every sweep before 10 ran against an arbitrary cap and must be read the
other way; `reduce_grid.cells(grind_is_wrong=False)` recovers that reading, and
the four-way outcome is kept on every record either way.

Cost of the rule: Qwen's boundary moves 9.15 → 9.02 digits, and 14 cells that
would have been dropped as unmeasurable are reported instead.

## Surfaces

| model | correct | rate | 95% CI | d\* |
|---|---|---|---|---|
| Qwen3-4B (14×14) | 908/1566 | 58.0% | 55.5–60.5% | **8.56** |
| Qwen3-4B (12×12 core) | 754/1062 | 71.0% | 68.2–73.6% | 9.02 |
| Phi-4-reasoning (12×12) | 601/1062 | 56.6% | 53.6–59.5% | **7.73** |

Qwen by problem size, full 14×14:

| N band | correct/attempts | p | 95% CI |
|---|---|---|---|
| 1–12 | 105/105 | 100% | 96–100% |
| 13–30 | 166/183 | 91% | 86–94% |
| 31–56 | 340/414 | 82% | 78–86% |
| 57–90 | 229/408 | 56% | 51–61% |
| 91–120 | 53/252 | 21% | 16–26% |
| 121–160 | 14/168 | 8% | 5–14% |
| 161–196 | 1/36 | 3% | 0–14% |

The grid spans the full range it was built to span: saturated at the top-left,
first cracks around N=13–30, and **nine cells at 0/12** where the model never
once returned the correct product.

## The paired result

1,062 problems, both models, same instances.

| outcome | count | share |
|---|---|---|
| both correct | 506 | 47.6% |
| only Qwen | 248 | 23.4% |
| only Phi-4-reasoning | 104 | 9.8% |
| neither | 204 | 19.2% |

**Qwen is decisively the better model.** McNemar χ² = 58.1 against a threshold
of 3.84.

**And a second vendor still buys 9.8 points of coverage.** Of the 308 problems
Qwen missed, Phi-4-reasoning solved **104 — 34%** (95% CI 29–39%). Either-model
coverage is 80.8% against Qwen's 71.0% alone.

Those two sentences are both true, and the second does not follow from the
first. The failures are not nested. In **51 of 144 cells** each model rescued
the other at least once, so the disagreement is not a clean split by problem
size — it interleaves inside a single cell.

Where the second model helps, by size:

| N band | rescue rate |
|---|---|
| 13–30 | 100% |
| 31–56 | 72% |
| 57–90 | 46% |
| 91–120 | 10% |
| 121–144 | 5% |

Redundancy pays until the problem is hard enough to defeat both models, then
stops paying entirely. That is a shape a systems argument can use.

## Predictions vs outcome

| pre-registered | outcome | verdict |
|---|---|---|
| ~537 disagreements | 352 | missed |
| 291 Qwen-only / 246 Phi-only | 248 / 104 | **missed** |
| McNemar below 3.84 — neither dominates | 58.1 | **missed** |
| both surfaces monotone in N | yes | held |
| truncation near zero | Qwen 1.4%, Phi 10.5% | Qwen held, Phi failed |

### Why: the screen used a different sampling shape than the run

Phi-4-reasoning was chosen on a screen that put it at d\* = 9.02, a third of a
digit from Qwen. It measured 7.73. Decomposing that:

| | screen | full run | drift |
|---|---|---|---|
| Qwen, grinds excluded | 9.33 | 9.15 | −0.18 |
| Qwen, grinds = wrong | 9.25 | 9.02 | −0.23 |
| Phi, grinds excluded | 9.02 | 8.82 | −0.20 |
| **Phi, grinds = wrong** | **8.73** | **7.73** | **−1.00** |

Every figure is stable except the last. Judged only on runs that finished,
Phi-4-reasoning really is an 8.8-digit model and the screen was right. The gap
opens entirely on **termination**.

The screen sampled n=1 uniformly across 144 cells. The sweep concentrated n=12
in the live band, where N is high — which is exactly where Phi runs out of
context. So the screen measured a 2.8% grind rate and the sweep measured 10.5%,
and the screen's estimate of capability was never wrong about the same quantity
the sweep reported.

**A screen must use the same allocation as the run it screens for.** Otherwise
it estimates a different quantity and the comparison is invalid regardless of
how many cells it covers.

A second, smaller version of the same error: screening on the diagonal
overstates a model. Phi-4-mini-reasoning fitted 6.07 on a diagonal ladder and
4.71 on the full grid, because square problems are easier than lopsided ones at
equal N.

## Phi-4-reasoning's context ceiling

10.5% of its generations exhausted 32,768 tokens, concentrated where it matters:

| N band | Qwen | Phi-4-reasoning |
|---|---|---|
| 1–20 | 0% | 0% |
| 21–50 | 1% | 4% |
| 51–80 | 2% | 8% |
| 81–110 | 2% | **19%** |
| 111–144 | 2% | **40%** |

This is a property of the model, not the harness — 32,768 is its native maximum
and all of it was granted. Qwen's 40,960 was enough for the same problems. Under
the scoring rule this counts against Phi, correctly: it did not return the
product.

It also means Phi's measured d\* is not comparable to a model with more room,
and any future comparison involving it must say so.

## Cost

| run | wall | tokens | actual |
|---|---|---|---|
| Qwen 12×12 core | 6,423s | 13.55M | $8.10 |
| Phi-4-reasoning 12×12 core | 11,863s | 12.15M | $14.96 |
| Qwen 13–14 extension | 5,333s | 9.68M | $6.72 |
| **total** | | **35.4M** | **$29.78** |

Against a pre-registered hard stop of **$35** — inside it, but the stop was set
for a 12×12 pair and the extension was added after. Project total for the day is
roughly **$41** including screening and probe runs.

**Estimates missed high on Phi and low on the extension.** The pattern across
every estimate today: token models are accurate to within ~10%, throughput
guesses are wrong by up to 60%, and every large cost miss traced to throughput
rather than tokens. Throughput is a function of the model, the cell mix, and the
long-job tail; treating it as a constant is what broke the estimates.

Lane count turned out to be the mechanism. Granting a real ceiling means vLLM
reserves `max_len` tokens of KV per concurrent sequence, so concurrency is
`(HBM − weights) / max_len`. Phi-4-reasoning got 15.1 lanes on H200 against
Qwen's 20.0, and 5.8 on an H100 — which is why H200 returned 2–3× the throughput
for 15% more per second.

## Defects found and fixed during the sweep

- **parse_answer v4.2.** The Phi family echoes the prompt template back three
  ways (`<the full integer>1234`, `<1234>`, `the full integer 1234`). All three
  scored as refusals by a model that had answered. Corpus 199 → 367 real tails.
- **Scores read from a stale field.** `reduce_grid` now re-derives answer and
  correctness from `raw_text`, because the stored `answer` is whatever the
  parser said the day it ran and this parser has shipped broken four times.
- **thinking=True was not being set.** It relied on the model's default.
  Granite 3.3 defaults thinking *off* and produced 144 silently non-reasoning
  records at 940 tokens each. `thinking_observed` is what caught it.
- **`grid` could not set the context ceiling.** `budget_mode="max"` meant "max
  of a 32,768 constant in the class definition" — D-10 one layer down.
- **`paired()` initialised each cell from the running totals** instead of zero,
  inflating every per-cell count.
- **A failed `modal run` does not release its container.** EXAONE died on load
  and held an H200 for eight minutes.

## Not claimed

- **Anything about temperature.** One temperature. A second would have halved
  samples per cell for the primary question.
- **That Phi-4-reasoning represents Microsoft, or Qwen3-4B Alibaba.** Two
  models, two sizes, one task.
- **Per-cell precision.** At n=12 a true 50% cell reads 25–75%. The 7×7 cell has
  17 pooled trials and still spans 53–90%. Every claim here rests on the fit
  across all cells, never on one.
- **That the boundary generalises off long multiplication.** The instrument was
  chosen because chain length is known in advance and the answer is free to
  compute, not because arithmetic is the subject.
