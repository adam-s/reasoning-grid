# Multiplication grid: design, economics, and implementation

Status: superseded in parts. This was written before any measurement. Several
of its planning estimates have since been measured and several of its design
choices were shown to be wrong — see [RESULTS.md](RESULTS.md) for what was
actually measured and [methods-and-edge-cases.md](methods-and-edge-cases.md)
for the defect register and the corrections. Kept because the reasoning that
led to the wrong choices is part of the record.

Known superseded here: the 45-samples-per-cell figure (see methods 7c), the
adaptive-n-by-observed-rate rule (7d), the claim that a single z per cell can
answer the blind-spot question (7b), and the token-cost constants.

Project name is still `carrychain`. A rename to something that does not hardcode
long multiplication is pending; see the end of this document.

---

## 1. What we are testing

Three claims, ordered by how much they are worth. Each has a stated falsifier,
because a claim without one is not worth GPU time.

### Claim 1 — the exponential form holds

`P(correct) = p_step^N`, where N is the number of single-digit operations the
problem requires.

**Test.** Fit `ln P` against N across the whole grid. If the form holds, that is
a straight line through the origin with slope `ln p_step`.

**Falsifier.** Curvature. If the line bends down as N grows, `p_step` is not
constant along the chain, and something degrades with position or context
length. That is a more interesting result than confirmation, and it is the open
question the "Reliably Incorrect" essay leaves hanging.

### Claim 2 — the step is the single-digit product

If the step unit is right, then `N = a·b` for an a-digit by b-digit problem, and
lines of equal probability on the grid are hyperbolas.

**Test.** Cells with the same product of digit counts should land at the same
probability regardless of shape. 3×8, 4×6, 6×4 and 8×3 all give N = 24. Plot
them together.

**Falsifier.** They disagree. Then N is not `a·b`, and we re-plot against `a+b`,
`max(a,b)`, and `a·b + a·(b−1)` (products plus the additions) to find the unit
that linearizes. Whichever one does becomes the defended definition of a step.

A diagonal-only sweep cannot run this test at all. It is the main reason to
build a two-dimensional grid rather than a line.

### Claim 3 — capability sets are not nested across companies

This is the one worth building the experiment around.

If capability were a single scalar per model, then a better model would succeed
everywhere a worse one does. Failure sets would nest, and the grid for model A
would be the grid for model B shifted along the N axis. The prior project's
conclusion, that models differ in precision and not in kind, predicts exactly
that.

The hypothesis here is that this is wrong at fine resolution. Model A solves
8×11 and fails 9×11. Model B does the reverse. Neither is better; they have
different holes.

**Test.** Fit the smooth `p^N` envelope per model, then map the residuals. The
residual map is the blind-spot map. Compare the two maps.

**Falsifier.** The residuals are pure noise, uncorrelated with cell identity
across repeated instances, and the two models' residual maps look statistically
identical. Then Claim 3 is dead and the scalar view survives.

---

## 2. Why Claim 3 is the payoff

If two models from different companies have holes in different places, then
running both is worth more than running the better one twice. That is a
concrete, checkable argument about how to build coding agents, and almost
nobody has measured it on a task with ground truth.

The essay already argued that same-model verification fails, because a model
re-checking its own work reproduces its own errors. The Opus trace that verifies
three times and confirms a wrong intermediate is the evidence. What the essay
asserts but never measures is the other half: that a *different* model catches
what the first one misses. Whether that is true depends entirely on whether the
two models' errors are correlated, and error correlation is directly measurable
from paired data.

So the deliverable is not just two heatmaps. It is these four numbers, per cell:

- `p_A`, `p_B` — each model's pass rate.
- `p_union` — at least one model correct. The ceiling for any "run both and pick
  the right one" strategy, achievable only with a checker.
- `p_both_wrong_same_answer` — both wrong and agreeing. This is the number that
  decides whether cross-model agreement is a usable signal.

And the derived statistic that matters most:

**`P(correct | A and B produced the same answer)`.** In a coding agent there is
no ground truth, so agreement is the only cheap checker available. If two models
agreeing means the answer is almost certainly right, agreement is a deployable
verifier. If they frequently agree on the same wrong answer, agreement is
worthless and the whole multi-model story collapses. Multiplication is a good
place to measure this because the wrong answers are numerous and specific, so
agreement on a wrong answer is strong evidence of shared mechanism rather than
coincidence.

---

## 3. What Claim 3 demands from the design

Three design changes fall out of taking blind spots seriously. All three are
cheap. Skipping any of them makes the blind-spot claim untestable.

### 3.1 Paired instances — both models see the same problems

Generate the operand pairs once per cell, then run every model on that same
list. Do not let each model draw its own random problems.

Unpaired data can only compare cell rates, and comparing two noisy rates is a
weak test. Paired data gives a 2×2 table per cell:

```text
                B correct    B wrong
A correct         n11          n10
A wrong           n01          n00
```

From that table: McNemar's test on `n10` vs `n01` says whether one model
dominates. The gap between observed `n11` and the independence prediction
`n·p_A·p_B` says whether the errors are correlated. Observed `n11` above
prediction means shared blind spots, so the failure lives in the task. Below
prediction means the models are genuinely complementary, which is the strongest
possible version of the result.

