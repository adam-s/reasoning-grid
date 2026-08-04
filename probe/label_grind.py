#!/usr/bin/env python3
"""Build the label array for trace C, the run that never terminated.

A and B were labelled segment by segment; 64 each is tractable. C is 396,
because after it locks up the segmenter keeps finding discourse markers in a
sentence the model repeats 276 times. Labelling 396 by hand would be 323
copies of the same judgment, so the labels come from two sources:

  segments 0-72   before the lock-up. Labelled individually, same as A and B.
  segments 73-395 after it. There are only 44 distinct texts in this region;
                  each is labelled once here and applied to every instance.

That is a real difference in method from A and B, and it is written down rather
than hidden: identical text gets an identical label by construction, which is
stricter than hand-labelling would have been, not looser.

    python probe/label_grind.py
"""
import json
import os
import re
from collections import Counter

SEGMENTS = "derived/segments-C-5x13-grind.json"
OUT = "labels/C-5x13-grind.json"

# --- segments 0-72, before the lock-up -------------------------------------
PRE = [
    "TASK_SETUP",                                              # 00
    "STRATEGY", "STRATEGY", "STRATEGY", "STRATEGY",            # 01-04  hunt for factors, then commit to 21000+28
    "PARTIAL_PRODUCT",                                         # 05
    "ACCUMULATE", "ACCUMULATE", "ACCUMULATE", "ACCUMULATE",    # 06-09
    "ACCUMULATE",                                              # 10
    "ACCUMULATE", "ACCUMULATE",                                # 11-12  align the addends (rule 5 says "aligns")
    "ACCUMULATE", "ACCUMULATE", "ACCUMULATE", "ACCUMULATE",    # 13-16
    "ACCUMULATE", "ACCUMULATE",                                # 17-18
    "ACCUMULATE",                                              # 19     reads off 30,682,678,033,547 and doubts it;
                                                               #         no value changes, so rule 1 does not fire
    "STRATEGY",                                                # 20     abandons digit-by-digit
    "ACCUMULATE",                                              # 21
    "RECHECK", "RECHECK",                                      # 22-23
    "PARTIAL_PRODUCT", "PARTIAL_PRODUCT", "PARTIAL_PRODUCT",   # 24-26  the 28x part
    "PARTIAL_PRODUCT", "PARTIAL_PRODUCT",                      # 27-28
    "STATE_TRACKING", "STATE_TRACKING",                        # 29-30
    "STRATEGY",                                                # 31
    "PARTIAL_PRODUCT",                                         # 32
    "PARTIAL_PRODUCT",                                         # 33     sums inside one term, not across terms
    "RECHECK", "RECHECK", "RECHECK",                           # 34-36  "let me do that again", same breakdown
    "RECHECK",                                                 # 37     "that seems high"
    "RECHECK", "RECHECK",                                      # 38-39
    "ACCUMULATE", "ACCUMULATE",                                # 40-41
    "RECHECK", "RECHECK",                                      # 42-43
    "ACCUMULATE",                                              # 44     lists the two parts in order to add them
    "ACCUMULATE", "ACCUMULATE", "ACCUMULATE", "ACCUMULATE",    # 45-48
    "ACCUMULATE",                                              # 49
    "ACCUMULATE",                                              # 50 <-- the correct total, first written here
    "STRATEGY", "STRATEGY", "STRATEGY",                        # 51-53
    "STATE_TRACKING",                                          # 54     "I think this is the right answer"
    "STRATEGY",                                                # 55
    "STATE_TRACKING",                                          # 56     names the answer the work holds
    "RECHECK", "RECHECK",                                      # 57-58
    "CROSSCHECK", "CROSSCHECK", "CROSSCHECK", "CROSSCHECK",    # 59-62  the sci-notation check
    "CROSSCHECK",                                              # 63 <-- "my previous addition was wrong"
    "ACCUMULATE", "ACCUMULATE",                                # 64-65  align the addends
    "ACCUMULATE", "ACCUMULATE", "ACCUMULATE", "ACCUMULATE",    # 66-69
    "ACCUMULATE",                                              # 70
    "ACCUMULATE",                                              # 71     align the addends
    "ACCUMULATE",                                              # 72
]

# --- segments 73-395, keyed on the distinct text ---------------------------
# Ordered by frequency, as printed by the dump. Index is position in that order.
POST = {
    0: "ACCUMULATE",    # x276  "Let me add X to Y:" -- announced, never performed
    1: "ACCUMULATE", 2: "CROSSCHECK", 3: "ACCUMULATE", 4: "ACCUMULATE",
    5: "ACCUMULATE", 6: "ACCUMULATE", 7: "ACCUMULATE", 8: "STRATEGY",
    9: "ACCUMULATE", 10: "ACCUMULATE", 11: "ACCUMULATE", 12: "ACCUMULATE",
    13: "CROSSCHECK", 14: "CROSSCHECK",   # 14 is the bug: 0.00042177... should be 0.0042177...
    15: "CROSSCHECK", 16: "RECHECK", 17: "RECHECK", 18: "RECHECK",
    19: "RECHECK", 20: "RECHECK", 21: "RECHECK", 22: "CROSSCHECK",
    23: "CROSSCHECK", 24: "CROSSCHECK", 25: "RECHECK", 26: "ACCUMULATE",
    # 28 (seg 101) and 30 (seg 103) both align-then-add; rule 5 fires before 6 and 7
    27: "ACCUMULATE", 28: "ACCUMULATE", 29: "ACCUMULATE", 30: "ACCUMULATE",
    31: "CROSSCHECK", 32: "RECHECK", 33: "RECHECK", 34: "RECHECK",
    35: "RECHECK", 36: "RECHECK", 37: "CROSSCHECK", 38: "CROSSCHECK",
    39: "CROSSCHECK", 40: "CROSSCHECK", 41: "ACCUMULATE", 42: "ACCUMULATE",
    43: "ACCUMULATE",
}

