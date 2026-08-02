# Classification rubric — carrychain multiplication traces

Written **before** any labelling. If run A's checks get graded more generously
than run B's, the comparison the post rests on is worthless — and unlike a
measurement, nothing downstream will catch it.

Method and provenance: [flame-classification.md](flame-classification.md).

## The two traces

| | run A | run B |
|---|---|---|
| cell | 7×11 (N=77) | 8×7 (N=56) |
| outcome | **correct** | **wrong** |
| tokens | 10,077 | 8,479 |
| truth | 63582712699139088 | 371499**799724**130 |
| answered | 63582712699139088 | 371499**719424**970 |
| checks used | mod 9, mod 10, mod 100 | last digit, digit count |

Both verified. Both concluded they were right. B's error sits in digits 7–12 of
15, where its two checks are structurally blind — mod 9 would have caught it
(answer 4, truth 3), and so would mod 11 (4 vs 0) or mod 100 (70 vs 30).

Labelling B confirmed something sharper than the design assumed. All seven of
B's partial products are correct, and **their sum is the truth**. The whole error
is one addition — the last one, where `80,379,530` is added as if it were
`80,370`. B then spent 40% of its trace verifying: it re-derived every partial
product (all already correct), reproduced the total by a "second method" that was
the same decomposition reordered, and checked the last digit and the digit count,
both of which a middle-digit error cannot disturb. At segment 58 it names casting
out nines and drops it in the same sentence: *"let me check the sum of the digits,
but that might not help."*

## Categories

Nine, to stay comparable with the λ chart. Two differ from theirs, and both
differences carry the argument.

| category | label | what it is |
|---|---|---|
| `TASK_SETUP` | Setup | Reading the problem, restating it, naming the operands. |
| `STRATEGY` | Strategy | Choosing *how* to decompose — split by place value, distributive property, "break into chunks". Choosing, not doing. |
| `PARTIAL_PRODUCT` | Partial | Computing **one** piece: a digit times a chunk, one row of the long multiplication. |
| `ACCUMULATE` | Sum | Aligning and adding the partial products. Carries, place-value shifts, running totals. |
| `STATE_TRACKING` | State | Naming where it is — which chunk, which power of ten, what the running total holds. Bookkeeping, not computing. |
| `RECHECK` | Recheck | Re-deriving something **by the same method**. "Let me check that" followed by the same multiplication again. |
| `CROSSCHECK` | Crosscheck | Validating by a **different** method with different failure modes: casting out nines, any modulus, last-digit, digit count, magnitude bound. |
| `ERROR_CORRECTION` | Correction | Detecting a specific error **and changing a value**. |
| `RESULT` | Result | Stating the final product, including the post-`</think>` write-up. |

Dropped from λ: `EXECUTION` (their own prompt says use it sparingly; our
discourse-merge segmentation already absorbs connective tissue), `SURRENDER` and
`SURRENDER_DELIBERATION` (neither trace quits — if a segment does, use
`STATE_TRACKING` and flag it for a rubric revision rather than inventing a label
mid-pass).

### Why RECHECK and CROSSCHECK are separate

This is the finding. λ has one `VERIFICATION`, and one colour cannot show that:

- **RECHECK** re-runs the same computation with the same faculty that produced
  the error. It cannot detect a systematic slip — only a transcription slip.
  94% of wrong runs across the whole sweep contain language asserting such a
  check agreed.
- **CROSSCHECK** uses a method whose failure modes differ, so it *can* see what
  the first cannot. Only 3% of runs ever reach for one.

A chart that paints both the same colour shows two traces that verified equally
hard and says nothing about why one worked.

### Why ARITHMETIC splits

λ's prompt shouts that arithmetic is rare in lambda calculus. Ours is nothing
but arithmetic, so a single `ARITHMETIC` would swallow the trace and erase all
structure. `PARTIAL_PRODUCT` and `ACCUMULATE` are genuinely different phases:
one is many independent small multiplications, the other is a single long
dependent chain where a carry error propagates.

### OODA mapping, for the post

Stated so the prose and the colours cannot drift apart:

| OODA | categories |
|---|---|
| Observe | `TASK_SETUP`, `RECHECK`, `CROSSCHECK` |
| Orient | `STRATEGY`, `STATE_TRACKING` |
| Decide | `STRATEGY`, `ERROR_CORRECTION` |
| Act | `PARTIAL_PRODUCT`, `ACCUMULATE`, `RESULT` |

`STRATEGY` spans orient and decide because in these traces the two are not
separable in text — the model states a plan and commits in the same breath. Say
so in the post rather than pretending the boundary is clean.

## Decision rules — apply in order, stop at the first match

1. Says wait/actually/that's wrong **and a value changes** → `ERROR_CORRECTION`.
2. Validates using a **different** method than the one that produced the value
   (any modulus, digit sum, last digit, digit count, magnitude) → `CROSSCHECK`.
3. Re-derives something already computed, **by the same method** → `RECHECK`.
4. Computes one piece of the product → `PARTIAL_PRODUCT`.
5. Adds, aligns or carries across partial products → `ACCUMULATE`.
6. Chooses or reconsiders a decomposition → `STRATEGY`.
7. Names position, chunk, power of ten, or what a running total holds, without
   computing → `STATE_TRACKING`.
