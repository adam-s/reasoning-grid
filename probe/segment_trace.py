#!/usr/bin/env python3
"""Split a thinking trace into classifiable segments.

Newline splitting gives 213 segments on a trace this size, because Qwen writes
fragments: median 52 characters, lines like "So 34." and "3+4=7.". A fragment
carries no context, so the classifier cannot tell what it belongs to and the
chart turns to noise.

So a segment is a discourse MOVE, not a line. Break at a marker that starts a new
move, once the accumulated text is long enough to stand alone.

`--min-chars` was originally 100 because that landed the trace inside the 30-130
segment band of the project the flame components came from. That was never a fact
about these traces and the constraint is gone; 100 is kept because nothing
measured argues for moving it, not because of the band.

`--max-chars` exists because the real defect is in the TAIL, not the median.
Across the four labelled traces, 65 segments of 803 ran past 400 characters while
holding 26% of all text, and reading them shows why that matters: one 1,043-char
block computes six separate terms and would carry a single label. Forcing a break
at the next line once a segment passes the cap drops those merged blocks from 65
to 24, for 11% more segments.

The asymmetry is the argument. Splitting one move in two costs a duplicate label
on adjacent bars, which the chart renders identically and the shares count the
same. Merging two moves puts a WRONG label on part of the text. So when the rule
is uncertain, it should cut.

What the cap cannot fix: the largest remaining blocks are single lines the model
emitted with no internal newline -- 831 characters in one case -- and no
line-boundary rule can split those.

    python probe/segment_trace.py --uid 8129d2dbafcc8e77 -o derived/segments-D.json

Deliberately NOT a classifier. This only cuts; labels come from a separate pass,
so a segmentation change never silently relabels anything.
"""
import argparse, glob, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reduce_grid import load  # noqa: E402

# A new move starts here. Ordered loosely by how strongly each implies a break.
BREAK = re.compile(
    r"^\s*(wait\b|hold on\b|actually\b|but\b|so,?\s|now\b|next\b|first\b|second\b"
    r"|third\b|then\b|let me\b|let's\b|alternatively\b|another\b|therefore\b|thus\b"
    r"|hmm\b|okay\b|ok\b|to (check|verify|compute)\b|check\b|verify\b"
    r"|i (need|should|can|'ll|think)\b|the (sum|product|result|answer|last|number)\b"
    r"|adding\b|multiply|compute)", re.I)

THINK_END = "</think>"


def segment(text: str, min_chars: int = 100, max_chars: int | None = 300):
    """Merge lines into moves. Returns [{index, start, end, text}] over the RAW
    string, so offsets stay usable as flame-chart coordinates.

    Two break conditions, and they answer different failure modes:
      - at a MARKER once the segment can stand alone (min_chars), which stops
        fragments like "So 34." from being classified without context;
      - at ANY line once the segment has run long (max_chars), which stops one
        block from holding several moves under a single label.
    Pass max_chars=None for marker-only breaking.
    """
    segs, cur, cur_start = [], "", 0
    pos = 0
    for raw in text.split("\n"):
        line_start = pos
        pos += len(raw) + 1
        s = raw.strip()
        if not s:
            continue
        overlong = max_chars is not None and len(cur) >= max_chars
        if cur and (overlong or (BREAK.match(s) and len(cur) >= min_chars)):
            segs.append((cur_start, line_start, cur.strip()))
            cur, cur_start = s, line_start
        else:
            if not cur:
                cur_start = line_start
            cur = (cur + " " + s).strip()
    if cur:
        segs.append((cur_start, len(text), cur.strip()))
    return [{"index": i, "start": a, "end": b, "chars": b - a, "text": t}
            for i, (a, b, t) in enumerate(segs)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uid", required=True,
                    help="instance_uid -- pins the exact trace. Selecting by "
                         "cell+outcome picks whichever run happens to be median "
                         "length, which is not the trace the rubric describes.")
    ap.add_argument("--min-chars", type=int, default=100)
    ap.add_argument("--max-chars", type=int, default=300,
                    help="force a break at the next line once a segment passes "
                         "this, so one block cannot hold several moves. 0 disables.")
    ap.add_argument("--cell", default=None, help="label only; taken from the record")
    ap.add_argument("--runs", default="runs")
    ap.add_argument("--glob", default="1[01]-grid1*-qwen-*.jsonl",
                    help="which run files to search. The default is the T=0.7 grid "
                         "sweep; the temp-0 runs live under 14-temp0-*.")
    ap.add_argument("--temperature", type=float, default=0.7,
                    help="must match the record, so a uid can never be pulled from "
                         "a condition other than the one being described.")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()
    recs = load(sorted(glob.glob(os.path.join(args.runs, args.glob))),
                model="Qwen/Qwen3-4B", temperature=args.temperature)
    hits = [r for r in recs if r["instance_uid"] == args.uid]
    if not hits:
        raise SystemExit(f"no run with instance_uid {args.uid}")
    r = hits[0]
    a, b = r["a"], r["b"]

    segs = segment(r["raw_text"], args.min_chars, args.max_chars or None)
    cut = r["raw_text"].find(THINK_END)
    for s in segs:
        s["after_think"] = cut >= 0 and s["start"] >= cut

    doc = {
        "cell": f"{a}x{b}", "N": a * b, "correct": r["correct"],
        "instance_uid": r["instance_uid"],
        "x": r["x"], "y": r["y"], "truth": r["truth"], "answer": r["answer"],
        # A trace that never answered is not a wrong answer, and the chart has to
        # be able to say which it is looking at.
        "outcome": r.get("outcome"), "finish_reason": r.get("finish_reason"),
        "temperature": r.get("temperature"),
        "max_tokens": r.get("max_tokens"), "engine_max_len": r.get("engine_max_len"),
        "completion_tokens": r["completion_tokens"],
        "total_chars": len(r["raw_text"]),
        "min_chars": args.min_chars,
        "max_chars": args.max_chars or None,
        "n_segments": len(segs),
        "segments": segs,
    }
    out = args.out or f"derived/segments-{a}x{b}.json"
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w") as fh:
        json.dump(doc, fh, indent=1)
    lens = sorted(s["chars"] for s in segs)
    print(f"wrote {out}")
    verdict = (r.get("outcome") or ("correct" if r["correct"] else "WRONG")).upper()
    print(f"  {a}x{b}  {verdict}  T={r.get('temperature')}  "
          f"{r['completion_tokens']:,} tok  {len(r['raw_text']):,} chars")
    print(f"  {len(segs)} segments   median {lens[len(lens)//2]} chars   max {lens[-1]}")
    print(f"  {sum(1 for s in segs if s['after_think'])} after </think>")


if __name__ == "__main__":
    main()
