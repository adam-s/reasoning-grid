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

## Rebuilding what depends on them

```sh
python probe/label_grind.py     # regenerates C from probe/label_grind.py
python probe/build_flame.py     # labels + derived/segments-*.json -> blog data
```

A and B have no generator. They are the input.
