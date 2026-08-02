#!/usr/bin/env python3
"""Rebuild the blind classification worklist, so the blind pass can be re-run.

The rubric's last fail condition is "labels assigned after knowing which trace
was correct, without a blind pass." One ran; its agreement rate is quoted in
labels/README.md and in the rubric. This script is what makes that number
regenerable rather than an anecdote.

It emits every judgment the pass has to make, stripped of trace identity,
outcome, and filename, shuffled under a fixed seed, each item carrying only the
target segment and two segments of context either side. The mapping back to
(trace, index) goes in a separate file that the classifier must not open until
every label is written. That sealing is the entire mechanism; nothing enforces
it but the person running the pass.

245 items: A 64, B 64, C 73 before the lock-up, plus the 44 distinct texts
after it (identical text gets an identical label, as probe/label_grind.py
already does, so labelling repeats would be labelling the same judgment 323
times).

    python probe/blind_worklist.py       # build the worklist and the keymap
    python probe/blind_dump.py 0 20      # print items [0,20) for judging

Two honest limits, unchanged since the first pass:

  - 35 of 245 targets contain the word "correct". That is the model talking to
    itself ("So that's correct"), present in all three traces. Not a leak.
  - The operands are the trace identity to anyone who has read the traces, and
    the rubric itself names one trace's operands. The pass is blind to which
    trace an item sits in by construction, not proof against recognising it.
    Run it in a session that has not read labels/*.json or the raw traces.
"""
import hashlib
import json
import random
import re

SEGMENTS = {
    "T1": "derived/segments-A-7x11-correct.json",
    "T2": "derived/segments-B-8x7-wrong.json",
    "T3": "derived/segments-C-5x13-grind.json",
}
WORKLIST = "derived/blind-worklist.json"
KEYMAP = "derived/blind-keymap.json"

LOCKUP = 73     # C's first segment after the lock-up; must match label_grind.py
SEED = 20260802
CONTEXT_CHARS = 220

norm = lambda s: re.sub(r"\s+", " ", s).strip()


def build():
    items = []
    for tk, path in SEGMENTS.items():
        segs = json.load(open(path))["segments"]
        if tk == "T3":
            take = range(LOCKUP)
            seen = set()
            for i in range(LOCKUP, len(segs)):
                t = norm(segs[i]["text"])
                if t not in seen:
                    seen.add(t)
                    items.append((tk, i, segs, True))
        else:
            take = range(len(segs))
        for i in take:
            items.append((tk, i, segs, False))

    random.Random(SEED).shuffle(items)

    out, key = [], {}
    for n, (tk, i, segs, is_post) in enumerate(items):
        ctx = lambda j: norm(segs[j]["text"])[:CONTEXT_CHARS] if 0 <= j < len(segs) else ""
        uid = hashlib.sha256(f"{tk}|{i}".encode()).hexdigest()[:8]
        key[uid] = {"trace": tk, "index": i, "post_lockup": is_post}
        out.append({"n": n, "id": uid,
                    "prev2": ctx(i - 2), "prev1": ctx(i - 1),
                    "target": norm(segs[i]["text"]),
                    "next1": ctx(i + 1), "next2": ctx(i + 2)})

    json.dump(out, open(WORKLIST, "w"), indent=1)
    json.dump(key, open(KEYMAP, "w"), indent=1)
    print(f"wrote {WORKLIST} and {KEYMAP}: {len(out)} items")


if __name__ == "__main__":
    build()
