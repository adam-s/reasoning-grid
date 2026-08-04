# Measured results

Everything measured so far, with sample sizes and intervals. Nothing here is
an estimate unless labelled one. All Qwen3-4B unless stated.

Session 2026-07-30. Total GPU spend $3.10. 626 generations on disk.

**Read [methods-and-edge-cases.md](methods-and-edge-cases.md) §7 before trusting
any of it** — several of these numbers are the second version, after a parser
defect was found that had scored 58 correct answers as failures.

---

## 1. Capability boundary

Fitted logistic in `log N`, N = a·b, bootstrap CI over cells, truncated
generations excluded.

| condition | boundary `d*` | 95% CI | generations |
| --- | --- | --- | --- |
| **reasoning on, full context, parser v4** | **9.66 digits** | **[8.67, 10.43]** | 48 |
| reasoning on, full context, parser v3 (SUPERSEDED, D-17) | 8.77 | [7.77, 9.62] | 46 |
| reasoning on, formula ceiling, parser v3 (SUPERSEDED, D-10) | 7.54 | [6.12, 8.77] | 70 |
| reasoning **off**, parser v3 (not rescored, also suspect) | 4.57 | [4.00, 5.24] | 31 |

**Two corrections have moved this number 2.1 digits, and both were found by
audit rather than by a test.** Truncation contamination was worth +1.23
(7.54 → 8.77, D-10); the parser missing `\boxed{}` answers was worth a further
+0.89 (8.77 → 9.66, D-17). Rescoring every run on disk with parser v4 recovered
**133 correct answers**, 702 → 835.

**The 7.54 figure was suppressed by truncation and should not be used.** Rerun
with `budget_mode="max"`, granting the engine's full 32,136 tokens instead of
the `2000 + 200N` formula, on the same seeded problems:

| cell | formula mode | max mode |
| --- | --- | --- |
| 8x8 | 6/12, 1 truncated | **8/12, 0 truncated** |
| 10x10 | 3/12, 4 truncated | **4/12, 0 truncated** |
| 12x12 | 0/12, 3 truncated | 0/11, 1 truncated |
| 14x14 | 0/12, 5 truncated | 0/11, 1 truncated |
| **total truncated** | **13** | **2** |

The old estimate sat on the bottom edge of the new interval. Generations were
being cut off mid-work and scored as failures. This is the `grind` outcome
class earning its place: had truncation been folded into "wrong", the boundary
would have been quietly wrong with no signal that anything was off.

**Max mode costs 1.3-1.5x more** — given more room, generations use it (8x8 went
from 10,209 to 15,257 mean tokens). Budget accordingly.

**Reasoning buys 2.7× the chain length** (N 21 → 57) for **35× the tokens**
(4.2 → 150 per unit of N). The intervals do not overlap, so the direction is
solid; the magnitude is not pinned down at these sample sizes.

Cell detail, reasoning on, pooled across GPUs, truncated excluded:

```text
 4x4    6/7   = 86%
 6x6    4/6   = 67%
 8x8   10/19  = 53%
10x10   4/14  = 29%
12x12   1/17  =  6%
14x14   0/7   =  0%
```

**Caveat that undercuts all of it:** truncation runs 8-42% per cell, so by the
project's own 5% validity rule **not one cell qualifies**. The zero at 12x12 is
partly the model failing and partly generations being cut off. Needs a rerun
with `budget_mode="max"`.

---

## 2. Temperature

20 problems x 5 repeats at 4x4, reasoning on, `top_p` pinned at 1.0.

| temp | rate | honest 95% CI | n_eff of 100 | flip rate | ICC |
| --- | --- | --- | --- | --- | --- |
| 0.0 | 0.81 | [0.60, 0.92] | 21 | 2% | 0.94 |
| 0.5 | 0.69 | [0.56, 0.80] | 53 | 42% | 0.22 |
| 1.0 | 0.71 | [0.60, 0.80] | 79 | 40% | 0.06 |
| 1.5 | 0.72 | [0.59, 0.81] | 63 | 40% | 0.15 |
| 2.0 | 0.48 | [0.38, 0.57] | 97 | 43% | 0.01 |

"Flip rate" = how often two runs of the **same** problem disagree.

**Only temperature 2.0 is statistically distinguishable** from greedy
(paired permutation, p = 0.002). Everything from 0 to 1.5 is one blob — an
earlier claim of monotone decline was reading an ordering out of noise.

The real finding is not accuracy, it is **determinism**:

| temp | solved 5/5 | coin flip | failed 5/5 |
| --- | --- | --- | --- |
| 0.0 | 14 | 1 | 5 |
| 0.5 | 3 | 16 | 1 |
| 1.0 | 4 | 15 | 1 |
| 1.5 | 3 | 17 | 0 |
| 2.0 | 0 | 16 | 4 |