Pairing costs nothing. It is just a shared random seed for operand generation.
Not pairing throws away most of the statistical power.

### 3.2 Two-tier sampling — breadth for the surface, depth for the holes

These pull in opposite directions and both are needed.

**Breadth tier (surface).** To estimate `P(correct | a digits × b digits)` you
want many *different* problems, one sample each. Running the same problem 45
times measures how hard that one problem is, and problems within a cell vary a
lot. A 7×7 with a 1 or a 0 in it is far easier than one made of 8s and 9s. So:
45 distinct instances per cell, one sample each. This tier produces the heatmap
and feeds Claims 1 and 2.

**Depth tier (holes).** A blind spot is a *reproducible* failure. The test that
separates a real hole from bad luck is: take an instance where A fails and B
succeeds, run it 30 more times on each model, and see whether the split holds.
If A fails 30/30 on an instance B gets 30/30, that is deterministic and the
scalar model cannot explain it. If A is at 18/30 and B at 22/30, it was noise.

This is where the user's temp-0 intuition is actually right, and it needs
stating carefully. Deterministic failure is the signature of a genuine hole. But
temperature 0 is the wrong way to look for it (Section 5). Repeated low
temperature sampling on a fixed instance measures the same thing and is
reportable.

Depth tier only runs on cells where the breadth tier already found disagreement,
so it costs a small fraction of the sweep.

### 3.3 Record the mechanisms that could produce size-specific holes

A hole at 8×11 that vanishes at 9×11 is a *size* effect, not an instance effect.
There are three plausible mechanisms, and all three are cheap to record now and
impossible to reconstruct later.

**Tokenizer digit grouping — measured, not assumed.** Run 2026-07-30 on the
actual tokenizers, no GPU required:

| Tokenizer | Rule | 15-digit number |
| --- | --- | --- |
| Qwen2.5, Qwen3 | one digit per token | 15 tokens |
| gpt-oss (o200k family) | groups of 3, left-aligned | 5 tokens, `429\|753\|186\|429\|753` |
| Mistral v0.3 | one digit per token | 15 tokens (+ leading space token) |
| Gemma, Llama | not checked, gated repos | — |

The grouping held in every prompt context tried: bare, after a space, after
`x`, mid-sentence. gpt-oss chunks left-to-right in threes regardless of what
precedes the number, so the alignment is a property of digit count alone.

That yields a prediction registered before any generation was run:

| operand digits | gpt-oss split | tail |
| --- | --- | --- |
| 7 | `429\|753\|1` | ragged, 1 |
| 8 | `429\|753\|18` | ragged, 2 |
| 9 | `429\|753\|186` | clean |
| 10 | `429\|753\|186\|4` | ragged, 1 |
| 12 | `429\|753\|186\|429` | clean |

**gpt-oss should show a period-3 ripple in its residuals. Qwen and Mistral
should show none.** If that appears, Claim 3 stops being "the models differ" and
becomes "the models differ, here is the mechanism, and it was predicted in
advance." If it does not appear, the mechanism is wrong and the residuals need
another explanation.

A second consequence worth measuring: gpt-oss emits answers in 3-digit chunks,
so one wrong token corrupts three digits at once, while Qwen corrupts one. The
two models should differ in error *width*, not only error rate. Record the
digit-level edit distance between the stated answer and truth, not just the
pass/fail bit.

Record, for every problem and every model: the token count of each operand, the
token count of the true answer, and the digit-group boundaries the tokenizer
chose.

**Chosen decomposition.** A model that habitually splits operands into 4-digit
chunks will do better when the digit count divides by 4. Harvestable from the
trace: look for the chunk sizes the model actually used.

**Training density.** Some digit counts appear more often in text than others.
Hard to control, worth naming as an unresolved confound.

---

## 4. The grid

### 4.1 The proposed range is wrong for these models

7 to 45 digits is Opus's band. It comes from the prior project, where a frontier
model with an enormous scratchpad was the subject. A 7-to-8-billion parameter
open model will break far earlier, plausibly between 3×3 and 6×6 digits, and may
already be under 50% at 4×4.

Running 7-to-45 on these models means most of the 780 cells sit pinned at zero.
That violates the "a cell pinned at 0% or 100% buys no information" rule and
would consume the entire budget confirming something already known.

The grid must be centred on where *these* models break, which Stage 1 finds.

### 4.2 Resolution problem, and why the grid solves it

If the live band turns out to be 2 through 8, that is only seven values per
axis, which is coarse for fitting a curve.

The two-dimensional grid fixes this without extra cost. N takes many more
distinct values than the diagonal offers: 2×3=6, 2×4=8, 3×3=9, 2×5=10, 3×4=12,
and so on. A 2-to-9 grid gives roughly 30 distinct values of N from 36 cells.
The diagonal alone would give 8.

### 4.3 Do not mirror the grid

`7×8` and `8×7` are different prompts. Models often handle "big times small"
differently from "small times big", and that asymmetry is itself a candidate
blind spot. Run the full square for a sub-block. If it comes out symmetric
within error bars, fold the rest and say so in the manifest. Assuming symmetry
up front discards a free finding.

