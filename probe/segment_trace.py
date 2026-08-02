#!/usr/bin/env python3
"""Split a thinking trace into classifiable segments.

Newline splitting -- what the lambda pipeline used -- gives 213 segments here
against their 30-130, because Qwen writes fragments: median 52 characters, lines
like "So 34." and "3+4=7.". A fragment carries no context, so the classifier
cannot tell what it belongs to and the chart turns to noise.

So a segment is a discourse MOVE, not a line. Break only at a marker that starts
a new move, and only once the accumulated text is long enough to stand alone.
That yields 64 segments per trace at a median of ~195 characters -- back inside
the lambda band, with each segment recognisable as a step.

    python probe/segment_trace.py --cell 7x11 --correct
    python probe/segment_trace.py --cell 8x7 --wrong --out derived/segments-B.json

Deliberately NOT a classifier. This only cuts; labels come from a separate pass
against .agents/reference/flame-rubric-carrychain.md, so a segmentation change
never silently relabels anything.
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


def segment(text: str, min_chars: int = 100):
    """Merge lines into moves. Returns [{index, start, end, text}] over the RAW
    string, so offsets stay usable as flame-chart coordinates."""
    segs, cur, cur_start = [], "", 0
    pos = 0
    for raw in text.split("\n"):
        line_start = pos
        pos += len(raw) + 1
        s = raw.strip()
        if not s:
            continue
        if cur and BREAK.match(s) and len(cur) >= min_chars:
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

    segs = segment(r["raw_text"], args.min_chars)
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
