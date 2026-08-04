# Categories for Qwen long-multiplication thinking

Derived from the traces in [qwen-move-inventory.md](qwen-move-inventory.md).
Nothing here is defined against a previous scheme, and nothing is kept or dropped
because an earlier scheme had it. Every definition below is written in the
language of long multiplication, because that is what these traces are.

**The earlier labels are out of the labelling path entirely.** They survive
read-only in [../../labels/v1-lambda-derived/](../../labels/v1-lambda-derived/)
as provenance for the methods write-up — a judgment cannot be rebuilt by a
script, so it is kept even when it is not used. No labelling prompt, rubric or
example in this pass may reference them, and no category here is justified as a
replacement for one of them. That reference is what steered the vocabulary the
first time.

Two constraints died with them, and both had been shaping the work:

- **The category count is free.** Nine was chosen to line up with another
  project's chart. The right number is the number of moves that can be told apart
  reliably, measured in the pilot.
- **Segmentation is free.** The merge rule was tuned to land inside another
  project's 30–130 segment band. It should instead follow where Qwen actually
  changes what it is doing.

## What these traces are

Qwen solving an n-digit by m-digit multiplication. The algorithm it reaches for,
in every trace read, is the same: break one operand into place-value pieces,
multiply each piece, shift each result by a power of ten, add the shifted results.
Then check the total, and react to what the check says.

So the categories fall into what the algorithm needs, what checking it needs, and
what happens when a check disagrees with the work.

## Running the algorithm

| label | what it is |
| --- | --- |
| `FRAME` | Restating the problem: writing the operands down, naming how many digits each has, noting they are large. |
| `SURVEY` | Naming a way to proceed without taking it. *"Alternatively, maybe I could…"*, *"maybe there's a common factor"*. Considering. No work follows. |
| `COMMIT` | Taking a specific decomposition. *"Let me write 30,957,123,778 as 30,000,000,000 + 957,123,778."* |
| `ABANDON` | Dropping a decomposition part-way. *"This is getting really complex. Maybe I need to find another way."* |
| `PRODUCT` | Computing one piece: a digit or chunk times the other operand. |
| `SCALE` | Powers of ten. Appending zeros, shifting by place, converting to and from scientific notation. |
| `SUM` | Adding the pieces: alignment, carries, running totals. |
| `REPORT` | Stating the final product, and the write-up after `</think>`. |

`SURVEY`, `COMMIT` and `ABANDON` are three separate moves because Qwen does all
three constantly and they are not the same act. Naming an option costs nothing and
produces nothing; taking one starts work; dropping one ends it. B names roughly
eight ways to verify and runs one.

`SCALE` is its own category because the powers of ten are where these traces
break. D writes 10^16 for 10^15 and has to recover. C's whole failure is one
decimal place in a conversion. Folding shifts into the multiplication or the
addition hides the step that actually fails.

## Checking the work

| label | what it is |
| --- | --- |
| `REDERIVE` | Computing a value again the same way. Catches a slip in transcription, cannot catch a systematic error, because the faculty that made the error is the one checking. |
| `CROSSCHECK` | Testing the digits by a method that fails differently: casting out nines, any modulus, last digit, last two digits. |
| `SCALE_CHECK` | Testing the size rather than the digits: how many digits the product should have, a rough magnitude, a scientific-notation comparison. |
| `CHECK_FLOATED` | Naming a check and not running it. *"Maybe I could check with modular arithmetic."* Then something else happens. |

Three kinds of check, not one, because in these four traces they do four different
things. A runs mod 9, 10, 100 and 1000 and they all pass. B runs a last-digit and
a digit-count check, both structurally blind to an error in the middle digits,
which is where its error is. D's casting out nines **fails**, correctly, and drives
the fix. C's scale check is itself wrong and destroys a correct answer.

`SCALE_CHECK` is separate from `CROSSCHECK` because it tests the exponent, not
the digits, and it has its own failure mode: it is the check that goes wrong in
two of the four traces.

`CHECK_FLOATED` is separate from `SURVEY` because the gap between checks proposed
and checks run looks like a result. Both A and B propose about eight; A runs four
and is right, B runs one weak one and is wrong.

## When a check disagrees

| label | what it is |
| --- | --- |
| `ALARM` | Saying something may be wrong. A flagged suspicion, or two values that do not match. *"There's an error here!"*, *"there is a discrepancy"*. |
| `REVISE` | Changing a value already written down. |
| `STAND` | Looking at an alarm and concluding nothing needs to change. |
| `STALL` | Holding a conflict open: re-checking sides already checked, restating the disagreement, settling nothing. |
| `LOOP` | Emitting the same text again with no new content. |

This is the part the traces argue about, so it gets the most resolution.

- `ALARM` → `STAND` is a false alarm, and every trace does it at least once. B
  announces an error, discovers it misread its own last digit, and continues.
- `ALARM` → `REVISE` is D. Its check fails, it hunts, it finds a power-of-ten
  slip, it changes the value, and it gets the right answer.
- `ALARM` → `STALL` → `LOOP` is C. It holds two totals for 280 segments,
  re-verifies both sides twice and finds both correct, never picks one, and then
  repeats a single sentence 276 times until the context ends.

`LOOP` is a category rather than an exclusion. Those 276 sentences are 70% of C.
Scoring them as addition would say C spent its run doing arithmetic, when it had
stopped doing anything.

## Sixteen, and how the number gets settled

More categories resolve more and label less reliably. A scheme nobody can apply
twice the same way is worse than a coarse one applied consistently.

This is settled by the pilot, not by argument: label a sample twice, report
agreement per category, and merge any category that cannot be applied
consistently into its nearest neighbour. The merge is recorded here with the
number that caused it.

Named in advance, so the call is not made after seeing which answer is
convenient:

- `COMMIT` against `SURVEY` — Qwen often floats an option and takes it in one breath.
- `SCALE` against `SUM` — a shift performed inside an addition step.
- `STALL` against `REDERIVE` — re-checking during a conflict is both at once.

## Labelling conditions

- The labelling prompt contains these definitions and nothing else. No earlier
  category names, no examples carried over, no mention that a previous scheme
  existed.
- A `NONE` option is offered and its rate is reported. A move that keeps landing
  in `NONE` is a category this list is missing.
- Labelled blind to the outcome. Knowing a run was right invites reading its
  checks as more careful than they were.

## The OODA map comes last

No category above was chosen with a phase in mind, and the map is not drawn until
the phase definitions are written separately against Boyd and against these
traces. Deciding the categories with the four phases already in view is how a
category ends up belonging to two of them.

What can be said in advance is that `DECIDE` will not be empty by construction:
`COMMIT`, `ABANDON`, `REVISE`, `STAND` and `STALL` are all decisions, and four of
the five occur in every trace.
