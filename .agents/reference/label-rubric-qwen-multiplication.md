# Labelling rubric — Qwen long-multiplication traces

Written **before** any label is assigned. If the run that got the right answer is
graded more generously than the run that got it wrong, the comparison the post
rests on is worthless, and unlike a measurement nothing downstream catches it.

Categories and the reasoning behind them:
[v2-categories-draft.md](v2-categories-draft.md). Observations they came from:
[qwen-move-inventory.md](qwen-move-inventory.md).

**No earlier scheme appears in this document or in any prompt built from it.** An
earlier set of nine, adapted from a study of a different model on a different
task, is frozen at [../../labels/v1-lambda-derived/](../../labels/v1-lambda-derived/)
for provenance only. Showing a labeller those names is how a vocabulary built for
one task decides what can be seen in another.

## The four traces

| | cell | N | T | tokens | segments | what it shows |
| --- | --- | --- | --- | --- | --- | --- |
| A | 7×11 | 77 | 0.7 | 10,077 | 75 | four independent checks, all pass. The control: nothing to catch |
| B | 8×7 | 56 | 0.7 | 8,479 | 70 | checks blind to a middle-digit error; a wrong answer survives them |
| D | 8×8 | 64 | 0.7 | 10,498 | 88 | two decompositions disagree; the model hunts, finds the slip, and revises |
| C | 5×13 | 65 | 0.0 | 40,704 | 403 | the check is itself wrong, destroys a correct total, run locks up |

D was chosen over a 36,202-token run that shows the same revision driven by
casting out nines. That trace was 304 of a 560-judgment job — 54% of the bill for
one behaviour — and at N=60 it matched the others no better. This one is 84
judgments at N=64. The cost of the swap is stated rather than hidden: the
abandoned trace had an *independent* check catch its error, which would have
completed the set against B (check too weak) and C (check wrong). D catches its
error by re-deriving instead, so the revision is real but the checking argument
is one example short and is made in prose.

Difficulty is held roughly still (N of 56 to 77) so what differs is the run, not
the problem. C is the one temperature outlier, and that is a property of what it
shows: degenerate repetition appears in 47% of T=0 grind traces against 7% at
T=0.7.

Segments come from `probe/segment_trace.py` at `min_chars=100, max_chars=300`,
written to `derived/v2/`. They tile each trace exactly — asserted, not assumed.

## Two labels are computed, not judged

Both are mechanical, so they are reproducible by script and never cost a
judgment call.

- **`LOOP`** — a segment whose whitespace-normalised text is identical to the
  segment immediately before it, in a run of three or more, plus a trailing
  segment that is a proper **prefix** of that text. Asking a model 276 times what
  an identical string means is waste, and the answers would not all agree.
  The prefix clause is not a convenience: a loop that ends because the context ran
  out leaves one emission cut mid-word, which is not identical to its neighbours
  and so escapes the test. Since `LOOP` may not be assigned by judgment, without
  the clause that final fragment would be forced into a label that is wrong.
- **`REPORT`** — any segment after `</think>`. That text is presentation of
  results already obtained, not reasoning. Inside `</think>`, `REPORT` is still
  available by rule 17 for the segment that states the final product.

Computed labels cover 293 of 862 segments — 276 `LOOP`, 17 `REPORT`. The
remaining 569 are judged, one call per **distinct** text, which is **560 calls**.
Counts are produced by `probe/precompute_labels.py`, not quoted from here.

## Categories

### Running the algorithm

| label | what it is |
| --- | --- |
| `FRAME` | Restating the problem: writing the operands down, counting their digits, noting they are large. |
| `SURVEY` | Naming a way to proceed without taking it. No work follows. |
| `COMMIT` | Taking a specific decomposition. *"Let me write 30,957,123,778 as 30,000,000,000 + 957,123,778."* |
| `ABANDON` | Dropping a decomposition part-way. |
| `PRODUCT` | Computing one piece: a digit or chunk times the other operand. |
| `SCALE` | Producing a value by a power of ten: appending zeros, shifting by place, converting to or from scientific notation. |
| `SUM` | Adding the pieces: alignment, carries, running totals. |
| `REPORT` | Stating the final product; all text after `</think>`. |

### Checking the work

| label | what it is |
| --- | --- |
| `REDERIVE` | Computing a value again **by the same method**. Cannot catch a systematic error — the faculty that made it is the one checking. |
| `CROSSCHECK` | Testing the digits by a method that fails differently: casting out nines, any modulus, last digit, last two digits. |
| `SCALE_CHECK` | Testing the size rather than the digits: expected digit count, rough magnitude, a scientific-notation comparison. |
| `CHECK_FLOATED` | Naming a check and not running it. |

