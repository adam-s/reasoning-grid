# v1 labels — frozen

The first labelling pass, against the nine categories in
[../../.agents/reference/flame-rubric-carrychain.md](../../.agents/reference/flame-rubric-carrychain.md).
Read-only. Nothing regenerates these; a script cannot rebuild a judgment.

## Why they are frozen rather than replaced

The nine categories were adapted from the λ-bench variance post, which recorded
**Sonnet 4.6** reasoning about lambda calculus. The rubric says so plainly —
*"Nine, to stay comparable with the λ chart"* — and comparability with that chart
was a design goal at the time.

Applied to **Qwen3-4B** doing long multiplication, two of the inherited
categories do not fit the task:

- `ERROR_CORRECTION` is λ's, near verbatim: detect an error, apply a fix. That is
  a coding move. Qwen does not patch a wrong digit, it recomputes the term. The
  category occurs **0 times in 524 segments**, and it is the only category the
  OODA mapping puts under DECIDE — so the "no decide phase" result is a property
  of an imported category, not of the model.
- `STRATEGY` is λ's `DECOMPOSITION`, whose own definition reads *"choosing
  strategy, planning structure, picking a representation, deciding which helpers
  to write"*. It mixes orienting and deciding because for writing code the
  distinction does not pay. It is also the largest category in both headline
  traces — 33% of A, 31% of B — so a third of the labelled thinking sits in the
  one category that cannot say which phase it belongs to.

A third symptom is coverage rather than fit: 330 of C's 396 segments (83%) are
`ACCUMULATE`. The vocabulary is fine-grained where Sonnet needed it and blunt
where Qwen actually spends its time.

## What survives on its own merits

Splitting λ's single `VERIFICATION` into `RECHECK` and `CROSSCHECK` is
carrychain's own, argued from 516 traces before labelling began, and it carries
the finding. v2 has to earn that distinction again rather than inherit it, but it
is not the reason for the redo.

## What these files are still good for

- The comparison that measures v2's disagreement with v1, per segment.
- The record behind every published v1 number, so a claim that moves can be
  traced to the label that moved it.
- The blind-pass agreement result described in [../README.md](../README.md),
  which is a fact about v1 and does not transfer.
