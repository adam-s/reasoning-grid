# Methods, edge cases, and known defects

For a reader evaluating whether the numbers in this project can be trusted.
Written to be read adversarially. Every defect found so far is listed, including
the ones already fixed, because the fix history is evidence about how the rest
was built.

Status as of 2026-07-30. 626 generations on disk, all Qwen3-4B, on two GPUs,
with reasoning both off and on. No grid has been run and no second model has
been touched. Nothing here is publishable yet.

Measured results live in [RESULTS.md](RESULTS.md). This file is the methods and
the defect register. The design is in [experiment-design.md](experiment-design.md),
sources in [references.md](references.md), and one standing prediction in
[PREREGISTRATION-order-symmetry.md](PREREGISTRATION-order-symmetry.md).

---

## 1. What a single number means

A cell is a pair of digit counts `(a, b)`. One generation is:

1. Draw the `i`-th problem from a per-cell pool seeded on `(seed, a, b)`. The
   pool is fixed at 256; `n` takes a **prefix**, so an n=10 draw is the first 10
   of an n=45 draw. This is what lets sample counts change without breaking
   pairing across models.
2. Render `PROMPT` with the operands. Free-form: the model is told what to
   compute and what the last line must look like, never how to compute it.
3. Generate with recorded sampling parameters and a per-generation seed hashed
   over `(sweep_id, model, a, b, instance_id, sample_idx)`.
4. Extract the final integer, compare to `x*y` computed exactly in Python.

`z` for the cell is the fraction of generations that converged to the exactly
correct product. **Not** a partial-credit score, and not a fraction of digits.

### Why exact match

Any partial-credit metric would have to define distance between integers, and
every natural choice (digit Hamming, relative error, log ratio) makes a
three-digit corruption look either identical to or wildly different from a
one-digit corruption depending on which you pick. Since one of the open
hypotheses is precisely that two tokenizers corrupt digits in different-sized
blocks, a metric with a built-in view on that would beg the question. Exact
match is the only scoring rule that does not encode a hypothesis.

Error *shape* is measured separately, on wrong answers only, and is reported as
a diagnostic rather than folded into `z`.

---

## 2. Outcomes: four, not two

Collapsing these into pass/fail destroys information that cannot be recovered
from stored data.

| outcome | condition | meaning |
| --- | --- | --- |
| `converged_right` | model stopped on its own, answer == truth | success |
| `converged_wrong` | model stopped on its own, answer != truth | genuine error |
| `quit` | model stopped on its own, no parseable answer | behavioural: it declined |
| `grind` | hit the token ceiling | it never finished |

**`grind` is excluded from `z`, not counted as failure.** A truncated generation
measures the token budget, not the model. A cell whose truncation rate is not
near zero is measuring the ceiling and is marked invalid.

**Known interaction (D-9):** `finish_reason` is checked before the answer, so a
generation that produced a correct answer *and then* kept going until truncation
is classed `grind`. 4 of 30 grind records in the current data contain the true
product. Under-counts `z` near the boundary, where grinding concentrates.

---

## 3. Answer extraction — the edge cases

This is where the largest single error in the project occurred (D-1). The parser
has been wrong in both directions.

### What models actually emit

Real tails observed in `runs/`:

```text
ANSWER: 16959492
**ANSWER: 16959492**              <- Qwen3's house style
**ANSWER:** 16959492
\boxed{ANSWER: 16959492}
ANSWER: 16,959,492
ANSWER: 16959492.
ANSWER: 123456<|im_end|>          <- with skip_special_tokens=False
```

### Rules (v4)

Three extraction paths, tried in order, each recorded in `parse_method`:

1. **`ANSWER:`** — the requested format, with markdown/LaTeX decoration allowed
2. **`\boxed{...}`** — the LaTeX convention models reach for unprompted. A
   format violation, not a refusal: the answer is unambiguous