### 4.4 Sample count

45 per cell gives a Wilson interval of roughly ±0.14 at p = 0.5 and about
[0.78, 0.96] at p̂ = 0.9. Adequate for a surface, coarse for a single cell.

Saturated cells do not need 45. At n = 10, a result of 0/10 gives a 95% interval
of [0, 0.28], which is enough to call a cell dead. Reserve 45 for cells where
the observed rate falls between roughly 0.15 and 0.85, and spend 10 elsewhere.
On a typical band this cuts total generations by a factor of two to three.

With hundreds of cells and 95% intervals, roughly one cell in twenty will look
anomalous by chance. Fit the surface and read the residuals as a field. Do not
build a story on the single weirdest cell. Any per-cell claim needs a
false-discovery-rate correction across the grid.

---

## 5. Sampling and temperature

### 5.1 What temperature is testing

Nothing, by itself. `p_step` is a property of the tuple (model, prompt, decoding
parameters). Temperature is one of those parameters, so it is a condition on
every number the project reports, not a variable under study.

The practical effect: for arithmetic, the highest-probability token is usually
the correct one, so raising temperature gives more chances to derail and
`p_step` falls. Temperature moves the level. The question worth asking is
whether it moves the *form*.

### 5.2 Why not temperature 0

Three reasons, and they compound.

Greedy decoding is not deterministic on batched GPU inference. vLLM's kernels
reduce in different orders depending on how requests get grouped into a batch,
so logits differ in the low bits. Most of the time nothing changes, but over a
few thousand tokens a near-tie will flip, and one flipped token diverges the
whole trace. The result is variance that cannot be seeded, reproduced, or
reported. That is strictly worse than sampling, where the randomness is ours and
is written down.

Even with perfect determinism, "identical outputs" would only hold per problem.
Across 45 different problems there is still a distribution, and that is the
distribution the grid is measuring. Temperature 0 does not remove the
probability; it relocates all of it into instance variation.

For reasoning models, greedy is a documented failure mode. The R1-family model
cards recommend against it because greedy decoding sends these models into
repetition loops. Running them at 0 measures a pathology.

### 5.3 What to do instead

Use each model's vendor-recommended sampling parameters, fix them, record them.
Do not invent values. Recommended settings are also the fairer cross-company
comparison, since each model gets run the way its makers intend.

Then make temperature a cheap axis rather than a hidden constant. Run one column
of the grid (fix `a`, vary `b` across the band) at three temperatures. If
`ln P vs N` stays straight at each temperature with a different slope, the
exponential form survives a knob we control, and temperature is shown to move
`p_step` without changing the structure. That is real validation for a few
percent of the budget. If the line bends at high temperature but not at low,
that is a finding.

### 5.4 Seeds

Record a seed per generation and pass it to the engine. Note in the manifest
that batch nondeterminism means seeds do not guarantee bit-identical replay on
GPU. They give reproducible *inputs*, which is what matters for regenerating the
problem set.

---

## 6. Reasoning models

Reasoning models are necessary because deployed coding agents are reasoning
models. They also change the economics by roughly an order of magnitude.

**Token cost.** A reasoning model may spend 5,000 to 15,000 thinking tokens on a
problem an instruct model answers in 1,500. Near its boundary, far more.

**Truncation stops being an edge case.** Near the boundary a large share of runs
will hit `max_tokens` mid-thought. Truncation is a third outcome, not a wrong
answer. Folding it into "incorrect" means the probability surface partly
measures the token ceiling instead of the model. Record `finish_reason` and
treat `length` as its own category throughout the analysis.

**Effort is a third axis, and it is out of scope for v1.** The prior project
found effort is not a precision dial: Haiku at medium effort scored worse and
cost more than at low effort on an easy problem. Hold effort fixed, record it,
and list it as a confound.

**Upside: far richer step data.** Thinking traces state hundreds of explicit
arithmetic claims. Harvesting `a × b = c` assertions from free-form text gives a
direct per-step accuracy estimate with no prompt confound, because the model was
never told what format to use. Reasoning models make this tier much stronger.

One rule to fix before harvesting: reasoning models recompute and re-verify, so
a trace contains more assertions than the problem requires. Decide whether to
count every assertion or only unique products. The two give different `p_step`
values, and the gap between them measures how much of the thinking is redundant.
Record both.

**Cross-company confound gets worse.** Labs train reasoning behaviour very
differently. Trace length, self-verification frequency, and give-up behaviour
differ in kind, not degree. There is no way to hold "amount of thinking"
constant across companies. The comparison is therefore "two models as their
makers intend them", not "two models under matched conditions". Say that in the
writeup rather than claiming a control we do not have.

**A cleaner comparison worth running.** Take one family that exposes thinking as
a switch and run the same grid both ways. Does thinking raise `p_step`, or does
it raise `N`? It plausibly does both, and they work against each other. The
essay's argument predicts the verification buys little, because it runs on the
same weights. That is a falsifiable prediction inside a single family, with no
cross-company noise.

---

## 7. Economics

### 7.1 The budget, expressed in tokens

