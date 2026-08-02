---
name: red-team-review
description: Launch a red-team reviewer (Opus) to find real defects in carrychain's measurement harness and charts — silent data corruption, broken invariants, figures that overstate what was measured. Not style nits. Use when the user asks for a "red team" or "bug hunt", or before publishing a number or a figure.
---

# Red-team review

One agent. Read-only: it reports, it does not edit.

## What counts as a defect here

This repo produces numbers an essay will cite. A crash is cheap — someone sees
it and fixes it. **The expensive defect is the one that yields a plausible
number.** Rank findings by how long a wrong result would survive undetected, not
by how broken the code looks.

Every failure this project has actually shipped produced believable output:

- **The answer parser has been wrong four times**, each in a different
  direction. A parser that scores a correct answer as a refusal moves a cell's
  rate without raising anything that looks like an error.
- **A `defaultdict(lambda: dict(t))` captured running totals**, so 143 of 144
  cells inherited the previous cell's counts.
- **A rate compared as `round(p, 4)` against exact fraction bounds** pushed edge
  cells outside their own interval and doubled a dispersion statistic.
- **A dedup keyed per file** silently used only the first chunk of a
  multi-chunk run.
- **Cost quoted from a token model** while billing is per second — off by 3.6×.
- **A painter's sort that mixed height into the depth key**, so a far peak
  painted over a near valley. The chart looked fine.

## Where to look, in order

1. **`probe/reduce_grid.py`, `probe/bakeoff.py`.** Scoring, pooling, condition
   filtering, outcome classification. Anything that drops or merges records
   without saying so.
2. **The invariants in [AGENTS.md](../../../AGENTS.md).** Each is a rule a defect
   can break quietly. Check specifically: does every model in a comparison see
   the same problems; are all four outcomes preserved rather than collapsed to
   right/wrong; does any cell's context ceiling bind; does every quoted rate
   carry an interval.
3. **`probe/build_*.py` and `blog/src/lib/viz/`.** A chart is a claim. Look for a
   figure showing fewer records than it implies, an axis that is a transform of
   its domain but labelled as the domain, a ramp applied to a quantity it does
   not encode, or a caption whose number is hard-coded rather than derived from
   the data beside it.
4. **`labels/` against the fail conditions in
   [flame-rubric-carrychain.md](../../reference/flame-rubric-carrychain.md).**
   Judgment, not measurement, so nothing downstream catches an error. Check them
   mechanically.

## Report format

Per finding: file and line, one sentence on the defect, and a concrete failure
scenario — inputs or state that produce a wrong output. **If you cannot write
the failure scenario, it is not a finding.**

Most severe first. Say plainly if the code is sound; a short honest report beats
a padded one.

## Out of scope

Formatting, naming, type-annotation coverage, coverage percentages, and anything
already recorded as a known limitation in a run manifest or `sweeps/*/RESULTS.md`.
Those are decisions, not defects.