3. **last meaningful line** if it is nothing but a number, skipping LaTeX
   delimiters and horizontal rules

`\boxed` accounted for 23 of 199 corpus tails. Treating it as a refusal is what
caused D-17.

**A parser extracts the model's assertion, not the correct answer.** A fixture
whose expectation is "the truth" conflates the two: in one real case the model
asserted a wrong product while the true value appeared earlier in its own
reasoning. The regression corpus therefore locks *what was extracted and by
which path*, never whether it was right.

Accepted: markdown bold/italic/code around the marker or the number, `\boxed{}`,
`\text{}`, thousands separators (comma, space, NBSP), trailing period, and a
leading sign. Case-insensitive marker. **Last** match wins, since models restate.

Rejected: decimals and scientific notation. An exact product is an integer, so
`ANSWER: 1.2345e7` must not parse as `1`. This is a real observed failure, not
hypothetical.

Fallback: the last non-empty line, only if it is *entirely* a number after
stripping decoration. Deliberately narrow — an earlier version grabbed the last
4+ digit run anywhere in the text, which turned refusals into fabricated wrong
answers and destroyed the `quit` category.

`parse_method` (`marker` / `last_line` / `none`) is recorded per generation so a
cell relying heavily on the fallback can be identified and excluded.

### Open risk: asymmetric parsing across models

**The single largest threat to the two-model comparison.** If the parser handles
Qwen's format and not gpt-oss's harmony channel markers, the blind-spot map
becomes a parser map. `skip_special_tokens=False` means channel markers appear
inline in `raw_text`.

**Gate: the parser must be validated against real completions from BOTH models
before any paired comparison is run.** Not against synthetic examples.

---

## 4. Statistics

### Clustering

Repeats of the same problem are **not** independent trials. Measured intraclass
correlation at 4x4:

| temperature | ICC | design effect (k=5) | effective n from 100 gens |
| --- | --- | --- | --- |
| 0.0 | 0.95 | 4.8 | **21** |
| 0.5 | 0.13 | 1.5 | 66 |
| 1.0 | 0.12 | 1.5 | 66 |
| 1.5 | 0.21 | 1.8 | 55 |
| 2.0 | 0.005 | 1.0 | 100 |

At temperature 0 a naive Wilson interval over 100 generations is **2.3x too
narrow**. Any rate computed over repeated instances must use a cluster-robust
interval on per-instance means, and must report the number of clusters beside
the number of generations.

Stronger still at temperature 0: only 31 of 100 generations were distinct
strings, and 9 of 20 instances produced 5 byte-identical outputs.

### ICC estimator

`mean(p̂(1-p̂))` estimates `(1-1/k)·σ²_w`, not `σ²_w`, so the naive estimator is
biased upward and has a floor near 0.06 when the truth is 0. Correct form:
`MSW = k/(k-1)·mean(p̂(1-p̂))`, `σ̂²_b = var(p̂) - MSW/k`. Report unclamped, with
an interval — 20 clusters gives an ICC of 0.95 a CI of roughly [0.83, 1.00].

### Boundary estimation

An integer bracket ("largest size above 70%") has a resolution of one whole
digit and cannot express the 4.2-versus-4.8 distinction that model selection
turns on. A logistic in `log N` is fitted instead, with a bootstrap over cells,
reporting `d*` = the diagonal digit count at the 50% crossing.

Measured interval width against samples per cell, from real data:

| n per cell | generations | 95% CI width on `d*` |
| --- | --- | --- |
| 8 | 32 | 1.24 digits |
| 16 | 64 | 0.80 |
| 32 | 128 | 0.62 |
| 64 | 256 | 0.42 |

**n=32 is the floor for any pairing decision; n=64 is safe.** And the reference
model must be measured at the same n as the candidates — an error in the
reference is common to every comparison and never averages out.

### The model that is fitted, and what it needs from the design