On Modal you rent GPU-seconds, not tokens, so the conversion depends on keeping
the batch full. With vLLM and high concurrency, cost per million output tokens
lands near the same figure across GPU tiers, because the faster card costs
proportionally more:

Modal bills per second, with no charge while idle. Published rates as of
July 2026:

| GPU | $/second | $/hour | est. aggregate output tok/s | est. $ per M output tokens |
| --- | --- | --- | --- | --- |
| A10 24GB | $0.000306 | $1.10 | 2,000 | $0.15 |
| L40S 48GB | $0.000542 | $1.95 | 4,000 | $0.14 |
| A100 40GB | $0.000583 | $2.10 | 4,000 | $0.15 |
| A100 80GB | $0.000694 | $2.50 | 5,000 | $0.14 |
| H100 80GB | $0.001097 | $3.95 | 8,000 | $0.14 |

Rates are Modal's published figures; throughput columns are planning estimates
and get replaced by Stage 1 measurement.

The choice of card barely matters if the batch stays saturated, because the
faster card costs proportionally more. Idle GPU is what costs money, and
per-second billing means the fix is to never leave one provisioned.

**Planning constant: about $0.15 per million output tokens. So $6 buys roughly
40 million output tokens.** Every decision below is measured against that.

**Actual balance: $5.41.** That is roughly 36 million output tokens if the
batch stays full, and materially fewer if it does not. Some Modal accounts carry
a monthly free compute allowance on top of purchased credit; worth checking the
billing page, but the plan below assumes $5.41 is the whole ceiling.

**L40S is the right card here.** It is proven in two existing repos in
`~/Projects` (Section 12), 48GB holds either candidate model with a large KV
cache for batching, and at $1.95/hr it sits between the A10's tight memory and
the H100's price.

### 7.2 What the proposed grid would actually cost

Sizes 7 through 45 is 39 values, or 780 upper-triangle cells. At 45 runs each
that is 35,100 generations. Token cost scales with the number of partial
products, and the average cell in that range is around N = 700.

Using the prior project's traces as anchors (Haiku 10×10 at 13K tokens, Sonnet
45×45 at 62K, Opus 50×50 at 83K), a mid-grid generation runs tens of thousands
of tokens. The sweep totals roughly one billion output tokens.

**That is about $150 with instruct models, and closer to $750 with reasoning
models.** Not $6. The full grid as originally specified is off by a factor of
twenty-five to a hundred and twenty.

### 7.3 What actually fits

Scoping to the live band is what saves it, and costs nothing except running
Stage 1 first.

Assume the band for a 7-to-8B instruct model is 2 through 9. That is 36
upper-triangle cells with a mean N near 30, so generations are short, perhaps
1,500 to 2,000 tokens each.

| Stage | Generations | Est. output tokens | Est. cost |
| --- | --- | --- | --- |
| Boundary hunt, 4 candidate models | ~400 | 1M | $0.15 |
| Instruct grid, 2 models, adaptive n | ~2,400 | 4M | $0.60 |
| Temperature column, 2 models × 3 temps | ~500 | 1M | $0.15 |
| Depth tier on disagreement cells | ~1,200 | 2M | $0.30 |
| Reasoning models, narrow strip only | ~800 | 8M | $1.20 |
| **Total** | | **16M** | **$2.40** |

*Planning estimates.* That leaves better than half the budget as reserve, which
is the right posture, because one run will go wrong.

### 7.4 Where the money leaks

**Weight downloads billed at GPU rates.** Pull the model into a Modal Volume
from a CPU-only function first, then mount that Volume in the GPU container. A
16GB download on a rented A100 is pure waste.

**Cold starts.** Loading weights from Volume to GPU takes a minute or two. Run
the whole sweep inside one container rather than one container per problem.

**Unbounded generation.** A small model on a hopeless problem will loop until
something stops it. Set `max_tokens` before the run, scale it with `a·b`, and
record truncation as an outcome. This is the single most likely way to lose the
budget to nothing.

**Lost work on crash.** Checkpoint results to the Volume per cell. A crash
should cost minutes, not the sweep.

**Idle capacity.** Set the container idle timeout low and keep-warm at zero.

### 7.5 Modal versus a hosted inference API

Together, Fireworks and DeepInfra serve open models per-token and are often
cheaper for bursty small-model work, with no ops at all.

Modal is still the right call, for one reason: reproducibility. A hosted
endpoint can change quantization or serving configuration without telling you,
and the standard here is that a run is reproducible or it is an anecdote. Modal
gives a pinned weight revision, a pinned vLLM version, and full control of
sampling parameters. That is worth the extra effort and probably the extra
money.

Worth being deliberate about rather than defaulting into.

---

## 8. Data capture

### 8.1 Principles

Raw model output is immutable. Scores, parses and aggregates are derived and
regenerable at any time from raw. A parser bug is fixed by rerunning the parser,
never by editing raw.

Analysis reads the manifest, never a filename. Paths may encode `a` and `b` for
sharding convenience, but every record carries its own parameters and nothing
downstream may infer a parameter from a path.

### 8.2 Raw record, one per generation

Written as JSONL, compressed, streamed to the Volume as the sweep runs.

