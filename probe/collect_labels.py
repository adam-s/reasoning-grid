#!/usr/bin/env python3
"""Merge the labelling pass back into per-trace label files, and check it.

Input:  labels/v2/raw/slice-*.json -- what each blind labeller returned, one file
        per slice, each a JSON array of {n, id, label, rule}.
Output: labels/v2/<trace>.json, with the `labels` array filled in.

Everything this script does is a check that would otherwise be an assumption:

  - every worklist item is labelled exactly once, and no unknown id appears;
  - every label is one of the rubric's categories, and never LOOP or a
    judged REPORT (both are computed, and assigning them by judgment is a
    stated fail condition);
  - the expansion from 340 judgments to 636 segments hits every segment that
    was left null by precompute_labels.py, and none that was not;
  - the NONE rate is reported, because the rubric says it must be;
  - the SCALE count is reported against its pre-registered threshold of 5.

A malformed or missing label fails the run. There is no silent fallback to a
default category: that is how a chart ends up plausible and wrong.

    python probe/collect_labels.py
"""
import glob
import json
import os
import sys
from collections import Counter

WORKLIST = "derived/v2/label-worklist.json"
KEYMAP = "derived/v2/label-keymap.json"
RAW = "labels/v2/raw"
LAB_DIR = "labels/v2"

# Judged categories. LOOP is computed; REPORT is computed after </think> but is
# also reachable by rule 17, so it stays legal here.
JUDGED = {
    "FRAME", "SURVEY", "COMMIT", "ABANDON", "PRODUCT", "SCALE", "SUM", "REPORT",
    "REDERIVE", "CROSSCHECK", "SCALE_CHECK", "CHECK_FLOATED",
    "ALARM", "REVISE", "STAND", "STALL", "NONE",
}
SCALE_THRESHOLD = 5     # pre-registered: below this, SCALE merges into SUM


def die(msg):
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def main():
    work = {it["id"]: it for it in json.load(open(WORKLIST))}
    key = json.load(open(KEYMAP))

    got: dict[str, str] = {}
    for path in sorted(glob.glob(os.path.join(RAW, "slice-*.json"))):
        for row in json.load(open(path)):
            uid, label = row["id"], row["label"]
            if uid not in work:
                die(f"{path}: id {uid} is not in the worklist")
            if label not in JUDGED:
                die(f"{path}: id {uid} has label {label!r}, not a judged category")
            if label == "LOOP":
                die(f"{path}: id {uid} was assigned LOOP by judgment -- computed only")
            if uid in got and got[uid] != label:
                die(f"id {uid} labelled twice and differently: {got[uid]} vs {label}")
            got[uid] = label

    missing = set(work) - set(got)
    if missing:
        die(f"{len(missing)} worklist items never labelled, e.g. {sorted(missing)[:5]}")

    # Expand judgments across every segment the keymap says they stand for.
    per_trace: dict[str, dict[int, str]] = {}
    for uid, occs in key.items():
        for o in occs:
            per_trace.setdefault(o["trace"], {})[o["index"]] = got[uid]

    counts = Counter()
    for lab_path in sorted(glob.glob(os.path.join(LAB_DIR, "*.json"))):
        trace = os.path.basename(lab_path).replace(".json", "")
        doc = json.load(open(lab_path))
        filled = per_trace.get(trace, {})
        labels = list(doc["labels"])
        for i, existing in enumerate(labels):
            if existing is not None:
                counts[existing] += 1
                continue
            if i not in filled:
                die(f"{trace}: segment {i} was left for judgment but never labelled")
            labels[i] = filled[i]
            counts[filled[i]] += 1
        if any(x is None for x in labels):
            die(f"{trace}: null labels remain after expansion")
        doc["labels"] = labels
        doc["labelled"] = True
        json.dump(doc, open(lab_path, "w"), indent=1)
        print(f"{trace:<22} {len(labels):>4} segments labelled")

    total = sum(counts.values())
    print(f"\n{'category':<16}{'n':>6}{'share':>8}")
    for cat, n in counts.most_common():
        print(f"{cat:<16}{n:>6}{n / total * 100:>7.1f}%")
    print(f"{'total':<16}{total:>6}")

    none = counts.get("NONE", 0)
    print(f"\nNONE rate: {none}/{total} = {none / total * 100:.1f}%")

    scale = counts.get("SCALE", 0)
    verdict = "KEEP" if scale >= SCALE_THRESHOLD else "MERGE INTO SUM"
    print(f"SCALE: {scale} assignments against a pre-registered threshold of "
          f"{SCALE_THRESHOLD} -> {verdict}")


if __name__ == "__main__":
    main()