Fit a **binomial GLM with a logit link** on cell counts, not OLS on `ln p̂`.
`statsmodels.GLM(..., family=Binomial())` takes a `(successes, failures)`
response directly, handles zero-success cells correctly under maximum
likelihood, and returns standard errors. `sklearn.LogisticRegression` is built
for prediction and gives no intervals, which are the entire point here.

The one-parameter form assumes the answer to an open question:

```text
logit(p) = alpha + beta * log(N),      N = a*b
```

The two-parameter form does not, and it is what should be fitted:

```text
logit(p) = alpha + beta1 * log(a) + beta2 * log(b)
```

- If **beta1 == beta2**, difficulty depends only on the product `a*b`, and the
  step unit is the single-digit product. A Wald test on `beta1 - beta2` is the
  test, and it needs no extra data beyond the grid.
- If they differ, the step unit is not `a*b`, and the **size of the gap is the
  operand-order effect** — the same coefficient answers both open questions.

**This is the reason off-diagonal cells are not optional.** On the diagonal
`a == b`, so `log a` and `log b` are perfectly collinear and beta1, beta2 are
unidentifiable. Every generation collected so far is diagonal, so this model
cannot be fitted to any of it. A diagonal-only design is not a cheaper version
of the grid; it is an experiment that cannot answer the question.

For clustered data (instances x repeats), `statsmodels.GEE` with an
exchangeable correlation grouped by instance gives cluster-robust errors
without hand-rolling a design effect. A beta-binomial GLM is the alternative
when the ICC is wanted as an explicit parameter rather than a correction.

### Where to place cells

For a two-parameter logistic the locally **D-optimal design points sit where
p ~= 0.176 and p ~= 0.824**, not at 0.5. Sampling the steepest part of the curve
is the intuitive choice and the wrong one — the shoulders carry more information
about the two parameters jointly. This argues for concentrating cells where the
model is around 20% and 80% rather than the 15-85% band used elsewhere in the
design docs, and it is a stronger reason than budget for not spending everything
at the 50% crossing.

Caveat: D-optimality is *local* — it depends on the parameters you are trying to
estimate. Use it to allocate a second pass after a pilot has located the curve,
never to choose the first pass.

### Streak analysis

Exact DP over current-streak-length, verified against 200k-trial Monte Carlo
(max deviation 0.0013). **Assumes independent trials.** It must not be run over
data containing repeats of the same problem: sorting repeats adjacently produced
an apparent 14-failure run whose iid p-value was 1 in 541,522, when the true
cause was four deterministic problems sitting next to each other.

### Multiple comparisons

With hundreds of cells and 95% intervals, roughly one cell in twenty looks
anomalous by chance. Per-cell claims require FDR correction. Surface fits do
not.

---

## 5. Engine and ordering effects

### Submission position affects output — measured

In 11 of 11 problems where the 5 repeats were not byte-identical, the odd one
out was `sample_idx 0`, the first call. Under random jitter that is `5^-11`.
Repeats 2 through 5 were byte-identical in every case.

So greedy decoding here **is** bit-reproducible once the engine is warm. What
differs is the first call after engine state changes. Prefix caching is the
likely mechanism: the shared prompt head is computed fresh on the first request
and reused afterward, and blocks cached under one batch composition carry that
batch's floating-point low bits.

### Mitigations in place

- **Seeded shuffle** of the whole job list, with a model-independent seed, so
  every model sees the same scrambled order. A systematic order would let an
  engine-state effect masquerade as a capability curve; a per-model random order
  would reintroduce it as between-model noise.
- **Warm-up burn** of throwaway generations before each batch, so no real
  generation lands in the first-call state.
- **`submit_index` recorded** per generation, so the order effect stays testable
  rather than merely diluted.

### Not yet controlled

`enable_prefix_caching` is on by default and is **not recorded per record**.
Disabling it for measurement runs removes the mechanism rather than
standardising it, at a throughput cost. Undecided.

---

## 6. Confound register

