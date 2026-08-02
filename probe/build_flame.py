#!/usr/bin/env python3
"""segments + labels -> the flame data the post renders.

Depth is not a model output. The labelling pass emits a FLAT list of
{start, end, label} sub-task ranges over segment indices, and nesting is derived:

    depth(range) = how many other ranges strictly contain it
    depth(leaf)  = 1 + depth of its innermost containing range

That is the trick worth keeping from the lambda pipeline. Because containment
decides the tree, bars at one depth are non-overlapping and in order by
construction -- there is no way for a model to hand back a malformed tree.

x is CHARACTER OFFSET in the trace, not time. There is no per-segment timing in
this data; only whole-generation token counts. Any axis label that says
"seconds" would be a lie, and the offset is arguably the better measure anyway:
it counts what the model produced rather than how fast the GPU ran.

    python probe/build_flame.py
"""
import json
import os
import re

TRACES = [
    ("A", "derived/segments-A-7x11-correct.json", "labels/A-7x11-correct.json",
     "Solved it", "Every check it ran could see the answer."),
    ("B", "derived/segments-B-8x7-wrong.json", "labels/B-8x7-wrong.json",
     "Got it wrong", "Verified for 40% of the trace, with checks blind to its own error."),
    ("C", "derived/segments-C-5x13-grind.json", "labels/C-5x13-grind.json",
     "Never answered", "Had the right answer at 21% and could not stop."),
]
OUT = "blog/src/lib/data/carrychain-traces.ts"
MAX_TEXT = 420          # tooltips do not need more, and C repeats one line 275 times


# Qwen writes its post-</think> summary in Markdown and LaTeX, so the last few
# segments of a finished trace carry $$, \begin{align*}, ** and \boxed{}. Drawn
# literally on a bar they are unreadable. Cleaning happens HERE, at build time,
# for display only: offsets and widths are measured on the raw string and are not
# affected, the segment files keep the raw text, and runs/ is never touched.
TAG = re.compile(r"</?think>")
BRACED = re.compile(r"\\(?:boxed|text|mathrm|mathbf|mathit)\s*\{([^{}]*)\}")
ENV = re.compile(r"\\(?:begin|end)\s*\{[^{}]*\}")
CMD = re.compile(r"\\[a-zA-Z]+")
# Longest first. Substring order matters: \cdot replaced before \cdots leaves a
# stray "s" behind, which is how "\cdots" first rendered as "·s".
SYMBOL = dict(sorted({
    r"\times": "×", r"\cdots": "…", r"\ldots": "…", r"\dots": "…", r"\cdot": "·",
    r"\approx": "≈", r"\leq": "≤", r"\geq": "≥", r"\neq": "≠", r"\pm": "±",
    r"\le": "≤", r"\ge": "≥", r"\ne": "≠",
    r"\sum": "∑", r"\prod": "∏", r"\frac": "/",
    r"\quad": " ", r"\qquad": " ", r"\,": " ", r"\;": " ", r"\!": "",
}.items(), key=lambda kv: -len(kv[0])))


def display(t):
    """What a reader sees on a bar and in its tooltip."""
    t = TAG.sub(" ", t)
    t = BRACED.sub(r"\1", t)          # \boxed{123} -> 123
    t = ENV.sub(" ", t)               # \begin{align*} -> gone
    for a, b in SYMBOL.items():
        t = t.replace(a, b)
    t = t.replace("\\\\", " ")        # LaTeX line break
    t = t.replace("$$", " ").replace("$", " ")
    t = t.replace("&=", "=").replace("&", " ")
    t = CMD.sub(" ", t)               # any command left over
    # Sub/superscripts: keep the value, drop the TeX braces. Done AFTER commands
    # are stripped, so \sum_{i=0}^{10} does not leave a dangling "_{i=0}".
    t = re.sub(r"([_^])\s*\{([^{}]*)\}", r"\1\2", t)
    t = t.replace("**", "").replace("__", "")
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"(?:^|(?<= ))(?:#{1,6}|-{3,}|\|)(?= |$)", " ", t)
    return re.sub(r"\s+", " ", t).strip(" -–—·:")


def clean(s):
    return re.sub(r"\s+", " ", s).strip()


