# TMP — reclassify the three flame traces (instructions for Opus 5)

Disposable. Do not commit. Delete after the labels are reconciled.

Written by a Fable review pass comparing how carrychain's labels were produced
against how the λ-bench post produced theirs. The λ method is documented in
[.agents/reference/flame-classification.md](.agents/reference/flame-classification.md);
what carrychain actually did happened in one Opus session on 2026-08-02 and is
recorded in [labels/README.md](labels/README.md).

## The comparison, honestly

| | λ-bench (proven) | carrychain (this session) |
|---|---|---|
| unit of judgment | **one call per segment**, ±2 segments of context, single uppercase word, malformed output fails the build | whole trace read at once, all 64 labels emitted together |
| outcome visible to classifier | **never** — the harness sends 5 segments and nothing else | **always** — outcome is in the filename and the labeller knew it |
| bias control | mechanical blindness | procedural ordering (B locked before A before C) |
| depth ranges | a **separate second call** on the same segments | same author, same sitting as the labels |
| iteration | 10 commits; Haiku attempts discarded after producing plausible-but-wrong charts | single pass, no independent check (the checker agent stalled and died) |
| rubric | prompt evolved by looking at bad charts | written **before** labelling, ordered rules, traps, fail conditions |
| verification of claims | none recorded | every arithmetic claim in the annotations recomputed in Python |

Read the last two rows before the first two: the carrychain rubric and its
verified annotations are *better* than λ's process. The exposure is narrower
but real — the labels themselves were produced holistically by a labeller who
knew the outcome. The rubric's own fail condition says: *"Labels assigned after
knowing which trace was correct, without a blind pass."* The ordering
discipline mitigated cross-trace favoritism; it did not produce a blind pass.
Nobody has yet reproduced these labels blind. That is the gap this document
closes.

Two specific decisions need adversarial attention because they were made
mid-labelling and both happen to favor trace A:

1. **The rule-3 amendment.** A recomputes, at segments 26–29, terms it first
   computed inside an abandoned decomposition (7–18). The amendment says an
   abandoned path's values are not "live", so recomputation is
   `PARTIAL_PRODUCT`, not `RECHECK`. B's second pass (33–42) re-derives values
   that fed its delivered answer, so it stays `RECHECK`. Principled or special
   pleading — the blind pass settles it: judge those segments by the written
   rules only.
2. **Scientific-notation checks as `CROSSCHECK`** (B[10], A[11], A[14], C[59–63]).
   Consistently applied, but decided by the same person in the same sitting.

## Already done, do not redo (Opus session, 2026-08-02)

The worklist exists: `derived/blind-worklist.json` (245 items) and its sealed
`derived/blind-keymap.json`. **Step 1 is complete.** Start at step 2.

Two audits that do not require blindness were run by the labelling session,
because a mechanical check of consistency is valid no matter who runs it.

**Cross-trace consistency: nothing found.** Compared all 201 distinct segments
pairwise with digits stripped (the traces differ in operands but share
phrasing). Three pairs came back structurally similar with different labels;
all three survive scrutiny and are correctly labelled:

- `A[21]` TASK_SETUP vs `C[99]`/`C[67]` ACCUMULATE — A restates the problem's
  own operands (rule 8); C aligns two already-computed partial products to add
  them (rule 5). Digit-stripping erased exactly the distinction that decides it.
- `A[24]` STRATEGY vs `C[67]` ACCUMULATE — A commits to a place-value
  decomposition (rule 6); C is mid-addition (rule 5).

**Scientific notation: consistent across all three traces.** 19 segments
labelled CROSSCHECK, 14 PARTIAL_PRODUCT, and the line between them is
rule 2 vs rule 4 applied the same way everywhere: converting an
already-computed value to test its magnitude is CROSSCHECK; using powers of ten
to place a term you are computing is PARTIAL_PRODUCT. The Fable review flagged
this as a bias risk. It held. Do not spend the blind pass re-litigating it.

**The rule-3 amendment is the live risk, and it carries a published claim.**
This is now the highest-value thing the blind pass decides. Sensitivity test:

| | as labelled (amendment) | strict rule 3 (no amendment) |
|---|---|---|
| A crosscheck : recheck | **17 : 3** | 17 : 7 |
| B crosscheck : recheck | 9 : 14 | 9 : 14 |
| A verification share | **36%** | **46%** |
| B verification share | 40% | 40% |

The direction survives either way — A is crosscheck-dominant, B is
recheck-dominant. That is the figure's core claim and it is safe.

But the sentence in `blog/src/App.svelte` that B *"gave more of its trace to
checking, not less"* is true only under the amendment. Strip it and A verifies
more than B, and that sentence must be deleted. So does the headline
`17 crosschecks to 3 rechecks`, which becomes 17:7.

The four segments at issue are `A[26]`–`A[29]`. They recompute terms that also
appeared in the decomposition A abandoned at `A[18]`, and `A[26]` says "as
before", which reads as recall rather than fresh computation. Judge them blind
on the rules alone. Whichever way it lands, update the prose and the rubric's
results table to match.

## The task

Reproduce all labels blind, one segment at a time, exactly the λ strict method
adapted to the carrychain rubric. Then reconcile against the stored labels.
**245 judgments**: A 64, B 64, C 73 pre-lockup + 44 distinct post-lockup texts.

No API calls, no spend. This runs in conversation. Budget one short judgment
per item — λ ran these at low effort deliberately; deliberation invites
narrative, and narrative is the bias being removed.

### Step 1 — build the blind worklist

Run this exactly (adjust nothing but the seed comment):

