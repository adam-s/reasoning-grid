# Pre-registration: does the loop appear in ordinary coding?

Written 2026-08-03, BEFORE any coding traces are labelled. Committed so the
prediction cannot be adjusted to fit the result.

## Why this run exists

The blog opener claims a reasoning model runs Boyd's loop, and offers three
kinds of evidence: Qwen on long multiplication, three sizes of Claude on long
multiplication, and five Sonnet runs on one lambda calculus task.

The obvious dismissal is that arithmetic is a chain by construction. Long
multiplication *has* to decompose into ordered steps that consume each other's
output, so finding an ordered, state-carrying process in an arithmetic trace
proves nothing about reasoning. The lambda task was supposed to answer that, and
it only half does: implementing a beta-normaliser is still a single closed
problem with a known decomposition and no external state.

Ordinary coding is the harder case, and the one a reader actually cares about.
Reading an unfamiliar codebase and wiring libraries together has no canonical
decomposition, no fixed step count, and no arithmetic anywhere.

## Hypothesis

Traces from ordinary coding tasks contain the same moves already labelled in the
multiplication and lambda traces, and every one of Boyd's four phases is
occupied.

## What would falsify it

- **A phase comes back empty.** Most likely DECIDE, which is what happened to
  the first reasoning-grid mapping and was a defect in the category definitions
  rather than a finding about the model. A second empty DECIDE, under
  definitions written before the run, would be a real result.
- **The moves are there but the ordering is not.** If phases occur in no
  particular sequence and nothing carries between them, "the model runs a loop"
  is the wrong description and "the model emits text in four registers" is the
  right one. This is the outcome the current evidence cannot rule out, and it is
  the one worth designing for.
- **The labeller cannot reach agreement.** If blind labellers disagree on
  ordinary coding segments at a materially worse rate than on multiplication
  segments, the rubric does not transfer and no result from it is reportable.

## Design

- **Tasks: 5, chosen before any run, spanning what "coding" actually means.**
  Reading an unfamiliar codebase to answer a question; adding a feature that
  touches more than one file; fixing a failing test; wiring a third-party
  library into existing code; a refactor with no behaviour change. One task per
  category, so no single flavour of work carries the claim.
- **Models: two, from different companies**, matching the pairing discipline
  the grid already uses. Same tasks, same prompts, same settings.
- **Runs: 3 per task per model.** 30 traces. The lambda post used 5 runs of one
  task to measure variance; this run is measuring presence, so breadth across
  tasks beats depth within one.
- **Labelling: one call per segment with neighbour context**, the strict variant
  described in [flame-classification.md](../.agents/reference/flame-classification.md).
  Batch labelling drifted there and would drift here.
- **The rubric is written and frozen before the first trace is labelled**, and
  it is written for coding, not inherited. The multiplication rubric's sixteen
  categories were rebuilt from Qwen traces precisely because the lambda nine did
  not fit; assuming either transfers to coding would repeat the mistake in the
  other direction.
- **The phase map is written at the same time as the rubric**, and checked
  against the rule that no single arguable placement can empty a phase. See the
  judgment calls recorded in [ooda.ts](../blog/src/lib/design/ooda.ts).

## The measurement that is actually new

Presence of the four phases is the weak claim, and a four-bucket scheme this
loose will come back full for almost any deliberate process. The claim the blog
opener needs, and does not yet have, is that **state carries between steps**.

So this run reports two things, and the second is the point:

1. Occupancy per phase, per task, per model.
2. **Whether a segment's content depends on an earlier segment's output.** For
   each ACT segment, whether a value, name, or decision it uses first appeared
   in an earlier segment of the same trace. A trace where acts are independent
   of everything before them is four registers, not a loop.

Item 2 needs its own definition before the run, and it is the part to get right.
Without it, this is a more expensive way to say what the existing traces already
say.

## Cost

Labelling is one call per segment. Coding traces segment coarser than Qwen's
(Qwen's median line is 52 characters; code and prose about code run longer), so
expect 40–120 segments per trace, call it 80.

    30 traces x 80 segments = ~2,400 labelling calls

Plus the generation itself, which is 30 runs on two hosted models and is the
cheap half. Estimate before launching and record actual after, per AGENTS.md.
This is small next to a GPU sweep, and it is not small enough to run twice
because the rubric was not settled first.

## What the blog may say if it holds

> and in ordinary coding, where the work is reading a codebase and wiring
> libraries together rather than computing anything

Until then the opener says *a coding task*, singular, and links to the lambda
post, which is what the evidence supports.
