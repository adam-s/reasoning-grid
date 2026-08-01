# Pre-registration: operand order

Written 2026-07-30, BEFORE the symmetry run returned. Committed so the
prediction cannot be adjusted to fit the result.

## Hypothesis

For an a-digit by b-digit product with a > b, P(a x b) != P(b x a).

## Direction, and why

Longhand multiplication is not symmetric in procedure. The number of partial
products equals the digit count of the operand you multiply BY. If the model
follows the written order:

    123 x 987654321   ->  9 partial products of 3 digits
    987654321 x 123   ->  3 partial products of 9 digits

Fewer, longer steps should compound fewer independent errors than more, shorter
steps. So:

**PREDICTED: P(big x small) > P(small x big).**

The cells under test are written small-first (2x18, 3x12, 4x9), so the
prediction is that their REVERSES score higher.

## What would falsify it

- Reverses score LOWER: the mechanism is real but backwards, and the
  explanation above is wrong.
- No difference at either direction, McNemar p > 0.05 on all three cells: the
  model normalises operand order internally and the grid CAN be folded.

## Secondary hypothesis, same data

All three cells have N = a*b = 36. Under P = p_step^(a*b) they should score
identically regardless of shape.

**PREDICTED: if the three cells differ beyond their intervals, the step unit is
not a*b.** Aspect ratio is 9:1, 4:1 and 2.25:1, so this is a strong shape
contrast at constant N.

## Method

- Same operand PAIR in both directions, so the comparison is paired per
  instance. Separate draws per cell would confound order with instance
  difficulty and could detect nothing.
- Submission order shuffled with a seed independent of direction, so engine
  position cannot track the treatment.
- Exact two-sided binomial (McNemar) on discordant pairs.
- n = 24 per cell per direction, 144 generations. Underpowered for a small
  effect: with 24 pairs, an effect must be roughly 25 points to reach p < 0.05.
  A null here means "no large effect", never "no effect".

## Prior art check

NOT yet done at time of writing. The tokenizer-periodicity prediction in this
project turned out to have been published five months earlier, so operand-order
effects in LLM arithmetic must be searched before this is called a discovery.
A search is running in parallel with the measurement.


---

## Evidence so far (appended 2026-07-31, prediction unchanged above)

**Token cost is symmetric.** Across 12 asymmetric Qwen pairs and 6 gpt-oss
pairs, mean tokens(a×b)/tokens(b×a) = 1.00 and 0.98, with small-first dearer in
exactly half the pairs. Fitting token cost: `a+b` gives R²=0.958, `a·b` 0.937,
but `b` alone only 0.636 — the same as `a` alone at 0.638.

This is evidence **against the mechanism** the prediction rests on. If the model
wrote one partial product per digit of the multiplier, `b` would predict cost
and `a` would not. It looks instead as though operand order is normalised
internally before any work happens.

Token cost is not accuracy, so the prediction is not yet tested. But if the
model canonicalises the order, there is no procedural asymmetry left to produce
an accuracy difference, and the expected result becomes a null.

**The accuracy test still cannot be run from grid data.** `make_problems` seeds
on `(seed, a, b)`, so cells (a,b) and (b,a) draw from different RNG streams and
share zero operands — verified across all six reversed pairs in the 01-smoke
grid. Only the `symmetry` entrypoint builds true swapped pairs. Any order claim
must come from that path.
