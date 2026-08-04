# What Qwen actually does — an open-coded inventory

Read before writing the v2 rubric. This is the observation step, not the rubric:
it names moves seen in the traces and cites where, and it deliberately does not
reuse the λ-bench category names. Those names came from **Sonnet 4.6 reasoning
about lambda calculus** and were kept "to stay comparable with the λ chart",
which is how a vocabulary built for one model on one task ended up deciding what
could be seen in another. The frozen v1 labels and the case against them are in
[../../labels/v1-lambda-derived/README.md](../../labels/v1-lambda-derived/README.md).

Method: every segment of A (64), B (64) and C (396) read in order, each described
in plain words. Citations are `TRACE[segment]` against
`derived/segments-*.json`, so every claim here is checkable.

## The traces

| | A | B | C |
|---|---|---|---|
| problem | 2,053,896 × 30,957,123,778 | 80,379,530 × 4,621,821 | 21,028 × 1,506,351,245,407 |
| outcome | correct | wrong | never answered |
| segments | 64 | 64 | 396 |

## The moves

### Getting oriented

1. **Restate the problem.** Write the operands down. `A[0,2,3]`, `B[0,1]`, `C[0]`
2. **Hunt for structure before committing.** Look for common factors, evenness, a
   shortcut. Usually finds nothing and drops it. `A[3,4,5]`, `C[1,2,3]`

### Choosing a route

3. **Float a candidate without taking it.** *"Alternatively, maybe I could…"*
   followed by nothing. `A[1,6,19,43,44,45]`, `B[1,2,27,29,30,31,32,44,45,48,49,50]`
   The single most common discourse move in B, and it produces no work.
4. **Commit to a route.** `A[7,24]`, `B[4,33]`
5. **Abandon a route part-way.** A halves both operands, computes two divisions,
   then drops it `A[5→6]`. A splits recursively four levels deep, then quits:
   *"this is getting really complex"* `A[18→19]`. B reaches a split it has
   already done and notices `B[47]`.
6. **Split recursively.** Break a piece, then break the remainder, then again.
   `A[12→15→16→17]` — structurally different from the flat place-value expansion
   at `A[24,25]`, though both are "choosing a decomposition".

### Doing the work

7. **Compute one piece.** A digit or chunk times the other operand.
   `A[10,13,17,26–29]`, `B[7,9,11,12,35–40]`
8. **Apply a power of ten.** Shift, append zeros, convert. Frequent, and its own
   source of trouble — see move 13.
9. **Add pieces into a running total.** `A[31–36]`, `B[15–20]`, `C[77]`
10. **List the pieces before summing.** `A[30]`, `B[13,41]`

### Checking

11. **Re-run the same computation the same way.** `A[37,38]`, `B[21–25,42,58]`
12. **Check by a method that fails differently.** Casting out nines, mod 10, mod
    100, mod 1000. `A[46–59]`, `B[53]`
13. **Check the scale.** Digit count, magnitude estimate, scientific notation.
    `A[41,42]`, `B[51,52]`, `C[84–86,112–113]`. Not the same faculty as 11 or 12:
    it tests the exponent, not the digits, and it is where two of the three
    traces get into trouble.
14. **Propose a check and never run it.** `A[40,43,44,45]`, `B[27,29,30,31,32,44,49,50]`
15. **Assert the check agreed.** *"Correct."* `A[39,51,55,59]`, `B[22,23,24,25,43,58,59]`

### Trouble

16. **False alarm.** Flag a problem, look, conclude nothing is wrong, change
    nothing. `A[10→11]` (power of ten), `A[41]` (digit count), `B[53→56]` — B
    announces *"There's an error here!"*, discovers it misread its own last
    digit, and continues. All three traces do this at least once and none of them
    ever edits a value as a result.
17. **Conflict.** Two methods return different answers and the model says so.
    `C[78,84,87,95,97,104,111,114,115]`
18. **Adjudicate a conflict — and fail.** Re-verify one side, re-verify the other,
    find both correct, still hold two answers. C does this twice, near verbatim:
    `C[88–94]` then `C[105–110]`.