1. **Prompt style.** One free-form template. Published work shows
   meaning-preserving format changes move results materially, so the surface is
   partly a property of this template. Unmitigated; a paraphrase arm is the fix.
2. **Chat templates differ across models.** Using each model's native template
   is correct but means prompts are not byte-identical.
3. **Digit tokenization differs.** Measured, not assumed: Qwen, Granite, Falcon
   and Mistral take one digit per token; gpt-oss, Phi-4-mini, SmolLM3 and OLMo-2
   group in threes, left-aligned, context-independently. A rate per *token* is
   therefore not comparable across models; the step is defined as the arithmetic
   operation, never the token.
4. **Vendor-recommended sampling differs** (gpt-oss 1.0, Qwen3 thinking 0.6).
   Running each "as intended" hands one model a temperature advantage, which
   alone produces asymmetric off-diagonal cells in a paired table. Matched
   parameters should be the primary condition; vendor-recommended secondary.
5. **Model size, architecture, quantization and training data** all vary
   alongside company. A difference in blind spots has several candidate causes,
   and only the tokenizer one is testable within a single model (by rewriting
   operands space-separated to abolish grouping, or comma-3 to induce it).
6. **Reasoning effort held fixed**, known to matter, deliberately not swept.
7. **Instance hardness varies within a cell.** A problem containing 0s or 1s is
   far easier. Digit sparsity is a first-class difficulty factor in published
   work and is currently uncontrolled.
8. **Batch nondeterminism.** Seeds reproduce inputs, not bit-identical outputs.
9. **Contamination at small sizes.** 2x2 through 4x4 overlap published
   multiplication tables. Those cells anchor any fit through the origin, so a
   fit should be reported with and without them.
10. **Substitution.** These are small open models. Findings are about a
    mechanism, never about frontier models.

---

## 7. Defect register

Every defect found. Severity is "could it produce a wrong published number".

### Fixed

