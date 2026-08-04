---
name: red-team-test
description: Launch a red-team reviewer (Opus) to attack reasoning-grid's tests — tautological assertions, fixtures that do not resemble real model output, and the gaps that let the answer parser ship broken four times. Use when the user says "red team the tests", "audit the tests", or after changing the parser or the reducer.
---

# Red-team review (tests)

One agent. Read-only: it reports, it does not edit.

## Why this repo needs it

There is one test file, `tests/test_parser.py`, and it guards the component with
the worst track record in the project. **The answer parser has shipped broken
four times.** Each break was caught by a human noticing an implausible number,
not by a test — so the interesting question is never "do the tests pass", it is
**"what shipped broken while they were passing?"**

Run it first; it needs no pytest:

```sh
python tests/test_parser.py
```

## The attack

For each assertion, ask what change to the parser would leave it green. If the
answer is "a change that alters a published rate", that is a finding.

Concretely:

- **Tautologies.** An assertion that re-implements the parser's own regex, or
  that checks a field the parser copied through unchanged, cannot fail for the
  reason the test exists.
- **Fixtures that do not look like model output.** The corpus is real generated
  text for a reason. A synthetic case that is cleaner than anything a model
  writes tests a parser that will never run. Check the corpus still covers every
  echo form the prompt template invites: the placeholder kept and digits
  appended, digits substituted into the brackets, and the placeholder echoed as
  bare words.
- **Direction blindness.** Past breaks went both ways: correct answers scored as
  refusals, and refusals scored as answers. A suite that only asserts "this
  string parses to this number" misses the second class entirely. Is there a case
  asserting that a non-answer parses to *nothing*?
- **Untested by construction.** `probe/reduce_grid.py` re-derives every score
  from `raw_text` precisely because stored scores go stale — but nothing tests
  the reducer. Pooling by condition, the context-ceiling filter, and the
  four-outcome classification all have no coverage. Say so, and say which one
  would do the most damage unnoticed.
- **Silent narrowing.** A corpus that shrank, a case commented out, a threshold
  loosened to make something pass. Check git history for the assertion, not just
  its current text.

## Report format

Per finding: the assertion, one sentence on what it fails to catch, and a
concrete parser change that would keep it green while moving a published rate.
**A finding without that change described is not a finding.**

Most severe first. If the suite is sound for what it covers, say so and spend the
report on what it does not cover instead.

## Out of scope

Coverage percentages, test naming, parametrisation style, and asking for tests of
code the repo does not have. Recommend a missing test only where you can name the
defect it would have caught.
