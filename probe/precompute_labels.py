#!/usr/bin/env python3
"""Assign the two labels that are computed rather than judged.

Rules 1 and 2 of .agents/reference/label-rubric-qwen-multiplication.md:

  LOOP    a segment identical to the one before it, in a run of three or more
  REPORT  any segment after </think>

Both are mechanical, so they are reproducible by script and cost no judgment.
LOOP matters most: one trace repeats a single sentence 276 times, and asking a
model 276 times what an identical string means is waste whose answers would not
all agree.

The run-of-three floor is deliberate. Two identical segments in a row can be a
model restating itself before moving on; three or more is the degenerate loop
this is meant to catch. The floor is stated here rather than tuned later, and
`--min-run` exists so a different floor has to be passed explicitly and recorded.

Everything not labelled here is left as null for the judged pass, so a
segmentation change can never silently relabel a judged segment.

    python probe/precompute_labels.py derived/v2/segments-*.json
"""
import argparse
import glob
import json
import os


def normalise(text: str) -> str:
    return " ".join(text.split())


def precompute(segments, min_run: int = 3):
    """Returns a list of labels, one per segment, None where a judgment is needed."""
    n = len(segments)
    labels = [None] * n
    norm = [normalise(s["text"]) for s in segments]

    # LOOP first: runs of identical consecutive text, at least min_run long.
    i = 0
    while i < n:
        j = i
        while j + 1 < n and norm[j + 1] == norm[i]:
            j += 1
        if j - i + 1 >= min_run:
            for k in range(i, j + 1):
                labels[k] = "LOOP"
            # A run that ends because the context ran out leaves one truncated
            # emission: the same sentence, cut mid-word. It is not identical, so
            # the test above misses it -- and the rubric forbids assigning LOOP by
            # judgment, so without this it would be forced into a wrong label.
            # A proper prefix of the looped text, directly after the run, is a
            # repeat that did not finish.
            if j + 1 < n and norm[j + 1] and norm[i].startswith(norm[j + 1]):
                labels[j + 1] = "LOOP"
                j += 1
        i = j + 1

    # REPORT second. A segment cannot be both; a locked-up trace never reaches
    # </think>, so in practice these do not overlap, but LOOP wins if they ever do.
    for k, s in enumerate(segments):
        if s.get("after_think") and labels[k] is None:
            labels[k] = "REPORT"
    return labels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--min-run", type=int, default=3)
    ap.add_argument("--out-dir", default="labels/v2")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    grand = {"LOOP": 0, "REPORT": 0, "judged": 0, "total": 0}

    for path in sorted(f for p in args.files for f in glob.glob(p)):
        doc = json.load(open(path))
        segs = doc["segments"]
        labels = precompute(segs, args.min_run)

        loop = sum(1 for x in labels if x == "LOOP")
        rep = sum(1 for x in labels if x == "REPORT")
        todo = sum(1 for x in labels if x is None)
        # Distinct texts still needing a judgment -- what the labelling actually costs.
        distinct = len({normalise(s["text"]) for s, x in zip(segs, labels) if x is None})

        name = os.path.basename(path).replace("segments-", "").replace(".json", "")
        out = os.path.join(args.out_dir, f"{name}.json")
        with open(out, "w") as fh:
            json.dump({
                "source": path,
                "instance_uid": doc["instance_uid"],
                "cell": doc["cell"], "outcome": doc.get("outcome"),
                "temperature": doc.get("temperature"),
                "min_chars": doc.get("min_chars"), "max_chars": doc.get("max_chars"),
                "min_run": args.min_run,
                "n_segments": len(segs),
                "computed": {"LOOP": loop, "REPORT": rep},
                "to_judge": todo, "distinct_to_judge": distinct,
                "labels": labels,
            }, fh, indent=1)

        grand["LOOP"] += loop
        grand["REPORT"] += rep
        grand["judged"] += todo
        grand["total"] += len(segs)
        print(f"{name:<24} {len(segs):>4} seg   LOOP {loop:>4}   REPORT {rep:>3}   "
              f"to judge {todo:>4} ({distinct} distinct)   -> {out}")

    print(f"\n{'total':<24} {grand['total']:>4} seg   LOOP {grand['LOOP']:>4}   "
          f"REPORT {grand['REPORT']:>3}   to judge {grand['judged']:>4}")


if __name__ == "__main__":
    main()