### When a check disagrees

| label | what it is |
| --- | --- |
| `ALARM` | Asserting that something may be wrong, or that two values disagree. |
| `REVISE` | Changing a value already written down. |
| `STAND` | Examining an alarm and concluding nothing changes. |
| `STALL` | Holding a conflict open: re-checking a side already checked in this conflict, restating the disagreement, settling nothing. |
| `LOOP` | Computed. See above. |

## Decision rules — apply in order, stop at the first match

1. Identical to the previous segment, in a run of three or more → `LOOP`. *(computed)*
2. After `</think>` → `REPORT`. *(computed)*
3. A value written earlier is replaced with a different one → `REVISE`. This
   includes choosing between two totals already on the table when the choice
   supersedes the one that was standing: a value that was accepted no longer is.
4. A conflict is settled and the value that was standing **survives** → `STAND`.
5. A side of an open conflict is checked that was **already** checked during this
   conflict, and nothing is settled → `STALL`.
6. Asserts that something is wrong, or that two values disagree → `ALARM`.
7. Validates using a **different** method than the one that produced the value —
   any modulus, digit sum, last digit → `CROSSCHECK`.
8. Tests the **size** of a value: digit count, magnitude, scientific-notation
   comparison → `SCALE_CHECK`.
9. Re-derives something already computed, **by the same method** → `REDERIVE`.
10. Names a check and does not perform it → `CHECK_FLOATED`.
11. Drops an approach already under way → `ABANDON`.
12. Names an approach without taking it → `SURVEY`.
13. Chooses a decomposition and proceeds → `COMMIT`.
14. Computes one piece of the product → `PRODUCT`.
15. Adds, aligns or carries across pieces → `SUM`, **even when a shift is
    performed to line them up first**.
16. Applies a power of ten and performs **no** addition → `SCALE`.
17. Restates the problem or the operands → `FRAME`; states the final product → `REPORT`.
18. None of these → `NONE`, and the segment is set aside for review.

Rules 3–6 sit above the checking rules on purpose. A segment that runs a check
**and** announces the result disagrees is doing two things, and which one it gets
decides whether the decide phase is visible at all. The conflict wins.

## Critical traps

Written from the four traces already read, not invented.

- **"Wait" is filler.** Qwen writes it constantly and almost none of it precedes
  a real problem. `ALARM` needs an actual assertion that something is wrong, not a
  discourse marker.
- **A check's category is set by the method, not by what the model calls it.** B
  redoes its whole multiplication and calls it "another method"; it is the same
  decomposition in a different order, so it is `REDERIVE`. The model's claim about
  its own method is evidence of nothing.
- **Digit count and magnitude are `SCALE_CHECK` even though they are weak.**
  Weakness is what the figure should reveal, not something the label decides in
  advance. B's failure has to be visible as *a check that was blind*, not as a
  missing check.
- **Scientific notation is `SCALE` when producing a value and `SCALE_CHECK` when
  testing one.** C's failure turns on this: it converts to compare against a total
  it already has, which is a test.
- **A shift performed in order to add is `SUM`, not `SCALE`.** Rescaling two terms
  to a common exponent and folding them into a running total is one move, and it
  is the addition. `SCALE` is for segments where the power of ten is the whole
  subject and nothing is added. This is written because the first pilot found it:
  every `SCALE`/`SUM` disagreement was a segment doing both, with nothing saying
  which won.
- **Choosing between two competing totals is `REVISE`, not `STAND`.** When a model
  holds two answers and picks the one it had not accepted, the accepted value has
  been replaced. `STAND` is only for an alarm that ends with the standing value
  still standing.
- **A digit sum is `CROSSCHECK`, not `SUM`.** Adding digits to get a residue tests
  the product; adding pieces builds it.
- **Listing pieces in order to add them is `SUM`, not `PRODUCT`.** The pieces
  already exist; that is the addition phase starting.
- **`CHECK_FLOATED` requires that no check follows.** Naming a check and then
  running it is the check. The point of the category is the gap between proposing
  and doing, and it is destroyed if proposals that are honoured are counted too.
- **The first re-derivation in a conflict is `REDERIVE`; the second time round the
  same values is `STALL`.** C re-verifies both sides of its conflict twice, near
  verbatim. Without this rule the second pass reads as diligence.
- **Do not reward the correct run.** Knowing A and D ended right invites reading
  their checks as more careful than they were. Label B and C first, or label all
  four blind to outcome.

## Fail conditions