| id | defect | consequence | how found |
| --- | --- | --- | --- |
| D-1 | Parser rejected `**ANSWER: n**` | 82 of 89 `quit` records actually answered, 58 correctly. Overall rate 0.567 → 0.675. Miss rate *correlated with temperature*, so the reported temperature slope was wrong by a quarter of its magnitude | adversarial audit |
| D-2 | `thinking` defaulted to False | Entire 538-generation campaign ran with reasoning off on a project about reasoning models | user |
| D-3 | `n` in the problem-set seed | An n=10 and an n=45 draw of the same cell shared *zero* problems; adaptive sampling silently destroyed cross-model pairing | adversarial review |
| D-4 | Seed keyed on batch position, then on instance only | Repeats of one instance got identical seeds, so a "30/30 reproducible failure" — the signature the design reads as a blind spot — was guaranteed by construction | adversarial review |
| D-5 | `prompt_text` read a leaked loop variable | Every record stored the *last* problem's prompt. 506 of 532 mismatch their own operands | own check |
| D-6 | Derived scores written into `runs/` as `.jsonl` | `analyze.py runs/*.jsonl` loaded raw and derived together, double-counting every generation and averaging a buggy parse with a fixed one | adversarial review |
| D-7 | Condition keys read with `.get(key, default)` | Would have labelled every reasoning-ON run as reasoning-OFF. D-2 fixed in the generator and re-introduced in the analyzer | adversarial review |
| D-8 | `_save` opened with mode `w`, tag lacked temperature/thinking | A second run silently truncated the first run's raw output | adversarial review |
| D-9 | `correct` computed independently of `finish_reason` | A truncated generation could score as a pass | adversarial review |
| D-10 | Fixed 12,000-token ceiling | Flat above ~11x11, so larger problems got proportionally *less* room — manufacturing a cliff at exactly the sizes under study, indistinguishable from a real one | user |
| D-11 | Dead `seed_base` parameter | Looked like it controlled seeding; did nothing | adversarial review |
| D-12 | Parser v2 was too STRICT | The fix for D-1's permissiveness anchored to `^ANSWER:...$`, which markdown bold breaks. Models write `**ANSWER: n**`. 82 of 89 `quit` records had answered, 58 correctly. Overall rate 0.567 → 0.675, and the miss rate *correlated with temperature*, so the reported temperature slope was wrong by a quarter of its magnitude | adversarial audit |
| D-13 | Boundary fitter diverged silently | Undamped Newton ran to `alpha=1.5e11, beta=-5.5e10` under separation; their ratio happened to give exactly `ln(16)`, so it reported a boundary of **4.00 digits with a zero-width bootstrap interval** on data whose 4x4 cell was at 86%. Truth was 7.54. Fixed with ridge penalty, step limiting and backtracking; verified against an independent grid-search MLE | own check |
| D-14 | Derived scores written into `runs/` as `.jsonl` | `analyze.py runs/*.jsonl` loaded raw and derived together and **double-counted every generation**, reporting 152/200 at a cell with 100 generations — the average of a buggy parse and a fixed parse of the same runs | adversarial review |
| D-15 | `prompt_text` read a leaked loop variable | Every record stored the *last* problem's prompt; 506 of 532 mismatched their own operands | own check |
| D-18 | Manifest keyed on `sweep_id` alone | A sweep spanning two models — which is the point, since they share an order seed — made the second model's manifest **overwrite** the first. Found by running it. Now keyed on (sweep, model), and `order_seed` is recorded so the shuffle is reproducible from the manifest | own check, mid-run |
| D-17 | Parser v3 required a colon after `ANSWER` | Qwen's actual house style is `### Final Answer` then `$$\boxed{1234}$$` — no marker at all — and the last-line fallback saw `$$`. **19 of 20 `quit` records in the smoke grid were correct answers.** Contaminated every run on disk: 133 recovered across 10 files, and the published boundary moved from 8.77 to **9.66 [8.67, 10.43]**. Third incarnation of the same class of bug (D-1, D-12). Fixed by parser v4 plus `tests/test_parser.py`, a 211-case regression corpus built from real tails across four models — the thing that should have existed after D-1 | adversarial audit |
| D-16 | Published essay says "45 repeated runs" | They were 45 **distinct problems**, one sample each. "Repeated runs" tells a statistician the trials are clustered and invites the question "where is your ICC?" The methodology was correct; the caption makes it look wrong | chart review |

### Open

| id | defect | consequence | plan |
| --- | --- | --- | --- |
| O-1 | No manifest exists | Model revision, engine versions, dtype, prefix-caching state, `top_k` unrecorded. Runs are not reproducible from their own artifacts | write before next sweep |
| O-2 | `n_in_cell` counts within the batch, not the cell | Never correct under chunking; wrong by 10-45x | compute in the entrypoint |
| O-3 | `thinking_observed` uses a `<think>` substring | Qwen opens the tag in the *prompt*, so the completion holds only the closing tag; a truncated trace never emits it, so the flag under-reports exactly at the boundary | derive from token ids |
| O-4 | `results_vol` declared, never mounted | No checkpointing. A dead RPC loses a whole batch after the GPU has billed | mount and commit per chunk |
| O-5 | Paired table keyed without `sample_idx`, `thinking`, `top_p` | Repeats collapse last-write-wins; conditions collide silently | key on the full tuple |
| O-6 | No McNemar, no FDR, no agreement statistics | The comparison the project exists to make cannot be reported | implement |
| O-7 | Token-cost fit includes truncated generations | Truncated runs sit exactly at `max_tokens`, so the regression partly recovers the budget formula rather than model behaviour. Produced a negative intercept | exclude truncated, weight by n, report p95 |
| O-8 | `digit_error_width` is a Hamming count, not a run length | Cannot distinguish 3 adjacent corrupted digits from 3 scattered ones — which is exactly the tokenizer prediction. Loses right-alignment when the answer is longer | longest consecutive run after right-alignment |
| O-9 | `n_lo`/`n_hi` live band derived from thinking-OFF data | Would spend 85% of generations on saturated cells once reasoning is on | re-derive from a thinking-ON scan |
| O-10 | `per_step=200`, `base=2000` unmeasured for thinking mode | Thinking-off cost was 4.2 tokens per unit of N, 48x under budget. Unknown for reasoning | measure p95 at the boundary first |
| O-11 | `valid` threshold of 5% truncation is a point estimate | Interacts with n: every n=10 cell is one truncation from being greyed out | Wilson upper bound instead |
| O-12 | Boundary ranked lexicographically | On a full grid, `(12,2)` sorts after `(3,3)` and wins as "largest passing size" | rank by N |

