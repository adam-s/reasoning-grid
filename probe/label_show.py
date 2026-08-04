#!/usr/bin/env python3
"""Print a slice of the labelling worklist for judging.

    python probe/label_show.py 0 20        # items [0, 20)
    python probe/label_show.py 0 20 --wide # full target text, no truncation

The worklist is shuffled and identity-stripped; the keymap that maps an item back
to (trace, index) lives in a separate file and must stay closed until every label
is written. Nothing enforces that but the person running the pass.

Prints the rubric's category list at the top of every slice, so a judgment is
never made from memory of the categories.
"""
import argparse
import json

WORKLIST = "derived/v2/label-worklist.json"

CATEGORIES = [
    "FRAME", "SURVEY", "COMMIT", "ABANDON", "PRODUCT", "SCALE", "SUM", "REPORT",
    "REDERIVE", "CROSSCHECK", "SCALE_CHECK", "CHECK_FLOATED",
    "ALARM", "REVISE", "STAND", "STALL",
    "NONE",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("start", type=int)
    ap.add_argument("end", type=int)
    ap.add_argument("--wide", action="store_true")
    args = ap.parse_args()

    work = json.load(open(WORKLIST))
    cut = 10_000 if args.wide else 500

    print("categories:", " ".join(CATEGORIES))
    print("rules: .agents/reference/label-rubric-qwen-multiplication.md")
    print("LOOP and REPORT are computed elsewhere and are NOT options here.")
    print("=" * 78)
    for it in work[args.start:args.end]:
        print(f"### {it['n']}  {it['id']}")
        if it["prev2"]:
            print(f"  [-2] {it['prev2'][:180]}")
        if it["prev1"]:
            print(f"  [-1] {it['prev1'][:180]}")
        print(f"  >>>> {it['target'][:cut]}")
        if it["next1"]:
            print(f"  [+1] {it['next1'][:180]}")
        if it["next2"]:
            print(f"  [+2] {it['next2'][:180]}")
        print()


if __name__ == "__main__":
    main()
