# Batch ordering: the long-job tail against the position confound

The order jobs are submitted in is both a cost decision and a validity decision,
and the two pull in opposite directions. This records the measurement on each
side and the decision taken, so the next person does not have to rediscover
the trade-off from a comment.

## The observation

Under continuous batching, vLLM admits sequences from the submitted list in
order and backfills as running sequences finish. A generation that is admitted
late runs with almost nothing beside it: the batch drains, concurrency falls
toward one, and the GPU spends minutes producing a single token stream.

Submitting the longest problems first fixes that. The long jobs start while the
queue is still deep, short jobs fill the slots freed around them, and what is
left at the end is short work that drains quickly. This is the classic
longest-processing-time-first result, and it applies here because our job
lengths are known in advance — output length rises with `N = a*b`, which is the
axis the grid is built on.

## What the tail actually costs

Measured from sweep 07, chunk 0: 128 generations, 778 seconds, Qwen3-4B on
H100, shuffled order.

| progress | elapsed | share of wall time |
|---|---|---|
| 32/128 | 146s | 19% |
| 64/128 | 290s | 37% |
| 96/128 | 447s | 57% |
| 115/128 | 586s | 75% |
| 128/128 | 778s | 100% |

The last 10% of prompts took 176s of 778s — **23% of the run for a tenth of the
work**. Had that tail proceeded at the batch's average rate it would have taken
78s, so **perfect scheduling could recover at most 98s, or 13%**.

Thirteen percent is the ceiling, not the expected saving; real schedulers do not
reach the bound. On a $26 sweep it is somewhere under $3.40.

The effect grows with batch size. A chunk of 128 hides it; one big queue of
1,227 with a handful of 40,000-token generations admitted last would be far
worse, which is the case where this matters.

## The argument against sorting

Sorting by size makes submission position a deterministic function of `N`. The
two then vary together, and a model with both terms cannot be fitted on such a
design — the coefficients are not merely imprecise, they are unrecoverable.
Any engine-state effect that accumulates through a batch would land entirely on
the difficulty coefficient, and the grid would report it as capability.

That is a bad failure to risk, because it is invisible. The curve would still
look like a curve.

## What the position effect actually is

The shuffle was justified in code by the claim that submission position
"measurably affects output". That claim was tested against every valid record
carrying a submission index — 1,310 records across 10 batches of 20 or more,
fitting `correct ~ 1 + log N + relative position` as a logistic.

| term | coefficient | se | z |
|---|---|---|---|
| intercept | 5.836 | 0.443 | 13.18 |
| log N | −1.087 | 0.104 | −10.46 |
| relative position | −0.321 | 0.285 | **−1.13** |

Position is **not significant**. Difficulty dominates by an order of magnitude.

The claim in the comment was stronger than the evidence supporting it. But
"not significant" is not "zero": the interval on the position coefficient runs
roughly −0.88 to +0.24 in log-odds, and the lower end would be a real effect.
Ten batches is a thin basis.

The reason the estimate is available at all is that position is currently
shuffled and therefore decorrelated from `N`. Sorting destroys the only design
that can measure the thing sorting would put at risk.

## Decision

**Keep the seeded shuffle.** The saving is bounded at 13% and realistically
under 10%; the risk is a confound that cannot be detected after the fact and
would corrupt the central measurement.

Conditions that would change this:

- **Chunk sizes grow past a few hundred.** The tail scales with queue depth. At
  1,000+ per batch this should be re-measured rather than assumed.
- **A partial sort.** Sorting by `N` and then applying bounded random
  displacement keeps position and size correlated but not collinear, so both
  terms stay identifiable. Cost: variance inflation on the position estimate,
  which needs more data to overcome.
- **More evidence on the position term.** If a later sweep tightens the interval
  around zero, sorting becomes defensible on the grounds that the confound has
  been bounded rather than assumed away.

## Cheaper ways to the same saving

The tail is a symptom of one queue holding a wide spread of job lengths. Two
options avoid it without touching order:

- **Stratify chunks by size.** Give each chunk a similar mix of `N` rather than
  letting the shuffle deal an unlucky chunk of uniformly huge cells. This
  narrows the spread inside any one batch without correlating position with
  size across the sweep. A run was already lost once to the opposite case —
  nine uniformly large cells with no short generations retiring to free KV
  cache.
- **Separate the extremes.** Run the largest cells as their own sweep at their
  own concurrency. They are a small share of generations and a large share of
  tokens, so they schedule better away from everything else.

Neither has been implemented. Both are cheaper to get right than a sort, because
neither touches the identifiability of the position term.
