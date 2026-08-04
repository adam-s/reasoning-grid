---
name: prose-review
description: Read a piece of reasoning-grid writing phrase by phrase for how it could be misread, then check it against Adam's voice and this repo's prose rules. Use when the user says "check this", "how does this read", "review the wording", "could this be taken wrong", or pastes a draft — and before publishing blog prose, a RESULTS write-up, or anything the essay will cite. Read-only; it reports and does not edit.
allowed-tools: Read, Grep, Glob, Task
model: opus
effort: high
---

# prose-review

Converted from the `subtext` plugin (`~/Projects/subtext`, Adam's own), with its
voice reference and this repo's prose rules folded in. It is a copy on purpose:
a skill that reaches into another repository is one an agent eventually edits by
mistake. If subtext's method improves, port the change; do not link to it.

## The one law

**Every finding names a concrete misreading, or it is dropped.** "A reader could
take this as X" is a finding. "This could be clearer" is noise, and noise is how
a review tool gets ignored. If you cannot state the specific wrong meaning a real
reader would take, do not report it.

## Step 0 — What is being reviewed

reasoning-grid's artifacts have known audiences, so infer rather than interrogate.
State the inference in one line and proceed.

| artifact | reader | the bar |
|---|---|---|
| chat reply to Adam | Adam, mid-task | 10th–11th grade reading level, plain sentences, short paragraphs ([AGENTS.md](../../../AGENTS.md)) |
| blog prose in `blog/` | a skeptical stranger who did not run the sweep | [anti-slop.md](../../reference/anti-slop.md), and every number traceable to a file |
| `sweeps/*/RESULTS.md`, `docs/` | a future session, or someone checking the work | negative results stated as plainly as positive ones |
| commit message | whoever bisects to it | why, not what; the diff already says what |
| a code comment | whoever breaks the invariant next | the reason it is that way, not a restatement of the line |

## Step 1 — FIND, coverage first

Sweep the text phrase by phrase through all seven lenses. The catalog — what each
catches, the tell, an example — is in
[../../reference/lenses.md](../../reference/lenses.md); **read it.** The seven:
connotation, lexical ambiguity, syntactic ambiguity, double meanings,
implicature, audience-shifted readings, and a whole-text goal-alignment pass.

**Maximize recall here.** Report every candidate including ones you doubt; Step 2
filters. Under-reporting now is not recoverable later. Record for each: the exact
quoted phrase with enough context to locate it, the lens, the misreading in one
sentence, a severity guess.

Two failure modes this repo produces more than most:

- **A hedge that erases a result.** "The data suggests the boundary may lie
  near..." reads as unsure of a number that has an interval on it. Say the number
  and the interval.
- **A number with no lineage.** A rate in prose that no committed file produces
  is the defect [AGENTS.md](../../../AGENTS.md) exists to prevent. Flag any
  figure you cannot trace to `runs/`, `labels/`, or a `probe/` script.

### The eighth lens: is a human the reader

Run this over every paragraph of blog prose, after the seven. It catches what
they do not, because nothing here is ambiguous — it is all perfectly clear to
someone who already knows the answer, which is the problem.

Ask four questions. Any "no" is a finding, and the rewrite is the deliverable.

1. **What can the reader see?** If the paragraph contains no image, it was
   written for a machine. Abstract nouns are the usual cause.
2. **Where is the action?** If the verbs are *is*, *has*, *states*, *provides*
   and the real action is buried in a noun, hand it back to a verb.
3. **Whose vocabulary is this?** `decomposition`, `segment`, `lap`, `cell`,
   `crosscheck` are this repo's words. A reader has met none of them.
4. **Is any sentence about the writing rather than about the world?** "Start
   with", "It is worth noting", "This section covers". Cut it and start at the
   thing.

The full list is [anti-slop.md](../../reference/anti-slop.md) rules 12 to 17.
A paragraph can satisfy every other rule in that file and still fail all four of
these, so do not treat a clean pass on the seven lenses as a clean pass.

## Step 2 — VERIFY, adversarially and cold

A model that just flagged a phrase will defend it. Hand each candidate to a
reader that has not seen your reasoning: spawn the **subtext:misread-verifier**
agent via Task, one call per finding, in parallel. Give it the full text, the
quoted phrase, the goal/audience/stakes and the claimed misreading — **not** your
severity guess or your reasoning.

Keep a finding only if the verifier agrees a real member of that audience would
take the wrong meaning. Drop what survives only as pedantry.

If that agent is not available in the current surface, run the refutation inline
as a separate, deliberately hostile pass. The separation of jobs is the point;
the sub-agent is only how the context is kept fresh.

## Step 3 — VOICE

Now, and only now, check register against
[../../reference/voice/](../../reference/voice/) — the profile, the eight style
rules, the anti-patterns, and **`stated-preferences.md`**. Read that directory's
README first: it records where the voice and this repo's rules genuinely
conflict, and which wins.

`stated-preferences.md` is the one to read closely and the one that overrides.
The other four files are derived from a corpus of forum comments and describe
what Adam once did; that file records what he has asked for directly, about
drafts of this project. Where they disagree, it wins. Two that catch drafts
constantly: **no colons and no em dashes**, which is stricter than anti-slop's
"ration them", and **name the concept if it has a name** rather than describing
around it.

The short version: **the repo owns the surface, the voice owns the reasoning.**
Sentence length, paragraph length and reading level are reasoning-grid's call —
shorten without apology. Explanation over slogan, context before the claim,
support instead of naked assertion, no hype and no lecturing — that is the voice,
and it survives the shortening.

A rewrite that is shorter *and* has lost a reason obeyed the wrong one of these.
Flag it.

## Step 4 — REPORT

1. **Framing line** — the artifact, reader and bar you judged against.
2. **Findings**, severity high → low. Each: the quoted phrase and where, the
   lens, the misreading in one sentence, and one or two rewrites that remove it
   without changing the meaning or flattening the voice.
3. **Whole-text verdict** — two or three sentences on cumulative tone and fit.

Scale the bar to the stakes. Published blog prose and anything the essay cites
get medium and high findings. A chat reply or an internal note gets high findings
only. **Cap low-severity findings at about five**; if there are more, report the
best few and say how many you held back.

**A clean bill of health is a first-class result.** If the text holds up, say so
in a sentence or two and stop. Manufacturing findings to look useful is the
fastest way to make the skill worth uninstalling.

## The blind spot that applies here almost always

If you drafted the text earlier in this same conversation — which in this repo is
usually true — you share the author's context and will under-flag. Say so, and
either lean harder on the fresh-context verifier or run the whole find step as a
sub-agent so it reads the text cold.
