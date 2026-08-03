#!/usr/bin/env python3
"""Thinking text + the arithmetic it states -> blog/src/lib/data/opener.ts

    python probe/build_opener.py

The opening figure runs a model's thinking past the reader and lands each
arithmetic claim in a second pane as it is stated, already checked. So this
script has to do two things: ship the raw thinking, and extract every closed
arithmetic claim in it with a verdict computed rather than trusted.

## What counts as a claim

A model writes two kinds of `=` line. One states a result. The other REWRITES
the same quantity -- "A x 50,000,000 = A x 5 x 10^7" -- which is not a claim
that can be true or false. Only the first is extracted, so a rewriting is never
reported as an error.

Three passes of this were wrong before it was right, all in the same direction:
inventing errors in runs that made none.

  1. A loose right-hand side read "A x 50,000,000 = A x 5 x 10^7" as a claim
     that the product is 2,053,896, and "= 80.4 x 10^6" as a claim it is 80.
  2. Guarding with a lookahead let the regex BACKTRACK into a shorter number
     when the guard failed, so "= 18,000,000" matched as "= 1" and trace A --
     which states 67 facts and gets every one right -- appeared to make
     seventeen errors.
  3. Rejecting a following "." killed sentence-ending periods along with
     decimals, and dropped the one real error there is.

The fix for all three is to match MAXIMAL runs of digits and commas, so there is
no shorter prefix to fall back into, then check the neighbourhood separately.
A number is also required to be well formed -- comma groups of exactly three --
which rejects the model interrupting itself mid-number, as trace C does at
"= 31,675,554,0 (wait, need to do this properly)".

## Result

  trace A, converged right   72 claims, 0 false
  trace B, converged wrong   36 claims, 1 false -- an ADDITION; every one of
                             its multiplications is correct
  trace C, never answered    52 claims, 0 false -- it does not fail at
                             arithmetic, it fails to commit

Decimals are read too, because the approximation check a model runs at the end
of a trace is done in them -- "0.4 x 4.62 = 1.848", "369.6 + 1.848 = 371.448".
Skipping those left the maths pane silent through the last 30% of the wrong run,
which is exactly where the model checks its answer, finds the check agrees, and
carries on. Arithmetic is done with Decimal: binary floating point grades some of
those wrong for being 1e-16 out.

Subtraction was added after an adversarial pass asked what the extractor cannot
see. It could only see x and +, so eleven subtraction claims went ungraded and
"160 claims, 1 false" was really "160 multiplications and additions". All eleven
turned out correct, so the headline did not move -- but it was not defensible
until they were checked.

Those counts are printed on every run. If they move, the extractor changed and
the prose that quotes them needs re-checking.
"""
import argparse
import glob
import json
import os
import re
import sys
from decimal import Decimal, getcontext

getcontext().prec = 60          # exact for every value these traces contain

OUT = "blog/src/lib/data/opener.ts"
MODEL = "Qwen3-4B"

# Subtraction is checked; DIVISION deliberately is not. A model casting out
# nines writes "87 / 9 = 9", meaning nine remainder six, and grading that as
# false would report a correct check as an error. Subtraction has no such
# second reading.
NUM = r"[\d,]+(?:\.\d+)?"
EQ = re.compile(rf"({NUM})\s*(×|x|\*|\+|-|−)\s*({NUM})\s*=\s*({NUM})")


def plain(d):
    """A Decimal as the shortest exact decimal string: no exponent, no trailing
    zeros invented by the arithmetic."""
    t = format(d.normalize(), "f")
    return t.rstrip("0").rstrip(".") if "." in t else t


def wellformed(s):
    """A number the model finished writing. Comma groups are exactly three, and
    a decimal part is digits."""
    head, _, frac = s.partition(".")
    if frac and not frac.isdigit():
        return False
    if head.startswith(",") or head.endswith(","):
        return False
    p = head.split(",")
    return len(p) == 1 or (1 <= len(p[0]) <= 3 and all(len(g) == 3 for g in p[1:]))


def claims(t):
    """Every closed arithmetic claim in `t`, with the truth computed."""
    out = []
    for m in EQ.finditer(t):
        x, op, y, z = m.group(1), m.group(2), m.group(3), m.group(4)
        if not all(map(wellformed, (x, y, z))):
            continue
        if re.search(r"[-+×x*/^]\s*$", t[max(0, m.start() - 2):m.start()]):
            continue                                   # third term of a longer sum
        if op in "-−" and re.search(r"\d\s*$", t[max(0, m.start() - 2):m.start()]):
            continue                                   # a minus sign inside a range
        if re.match(r"[.,]\d|\s*[-+×x*/^]", t[m.end():m.end() + 2]):
            continue                                   # a decimal, or a rewriting
        # Decimal, not float. The approximation check a model runs at the end
        # of a trace is done in decimals -- "0.4 x 4.62 = 1.848" -- and binary
        # floating point would grade some of those wrong for being 1e-16 out.
        a, b, c = (Decimal(v.replace(",", "")) for v in (x, y, z))
        if not a or not b:
            continue
        sym = {"+": "+", "-": "−", "−": "−"}.get(op, "×")
        truth = a + b if sym == "+" else a - b if sym == "−" else a * b
        out.append({"at": m.start(), "end": m.end(), "op": sym,
                    "a": plain(a), "b": plain(b), "said": plain(c),
                    "truth": plain(truth), "ok": truth == c})
    return out