19. **Lock up.** Emit the same text over and over with no progress.
    `C[118–394]` — 276 segments of one identical sentence, 70% of the trace,
    until the context ends.

### Finishing

20. **State the answer.** `A[60]`, `B[60]`
21. **Write it up after `</think>`.** Presentation of results already obtained.
    `A[61–63]`, `B[61–63]`

## What C shows, and why it decides the category set

C is the trace the v1 labels damage most, so it is worth stating plainly.

C splits 21,028 into 21,000 + 28, computes both parts correctly, adds them at
`C[77]`, and gets **31,675,553,988,418,396** — which is the right answer. It then
checks the sum in scientific notation and writes
`42,177,834,871,396 / 10^16 = 0.00042177834871396`. The correct value is
`0.0042177834871396`. **The check dropped one order of magnitude.**

So the arithmetic was right and the check was wrong. C believes the check. From
`C[78]` onward it holds two conflicting totals and tries to find the error. It
re-derives `21 × 1506351245407` (correct), re-derives `28 × 1506351245407`
(correct), re-does the addition (correct), and re-runs the same broken conversion
(wrong again, the same way). It never questions the check. It never picks a side.
At `C[118]` it collapses into repeating one sentence 276 times.

C is a decision failure held for 280 segments and then a lock-up — and under v1
it is labelled 83% `ACCUMULATE`, which reads as a model that spent its run doing
arithmetic. The single most repeated string in the trace is scored as work.

## What the inherited nine could not see

| move | where it lands under v1 | cost |
|---|---|---|
| 3 — float without committing | `STRATEGY` | the most common move in B is scored as choosing a decomposition |
| 5 — abandon a route | `STRATEGY` | λ had `SURRENDER` for quitting the task; quitting an *approach* has no label |
| 13 — check the scale | `RECHECK` or `CROSSCHECK`, by labeller's choice | the faculty that failed in C is not separable from the ones that worked in A |
| 14 — propose a check, never run it | `STRATEGY` / `CROSSCHECK` | A ran four independent checks and B ran one; both *proposed* about eight. The gap is the finding and it is invisible |
| 16 — false alarm | `RECHECK` | excluded from `ERROR_CORRECTION` by rule, so the one moment the model examines its own answer is scored as re-derivation |
| 17, 18 — conflict, failed adjudication | `RECHECK` / `ACCUMULATE` | 280 segments of a model unable to choose, scored as checking and adding |
| 19 — lock up | `ACCUMULATE` | 276 identical sentences scored as arithmetic. Inverts what C shows |

Two v1 categories do not earn their place:

- **`ERROR_CORRECTION` — 0 of 524.** It names a coding move: find a bug, patch it.
  Qwen does not patch, it recomputes. The behaviour that actually occurs at the
  same moments — move 16, the false alarm — is excluded by the category's own
  definition, which requires a value to change. This category is the *only* one
  the v1 OODA mapping puts under DECIDE, so "the loop has no decide phase" is a
  fact about an imported label, not about the model.
- **`STRATEGY` — 33% of A, 31% of B.** It absorbs moves 2, 3, 4, 5 and 6: five
  distinct things, including the difference between naming an option and taking
  it. That is why the v1 rubric had to list it under both Orient and Decide.

## What survives on its own merits

The split of λ's single `VERIFICATION` into re-derivation (move 11) and
independent check (move 12) is carrychain's own and the traces support it: A ran
mod 9, 10, 100 and 1000 and was right; B re-derived everything and ran one weak
independent check and was wrong. v2 should keep the distinction and re-earn it,
not inherit it. Move 13 argues it needs a third branch rather than two.

## Open questions for the rubric

- **Does the lock-up get a category, or is it out of scope?** 276 identical
  segments are not a cognitive move. A category keeps them visible and honest; it
  also puts 70% of one trace in a bin that means "nothing happened".
- **Does segmentation change?** The ~100-character merge rule turns one repeated
  sentence into 276 segments and one genuine addition into one. Counting the
  lock-up by segment gives it 70% of C by construction.
- **Do proposed and executed checks share a category or split?** They are the
  same words and different work.
