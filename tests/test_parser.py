"""Regression corpus for parse_answer, built from REAL model output.

Three versions of the parser have shipped broken. Each time the fix for one
failure mode created another, because the test cases were invented rather than
taken from records. Every tail here came off disk.

  .venv/bin/python tests/test_parser.py
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
src = (ROOT / "probe" / "bakeoff.py").read_text()
ns = {}
m = re.search(r"^def parse_answer\(.*?(?=\n# ---)", src, re.S | re.M)
exec(compile(m.group(0), "parser", "exec"), ns)
parse_answer = ns["parse_answer"]

# hand-written edge cases that must never regress
SYNTHETIC = [
    ("ANSWER: 12345", "12345"),
    ("**ANSWER: 14019192**", "14019192"),
    ("**ANSWER:** 42", "42"),
    ("ANSWER: 1,524,157,875", "1524157875"),
    ("ANSWER: 12345.", "12345"),
    ("### Final Answer\n\n$$\n\\boxed{2781186379132}\n$$", "2781186379132"),
    ("$$\\text{ANSWER: } 5822212423362 $$", "5822212423362"),
    ("working...\n59085180", "59085180"),
    ("ANSWER: 1.2345e7", None),          # scientific notation is not an integer
    ("ANSWER: 3.5", None),               # a product is an integer
    ("I cannot compute this reliably.", None),
    ("144*7=1008\n288*7=2016\nI give up.", None),
]


def main():
    fails = []
    for text, want in SYNTHETIC:
        got, _ = parse_answer(text)
        if got != want:
            fails.append(("synthetic", repr(text[:44]), want, got))

    corpus = ROOT / "tests" / "parser_fixtures.json"
    n_corpus = 0
    if corpus.exists():
        for f in json.loads(corpus.read_text()):
            got, method = parse_answer(f["tail"])
            n_corpus += 1
            # the corpus locks BEHAVIOUR: what the model asserted, and by which
            # path. `was_correct` is recorded but never asserted -- a parser's
            # job is to extract the claim, not to find the right answer.
            if got != f["expect"] or method != f.get("method", method):
                fails.append((f.get("model","?"), f["cell"], f["expect"], got))

    print(f"synthetic {len(SYNTHETIC)}  corpus {n_corpus}  failures {len(fails)}")
    for why, where, want, got in fails[:12]:
        print(f"  FAIL [{why}] {where}: want {want} got {got}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