---

## 7b. The framing error, and why it matters

Recorded because it shaped the design, not just the prose.

The convergence chart (running pass rate over 45 trials at one difficulty) was
read throughout this session as a **validity exhibit** — proof that a pass rate
is stable enough to put in a grid cell. That reading is wrong in a way that
inverted the project.

Three of its four visual elements are tautologies. A running mean flattens
because 1/n shrinks, for any process — simulated, a model whose true rate
collapses from 1.00 to 0.50 across the run produces a curve that looks equally
settled. The line stays inside the band because the band is computed from the
line. The specific wiggle is a function of submission order: reshuffling the
same 45 outcomes gives running means anywhere from 0.36 to 1.00, all ending at
the same value.

**The information is in the strip**, not the curve. Passes and failures
interleave at a fixed difficulty with no block structure. That is a claim about
the model, not about the measurement: capability at a given difficulty is not a
threshold the model passes or fails, it is a **rate**. The grid exists to find
which cells are worth opening; the cell's internal structure is the finding.

Practical consequence, and the reason this is in a methods document rather than
a style note: **a single `z` per cell cannot distinguish a rate from a set of
holes.** "Every problem is a 0.778 coin" and "78% of problems are deterministic
passes, 22% deterministic fails" produce *identical* binomial distributions. No
sample size separates them. The per-cell output must be at least `(z, ICC)`,
which requires instances x repeats, not 45 distinct instances x 1 sample.

## 7c. Where 45 came from

Not derived. Traced to
`agent-capability-threshold/statistics/explorations/01_arithmetic_ceiling_scan/runners/amplify_calibrate.py`,
an adaptive difficulty search whose loop stops when a Wilson interval drops
below `--max-ci-width` (argparse default 0.25) and which spends probes in
batches of `--parallel` (default 5). At n=40 the width is 0.2519; at n=45 it is
0.2373. **45 is the first multiple of 5 at which an arbitrary CLI default was
crossed.** With `--parallel 4` it would be 44; with the script's own shadowed
dataclass default of 0.20 it would be ~65.

This project's own measured table (§4, boundary estimation) says n=32 is the
floor and n=64 is safe for a pairing decision. Those numbers were derived. 45
was inherited. They have not been reconciled, and 45 should not be treated as
a constant.

Related: the "useful measurement band 60-90%" label in the published essay is
also a CLI default (`--target-low 0.6 --target-high 0.9`), not a discovered
property.

## 7d. Adaptive n by observed rate is a biased estimator

The plan of "n=45 if the observed rate is between 0.15 and 0.85, else n=10" is
optional stopping. Simulated:

| true p | stops early | E[reported z] | bias |
| --- | --- | --- | --- |
| 0.90 | 74% | 0.927 | +0.027 |
| 0.85 | 54% | 0.887 | **+0.037** |
| 0.80 | 38% | 0.837 | **+0.037** |
| 0.50 | 2% | 0.501 | +0.000 |

Cells that stop early are those whose first 10 draws were extreme, so
conditioning on stopping pushes the estimate outward. Nearly 4 points of upward
bias at the shoulder of the curve, which is where the boundary fit is most
sensitive.