def load(uid, runs, chars):
    """The generation the flame figure segmented, not merely one of the same
    problem.

    `instance_uid` identifies the PROBLEM. The same problem was sampled several
    times, across sweeps and at more than one temperature, so matching on the
    uid alone returns whichever record happens to come first -- and for two of
    the three traces that was a different generation from the one the flame
    graph was built from. The two figures then showed different text under the
    same heading, and a playhead driven by one indexed the other.

    So the response LENGTH is matched too, which is what the flame data records
    and what pins a specific generation.

    A trace with no `</think>` is not skipped. That is what running out of
    context mid-thought looks like, and it is the whole reason one of these runs
    never answered.
    """
    hits = []
    for f in sorted(glob.glob(os.path.join(runs, "*.jsonl"))):
        for line in open(f):
            if uid not in line:
                continue
            j = json.loads(line)
            if not (j.get("model") or "").endswith(MODEL):
                continue
            raw = j.get("raw_text") or ""
            if len(raw) != chars:
                continue
            # VERBATIM. The flame graph's offsets index the raw response --
            # its span equals the response length exactly -- so stripping the
            # <think> tag shifted every bar seven characters off the text it
            # labels, and trimming the ends stopped the playhead reaching 100%
            # because the stream was shorter than the graph it drove.
            hits.append((j, raw))
    if len(hits) != 1:
        sys.exit(f"{uid}: expected exactly one {MODEL} response of {chars:,} chars, "
                 f"found {len(hits)}")
    return hits[0]


HEADER = '''/**
 * GENERATED by probe/build_opener.py -- do not edit.
 *
 * A model's response verbatim, and every arithmetic claim inside it with the
 * answer computed rather than taken on trust. `at` is a character offset into
 * `text`, so the figure can land a claim exactly when the stream reaches it --
 * and the SAME offsets index the flame graph, because both are built from this
 * one string.
 *
 * `segments` are the same boundaries and categories the flame figure uses, so
 * the stream can be tinted by what kind of move the model was making. The three
 * runs are the flame figure's three runs -- same instance_uid, same Qwen3-4B
 * generation -- so the opener and section 05 are two readings of one set of
 * traces, not two sets that happen to look alike.
 */
export type Claim = {
  readonly at: number;
  readonly end: number;
  readonly op: '×' | '+' | '−';
  /** decimal strings: several exceed Number.MAX_SAFE_INTEGER */
  readonly a: string;
  readonly b: string;
  readonly said: string;
  readonly truth: string;
  readonly ok: boolean;
};

export type OpenerSegment = {
  readonly start: number;
  readonly end: number;
  readonly category: string;
  readonly label: string;
};

export type OpenerTrace = {
  readonly key: string;
  /** The same instance_uid the flame figure uses. These two figures show the
   *  SAME three runs, and this is what makes that checkable from the data
   *  rather than from someone remembering it. */
  readonly uid: string;
  readonly cell: string;
  readonly x: string;
  readonly y: string;
  readonly truth: string;
  readonly answer: string | null;
  readonly outcome: string;
  readonly verdict: string;
  /** The response VERBATIM, exactly the string the flame graph's character
   *  offsets index. Tags and final answer included. */
  readonly text: string;
  readonly claims: readonly Claim[];
  readonly segments: readonly OpenerSegment[];
};

export const OPENER: readonly OpenerTrace[] = '''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs")
    ap.add_argument("-o", "--out", default=OUT)
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ts = open(os.path.join(root, "blog/src/lib/data/carrychain-traces.ts")).read()
    built = json.loads(ts[ts.index("= [") + 2:ts.rindex("];") + 1])

    out = []
    for tr in built:
        j, text = load(tr["uid"], args.runs, tr["chars"])
        cl = claims(text)
        # Segment offsets are into the trace as segmented, which starts at the
        # same place this thinking does; leaves carry the boundaries.
        # SORTED BY START. The flame rows are ordered for flame rendering, which
        # is not ascending by offset -- trace A jumps from 17,682 back to 952 at
        # index 19. Anything that walks these in array order and stops at the
        # first segment past a cursor renders a fifth of the trace, in the wrong
        # order, and looks fine because the pane still fills.
        segs = sorted(
            ({"start": r["start"], "end": r["start"] + r["width"],
              "category": r["category"], "label": r["label"]}
             for r in tr["rows"] if not r.get("container")),
            key=lambda s: s["start"])
        # The segments must tile the thinking exactly, or the left pane is not
        # showing what the model wrote. Checked here rather than trusted.
        rebuilt = "".join(text[s["start"]:s["end"]] for s in segs)
        if rebuilt != text:
            sys.exit(f"{tr['key']}: segments do not tile the thinking "
                     f"({len(rebuilt):,} rebuilt vs {len(text):,})")
        out.append({"key": tr["key"], "uid": tr["uid"],
                    "cell": tr["cell"], "x": tr["x"], "y": tr["y"],
                    "truth": tr["truth"], "answer": tr["answer"],
                    "outcome": tr["outcome"], "verdict": tr["verdict"],
                    "text": text, "claims": cl, "segments": segs})
        bad = [c for c in cl if not c["ok"]]
        print(f"  trace {tr['key']} {tr['cell']:>5}  {tr['outcome']:16s} "
              f"{len(text):6,} chars  {len(cl):3d} claims, {len(bad)} false")
        for c in bad:
            print(f"      {int(c['a']):,} {c['op']} {int(c['b']):,} = {int(c['said']):,}"
                  f"   actually {int(c['truth']):,}")

    path = args.out if os.path.isabs(args.out) else os.path.join(root, args.out)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write(HEADER + json.dumps(out, indent=1, ensure_ascii=False) + ";\n")
    tot = sum(len(t["claims"]) for t in out)
    wrong = sum(1 for t in out for c in t["claims"] if not c["ok"])
    print(f"\nwrote {args.out}  ({os.path.getsize(path)/1024:.0f} KB)")
    print(f"  {tot} claims across {len(out)} traces, {wrong} false")


if __name__ == "__main__":
    main()