def short(s, n=58):
    s = display(s)
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def build(segs, labels, subtasks):
    def depth_of(r):
        return sum(1 for o in subtasks
                   if (o["start"], o["end"]) != (r["start"], r["end"])
                   and o["start"] <= r["start"] and o["end"] >= r["end"])

    ranked = [(r, depth_of(r)) for r in subtasks]

    # dominant leaf category, by characters, names the container bar
    def dominant(a, b):
        w = {}
        for i in range(a, b + 1):
            w[labels[i]] = w.get(labels[i], 0) + segs[i]["chars"]
        return max(w, key=w.get)

    rows = []
    for r, d in ranked:
        a, b = r["start"], r["end"]
        rows.append(dict(depth=d, start=segs[a]["start"],
                         width=segs[b]["end"] - segs[a]["start"],
                         category=dominant(a, b), label=r["label"],
                         # FlameGraph draws `text` on the bar, so the subtask name
                         # lives there. The segment range used to trail it and was
                         # cut: the bar already shows the span, which is the only
                         # thing those numbers were saying.
                         text=r["label"],
                         index=a, container=True, muted=True))

    for i, s in enumerate(segs):
        inner = [d for r, d in ranked if r["start"] <= i <= r["end"]]
        rows.append(dict(depth=(max(inner) + 1) if inner else 0,
                         start=s["start"], width=s["chars"],
                         category=labels[i], label=short(s["text"]),
                         text=display(s["text"])[:MAX_TEXT], index=i,
                         container=False, muted=False))
    rows.sort(key=lambda r: (r["depth"], r["start"]))
    return rows


def main():
    out = []
    for key, sf, lf, verdict, blurb in TRACES:
        seg = json.load(open(sf))
        lab = json.load(open(lf))
        segs, labels = seg["segments"], lab["labels"]
        assert len(segs) == len(labels), f"{key}: {len(segs)} vs {len(labels)}"
        rows = build(segs, labels, lab["subtasks"])
        out.append(dict(
            key=key, cell=seg["cell"], n=seg["N"], uid=seg["instance_uid"],
            outcome=seg.get("outcome") or ("converged_right" if seg["correct"] else "converged_wrong"),
            verdict=verdict, blurb=blurb,
            temperature=seg.get("temperature", 0.7),
            x=seg["x"], y=seg["y"], truth=seg["truth"], answer=seg["answer"],
            tokens=seg["completion_tokens"], chars=seg["total_chars"],
            segments=len(segs), rows=rows,
        ))

    body = ",\n".join(json.dumps(t, indent=1) for t in out)
    ts = f'''/**
 * GENERATED by probe/build_flame.py -- do not edit.
 *
 * Three Qwen3-4B traces at neighbouring difficulty, one per outcome. Segments
 * from probe/segment_trace.py; categories hand-assigned against
 * .agents/reference/flame-rubric-carrychain.md; depth derived from containment.
 *
 * `start` and `width` are CHARACTER OFFSETS in the trace, not seconds.
 */
import type {{ CarryCategory }} from '../design/carrychain-categories';

export type CarryFlameRow = {{
  readonly depth: number;
  readonly start: number;
  readonly width: number;
  readonly category: CarryCategory;
  readonly label: string;
  readonly text: string;
  readonly index: number;
  readonly container: boolean;
  readonly muted: boolean;
}};

export type CarryTrace = {{
  readonly key: 'A' | 'B' | 'C';
  readonly cell: string;
  readonly n: number;
  readonly uid: string;
  readonly outcome: 'converged_right' | 'converged_wrong' | 'grind' | 'quit';
  readonly verdict: string;
  readonly blurb: string;
  readonly temperature: number;
  readonly x: string;
  readonly y: string;
  readonly truth: string;
  readonly answer: string | null;
  readonly tokens: number;
  readonly chars: number;
  readonly segments: number;
  readonly rows: readonly CarryFlameRow[];
}};

export const CARRY_TRACES: readonly CarryTrace[] = [
{body}
];
'''
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write(ts)
    print(f"wrote {OUT}  ({os.path.getsize(OUT)/1024:.0f} KB)")
    for t in out:
        d = max(r["depth"] for r in t["rows"])
        print(f"  {t['key']}  {t['cell']:<5} N={t['n']:<3} T={t['temperature']}  "
              f"{t['segments']:>3} segments  {len(t['rows']):>3} rows  max depth {d}  "
              f"{t['tokens']:>6,} tok  {t['outcome']}")


if __name__ == "__main__":
    main()