```text
run_id                 unique per generation
sweep_id               links to the manifest
model_key              short name, e.g. "qwen-7b-instruct"
model_revision         exact HF commit hash, not a tag
cell                   {a, b}
instance_id            index into the shared per-cell problem list
sample_idx             which repeat of that instance
operand_a, operand_b   the actual integers, as strings
truth                  the correct product, as a string
prompt_text            full prompt as sent
prompt_hash            sha256 of prompt_text
sampling               {temperature, top_p, top_k, seed, max_tokens, ...}
raw_text               untouched completion, including any <think> tags
reasoning_text         engine-split reasoning field if provided, else null
finish_reason          stop | length | error
usage                  {prompt_tokens, completion_tokens, reasoning_tokens}
started_at, latency_ms
engine                 {vllm_version, dtype, tensor_parallel, gpu_type}
tokenization           {a_token_ids, b_token_ids, a_token_count, b_token_count,
                        truth_token_count, digit_group_sizes}
```

Store both `raw_text` and `reasoning_text`. vLLM can split reasoning content
from the answer with the right reasoning parser, but parsers change. Keep the
untouched string as the artifact of record and treat the split as derived.

### 8.3 Derived records

Regenerable from raw. Written as Parquet for the analysis.

```text
scores:  run_id, parsed_answer, correct, outcome, parse_confidence
         outcome ∈ {correct, incorrect, truncated, refused, unparseable}

steps:   run_id, assertion_idx, lhs_a, lhs_b, stated_result, true_result,
         correct, char_offset, is_duplicate_of
```

The `steps` table is the point of the whole exercise. It comes from a regex
sweep over `raw_text` for arithmetic assertions of the form `a × b = c` (with
all the multiplication symbols and spacing variants models actually use), each
one checked against truth. It gives thousands of direct per-step observations at
zero extra generation cost, and no prompt confound, because the model was never
told what format to use.

`first_error_index` on the steps table gives the survival-analysis view directly:
how far into the chain the run got before the first bad step.

### 8.4 Manifest

One per sweep. Holds everything constant across it: prompt template text, model
list with revisions, sampling parameters, grid bounds, sample-count policy,
`max_tokens` policy, engine version, the seed used to generate the problem set,
estimated cost, and after the run, actual cost and wall time.

Estimate before launching. Record actual after. A run whose spend was never
compared to its estimate teaches nothing about the next one.

### 8.5 Logprobs — one cell only

Per-token logprobs give a third, independent route to `p_step`: the model's own
confidence at each arithmetic assertion, rather than the observed outcome
frequency. Three independent estimates of the same quantity is a strong result
when they agree and a very interesting one when they do not.

Logprobs are also enormous. Top-5 logprobs across a 10,000-token reasoning trace
dwarfs the text itself. Enable them for one boundary cell as a sub-study, never
for the grid.

### 8.6 Layout

```text
runs/<sweep_id>/manifest.json
runs/<sweep_id>/problems/a=<a>_b=<b>.json      shared operand lists
runs/<sweep_id>/raw/<model_key>/a=<a>_b=<b>.jsonl.zst
runs/<sweep_id>/derived/scores.parquet
runs/<sweep_id>/derived/steps.parquet
runs/<sweep_id>/derived/cells.parquet          per-cell aggregates + CIs
```

Problem lists live outside the per-model directories, because every model runs
the same instances. That structure enforces pairing physically rather than by
convention.

---

## 9. Analysis plan

Written before the run, so the analysis is not chosen after seeing the data.

**The surface.** Heatmap of pass rate, `a` on x, `b` on y, one panel per model.
Cell annotation shows n and the Wilson interval. This is the figure for looking
at, not the figure that tests anything.

**The form test.** `ln P` against N, scatter with per-point intervals, fitted
line through the origin. One series per model. Slope gives `p_step`. Residual
plot underneath, because curvature is the finding.

**The step-unit test.** Same axes, re-plotted against `a+b`, `max(a,b)` and
`a·b + a·(b−1)`. The unit that linearizes wins and gets defended in the writeup.

**The two independent `p_step` estimates.** Slope-derived versus
harvested-from-traces, per model, with intervals. If harvested `p_step` runs
higher than the slope implies, either N is undercounted (carries, alignment,
final addition) or the errors are correlated within a trace. Either answer is
reportable.

**The residual map.** Fitted envelope subtracted from observed, per model. This
is the blind-spot map and the core figure for Claim 3.

**The disagreement map.** Per cell, `n10` and `n01` from the paired table, with
McNemar p-values and an FDR correction across the grid. Cells that survive
correction are candidate blind spots and get promoted to the depth tier.

**The correlation figure.** Observed `n11` against the independence prediction
`n·p_A·p_B`, one point per cell. Points above the diagonal mean shared blind
spots. Below means complementary models. This single chart carries the whole
multi-model argument.

**The deployable statistic.** `P(correct | both models produced the same
answer)`, with an interval, per cell and pooled. Also the rate at which both are
wrong *and* agree, since that is the failure mode that makes agreement useless.

**The token-cost curve.** Output tokens against N, per model. Needed to budget
the next sweep, and it is free.

