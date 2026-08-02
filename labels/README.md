# labels/ — the hand-assigned categories

These are judgments, not derivations, which is why they live here and not in
[`derived/`](../derived/). Everything in `derived/` can be rebuilt from
[`runs/`](../runs/) by running a script; these files cannot be rebuilt by
anything. Delete them and the work is gone.

One file per trace, against
[../.agents/reference/flame-rubric-carrychain.md](../.agents/reference/flame-rubric-carrychain.md),
which was written **before** any label was assigned.

| file | trace | outcome |
|---|---|---|
| `A-7x11-correct.json` | Qwen3-4B, N=77, T=0.7 | answered, correct |
| `B-8x7-wrong.json` | Qwen3-4B, N=56, T=0.7 | answered, wrong |
| `C-5x13-grind.json` | Qwen3-4B, N=65, T=0 | never answered |

## What a file contains

| field | |
|---|---|
| `labels` | one category per segment, in order. Same length as the matching `derived/segments-*.json` |
| `subtasks` | flat `{start, end, label}` ranges over segment indices. Depth is **derived from containment**, never stored — see `probe/build_flame.py` |
| `annotations` | `{segment, kind, text}` — the moments the post argues about, pinned to where they happen |
| `verified` | the arithmetic claims in those annotations, recomputed and checked in `probe/` rather than asserted |
| `labelled_blind` | whether the labeller had seen the other traces yet |

## Order of labelling, and why it is recorded

B first, then A, then C, each locked before the next began. The rubric requires
it: *"Do not reward the correct run. Knowing A is right invites reading its
checks as more careful."*

The one borderline call that appears in more than one trace — a place-value doubt
resolved by converting to scientific notation — got `CROSSCHECK` in all three,
decided while labelling B and then applied without revisiting it. That is the
whole point of fixing the order.

C is the exception to hand-labelling and says so in its own `note`: 396 segments,
of which 323 sit after the model locks up and contain only 44 distinct texts.
Those 44 are labelled once each in `probe/label_grind.py` and applied by
matching, so identical text gets an identical label by construction. Segments
0–72 were labelled individually, like A and B.

Ordering is not blindness, and the rubric's fail condition asked for a blind
pass. One ran afterward; the next section is its result.

## Reconciliation against a blind pass

All 245 judgments (A 64, B 64, C 73 pre-lockup + 44 distinct post-lockup texts)
were reproduced from segment text alone: shuffled under a recorded seed, each
item presented as five segments of context with no trace identity, no outcome,
and no filename, one uppercase word out of the nine per item, written before the
keymap was opened. **Agreement 205/245 = 84%** — A 97%, B 84%, C 76%.

Adjudicating the 40 disagreements against the numbered rules moved **16 labels,
all in C**. A and B are unchanged, so `17:3`, `9:14`, the 36%/40% verification
shares and the zero `ERROR_CORRECTION` counts all stand as published. C's
changes: `11,12,44,64,65,71,101,103` → `ACCUMULATE` (rule 5 says "aligns", and C
already used `ACCUMULATE` for the identical move elsewhere), `34–37` →
`RECHECK` (rule 3 fires before 5 and 6 — "let me do that again", same
breakdown, on a value C[33] had finished), `33` → `PARTIAL_PRODUCT` (sums
*inside* one term, not across terms), `54,56` → `STATE_TRACKING` (rule 6 needs
a decomposition and neither chooses one), and `19` → `ACCUMULATE`, which
removes C's lone `ERROR_CORRECTION`: no value changes there, and the rubric
lists "`ERROR_CORRECTION` assigned where no value changed" as a fail condition.
A's and B's equivalent false alarms (A[41], B[53]) are `CROSSCHECK`, so C's is
now consistent with them. The new labels also open one sub-range, C `34–39`.

**The rule-3 amendment survives.** `A[26]`–`A[29]`, the four segments the whole
exposure rested on, came back `PARTIAL_PRODUCT` blind — identical to stored. The
amendment was not special pleading, and `17:3` is not load-bearing on an
unaudited judgment any more.

**No sign the stored labels favour the correct run.** A had the *fewest*
disagreements of the three, and neither of its two produced a change. Where the
blind pass disagreed with B it mostly wanted `PARTIAL_PRODUCT` in place of
`RECHECK` at `B[35]`–`B[42]` — which would have weakened "B is recheck-dominant",
not strengthened it. That cluster is an artefact of the ±2 window: B's second
pass re-derives products computed 25 segments earlier, outside what the blind
context could show, so rule 3 applies on the full trace and the stored label
stands. The only outcome-correlated drift found anywhere was **in the blind pass
itself** — it called A's two scientific-notation place-value doubts `CROSSCHECK`
and B's identical `B[10]` `PARTIAL_PRODUCT`, while the stored labels give all
three `CROSSCHECK`. Stored was the consistent one and was kept.

One honest limit: the rubric is binding on the classifier and the rubric names
B's operands and both truths, so the pass was blind to trace identity by
construction but not proof against recognising it. The four amendment segments
were nonetheless judged with no marker in the window saying which trace they
were in.

## Rebuilding what depends on them

```sh
python probe/label_grind.py     # regenerates C from probe/label_grind.py
python probe/build_flame.py     # labels + derived/segments-*.json -> blog data
```

A and B have no generator. They are the input.