Fix: allocate n from the **fitted surface's prediction** for that cell, or from
an independent pilot that is then discarded — so the stopping decision never
uses the data being estimated.

## 8. What the data cannot support

Stated so a reader does not have to work it out.

- **Nothing about per-step accuracy.** No generation is scored at step level. Any
  `p_step` here is back-solved from whole-problem pass/fail under an assumed
  independent-steps model. Distinguishing "constant `p_step`" from "declining
  `p_step`" requires step-level scoring that does not exist yet.
- **Nothing about the step unit.** On a diagonal, `a·b`, `a+b` and `max(a,b)` are
  monotone transforms of one another and are perfectly confounded. Only an
  off-diagonal grid can separate them.
- **Nothing about reasoning models.** All current data has reasoning disabled.
- **Nothing about between-model blind spots.** One model has been run.
- **Nothing about coding agents.** Long multiplication is a chain of silent,
  unrecoverable steps with no tool use and no feedback. Coding tasks have type
  checkers, tests and the ability to retry. Any transfer claim needs an argument
  this project does not supply.

---

## 9. Prior art

Four published results pre-empt parts of this design. They are cited in
`references.md` and must be cited in any writeup.

- **AI-rithmetic** (Google, Feb 2026) already found period-3 accuracy ripple
  caused by 3-digit tokenizer grouping, via DFT over argument length. Addition
  only, no gpt-oss or Qwen. Our version is a replication extended to
  multiplication and open weights, not a discovery.
- **Faith and Fate** (NeurIPS 2023) published the multiplication grid and the
  local-versus-propagation error split, with code.
- **When LLMs Agree, Are They Right?** (July 2026) measured cross-vendor
  agreement and found it does not certify correctness — models agree on the
  *same* wrong answer above chance.
- **The Illusion of Diminishing Returns** (ICLR 2026) showed per-step accuracy
  is not constant, with self-conditioning as the mechanism. Curvature is the
  expected result, not an open question.

The remaining genuinely novel angles are narrow: agreement-as-verifier on a task
with a near-infinite wrong-answer space (published work used 4-option multiple
choice, where coincidental agreement is inflated), and error *width* versus
error *rate* under different tokenizations.

---

## 9b. Harness validation, 2026-07-31

The `grid` entrypoint had never executed before today. First real run, 36
generations over a 3x3 block of cells, verified against the saved records:

| check | result |
| --- | --- |
| every required field present | pass |
| any field always null | none — `submit_index` now populates |
| `n_in_cell` matches the actual cell count | pass (previously counted the batch) |
| `submit_index` distinct across the sweep | 36/36, range 0-35 |
| `prompt_text` matches its own operands | pass (loop-variable leak gone) |
| seeds distinct | 36/36 |
| both triangles present | (2,3) and (3,2) both drawn |

Four previously-recorded defects confirmed fixed in one run: D-5 (prompt leak),
D-11 (dead seed parameter), O-2 (`n_in_cell`), and the null `submit_index`.

`budget_mode="max"` validated the same day — see RESULTS §1. Truncation fell
from 13 of 48 to 2 of 46 and the boundary moved from 7.54 to 8.77 digits.

## 10. Gates before spending

1. Parser validated against real completions from **both** models.
2. Manifest written, including model revision SHAs.
3. Reference and candidates measured at the same `n`, `n >= 32`.
4. `n_lo`/`n_hi` re-derived from a reasoning-ON scan.
5. ~~Token ceiling validated at the boundary in reasoning mode.~~ **Done** —
   `budget_mode="max"`, see §9b.
6. ~~One chunk proven to finish inside the RPC timeout~~ **Partly done** — the
   `grid` entrypoint runs and its records verify (§9b). Checkpointing to
   `results_vol` is still not wired (O-4); `_save` writes per chunk to local
   disk, so a dropped local process still loses the chunk in flight.
7. Condition keys raise on absence rather than defaulting.