One step of temperature converts a world of deterministic passes and
deterministic failures into 16 of 20 coin flips. Sampling **rescues** dead
problems (5 → 1 → 0) and **wrecks** reliable ones (14 → 3). Net loss at this
cell; real mechanism either way.

**Consequence for design:** a per-problem blind spot is only a checkable claim
at temperature 0, where the same problem gives the same answer 98% of the time.
Above it, any disagreement between two models is indistinguishable from
disagreement between two runs of one model.

---

## 3. Convergence — the rate settles at every temperature

Running pass rate over 100 generations at 4x4.

| temp | settles at | within 5 points of final from trial |
| --- | --- | --- |
| 0.0 | 81% | 21 |
| 0.5 | 69% | 37 |
| 1.0 | 71% | 51 |
| 1.5 | 72% | 38 |
| 2.0 | 48% | 25 |

Temperature 2.0 has the **highest** run-to-run disagreement and settles
**faster** than 1.0. Chaos in single answers does not prevent the average being
a stable, measurable quantity — at high temperature every generation carries
fresh information rather than repeating a problem the model already decided.

**Caveat (from the chart review):** a running mean flattens because 1/n
shrinks, for *any* process. Simulated, a model whose true rate collapses from
1.00 to 0.50 across the run produces a curve that looks equally settled. The
flattening is arithmetic, not evidence. What carries information is the raw
outcome strip, not the smoothness of the line.

---

## 4. Reasoning on vs off, same problems

16 identical problems run both ways at temp 0.7.

| | count |
| --- | --- |
| both right | 4 |
| **thinking rescued it** | 6 |
| **thinking broke it** | 3 |
| both wrong | 3 |

Net +3 of 16. McNemar on 9 discordant pairs: **p = 0.508** — underpowered.

Split by difficulty, which is the interesting part:

| cell | rescued | broke | off → on |
| --- | --- | --- | --- |
| 4x4 (easy) | 2 | 2 | 6/8 → 6/8 |
| 6x6 (hard) | 4 | 1 | 1/8 → 4/8 |

Direction matches the hypothesis that reasoning helps where the model is
struggling and does nothing where it is not. Evidence does not establish it.

---

## 5. Tokenizers — measured locally, no GPU

15-digit number, five prompt contexts, grouping identical in all of them.

| company | model | rule |
| --- | --- | --- |
| OpenAI | gpt-oss-20b | **groups of 3**, left-aligned |
| Microsoft | Phi-4-mini-instruct | **groups of 3** |
| HuggingFace | SmolLM3-3B | **groups of 3** |
| AllenAI | OLMo-2-7B-Instruct | **groups of 3** |
| Alibaba | Qwen2.5, Qwen3 | 1 digit per token |
| IBM | granite-3.3-2b | 1 digit per token |
| TII | Falcon3-3B | 1 digit per token |
| Mistral | Mistral-7B, Ministral-8B | 1 digit per token |

Gemma and Llama are `gated=manual` and were not checked.

This is what makes a **within-scale** mechanism test possible: Qwen3-4B against
Phi-4-mini is two ~4B models, two companies, opposite digit grouping, both
ungated, both on an L40S. No need for gpt-oss-20b and its MXFP4 problems.

---

## 6. Engine behaviour

**Greedy is bit-reproducible once warm, and the first call is different.**
In 11 of 11 problems whose 5 repeats were not byte-identical, the odd one out
was `sample_idx 0`. Under random jitter that is 5^-11. Repeats 2-5 were
byte-identical in every case. Likely prefix-cache state; mitigated by a warm-up
burn before each batch.

**Cross-GPU flips are indistinguishable from sampling noise at temp 0.7.**
24 identical problems on L40S and H100: 42% outcome flips, 0% byte-identical
text. But the same card at that temperature flips 40-43% of repeated pairs, so
the test could not isolate hardware. **A clean test needs temperature 0**, where
the same-card flip rate is 2%. Not yet run.

**Throughput is KV-bound, not compute-bound, once reasoning is on.**

| | KV cache | tokens | peak observed |
| --- | --- | --- | --- |
| L40S 48GB | 30.9 GiB | 225,232 | 418 tok/s, and 48 tok/s when starved |
| H100 80GB | 57.9 GiB | 421,904 | 1,132 tok/s |

The H100 costs 2.03× and delivered up to ~15× on large-N cells. **Buy memory
when generations are long.** For small cells the L40S is cheaper — but a grid
must not be split across cards, because GPU would then be confounded with cell
size.

**Throughput scales steeply with batch size** — measured on one H100 container,
identical cells, reasoning on:

| batch | wall s | output tokens | tok/s | $/1k generations |
| --- | --- | --- | --- | --- |
| 48 | 95 | 242,903 | 2,552 | $2.18 |
| 128 | 158 | 635,425 | 4,032 | $1.35 |

The earlier 1,131 tok/s figure came from a single batch of large-N cells where
KV cache throttled concurrency. Applying it to the whole grid overestimated
every cost by ~3.6x. **Cost per generation falls 38% from batch 48 to 128**, and
the grid submits 256. This one $0.36 measurement cut the projected programme
from $57 to $15.

**Token cost declines with problem size:** `tokens_per_N = 452 · N^-0.240`.
226 at N=16, 137 at N=144. So the measurable ceiling on a 32K context is
**N ≈ 276, or 16.6 digits on the diagonal.** 17x17 does not fit. Asymmetric
cells do not escape this — tokens scale with N, not shape.

---

## 6b. Grid sample size, calibrated from this data

The fitted surface (alpha=8.589, beta=-2.126 from 70 real reasoning-on
generations) was used as ground truth to simulate a full 121-cell grid at
several sample sizes, refitting each time. Cost uses the measured token curve.

| design | generations | cost | mean d* error | mean CI width |
| --- | --- | --- | --- | --- |
| flat n=5 | 605 | $0.76 | 0.168 | 0.68 |
| flat n=8 | 968 | $1.21 | 0.109 | 0.57 |
| **flat n=12** | **1,452** | **$1.82** | **0.089** | **0.43** |
| flat n=20 | 2,420 | $3.03 | 0.089 | 0.35 |
| flat n=45 | 5,445 | $6.82 | 0.044 | 0.24 |
| adaptive 20/6 by predicted p | 1,986 | $2.81 | 0.082 | 0.37 |
| adaptive 30/8 by predicted p | 2,948 | $4.20 | 0.069 | 0.30 |

**n=12 is the knee.** n=20 costs 67% more for *identical* point-estimate error
and buys only a narrower interval. n=45 costs 3.7x for half the error.

Note the adaptive rows allocate from the **predicted** p for that cell, not the
observed one — allocating from observed data is the biased estimator in
methods §7d.

This calibration is for the **surface and boundary** only. Distinguishing a
rate from a set of holes is a different question that cell count does not
answer; see methods §7b.

## 6c. Two-model pairing — verified 2026-07-31

Sweep `02-smoke-1to4-2models`: 16 cells (1x1 through 4x4), Qwen3-4B and
gpt-oss-20b, n=6, reasoning on, shared `order_seed`.

| check | result |
| --- | --- |
| distinct `instance_uid` | 96 |
| seen by **both** models | **96** |
| same operands per uid | yes |
| same submission position per uid | yes |
| parse path, gpt-oss | 96/96 `marker` |
| parse path, Qwen | 94 `marker`, **2 `boxed`** |

The paired path works. Every problem reached both models with identical operands
and identical queue position, so paired statistics finally have a valid basis.

The two `boxed` records matter more than they look: under parser v3 they would
have scored as refusals, making Qwen read 98% against gpt-oss's 100% — a 2-point
gap that would have been **pure parser artifact**. That is the cross-model
asymmetry methods §3 names as the largest threat to the comparison, and it
appeared in the very first two-model run.

Rates were 100%/100%, as expected for the saturated corner. This sweep measures
plumbing, not capability.

## 6d. Operand order does not change token cost

From 12 asymmetric Qwen pairs and 6 gpt-oss pairs across both smoke grids:

| model | mean tokens(a×b) / tokens(b×a) | small-first dearer in |
| --- | --- | --- |
| Qwen3-4B | 1.00 | 6 of 12 pairs |
| gpt-oss-20b | 0.98 | 3 of 6 pairs |

And the fit says the same thing — token cost is **symmetric** in the operands:

| predictor | R² |
| --- | --- |
| `a+b` | **0.958** |
| `a·b` | 0.937 |
| `b` alone (the multiplier) | 0.636 |
| `a` alone | 0.638 |

If the model wrote one partial product per digit of the multiplier — the
mechanism behind the pre-registered order prediction — then `b` would predict
cost and `a` would not. They predict equally badly. The likely explanation is
that the model normalises operand order internally before computing, which is
exactly what Goat (2305.14201) hard-codes: *"The larger number of the two is
placed in front and then the smaller one is split."*

**This is about cost, not accuracy.** The accuracy question remains open and
still needs genuinely paired cells — `grid` draws (a,b) and (b,a) from different
RNG streams, so its reversed cells share zero operands.

## 6e. Throughput is driven by cell size, not chunk size

The confound is resolved. Same GPU, same chunk size, different cells:

| run | cells | chunk | tok/s |
| --- | --- | --- | --- |
| 01-smoke | N ≤ 121 | 48 | 1,262 |
| 02-smoke | N ≤ 16 | 48 | **2,456–2,994** |

Chunk size held constant and throughput doubled, so the earlier 48-vs-128
comparison was measuring cell mix. Large cells hold more KV cache per sequence
and throttle concurrency.

**gpt-oss is 5–8× cheaper per generation than Qwen** on identical problems —
392 vs 2,935 tokens at 3x4, 166 vs 1,011 at 1x4. It answers tersely; Qwen writes
long reasoning even on trivial problems. Over a full grid, Qwen is ~87% of the
bill.

## 6f. Self-correction is a function of trace length, not of the model

Regenerate: `python probe/revision_rate.py`

A hand-labelled sample of three traces contained **zero** cases of the model
changing a value it had already written down, and that was reported as a fact
about the model. It is a fact about the sample. Across 2,558 correct, unclipped,
naturally-stopped Qwen3-4B runs:

| trace length | runs | contain a revision | median revisions |
| --- | --- | --- | --- |
| under 5k tokens | 1,274 | 1% | 0 |
| 5k–10k | 572 | 10% | 0 |
| 10k–20k | 605 | 29% | 0 |
| 20k–40k | 107 | **80%** | 2 |

The two labelled traces that produced the zero were 10,077 and 8,479 tokens —
squarely in the band where **90% of runs do not revise**. Finding none was the
expected outcome for traces that length, not a discovery.

Why it happens is mechanical rather than mysterious: a revision needs a conflict
to have been detected first, detection needs a check, and long runs check more.

**This is a text-pattern count, not a label.** It requires an explicit statement
that a written value was wrong, so it undercounts every silent recomputation.
Direction and magnitude are solid; the percentages are a floor. The hand-labelled
`REVISE` category in `labels/v2/` is the accurate instrument on the four traces
that have one.

## 6g. `outcome == "grind"` is merging two different endings

Regenerate: `python probe/revision_rate.py`

A run that locks into repeating one sentence and a run still producing new text
when the ceiling arrives both come out as `grind`. Measured as the share of
unique lines, they separate cleanly — locked-up traces sit near 30%, working ones
near 90%:

| temperature | grind traces | locked up | share |
| --- | --- | --- | --- |
| 0.0 | 34 | 16 | **47%** |
| 0.7 | 85 | 6 | 7% |
| 2.0 | 26 | 0 | 0% |

So degenerate repetition is a temperature-0 behaviour, and the existing finding
that T=0 grinds more is really two findings: it grinds more, and it grinds
*differently*. One labelled trace repeats a single 113-character sentence 276
times — 70% of its segments and 56% of its characters.

This violates the project's own rule against collapsing "stopped early",
"finished long" and "never finished" into one bucket, and it is recorded here
rather than fixed silently: changing the `outcome` vocabulary would rewrite a
field that published numbers already depend on.

## 7. What has NOT been measured

- Any second model. Every number above is Qwen3-4B.
- Operand order (`3x12` vs `12x3`). Test was launched, killed on cost, pre-registered in [PREREGISTRATION-order-symmetry.md](PREREGISTRATION-order-symmetry.md).
- Per-cell ICC. Without it the grid cannot distinguish "every problem is a 0.778 coin" from "78% deterministic passes, 22% deterministic fails" — those give *identical* binomial distributions at any n.
- ~~Any cell that passes the truncation validity rule.~~ **Fixed** — max mode
  brings truncation to 2 of 46, and all but the two largest cells clear the 5%
  rule.
- Cross-GPU determinism at temperature 0.
- Whether higher temperature rescues very hard cells (run in progress at time of writing).
- Whether the revision rate in 6f holds for any model other than Qwen3-4B, and
  whether revising actually helps: 6f counts revisions in runs that were already
  correct, so it says nothing about whether a revision rescued a run or a wrong
  run revised just as often.

---

## 8. Cost actuals

| run | what | cost |
| --- | --- | --- |
| smoke | 6 generations, L40S | $0.10 |
| variance | 500 generations, 5 temperatures, L40S | $1.15 |
| boundary, reasoning on | 40 generations, L40S | $0.57 |
| symmetry (killed) | KV-starved, stopped before timeout | $0.30 |
| boundary, H100 | 48 generations | $0.72 |
| weight prefetch | 9 models, CPU only | $0.02 |
| **total** | **626 generations kept** | **~$3.10** |

Balance ~$21.90 of $25.

Planning constant that held up: **~$0.15 per million output tokens** when the
batch is saturated. It does *not* hold when KV cache is the constraint — the
starved L40S run was effectively 8× that.