**The tokenizer test.** Residual against operand token count and against
alignment to the tokenizer's digit-group boundaries. If holes line up with group
boundaries, that is the mechanism for Claim 3 and it explains why different
companies have different holes.

---

## 10. Implementation

Five stages. Each has a gate; do not proceed past a failing gate.

### Stage 0 — local, free

Build the entire pipeline on the Mac with a small quantized model. Problem
generation, prompting, generation, answer parsing, step harvesting, scoring,
manifest writing, aggregation, and every chart in Section 9.

Ten problems exercise every code path. Correctness gets proven on the cheapest
hardware that can prove it. Reaching a rented GPU with an unproven pipeline is
how a budget disappears into a typo.

**Gate.** Every figure in Section 9 renders from ten local generations, even if
the data is meaningless. The parser handles commas, spaces, `=`, scientific
notation, and trailing prose. Rerunning the scorer over untouched raw reproduces
the derived tables exactly.

### Stage 1 — boundary hunt and model selection, ~$0.30

Bisect on the diagonal per candidate model: 2×2, 4×4, 8×8, 16×16, n = 5 each.
Find where each candidate crosses roughly 90% and roughly 10%.

Four to six candidates. Pairing across companies is the goal, but the real
selection criterion is **overlapping live bands**. Two models whose boundaries
sit far apart cannot be compared on a shared grid, because they are being
measured in different regions of the surface.

Skip reasoning-tuned distills for the pairing. A DeepSeek distill on a Qwen base
is not cleanly either company, which defeats the point.

This stage also produces the token-cost curve that makes Stage 2's budget real
rather than a guess.

**Gate.** Two models chosen, with overlapping bands, a measured token-cost curve,
and a Stage 2 cost estimate written into the manifest before launch.

### Stage 2 — the instruct grid, ~$0.60

Full upper triangle over the live band, both models, paired instances, adaptive
sample counts (45 in the uncertain range, 10 in saturated cells). Full square
for one sub-block to test the `a×b` versus `b×a` asymmetry.

**Gate.** The `ln P vs N` fit converges, the two `p_step` estimates are within
range of each other, and the disagreement map identifies candidate cells.

### Stage 3 — temperature column and depth tier, ~$0.45

One column at three temperatures, to check the form survives the knob.

Depth tier on cells that survived FDR correction in Stage 2: fixed instances,
30 samples per model, testing whether disagreement is reproducible.

**Gate.** Either reproducible holes exist, or they do not. Both outcomes are
reportable and Claim 3 resolves here.

### Stage 4 — reasoning models, ~$1.20

Narrow strip only, centred on the boundary, where the information is. Same
paired instances. Vendor-recommended sampling. `max_tokens` set from the Stage 1
curve times a generous factor, with truncation recorded.

If one family exposes a thinking on/off switch, run both ways on the same
instances. That comparison has no cross-company noise in it.

### Engineering notes

One Modal function holds the vLLM engine and processes a work queue of
generations, so weights load once. A CPU-only function pre-populates the weight
Volume. Requests submit in large batches to keep the GPU saturated, since
saturation is what makes the cost-per-token figure hold. Results append to the
Volume per cell, so a crash costs minutes.

Gated repositories (Llama and Gemma among them) need a Hugging Face token as a
Modal secret. Test that before the sweep, not during it.

---

## 11. Confound register

Recorded when noticed, not when resolved. A confound in the manifest is a known
limitation; the same confound in one person's head is a defect waiting for a
reader to find.

1. **Prompt style.** Free-form versus prescribed algorithm. Free-form is the
   plan, because prescribing the method makes any procedural error rate an
   artifact of the prescription, which is exactly what the prior project had to
   caveat. The cost is extra variance, since two models may pick different
   decompositions and we are then comparing strategy as well as precision.
2. **Chat template.** Each model has its own. Using each one's native template is
   correct but means the prompts are not byte-identical across models.
3. **Digit tokenization.** Differs across models. A per-token rate is not
   comparable across companies. The step is defined as the single-digit
   arithmetic operation, never the token, and that definition is what makes the
   comparison legitimate.
4. **Vendor-recommended sampling differs per model.** Fair in the sense of "as
   intended", not matched in the sense of "identical".
5. **Reasoning effort held fixed.** Known to matter, deliberately not swept.
6. **Batch nondeterminism.** Seeds reproduce inputs, not bit-identical outputs.
7. **Instance hardness within a cell.** Problems containing 0s and 1s are much
   easier. The breadth tier averages over this; the depth tier deliberately does
   not, and any depth-tier claim is about that specific instance.
8. **Multiple comparisons.** Hundreds of cells, so per-cell claims need FDR
   correction. The surface fit does not.
9. **Model size is not matched to capability.** Two 7B models from different
   companies may sit at very different points. Stage 1 selects on measured band
   overlap rather than parameter count.
10. **Truncation.** `max_tokens` is a design choice that partly determines the
    measured surface near the boundary. Recorded separately and reported.
11. **Substitution.** These are small open models. Findings are about the
    mechanism, not about frontier models. Any claim that needs the frontier
    requires a small number of anchor runs there and must be stated as such.

