# Sweep 10 — the 14x14 paired grid

Pre-registration. Written before the run, committed before launch.

## The question

Do two reasoning models from different companies stop being reliable in the
**same** places or **different** ones?

If the same, one model is enough and the only question is which is better. If
different, running two vendors buys coverage that no single model provides at
any quality level. This sweep is built to settle that, and nothing else.

## Why this pair

Every earlier candidate failed on capability distance, and distance is what
kills the comparison: when one model is much stronger, the off-diagonal of the
paired table is one-sided and the honest reading collapses to "use the better
one".

Measured on identical 12x12 n=1 grids, temp 0.7, thinking on, H200:

| model | company | d\* (digits at 50%) | projected balance vs Qwen |
|---|---|---|---|
| gpt-oss-20b | OpenAI | 15.66 | 4% |
| **Qwen3-4B** | **Alibaba** | **9.33** | anchor |
| **Phi-4-reasoning** | **Microsoft** | **9.02** | **44%** |
| Phi-4-mini-reasoning | Microsoft | 4.71 | 6% |
| granite-3.3-8b | IBM | 3.74 | 1% |

Balance is `min(only_a, only_b) / (only_a + only_b)`: 50% is perfectly symmetric
disagreement, near 0% means one model dominates. Qwen and Phi-4-reasoning are
**0.31 digits apart**. Nothing else came close.

Two candidates could not be screened at all and are recorded so they are not
retried blind: **EXAONE-Deep-7.8B** fails to import under transformers 4.57.0
(`RopeParameters`), and **Magistral Small** needs vLLM >= 0.19 against our 0.11.0.

## Design

**Grid.** 14x14 full square, 196 cells. Both `3x12` and `12x3` — for a language
model those are different token sequences inviting different procedures, and
folding the grid would erase the asymmetry it exists to measure.

**Allocation.** n = 12 / 6 / 3, assigned by predicted difficulty from the
**union** of both models' fitted curves, never from observed rates (a
data-dependent stopping rule would sharpen the very cliff we are locating).

| tier | cells | n | criterion |
|---|---|---|---|
| live | 96 | 12 | either model between 20% and 80% |
| mid | 42 | 6 | either model between 7% and 93% |
| saturated | 58 | 3 | both models pinned; confirm the bound only |

**1,578 generations per model, 3,156 total.**

**Conditions.** temperature 0.7, top_p 1.0, thinking ON and verified per record,
`budget_mode=max`, seed 20260730, shared `order_seed` so both models meet
identical problems in identical submission positions.

**Ceilings.** Qwen 40,960 and Phi-4-reasoning 32,768 — each model's native
maximum, not a constant we chose. At 14x14 **zero cells** have a predicted mean
generation exceeding either ceiling.

**Hardware.** H200 for both. 15% more per second than H100 and 2-3x the
throughput on this workload, because granting a real ceiling makes lane count
`(HBM - weights) / max_len` and 141GB roughly doubles what is left after
weights. Same card for both models so hardware is not confounded with model.

**Chunking.** 128, giving ~13 checkpoints per model. Two runs have already been
lost whole to a single terminal write.

## Cost

**Estimated $24.80.** Hard stop: past $35, kill it and report.

## What this sweep predicts

Written down now so it cannot be adjusted afterward:

1. ~537 problems where exactly one model is correct, of ~1,578 — a third of all
   work.
2. The split near 291 Qwen-only against 246 Phi-only; McNemar around 3.5,
   **below** 3.84, so neither model is demonstrably better overall.
3. Both surfaces monotone in N, from ~100% at the top-left corner to ~14-15% at
   14x14.
4. Truncation near zero in every cell.

## What would make this a FAILURE

- any `instance_uid` not matched across both models
- `thinking_observed` false on any non-truncated record
- truncation above 5% in any cell (the ceiling bound; that cell is invalid)
- a cell's records disagreeing on `n_in_cell`
- the manifest not reconstructing what ran
- the surface non-monotone in N beyond sampling noise

## Explicitly NOT claimed

- **That the grid reaches zero.** It bottoms out near 14-15%. Both models run
  out of context before they run out of competence: Qwen would need a 22x22 grid
  to reach 2% and its context binds at 16.7. Reaching zero is a property of the
  model's context budget as much as its ability, and this sweep does not have it.
- **Anything about temperature.** One temperature only. A second would halve the
  samples per cell for the primary question; temperature deserves its own budget.
- **Anything about arithmetic ability.** Long multiplication is the instrument,
  chosen because chain length is known in advance and the answer is free to
  compute.
- **That these two models represent their vendors.** Two models, two sizes
  (4B and 14B), one task.
- **Per-cell precision.** At n=12 a true 50% cell reads as 25-75%. The surface
  is estimated from 196 cells jointly; no single cell carries a claim.
