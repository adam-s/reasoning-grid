#!/usr/bin/env python3
"""Build the labelling worklist: every judgment the pass has to make, stripped of
trace identity and shuffled, plus a keymap that must stay sealed until the last
label is written.

Rubric: .agents/reference/label-rubric-qwen-multiplication.md

What this emits and why each part is there:

  - **One item per DISTINCT target text.** Identical text in identical context is
    the same judgment; asking twice buys two chances to disagree with yourself,
    not two observations. The keymap records every (trace, index) an item stands
    for, so expanding back is exact.
  - **Segments already labelled by `precompute_labels.py` are skipped.** `LOOP`
    and `REPORT` are computed, and a fail condition says they may not be assigned
    by judgment.
  - **Shuffled under a fixed seed**, so trace identity cannot be read off the
    order, and so the shuffle is reproducible rather than a one-off.
  - **Two segments of context either side**, truncated. A target alone is often
    unreadable -- "So 34." -- and the rubric's conflict rules need to know what
    came before.
  - **The keymap is a separate file.** Nothing enforces the sealing but the person
    running the pass. Stating that is more honest than implying a mechanism.

Two limits, carried forward because they have not gone away:

  - The operands identify the trace to anyone who has read the traces. The pass is
    blind to trace identity by construction, not proof against recognising it.
    Run it in a session that has not read the raw traces or labels/.
  - Targets containing outcome words are counted and reported below. They are the
    model talking to itself -- "So that's correct" -- and appear in every trace,
    winning and losing alike. Counted so the claim can be checked, not asserted.

    python probe/label_worklist.py
    python probe/label_show.py 0 20
"""
import glob
import hashlib
import json
import os
import re

SEG_DIR = "derived/v2"
LAB_DIR = "labels/v2"
WORKLIST = "derived/v2/label-worklist.json"
KEYMAP = "derived/v2/label-keymap.json"

SEED = 20260803
CONTEXT_CHARS = 220
# Words that would tell a labeller how the run ended. Counted, not stripped:
# removing them would change the text being labelled.
OUTCOME_WORDS = re.compile(r"\b(correct|wrong|mistake|error)\b", re.I)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def build():
    # text -> item; first occurrence supplies the context, all occurrences are keyed
    items: dict[str, dict] = {}
    order: list[str] = []
    skipped = 0

    for lab_path in sorted(glob.glob(os.path.join(LAB_DIR, "*.json"))):
        lab = json.load(open(lab_path))
        segs = json.load(open(lab["source"]))["segments"]
        trace = os.path.basename(lab_path).replace(".json", "")

        def ctx(j):
            return norm(segs[j]["text"])[:CONTEXT_CHARS] if 0 <= j < len(segs) else ""

        for i, precomputed in enumerate(lab["labels"]):
            if precomputed is not None:
                skipped += 1
                continue
            t = norm(segs[i]["text"])
            if t not in items:
                items[t] = {
                    "target": t,
                    "prev2": ctx(i - 2), "prev1": ctx(i - 1),
                    "next1": ctx(i + 1), "next2": ctx(i + 2),
                    "occurrences": [],
                }
                order.append(t)
            items[t]["occurrences"].append({"trace": trace, "index": i})

    # Shuffle deterministically, without depending on dict order.
    import random
    random.Random(SEED).shuffle(order)

    out, key = [], {}
    for n, t in enumerate(order):
        it = items[t]
        uid = hashlib.sha256(t.encode()).hexdigest()[:10]
        key[uid] = it["occurrences"]
        out.append({"n": n, "id": uid,
                    "prev2": it["prev2"], "prev1": it["prev1"],
                    "target": it["target"],
                    "next1": it["next1"], "next2": it["next2"]})

    os.makedirs(os.path.dirname(WORKLIST), exist_ok=True)
    json.dump(out, open(WORKLIST, "w"), indent=1)
    json.dump(key, open(KEYMAP, "w"), indent=1)

    leak = sum(1 for it in out if OUTCOME_WORDS.search(it["target"]))
    covered = sum(len(v) for v in key.values())
    print(f"wrote {WORKLIST}")
    print(f"wrote {KEYMAP}   (SEAL THIS until every label is written)")
    print(f"  {len(out)} items, standing for {covered} segments")
    print(f"  {skipped} segments skipped as already computed (LOOP / REPORT)")
    print(f"  {leak} targets ({leak / len(out) * 100:.0f}%) contain an outcome word "
          f"-- the model talking to itself, present in every trace")


if __name__ == "__main__":
    build()
