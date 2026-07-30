# AGENTS.md

Canonical instructions for coding agents in this repo. Agent-specific entry
points (e.g. [CLAUDE.md](CLAUDE.md)) reference this file; shared reference
material lives under [.agents/](.agents/).

**This file holds generalized principles only — never a specific fact, path,
constant, model id, or price.** Concrete things live where they can be verified:
the code, the run manifests, and [.agents/reference/](.agents/reference/). A
measured constant carries its justification where it is defined, never in a
document beside it that can drift. If a rule here names one instance, it is in
the wrong place: rewrite it as a principle, or move the fact to the file that
owns it.

**A reference cited here is a step, not background.** When its subject comes up,
open it.

## What this repo is

A measurement harness that builds one artifact: a grid. Each cell is a problem
size, each cell is run many times, and the cell's value is the probability the
model returns the exactly correct answer.

**The purpose is to find where each model stops being reliable, and whether two
models from different companies stop in the same places or different ones.**

That second half is the point. If two models fail on the same problems, one
model is enough and the only question is which is better. If they fail on
different problems, then running two models from different vendors buys
something a single model cannot provide at any quality level. That is a claim
about how to build systems on top of these models, and it is settled by data
rather than by argument.

Long multiplication is the instrument, not the subject. It is used because the
chain length is known exactly in advance and the correct answer is free to
compute. An n-digit by m-digit product decomposes into a countable number of
single-digit operations, so the difficulty axis is not estimated, it is
arithmetic. Nothing here is a claim about whether models can do arithmetic.

The grid is the deliverable. Everything else — per-step rates, tokenizer
effects, give-up behaviour — is read off the grid afterward, and none of it
justifies compromising the grid to obtain.

The findings feed an essay argued elsewhere. This repo owes that essay evidence,
which means every number it produces must survive someone trying to break it.

## Measurement principles

These are the rules that decide whether a run was worth its GPU time.

- **Every model in a comparison sees the same problems.** Generate the instances
  once per cell from a recorded seed, then run every model against that list.
  Comparing two independently sampled rates is a weak test; paired outcomes let
  you ask, per problem, whether one model succeeded where the other failed.
  Pairing costs nothing and cannot be added afterward.
- **Record the outcome, not the verdict.** Correct and incorrect are not the
  only things that happen. A model can stop early without answering, or consume
  everything it was given and never finish. Collapsing those into "wrong"
  destroys a behavioural result that cannot be recovered from the stored data.
- **Measure the step, not the problem.** A pass/fail on a whole problem is one
  bit. The same generation scored per-step yields thousands of observations at
  no extra cost. Prefer the instrument that returns a distribution over the one
  that returns a verdict.
- **Two questions want two sampling shapes.** Estimating a cell's probability
  wants many different problems sampled once each, because instances within a
  cell vary in difficulty. Proving a specific failure is real wants one problem
  sampled many times, because a genuine blind spot reproduces and bad luck does
  not. A sweep states which question it serves before it runs.
- **A cell pinned at 0% or 100% buys no information.** Before spending on a
  configuration, state what result would change your mind. If success is
  certain or impossible at that size, the run measures only that you already
  knew the answer. Spend the budget where the outcome is genuinely uncertain,
  and treat saturated cells as single confirmations of a bound, not as sample
  campaigns.
- **The prediction is the product.** Deriving a per-step rate is half the work.
  The claim only becomes falsifiable when that rate is used to predict an
  end-to-end rate at a size where the end-to-end rate is observable, and the two
  are compared. Report the comparison, including when it fails.
- **Name the unit of a step, and defend it.** "Step" is a modeling choice, not a
  given. Different tokenizers group digits differently, so a rate measured per
  token is not comparable across models unless the unit is normalized and the
  normalization is stated. An unstated unit makes every cross-model comparison
  meaningless.
- **Choose the estimator before the run, and check the design can identify it.**
  A model with two terms cannot be fitted where the design varies them together;
  the parameters are not merely imprecise, they are unrecoverable. A design that
  cannot identify the quantity in question is not a cheaper version of one that
  can — it is a different experiment, and no amount of extra sampling converts
  one into the other. Write down the fit before spending, then confirm each of
  its terms varies independently in what you are about to run.
- **Sample counts imply error bars, and error bars are reported.** State the
  interval alongside every rate. A rate quoted bare invites a reader to treat
  noise as signal, and near the extremes the interval is wide enough to reverse
  the reading.