8. Restates the problem or the operands → `TASK_SETUP`.
9. States the final answer → `RESULT`.

## Amendment, made during labelling

**Rule 3 applies only to a value still live in the current line of work.** A
model that abandons an approach part-way and later recomputes the same
sub-product is computing it for the first time in the path that reaches an
answer, not checking it. `PARTIAL_PRODUCT`, not `RECHECK`.

This came up because A abandons its first decomposition at segment 18 without
ever producing a total, then recomputes several of the same terms at 26–29. B's
second pass is unaffected: it re-derives values that had already produced the
answer it was checking, so those stay `RECHECK`. Written down because without it
the same text gets two labels depending on which trace it sits in.

## Results of labelling

Both traces, 64 segments each, against the fail conditions above: all pass, no
category appears in one trace and not the other.

| | A (correct) | B (wrong) |
|---|---|---|
| verification, share of trace | 36% | **40%** |
| `CROSSCHECK` : `RECHECK`, segments | **17 : 3** | 9 : 14 |
| `ERROR_CORRECTION` | 0 | 0 |

**The kind of checking separates these runs, not the volume.** A put most of its
verification into methods with different failure modes and reached mod 1000. B
put more than half into re-deriving what it had already derived, and its deepest
independent check was one digit.

**Two of those numbers are load-bearing on one unaudited judgment.** The
amendment above decides four segments, `A[26]`–`A[29]`. Removing it moves A to
17:7 and lifts A's verification share to 46%, which reverses "B verified more":

| | with the amendment | strict rule 3 |
|---|---|---|
| A crosscheck : recheck | 17 : 3 | 17 : 7 |
| A verification share | 36% | 46% |

B's 9:14 and 40% do not move. What survives either labelling is the direction —
A is crosscheck-dominant, B is recheck-dominant, and the two spend a similar
share of the trace checking. **Only that is safe to publish** until a blind pass
settles those four segments, and the post is written to the safe version.

A mechanical cross-trace consistency check found no other exposure: all 201
distinct segments compared pairwise with digits stripped produced three
similar-but-differently-labelled pairs, and all three are correct under the
rules. The scientific-notation calls are consistent across all three traces.

**A prediction in the traps section missed.** It expected roughly four
corrections per trace and got zero in 128 segments — neither model ever changed
a value it had written down. Both raised exactly one false alarm (A at 41, B at
53) and both talked themselves back out of it. The ~4 figure came from a
different unit (newline splits) on a different sample, and does not survive at
this granularity. Two traces cannot settle how often models self-correct, but
they are enough to say the estimate was not measuring the same thing.

**A is not the careful one.** At segment 5 it halves both operands and states
the problem "becomes" a product that is one quarter of the answer. It never
notices. It escapes by abandoning the route as unhelpful. What separates these
runs is not that A made fewer mistakes — it is that the path A finished on got
checked by something that could see.

## Critical traps

Written from 516 traces already read, not invented.

- **"Wait" is usually filler.** Median 33 per correct trace and 45 per wrong
  one, against ~4 actual corrections. `ERROR_CORRECTION` requires a *value that
  changes*. "Wait, let me check that" then confirming the same number is
  `RECHECK`.
- **The check's category is decided by the method, not the intention.** Both
  runs say "let me verify". A uses mod 9; B counts digits. Rule 2 versus rule 3
  turns only on whether the method differs from the one under test.
- **Digit-count and last-digit are CROSSCHECK**, even though they are weak.
  Weakness is what the chart should reveal, not something the label decides in
  advance. B's failure must be visible as *a crosscheck that was blind*, not as
  a missing crosscheck.
- **Listing partial products in order to add them is `ACCUMULATE`**, not
  `PARTIAL_PRODUCT`. The products already exist; this is the sum phase starting.
- **The text after `</think>` is `RESULT`**, even when it re-derives the whole
  thing. It is presentation, not reasoning, and folding it into `ACCUMULATE`
  would inflate the act phase in both traces equally and misleadingly.
- **A digit sum is not `ACCUMULATE`.** Adding digits to get a residue is
  `CROSSCHECK`; adding partial products is `ACCUMULATE`.
- **Do not reward the correct run.** Knowing A is right invites reading its
  checks as more careful. Label B first, or label both blind to the outcome.

## Segmentation

Newline splitting yields 213 and 208 segments — λ used 30–130 — because Qwen
writes fragments (median 52 chars: `"So 34."`, `"3+4=7."`). Merge each fragment
into the discourse move it belongs to: break only at a marker
(`wait / so / now / first / let me / therefore / check / alternatively / …`)
and only once the accumulated segment exceeds ~100 characters.

Result: **64 segments per trace**, median 195 characters, inside λ's band.

## Positioning

- `start` and `width` are **character offsets** in the raw trace, not seconds.
  We have no per-segment timing. Label the axis "position in the reasoning".
- Depth by containment, exactly as λ: a second pass emits flat
  `{start, end, label}` sub-task ranges; depth is the number of ranges strictly
  containing a given one; each leaf sits one below its innermost container.

## Fail conditions

- Any segment unlabelled, or labelled outside the nine.
- `ERROR_CORRECTION` assigned where no value changed.
- A category used in one trace and never considered in the other.
- Sub-task ranges that overlap at the same depth.
- Labels assigned after knowing which trace was correct, without a blind pass.