---

## 12. Repo layout, and what to reuse from ~/Projects

A survey of the sibling projects found working Modal infrastructure and two
competing layout conventions. Both are worth inheriting from, selectively.

### 12.1 Proven Modal code already exists — do not rewrite it

`~/Projects/goblins/goblins-takehome/infra/modal/qwen_grader.py` is the original
and carries hard-won version pins in its comments. `vLLM 0.11.0 +
transformers 4.57.0` on a `nvidia/cuda:12.8.1-devel-ubuntu22.04` base is
documented as a known-good pair, because vLLM 0.6.3 crashed on Qwen2.5's
`rope_scaling` config and transformers 5.0 broke the tokenizer cache. That is
two debugging sessions already paid for.

`~/Projects/car-diagnosis/src/cardiag/modal/modal_qwen.py` is the batch variant,
explicitly ported from goblins. Its structure is the one this project wants: an
`@app.cls` with `@modal.enter()` loading the engine once, then a `@modal.method()`
that takes a list of prompts. Weights load per container, not per request. Its
sibling `serve_qwen.py` is the OpenAI-endpoint variant, useful if the harness
ends up talking HTTP instead of Modal RPC.

Concretely reusable:

- The pinned image definition, verbatim.
- The `huggingface-cache` and `vllm-cache` Modal Volumes, which already exist in
  the account. Weights previously pulled there do not get pulled again.
- The cost guardrails, which goblins documents as verified against Modal's docs:
  `max_containers=1`, `min_containers=0`, `scaledown_window=60`, plus the habit
  of `modal app stop <app> -y` when finished.
- The batch-jsonl in, batch-jsonl out interface, which keeps the harness
  backend-agnostic and makes local Stage 0 runs use the identical code path.

What needs adding: per-generation seeds, logprob capture, `finish_reason`
propagation, and streaming results to a Volume rather than accumulating in the
local process.

### 12.2 Two layout conventions in use, and which to take

`car-diagnosis` is the mature Python pattern: `src/<pkg>/` package layout,
`pyproject.toml` with `uv.lock`, optional dependency groups (`cloud` gates the
Modal dependency so local work does not need it), a gitignored `data/` tree, and
`paths.py` as the single place that resolves directories with an env-var
override. Ruff and mypy are configured to lint the engineered core strictly and
the ported research code lightly, which is a sane compromise this project will
want too.

`agent-capability-threshold` and `claudodidact` use numbered experiment folders
instead: `statistics/explorations/NN_name/` and `experiments/NN_name/`, each with
its own runner script, README or `PREFLIGHT.md`, and an `output/` directory. That
reads as a chronological lab notebook and it works well for a sequence of
one-off probes.

**Take the package layout from car-diagnosis, and the pre-registration habit
from claudodidact.** This project runs one instrument many times rather than
many different probes once, so the code belongs in a tested package, not copied
into per-experiment scripts. But claudodidact's `PREFLIGHT.md` per experiment is
exactly the discipline AGENTS.md asks for: state what result would change your
mind before spending. Every sweep gets a PREFLIGHT written and committed before
launch.

### 12.3 The anti-pattern to avoid

`agent-capability-threshold` names its trace files
`haiku-m601-90e18-4.conv.jsonl`, encoding model, modulus, exponent and index in
the path. AGENTS.md's rule that analysis reads a manifest and never a filename
was almost certainly written because of that. Paths here may shard by cell for
convenience, but every record carries its own parameters and no analysis code
may parse a filename.

### 12.4 Proposed layout

```text
carrychain/
  pyproject.toml          uv, package name matches the project
  uv.lock
  AGENTS.md  CLAUDE.md
  .agents/
  src/carrychain/
    paths.py              single source of directory truth, env-overridable
    problems.py           seeded operand generation, shared across models
    prompts.py            prompt templates, versioned and hashed
    parse.py              answer extraction + arithmetic-assertion harvesting
    score.py              raw -> scores.parquet, steps.parquet
    manifest.py           write/read sweep manifests
    stats.py              Wilson intervals, McNemar, FDR, envelope fitting
    charts/               every figure in Section 9
    modal/
      image.py            pinned image + Volumes, ported from goblins
      weights.py          CPU-only weight prefetch into the Volume
      sweep.py            @app.cls engine + work-queue driver
    local/
      backend.py          same interface, MLX or llama.cpp, for Stage 0
  sweeps/
    NN_name/PREFLIGHT.md  pre-registration, committed before launch
    NN_name/manifest.json
  runs/                   gitignored, raw + derived artifacts
  tests/
  docs/
```

`runs/` is gitignored like car-diagnosis's `data/`, with a `CARRYCHAIN_DATA`
style env override so tests point at fixtures. `sweeps/` is tracked, because the
pre-registration and the manifest are the reproducibility record.

---

## 13. Model selection

Requirements, in priority order: two different companies, ungated weights (a
license-acceptance wall costs a session), thinking mode available, first-class
vLLM support, and small enough that one L40S holds the model with a large KV
cache for batching.

### 13.1 The recommendation

**Qwen3-8B (Alibaba) and gpt-oss-20b (OpenAI).**