- **Every confound gets written down when it is noticed, not when it is
  resolved.** Prompt format, sampling temperature, scratchpad style, and context
  length all move these numbers. A confound recorded in the run manifest is a
  known limitation; the same confound remembered by one person is a defect
  waiting to be discovered by a reader.

## Substitution changes the claim

Running a cheaper model in place of the one the argument is about does not
produce evidence about the expensive one. It produces evidence about a
mechanism, which is a different and often better claim — but only if stated as
such.

Be explicit in every artifact about which model produced which number, and never
let a curve measured on one family carry a conclusion about another. Where a
claim needs the frontier, anchor it with a small number of runs there rather
than extrapolating from the cheap ladder.

## Spending rented compute

The budget is small and non-renewable, so the failure mode is losing it to
mechanics rather than to measurement.

- **Correctness is proven on the cheapest hardware that can prove it.** A
  harness is debugged at the smallest scale that exercises the same code path.
  Reaching an accelerator with an unproven pipeline is how a budget is spent
  discovering a typo.
- **A generation's ceiling is room to work, never a cost control.** The moment
  the ceiling is what ends a generation, the cell stops measuring the model and
  starts measuring the budget. Two traps follow. A fixed ceiling gives harder
  problems proportionally less room than easy ones, which manufactures a
  breaking point at exactly the sizes under study — and since a breaking point
  is what these sweeps expect to find, nothing flags it as an artifact. And any
  binding ceiling merges "stopped early", "finished long", and "never finished"
  into one bucket. Scale the allowance with problem size, take the limit from
  the engine rather than a constant, record what was granted against what the
  size asked for, and treat any cell where the ceiling bound as invalid until
  rerun. Cost is controlled by the number of generations, which is cheap to
  reason about, not by starving each one.
- **Pay for work, not for waiting.** Amortize setup across a whole sweep rather
  than per unit of work, and make sure nothing stays provisioned once the work
  is done. Idle capacity spends the same as busy capacity.
- **Estimate cost before launching, and record actual cost after.** A run whose
  spend was never compared to its estimate teaches nothing about the next one.

## Data discipline

- **Raw output is immutable.** Whatever the model produced is kept exactly as
  produced. Scores, parses, and aggregates are derived artifacts, regenerable
  from raw at any time. Never edit raw to fix a downstream parser.
- **A run is reproducible or it is an anecdote.** Seeds, pinned model revisions,
  decoding parameters, and prompt text are recorded with the output. A number
  that cannot be regenerated cannot be defended.
- **Analysis reads a manifest, never a filename.** Encoding parameters in paths
  guarantees they will eventually disagree with what actually ran.
- **A result that surprises you is checked before it is believed.** The most
  likely cause of a striking number is a harness defect. Verify against a case
  with a known answer first.

## Language & voice

Write chat replies to the maintainer at a 10th–11th grade reading level: plain
sentences, common words, short paragraphs. In code, commits, and docs, use
whatever a reader will understand fastest.

Strip the AI register from anything that ships. No throat-clearing, no "not X
but Y" balancing, no rule-of-three padding, no hedge on every claim. The running
tell-list is in [.agents/reference/anti-slop.md](.agents/reference/anti-slop.md)
— read it before writing prose anyone else will see.

State results plainly, including negative ones. A run that failed, a cell that
was skipped, and a prediction that missed are all reportable outcomes. Burying
them costs more credibility than the failure itself.

## Durable knowledge — no memory systems

Do not use assistant memory for anything about this project. Durable knowledge
lives in version-controlled files: this one for principles, the reference
material for formats, and the code and manifests for facts. If it is worth
keeping, write it to the right file before the session ends.

## Conventions

Formats for skills, hooks, sub-agents, rules, and settings are in
[.agents/reference/anthropic-conventions.md](.agents/reference/anthropic-conventions.md).

Visualization approaches already in use across the surrounding projects — the
charting stack, the 3D-to-2D projection, and the raw → reduced → rendered
pipeline — are surveyed in
[.agents/reference/dataviz/](.agents/reference/dataviz/). Read it before
building any chart, so a technique that already exists is reused rather than
reinvented.

Everything shared across coding agents lives in `.agents/`. `.claude/` holds
only what is Claude Code specific, plus symlinks so auto-discovery resolves. The
test that a change respects this: an agent that has never heard of `.claude/`
can read this file, follow it into `.agents/`, and find everything.

## Naming

The project is `carrychain`, lowercase, everywhere it is written.