- Any segment unlabelled, or labelled outside this list.
- `REVISE` assigned where no value changed.
- `ALARM` assigned to a check that passed.
- `LOOP` or `REPORT` assigned by judgment rather than computed.
- `CHECK_FLOATED` assigned where the check was then performed.
- A category used in one trace and never considered in the others.
- Labels assigned after knowing which trace was correct, without a blind pass.
- The `NONE` rate not reported.

## Labelling conditions

- One call per distinct segment text. Context is the two segments before and two
  after, with the target marked. Output is a single label and nothing else.
- Malformed output fails the build. No silent fallback to a default category.
- `NONE` is offered and its rate reported. A move that keeps landing in `NONE` is
  a category this rubric is missing, and the rubric gets amended and reported
  rather than the segment forced.
- Blind to outcome: the prompt says nothing about whether the run was right.

## How the category count gets settled

Sixteen resolves more than a coarser set and labels less reliably. A scheme nobody
can apply twice the same way is worse than a blunt one applied consistently.

The pilot settles it with a number: label the same sample twice, independently and
blind, and report agreement per category.

Three distinctions were named as at risk **before** the first pilot ran, so the
call could not be made after seeing which answer was convenient:

- `COMMIT` against `SURVEY` — Qwen often floats an option and takes it in one breath.
- `SCALE` against `SUM` — a shift performed inside an addition step.
- `STALL` against `REDERIVE` — re-checking during a conflict is both at once.

### Pilot 1 — 20 items, two blind passes: 15/20, and one pair failed

| distinction | agreed |
| --- | --- |
| `COMMIT` / `SURVEY` | 6/6 |
| `STALL` / `REDERIVE` | 5/6 |
| `SCALE` / `SUM` | **2/6** |
| uncontested controls | 2/2 |
| `NONE` used | 0 of 40 judgments |

Two of the three named risks held, including both splits the OODA argument leans
on. No labeller reached for `NONE`, so nothing in this sample is a move the
categories cannot name.

`SCALE` against `SUM` failed. Every one of the four disagreements was a segment
that shifts a term to a common exponent **and then adds it** — one pass read those
as adding, the other as rescaling. The rules gave `SCALE` priority while the text
supports both, so the ambiguity was in the ordering, not in the categories.

**The rule was corrected rather than the category merged, and that is a departure
from what was pre-registered here.** It is recorded rather than quietly repaired,
because "the category failed, so the rule changed" is the move a reader should be
suspicious of. What makes it checkable: the diagnosis is specific (4 of 4
disagreements are the same co-occurrence), and merging would have deleted the
category that names how two of the four traces actually fail — D's `10^16` for
`10^15`, and C's misplaced decimal.

### The stopping rule, written before pilot 2 ran

- Same 20 items. Changing the sample after a failure is the other way to cheat.
- Fresh labellers, blind, same rubric with rules 15 and 16 swapped and the
  `STAND`/`REVISE` gap closed.
- **One attempt.** If `SCALE` / `SUM` does not reach 5 of 6, `SCALE` merges into
  `SUM` and the scheme drops to fifteen. There is no third pilot.

### Pilot 2 — 19/20, all three contested pairs clean

| distinction | pilot 1 | pilot 2 |
| --- | --- | --- |
| `COMMIT` / `SURVEY` | 6/6 | 6/6 |
| `STALL` / `REDERIVE` | 5/6 | 6/6 |
| `SCALE` / `SUM` | 2/6 | **6/6** |
| controls | 2/2 | 1/2 |
| overall | 15/20 | **19/20** |
| `NONE` used | 0 of 40 | 0 of 40 |

The ordering fix worked, and `SCALE` stays a category. Results in
`labels/v2/pilot/`.

The one disagreement is a segment announcing a recomputation by another
decomposition: one pass read the recomputation as following (`REDERIVE`), the
other as merely named (`SURVEY`). That is a real judgment call about whether the
next segment executes, and 1 in 20 of them is acceptable.

### `SCALE` passed by never being used, and that is not a pass

Both passes used `SCALE` **zero** times. `SCALE` / `SUM` agreement is 6/6 because
every one of those six went to `SUM`, not because a labeller successfully told the
two apart.

The sample is at fault, and the fault is in how it was drawn: items were selected
by matching text against `10^|zeros|shift`, which finds shift-**and**-add segments
and misses segments where a power of ten is the whole subject. Those exist —
one trace spends two segments converting `6,161,688 × 10^10` to scientific
notation and back because it does not believe its own exponent, and another
writes `10^16` for `10^15` and has to recover. Neither was drawn.

So `SCALE` is **untested**, not validated. Shipping it on this evidence would
repeat the exact defect this rubric was written to remove: a category kept for a
behaviour nobody demonstrated, which then reads as a finding when it comes back
empty.

