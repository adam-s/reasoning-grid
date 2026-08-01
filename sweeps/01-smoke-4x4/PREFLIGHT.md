# Sweep 01 — 4x4 smoke grid

Pre-registration. Written before the run. Committed before launch.

## Purpose

Prove the full grid pipeline end to end on a 16-cell grid before committing to
the 196-cell version. **This is a pipeline test, not a measurement.** No number
from it is publishable; n is far too small.

Secondary: produce the first real x/y/z surface, however coarse, so the chart
code has something to render.

## What is being tested that has never run together

1. `grid` entrypoint against **two models** in one sweep (only ever run on one)
2. A **manifest** written before launch and closed after (never done — open gate #2)
3. **Paired instances** across two models, verified by `instance_uid`
4. `budget_mode="max"` inside `grid` (only tested via `boundary`)
5. Per-chunk checkpointing to disk under a real sweep id
6. The analysis path from raw → cells → fitted surface, on a genuine grid

## Corrections made before launch

Four defects found reviewing this plan against the code, all fixed:

1. **`grid` could not express a sparse cell list.** It built `range(lo, hi+1)`,
   so `lo=2 hi=11` would have produced a dense 10x10 = 100 cells, 1,200
   generations and **$2.28** against a $0.69 balance. Added an `axes` parameter
   taking an explicit list.
2. **`grid` did not accept `budget_mode`**, so it would have defaulted to
   `formula` and re-triggered the truncation defect fixed yesterday. Added, and
   defaulted to `max`.
3. **`instance_uid` did not exist.** This document claimed pairing would be
   verified by it. Now implemented as `sha256(seed|a|b|x|y)[:16]` and carried on
   every record, so two records refer to the same problem iff the uid matches.
4. **No manifest code existed**, though this document promised one. Now written
   before the first generation with status `open`, and closed afterward with
   actual counts, tokens and per-batch timing.

## Design

**Cells.** 4x4 = 16 cells, axes `a, b ∈ {2, 5, 8, 11}`.

Chosen so N spans 4 → 121, i.e. from saturated to nearly dead, rather than
1-4 which would be uniformly ~100% and test nothing about the surface. Includes
8 asymmetric pairs (2x5 and 5x2 etc.) so the order question is exercised.

| | b=2 | b=5 | b=8 | b=11 |
|---|---|---|---|---|
| **a=2** | N=4 | N=10 | N=16 | N=22 |
| **a=5** | N=10 | N=25 | N=40 | N=55 |
| **a=8** | N=16 | N=40 | N=64 | N=88 |
| **a=11** | N=22 | N=55 | N=88 | N=121 |

**Models.** `Qwen/Qwen3-4B` and `openai/gpt-oss-20b`.

Both, despite the known capability gap (8.77 vs ~14.8 digits), because the point
is to exercise the paired path. The gap means the *comparison* will be
uninformative; that is expected and is not what this sweep is for.

**n.** 6 per cell, flat. Not Neyman — flat n makes it obvious if allocation code
misbehaves, and 6 is enough to see a surface shape without spending.

**Conditions.** reasoning ON, `budget_mode="max"`, temperature 0.7, `top_p` 1.0,
same seeded problem pool as every prior run (`seed=20260730`).

**GPU.** H100 for both. Same card for both models so hardware is not confounded
with model. gpt-oss requires it (MXFP4); Qwen runs there too.

**Volume.** 16 cells × 6 × 2 models = **192 generations**.

**Command** (the `axes` argument is what makes it 16 cells, not 100):

```
modal run probe/bakeoff.py::grid --model "Qwen/Qwen3-4B" --gpu h100 \
  --axes "2,5,8,11" --n-live 6 --n-saturated 6 --n-lo 0 --n-hi 99999 \
  --thinking "true" --budget-mode "max" --chunk 128 --sweep-id "01-smoke-4x4-qwen"
```

## Cost

Estimated tokens: Σ 6·505.2·N^0.714 over the 16 cells, ×2 models ≈ 1.1M.
At the measured 4,032 tok/s on H100 plus two cold starts (~107s and ~73s):

**≈ $0.55.** Hard stop: if it exceeds $1.00, something is wrong — kill it.

## What would make this a FAILURE

Not the numbers. The pipeline failing in any of these ways:

- any record missing a field the analysis needs
- `instance_uid` not matching across models for the same cell and index
- a cell's records not all carrying the same `n_in_cell`
- `thinking_observed` disagreeing with `thinking_requested` on non-truncated runs
- truncation rate above 5% in any cell (would mean `budget_mode=max` did not work)
- the manifest not reconstructing what ran
- two chunks writing to the same file

## What would make it a SUCCESS

All of the above clean, plus a surface that is monotone in N — high at N=4,
low at N=121 — for both models. Anything non-monotone at n=6 is noise, not a
finding.

## Explicitly NOT claimed by this sweep

- Any boundary estimate (n=6 gives intervals ~±0.4)
- Any statement about operand order (underpowered by an order of magnitude)
- Any model comparison (the two models are known to be badly mismatched)
