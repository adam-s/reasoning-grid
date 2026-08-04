#!/usr/bin/env python3
"""Two behaviours the label work turned up, measured across the whole Qwen corpus
rather than the four traces that are labelled by hand.

1. HOW OFTEN A RUN REVISES A VALUE IT ALREADY WROTE, against trace length.
   This matters because a hand-labelled sample of mid-length traces found zero
   revisions, and that was reported as a property of the model. It is a property
   of the sample: revision is rare in short traces and usual in long ones.

2. WHAT `outcome == "grind"` IS ACTUALLY MERGING. Two different endings share the
   label: a run that locked into repeating itself, and a run still making
   progress when the token ceiling arrived. Those are not the same result, and
   the project's own rules say not to collapse "stopped early", "finished long"
   and "never finished" into one bucket.

WHAT THIS IS NOT. The revision detector is a text pattern, not a label. It
requires an explicit statement that a written value was wrong -- "this is a
mistake", "let me correct", "should be X, not Y" -- so it UNDERCOUNTS: a model
that silently recomputes a term is not caught. Treat the direction and the
magnitude as solid and the exact percentages as a floor. The hand-labelled
`REVISE` category is the accurate instrument; this is the wide-angle one.

Degeneracy is measured as the share of unique non-blank lines. It separates the
two endings cleanly here -- the locked-up traces sit near 30% and the
still-working ones near 90% -- but it is a proxy for "the model stopped saying
anything new", not a definition of it.

    python probe/revision_rate.py
"""
import glob
import json
import re
import statistics
from collections import Counter

MODEL_GLOB = "runs/*Qwen3-4B*.jsonl"

# Explicit statements that a written value was wrong. Deliberately narrow.
REVISION = re.compile(
    r"(this is (a |the )?mistake"
    r"|i must have made a mistake"
    r"|let me correct"
    r"|i made an error"
    r"|which is wrong\.? the correct"
    r"|should be .{0,40}, not )", re.I)

LENGTH_BANDS = [(0, 5_000), (5_000, 10_000), (10_000, 20_000), (20_000, 40_000)]
DEGENERATE_BELOW = 0.50      # share of unique lines
MIN_LINES = 20               # too short to judge repetition


def unique_line_share(text: str) -> float:
    lines = [" ".join(l.split()) for l in text.split("\n") if l.strip()]
    if len(lines) < MIN_LINES:
        return 1.0
    return len(set(lines)) / len(lines)


def main():
    correct, grinds = [], []
    for path in glob.glob(MODEL_GLOB):
        for line in open(path):
            r = json.loads(line)
            if r.get("outcome") == "grind":
                lines = [l for l in r["raw_text"].split("\n") if l.strip()]
                if len(lines) >= MIN_LINES:
                    grinds.append((r.get("temperature"), unique_line_share(r["raw_text"])))
            # Revision rate is asked of runs that ANSWERED CORRECTLY, so the
            # comparison is not contaminated by runs that were failing anyway.
            if (r.get("correct") and not r.get("room_clipped")
                    and r.get("finish_reason") == "stop"):
                correct.append((r["completion_tokens"],
                                len(REVISION.findall(r["raw_text"]))))

    print("1. REVISION RATE AGAINST TRACE LENGTH")
    print(f"   {len(correct)} correct, unclipped, naturally-stopped Qwen3-4B runs\n")
    print(f"   {'tokens':>14}{'runs':>7}{'with a revision':>18}{'median':>9}")
    for lo, hi in LENGTH_BANDS:
        band = [(t, n) for t, n in correct if lo <= t < hi]
        if not band:
            continue
        withrev = sum(1 for _, n in band if n > 0)
        print(f"   {f'{lo:,}-{hi:,}':>14}{len(band):>7}{withrev / len(band) * 100:>17.0f}%"
              f"{statistics.median(n for _, n in band):>9.0f}")

    print("\n2. WHAT 'grind' MERGES")
    print(f"   {len(grinds)} grind traces with at least {MIN_LINES} lines\n")
    print(f"   {'temperature':>13}{'traces':>8}{'locked up':>11}{'share':>8}")
    for T in sorted({t for t, _ in grinds}):
        band = [u for t, u in grinds if t == T]
        deg = sum(1 for u in band if u < DEGENERATE_BELOW)
        print(f"   {T:>13}{len(band):>8}{deg:>11}{deg / len(band) * 100:>7.0f}%")
    print(f"\n   'locked up' = under {DEGENERATE_BELOW:.0%} unique lines. The rest ran out"
          f"\n   of room while still producing new text, which is a different result.")


if __name__ == "__main__":
    main()