**Pre-registered, before the full pass runs:** if `SCALE` is assigned to fewer
than 5 segments across all four traces, it merges into `SUM` and the scheme drops
to fifteen. The count is reported either way, and a zero is reported as a defect
in this rubric rather than as a result about the model.

## Results of labelling

340 distinct judgments across 9 blind labellers, expanded to all 636 segments by
text identity. Validated by `probe/collect_labels.py`: every item labelled once,
no unknown ids, no `LOOP` assigned by judgment.

| category | n | share |
| --- | --- | --- |
| `LOOP` *(computed)* | 276 | 43.4% |
| `SUM` | 72 | 11.3% |
| `REDERIVE` | 62 | 9.7% |
| `PRODUCT` | 40 | 6.3% |
| `SURVEY` | 25 | 3.9% |
| `COMMIT` | 23 | 3.6% |
| `REPORT` | 22 | 3.5% |
| `CROSSCHECK` | 20 | 3.1% |
| `SCALE_CHECK` | 19 | 3.0% |
| `ALARM` | 19 | 3.0% |
| `CHECK_FLOATED` | 13 | 2.0% |
| `STALL` | 12 | 1.9% |
| `FRAME` | 10 | 1.6% |
| `ABANDON` | 7 | 1.1% |
| `STAND` | 6 | 0.9% |
| `SCALE` | 5 | 0.8% |
| `REVISE` | 3 | 0.5% |
| `NONE` | 2 | 0.3% |

Per trace, the two groups the traces were chosen to separate:

| | `REDERIVE` | `CROSSCHECK` | `ALARM` | `REVISE` | `STAND` | `STALL` |
| --- | --- | --- | --- | --- | --- | --- |
| A — checks pass | 6 | 14 | 1 | 0 | 1 | 0 |
| B — checks blind, wrong | 10 | 2 | 3 | 0 | 2 | 0 |
| D — conflict found, revised | 13 | 4 | 4 | 2 | 2 | 0 |
| C — check wrong, lock-up | 33 | 0 | 11 | 1 | 1 | 12 |

40 segments of decide machinery, 11% of everything outside the lock-up.

### Agreement: 72%, and that is worse than the scheme it replaces

A reproduction pass over a seeded random third of the worklist, fresh labellers,
same rubric:

| | agreement | 95% interval |
| --- | --- | --- |
| this scheme, 76 items | **55/76 = 72%** | 61–81% |
| the previous scheme, 245 items | 84% | 79–88% |

**The intervals do not overlap.** These labels are measurably less reproducible
than the ones they replace, and that is the one measure that decides whether
anyone can trust them. It is stated first because everything else about the
rebuild improved, and that makes it easy to bury.

The cause is one rule. `REDERIVE` sits at position 9, above `PRODUCT` (14) and
`SUM` (15), and in long multiplication almost any step can be read as recomputing
something already computed. It absorbed **11 of 21** disagreements: `SUM` → 6,
`PRODUCT` → 3, `REPORT` → 1, `STALL` → 1.

**This defect was already found and fixed once, and this rubric threw the fix
away.** The previous rubric carried an amendment written mid-labelling: a
re-derivation only counts when the value is *still live in the current line of
work*, otherwise a model that abandons an approach and later recomputes the same
sub-product is computing it for the first time, not checking it. That amendment
was discarded along with the vocabulary it was written against. Throwing out the
labels was right; throwing out the amendment was not, and it cost 12 points of
agreement.

The fix is known and not applied here: `REDERIVE` should require the value to be
still live *and* the segment's purpose to be checking rather than producing.
Testing it costs one reproduction pass.

### Two gaps the `NONE` option found

2 of 636, both real, neither yet a category:

- **Probing an operand's structure.** Factorising 21028 into 2² × 7 × 751 to hunt
  for a shortcut. Real arithmetic, so not `SURVEY` ("no work follows"); not a
  piece of the product, so not `PRODUCT`; abandoned, so not `COMMIT`.
- **Declaring the work done.** *"After verifying several steps and checking for
  inconsistencies, I believe the final result is correct."* Names no value, so
  rule 17 cannot reach it, and there is no conflict for `STAND` to settle.

### `SCALE` survived by one label

Exactly 5 against a threshold of 5. One judgment either way flips it. Reported
as the knife-edge it is rather than as a pass.

## What is not decided here

The OODA mapping. Phase definitions get written separately, against Boyd and
against these traces, and the map is drawn only after labelling is done. Choosing
categories with the four phases already in view is how a category ends up
belonging to two of them.
