# Classifying a thinking trace into a flame chart

How the λ-bench variance post did it, and what changes for reasoning-grid.

Source: `agent-capability-threshold`, branch `sonnet-variance-demo`, published in
the post's own Methods section. Ten commits went into the classification alone,
ending at `8fa9dff` — *"Strip ALL Haiku-classification artifacts: Opus-only on
this branch."* Smaller models produced charts that looked plausible and were
wrong. Budget for Opus or do not do this.

## The method

**Two passes, both Opus at low effort, traces in parallel.**

**Pass 1 — categorise.** Split the trace at newlines into 30–130 segments. Ask
for exactly one category per segment. Returns `[{index, category}]`.

**Pass 2 — build the tree.** A *second* call on the same segments asks for a
**flat list of `{start, end, label}` ranges** describing the implicit sub-task
hierarchy. Depth is then arithmetic, not a model output:

> Depth = number of ranges that strictly contain a given range. Each segment's
> leaf row sits one depth below its innermost containing sub-task.

That is the trick worth stealing. The model never emits a tree — it emits flat
ranges, and containment derives the nesting. Bars at one depth are guaranteed
non-overlapping and chronological.

**The strict variant** (`22d1b5a`) replaced batch classification with **one call
per segment**, given two segments before and two after as context, target marked
`→ TARGET →`, returning a single uppercase word. **Malformed output fails the
build — no silent fallback.** They moved to this because batch labels drifted.

## Their prompt, verbatim

Kept intact because the *shape* is the reusable part, not the content.

```text
You are classifying ONE segment of a language model's thinking trace into one
cognitive category. The model is solving the LamBench algo_evl task:
implementing a beta-normalizer for Scott-encoded de Bruijn lambda terms in pure
lambda calculus.

**Categories:**
- TASK_SETUP — Reading the prompt, restating what needs to be done, recalling
  encodings/conventions/definitions verbatim.
- DECOMPOSITION — Choosing strategy, planning structure, picking a
  representation, deciding which helpers to write.
- PROCEDURAL_TRACKING — Tracking algorithm state mid-execution.
- ARITHMETIC — RAW NUMERIC COMPUTATION ONLY. **In a lambda calculus task there
  is rarely any ARITHMETIC.**
- EXECUTION — Connective tissue. Use sparingly; prefer a more specific category.
- VERIFICATION — Checking correctness: tracing a worked example, sanity-checking
  a rule, verifying termination.
- ERROR_CORRECTION — Detecting an error and correcting it. 'Wait', 'Actually',
  followed by an actual fix.
- SURRENDER — Giving up.
- SURRENDER_DELIBERATION — Hesitating about whether to continue.

**Decision rules (apply in order):**
1. 'wait/actually/I was wrong' AND proposes a fix → ERROR_CORRECTION.
2. Performs a concrete numeric step → ARITHMETIC.
3. Checking, tracing, or sanity-validating → VERIFICATION.
4. Defines a helper, picks an algorithm, describes 'what I'll do' → DECOMPOSITION.
5. Names variables/depths/indices/cases mid-execution → PROCEDURAL_TRACKING.
6. Quotes the prompt or recalls an encoding → TASK_SETUP.
7. Generic narration AND nothing more specific applies → EXECUTION.
8. Surrender categories only for actual quitting.

**Critical traps:**
- 'Implementing the Y combinator' is DECOMPOSITION, not ARITHMETIC.
- 'Considering whether I need natAdd' is DECOMPOSITION, not SURRENDER_DELIBERATION.
- A segment that LOOKS arithmetic but is generic is DECOMPOSITION because no
  actual numbers are computed.

**Context** (segment to classify is marked with → TARGET →):
       [N-2] {previous}
       [N-1] {previous}
→ TARGET → [N]  {the segment to classify}
       [N+1] {next}
       [N+2] {next}

**Output:** the single uppercase category name for the TARGET segment. Nothing else.
```

Three parts, and only the third has to be earned:

1. **Definitions written for that task**, not generic ones.
2. **Ordered decision rules**, so ties resolve deterministically instead of
   leaving the model to weigh them.
3. **Critical traps** — the confusions that actually occurred. This section can
   only be written after seeing bad charts. Note the shouted caveat on
   ARITHMETIC: the model kept reaching for it.

## What changes for reasoning-grid

**Segmentation.** Splitting at newlines gives them 30–130 segments; it gives us
**213**, because Qwen writes short lines (median 52 chars — `"So 34."`,
`"3+4=7."`). Too fine to label. Merging fragments into the discourse move they
belong to — breaking only at `wait / so / now / let me / therefore / check / …`
and only once a segment exceeds ~100 characters — yields **64 per trace**, back
inside their band, with segments that are recognisable moves.

**The x-axis is not time.** Theirs is wall-clock seconds from streaming
timestamps (`width: 160.94`, `elapsedSeconds: 206.2`). We have no per-segment
timing — only `completion_tokens` for the whole generation. Ours must be
**character offset in the trace**, and the axis has to say so. Arguably better
for this argument: it measures what the model produced, not how fast the GPU ran.

**ARITHMETIC inverts.** Their prompt shouts that arithmetic is rare. Ours is
nothing but arithmetic, so the trap reverses: everything will want to be
ARITHMETIC and the structure will vanish. Ours must distinguish *computing one
partial product* from *summing the partial products*.

**VERIFICATION must split, and this is the whole finding.** Their single
category cannot hold the difference between:

- **re-deriving the same way** — recomputing a step by the same method. Cannot
  detect a systematic slip, because the same faculty that made the error is
  checking it. 94% of wrong runs contain language asserting such a check agreed.
- **an independent check** — casting out nines, a different modulus, a magnitude
  bound. Different failure modes, so it *can* catch what the first cannot. Only
  3% of runs ever use one.

Run A (7×11, correct) used mod 9, mod 10 and mod 100. Run B (8×7, wrong) used
last-digit and digit-count — both structurally blind to an error in the middle
digits, which is exactly where its error was. Mod 9 would have caught it (3 vs
4). Collapsing those into one colour throws away the result.

## Cost, and what to parse

Their strict method is one call per segment. For our pair that is **128 calls**,
after merging — down from 421 at naive newline splitting.

Scope deliberately:

- **Two traces, not five.** The argument is a contrast, and a pair carries it.
- **Merge before classifying.** 64 segments beats 213 on both cost and quality.
- **The pair is fixed**: `7x11` correct (10,077 tok) against `8x7` wrong
  (8,479 tok). Both mid-length, both heavy on verification, opposite outcomes.
- **One rubric, written before labelling starts.** If run A's checks are graded
  more generously than run B's, the comparison is worthless. This is the same
  discipline as a pre-registration and it matters more here, because the labels
  are judgment rather than measurement.