```python
import json, re, random, hashlib, collections

SEG = {"T1": "derived/segments-A-7x11-correct.json",
       "T2": "derived/segments-B-8x7-wrong.json",
       "T3": "derived/segments-C-5x13-grind.json"}
norm = lambda s: re.sub(r"\s+", " ", s).strip()
items, key = [], {}

for tk, f in SEG.items():
    d = json.load(open(f)); S = d["segments"]
    if tk in ("T1", "T2"):
        take = range(len(S))
    else:
        LOCK = 73
        take = range(LOCK)
        seen = set()
        for i in range(LOCK, len(S)):          # 44 distinct post-lockup texts
            t = norm(S[i]["text"])
            if t not in seen:
                seen.add(t); items.append((tk, i, S, True))
    for i in take:
        items.append((tk, i, S, False))

random.Random(20260802).shuffle(items)
out = []
for n, (tk, i, S, is_post) in enumerate(items):
    ctx = lambda j: norm(S[j]["text"])[:220] if 0 <= j < len(S) else ""
    uid = hashlib.sha256(f"{tk}|{i}".encode()).hexdigest()[:8]
    key[uid] = {"trace": tk, "index": i, "post_lockup": is_post}
    out.append({"n": n, "id": uid,
                "prev2": ctx(i-2), "prev1": ctx(i-1),
                "target": norm(S[i]["text"]),
                "next1": ctx(i+1), "next2": ctx(i+2)})

json.dump(out, open("derived/blind-worklist.json", "w"), indent=1)
json.dump(key, open("derived/blind-keymap.json", "w"), indent=1)
print(len(out), "items")   # must print 245
```

The worklist carries no trace identity, no outcome, no filename. **Do not open
`blind-keymap.json` until every label is written.** That is the entire
mechanism; there is no other enforcement.

Two honest limits of the blinding, verified before this doc was written:

- 35 of 245 targets contain words like "correct" — that is the model talking
  to itself ("So that's correct"), present in all three traces, not verdict
  metadata. Not a leak.
- The operands ARE the trace identity. Anyone who has read these traces
  recognizes 80,379,530 on sight. **The pass must therefore be run by a fresh
  Opus session that has not read the label files or the traces** — start it
  with this document and nothing else. A session that already labelled them
  cannot be blinded by a shuffle.

### Step 2 — classify

For each item, in worklist order: read `prev2…next2`, apply the rubric's nine
decision rules **in order, stopping at the first match**
([.agents/reference/flame-rubric-carrychain.md](.agents/reference/flame-rubric-carrychain.md)
— rules AND traps AND the rule-3 amendment are all binding). Emit exactly one
uppercase word from the nine. No prose, no hedging, no revisiting earlier
items. Write results to `derived/blind-labels.json` as `{id: CATEGORY}`.

Judge the amendment cases by the amendment's own text: is the value being
re-derived *live in the line of work that reaches an answer*? You cannot know
which trace you are in, which is the point.

### Step 3 — unblind and reconcile

Open the keymap. Expand C's 44 post-lockup judgments to all their instances
(identical text → identical label, as `probe/label_grind.py` already does).
Diff against `labels/*.json`.

For every disagreement, one line:
`T2[41] stored=ACCUMULATE blind=RECHECK — rule N decides: <one sentence> → keep|change`

Rules of adjudication, in order:
- A blind label that follows from a numbered rule beats a stored label that
  does not. Change it.
- Where both are defensible under the rules, **the stored label stands** —
  churn without a deciding rule is noise, not accuracy.
- If a disagreement pattern tracks outcome (stored labels systematically
  kinder to T1 than the blind pass), say so plainly in the reconciliation
  notes even if no single change results. That finding matters more than any
  individual label.

Expected agreement is high. If more than ~15% of the 245 disagree, stop and
re-read the traps section before adjudicating — the more likely failure is the
blind pass misapplying rule 2 vs 3 than the stored labels being 15% wrong.

### Step 4 — ranges, if labels moved

If any labels changed inside a subtask range, redo that trace's ranges as a
separate pass, λ style: from the (new) labels and segment text only, emit flat
`{start, end, label}` ranges; containment gives depth. Do not adjust ranges to
preserve the current chart's look.

### Step 5 — rebuild and propagate

```sh
python probe/label_grind.py      # only if C changed
python probe/build_flame.py
cd blog && ./node_modules/.bin/svelte-check --threshold error --output human
node scripts/viewports.mjs       # dev server must be running
```

Numbers that live outside the label files and must be updated if they move:

- `17 crosschecks to 3 rechecks` and `9 to 14` — hard-coded in
  `blog/src/App.svelte` prose.
- The Results table in `.agents/reference/flame-rubric-carrychain.md`
  (36%/40% verification shares, 17:3 / 9:14, ERROR_CORRECTION counts).
- `verified` blocks in `labels/*.json` are arithmetic, not judgment — they do
  not change, do not touch them.
- Update `labels/README.md`'s order-of-labelling section to record that a
  blind pass ran, with the agreement rate.

### Step 6 — record and delete

Append the agreement rate, every changed label, and the outcome-pattern check
to the reconciliation section of `labels/README.md` (three or four sentences —
it is the record that the fail condition was closed). Then delete this file,
`derived/blind-worklist.json`, `derived/blind-keymap.json`, and
`derived/blind-labels.json`.

## What NOT to redo

- Segmentation. Full coverage, zero gaps/overlaps, audited this session.
- The arithmetic in the annotations. Recomputed and verified; the `verified`
  blocks in `labels/*.json` list the results.
- The display cleaning in `build_flame.py`. Swept all 524 segments; zero
  residual markup.
- C's post-lockup expansion mechanism. Identical text → identical label is
  stricter than hand labels; only the 44 distinct judgments are in scope.
- The chart components. FlamePanel is the production λ component; the fork is
  already deleted.