LOCKUP_SEG = 73     # first segment at or after char 17,019


def main():
    doc = json.load(open(SEGMENTS))
    segs = doc["segments"]
    norm = lambda s: re.sub(r"\s+", " ", s).strip()

    post = [s for s in segs[LOCKUP_SEG:]]
    order = [t for t, _ in Counter(norm(s["text"]) for s in post).most_common()]
    if len(order) != len(POST):
        raise SystemExit(f"{len(order)} distinct texts after lock-up, {len(POST)} labelled")

    idx = {t: i for i, t in enumerate(order)}
    labels = list(PRE) + [POST[idx[norm(s["text"])]] for s in post]
    if len(labels) != len(segs):
        raise SystemExit(f"{len(labels)} labels for {len(segs)} segments")

    # where the pure repetition starts: the longest run of the modal text
    modal, best, cur, start, best_start = order[0], 0, 0, 0, 0
    for i, s in enumerate(post):
        if norm(s["text"]) == modal:
            if cur == 0:
                start = i
            cur += 1
            if cur > best:
                best, best_start = cur, start
        else:
            cur = 0
    repeat_from = LOCKUP_SEG + best_start

    out = {
        "trace": "C", "uid": doc["instance_uid"], "cell": doc["cell"],
        "outcome": doc["outcome"], "temperature": doc["temperature"],
        "rubric": ".agents/reference/flame-rubric-reasoning-grid.md",
        "labelled_blind": False,
        "note": (
            "Labelled after A and B, whose labels were already locked and were not "
            "revised. Segments 0-72 individually; 73-395 by mapping each of the 44 "
            "distinct texts once. See probe/label_grind.py. A later blind pass "
            "reproduced all 117 judgments from segment text alone and moved 16 of "
            "them; see the reconciliation section of labels/README.md."
        ),
        "labels": labels,
        "lockup_segment": LOCKUP_SEG,
        "repeat_from_segment": repeat_from,
        "subtasks": [
            {"start": 0,  "end": 3,   "label": "Look for a shortcut"},
            {"start": 4,  "end": 23,  "label": "First part: 21,000 x"},
            {"start": 24, "end": 43,  "label": "Second part: 28 x"},
            {"start": 34, "end": 39,  "label": "Recheck the eighth partial product"},
            {"start": 44, "end": 50,  "label": "Add the two parts"},
            {"start": 51, "end": 58,  "label": "Recheck"},
            {"start": 59, "end": 63,  "label": "Scientific-notation crosscheck"},
            {"start": 64, "end": 72,  "label": "Try to reconcile"},
            {"start": LOCKUP_SEG, "end": len(segs) - 1, "label": "Locked"},
            {"start": repeat_from, "end": len(segs) - 1,
             "label": f"One sentence, {best} times, to the end of the context"},
        ],
        "annotations": [
            {"segment": 50, "kind": "correct_answer_reached",
             "text": "31,675,553,988,418,396 -- the exact truth -- written at 21% of the "
                     "trace. It is written 21 times in total and never delivered."},
            {"segment": 59, "kind": "crosscheck_begins",
             "text": "Converts both terms to scientific notation. This is the same move "
                     "that saved run A, and here it is the cause of everything that follows."},
            {"segment": 63, "kind": "false_contradiction",
             "text": "'this suggests that my previous addition was wrong.' It was not. The "
                     "crosscheck wrote 42,177,834,871,396 as 0.00042177834871396 x 10^16; "
                     "the correct coefficient is 0.0042177834871396. One zero too many "
                     "makes the smaller term 10x too small and produces "
                     "31,637,593,937,034,000, a plausible rival to the right answer."},
            {"segment": LOCKUP_SEG, "kind": "lockup",
             "text": "From here the model holds two answers it cannot choose between and "
                     "re-derives both. Neither ever wins, because the bug is in the "
                     "checker rather than in the sum, so every honest re-derivation "
                     "confirms both sides."},
            {"segment": repeat_from, "kind": "collapse",
             "text": "Greedy decoding has no way out of a repeating state: the same context "
                     "yields the same next token, so the cycle is closed. The remaining "
                     "context is spent on one sentence."},
        ],
        "verified": {
            "truth": 31675553988418396,
            "reached_correct_total_at_char": 11896,
            "times_correct_total_written": 21,
            "rival_from_broken_crosscheck": 31637593937034000,
            "times_rival_written": 6,
            "answer_delivered": None,
            "think_block_closed": False,
        },
    }
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    json.dump(out, open(OUT, "w"), indent=1)

    c = Counter(labels)
    ch = Counter()
    for l, s in zip(labels, segs):
        ch[l] += s["chars"]
    tot = sum(ch.values())
    print(f"wrote {OUT}")
    print(f"  {len(labels)} labels   lock-up at segment {LOCKUP_SEG}   "
          f"pure repeat from {repeat_from} ({best} in a row)")
    for k, n in c.most_common():
        print(f"    {k:<17}{n:>4}  {ch[k]/tot*100:>5.1f}% of chars")


if __name__ == "__main__":
    main()