Both are Apache 2.0 and ungated, so no Hugging Face license gate and no token
friction. Both are native reasoning models with vLLM reasoning-parser support.
gpt-oss-20b is a mixture-of-experts model with roughly 3.6B active parameters,
so it generates fast despite the parameter count, and in its native MXFP4 form
it needs about 12 to 16GB. Qwen3-8B is dense and needs about 16GB at bf16. Both
sit comfortably on one L40S with room for a deep batch.

The reason this specific pair beats the alternatives is the tokenizer.

Qwen's tokenizer splits numbers into single digits. The o200k-family tokenizer
that gpt-oss uses groups digits, up to three at a time. If the token-boundary
mechanism in Section 3.3 is real, these two models should have holes at
*different digit counts*, and the pattern should be predictable in advance from
the grouping. That converts Claim 3 from "they have different blind spots" into
"they have different blind spots, here is the mechanism, and here is where we
predicted them before looking." That is a much stronger result, and no other
available pair sets it up this cleanly.

**Verify the tokenization claim first.** It takes two minutes, needs no GPU, and
the entire prediction rests on it: load both tokenizers locally, encode the
integers 1 through 10^12, and record where the group boundaries fall. This is
step one of Stage 0. If both tokenizers turn out to split digits identically,
the mechanism story is dead and the pairing choice should be revisited.

### 13.2 Free bonus from Qwen3

Qwen3 exposes thinking as a switch (`enable_thinking`). Running the same
weights both ways gives the thinking-versus-not comparison from Section 6 with
no cross-company noise at all: does thinking raise `p_step`, or does it raise
`N`? That is a second experiment for the price of a flag, and it removes the
need to source a separate non-reasoning model.

Vendor-recommended sampling for Qwen3, to be used as-is rather than invented:
thinking mode at temperature 0.6, top_p 0.95, top_k 20; non-thinking at
temperature 0.7, top_p 0.8, top_k 20.

### 13.3 Candidates for the Stage 1 bake-off

Boundary-hunting four models costs roughly $0.30, which is worth spending to
select on measured band overlap rather than on a guess.

| Model | Company | License | Notes |
| --- | --- | --- | --- |
| Qwen3-8B | Alibaba | Apache 2.0 | ungated, thinking switch, first choice |
| gpt-oss-20b | OpenAI | Apache 2.0 | ungated, MoE so fast, contrasting tokenizer |
| Mistral Small | Mistral AI | Apache 2.0 | dense, good control if the MoE confound bites |
| Gemma (12B class) | Google | gated | needs HF license acceptance + Modal secret |
| Llama (8B class) | Meta | gated, MAU cap | needs acceptance; license is the least clean |

Model families move fast. Confirm current version numbers on Hugging Face before
pinning, and pin a commit SHA rather than `main`, which the goblins code flags as
a known reproducibility gap in its own comment.

### 13.4 The confound this pairing introduces

8B dense against 20B MoE means "company" is confounded with "architecture" and
"parameter count". A difference in blind spots could come from any of the three.

The honest framing: the tokenizer prediction is what rescues this. If holes land
where digit-grouping predicts, the mechanism is identified regardless of
architecture. If they land somewhere else, the result is "these two models have
different holes" without a cause, and the architecture confound has to be stated
plainly. Adding Mistral Small as a dense third model is the cheap insurance, and
Stage 1 already runs it.

### 13.5 Operational notes for two models on $5.41

Finish all work for one model before loading the other. Every swap is a cold
start of one to three minutes of GPU time, which is a few cents each and adds up
if the sweep interleaves.

Prefetch both models' weights into the `huggingface-cache` Volume from a
CPU-only Modal function. CPU time is close to free; pulling 16GB on a rented
L40S is not.

Revised budget against the real balance:

| Stage | Est. cost |
| --- | --- |
| Weight prefetch (CPU only) | $0.02 |
| Stage 1 boundary hunt, 3 to 4 candidates | $0.30 |
| Stage 2 grid, 2 models, non-thinking | $0.60 |
| Stage 3 temperature column + depth tier | $0.75 |
| Stage 4 thinking mode, narrow strip, 2 models | $1.50 |
| **Total** | **$3.17** |
| **Reserve** | **$2.24** |

---

## 14. Open decisions

**The prompt.** Free-form (`A × B = ?`, model picks its own method) or
prescribed. The recommendation above is free-form, for the reasons in the
confound register. This is the largest single lever in the design and it should
be a deliberate choice, not a default.

**Whether temperature-0 runs are worth a small budget line.** The argument
against is in Section 5.2. The argument for is that a coding agent deployed at
low temperature is closer to greedy than to 0.7, so greedy has some external
validity. A compromise: run the depth tier at the lowest temperature the model
cards permit rather than at 0, which keeps the determinism story honest.

**Project name.** `carrychain` names the test case rather than the question, and
carries a term (carry) that does not exist in modular exponentiation, cube
moves, or agent trajectories. `firsterror` is the leading alternative, because
`P = p^N` is exactly the survival function for time-to-first-error, and that name
survives the move off multiplication. Renaming costs one line in AGENTS.md and a
directory move today. It gets more expensive every commit.
