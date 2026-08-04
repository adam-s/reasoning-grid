# reasoning-grid

reasoning-grid measures where a language model stops being able to finish a long
chain of reasoning, and whether two models from different companies stop in the
same place.

It works in long multiplication, because that is the rare task where the answer
is free to check and the amount of work is known before you ask. An n-digit by
m-digit product decomposes into a countable number of single-digit operations,
so difficulty is not estimated, it is arithmetic. None of this is a claim about
whether models can do arithmetic.

The output is one grid. Each cell is a problem size, each cell is run many
times, and its value is the probability the model returns the exactly correct
answer.

[Read the post](https://adamsohn.com/reasoning-grid/)

## What It Found

Qwen3-4B and Phi-4-reasoning were run on the same 1,062 problems across 144
cells. Both fall along the same curve and differ only in where they sit on it:
Qwen is right half the time at 9.24 digits per factor, Phi at 8.39. Of the 144
cells, 10 differ by more than noise and none of those favour Phi.

That is a weaker result than the one this repo set out to test. The original
hypothesis was that two vendors would fail on *different* problems, so running
both would buy coverage a single model cannot. It does not survive the data:
at the sampling used, a second sample of Qwen would have rescued about as many
of Qwen's own failures as Phi did. `probe/self_rescue.py` has the numbers and
what sampling shape would settle it.

What survives is the shape claim, which needs no pairing. Two models built by
different companies on different data with different tokenizers hold the same
curve, which makes the grid an instrument rather than one model's benchmark.

Full numbers, intervals and the defects found along the way are in
[docs/RESULTS.md](docs/RESULTS.md).

## How It Works

Raw generations are immutable. Everything else is derived from them and can be
rebuilt at any time.

```text
probe/bakeoff.py      runs generations on rented GPUs  ->  runs/*.jsonl    raw, tracked, never edited
probe/reduce_grid.py  rescores from the raw text       ->  derived/*.json  small, regenerable
probe/render_*.py     standalone HTML + inline SVG     ->  derived/*.html  the working charts
blog/                 the published post
```

Scores are re-derived from `raw_text` on every reduction rather than read back
from what was stored, because the answer parser has shipped broken four times
and every one of those breaks was caught by a person noticing an implausible
number. A stored score goes stale silently; a re-derived one does not.

## Reproduce

```bash
python tests/test_parser.py          # the parser, against real generated text
python probe/reduce_grid.py --sweep 10-grid12-qwen
cd blog && npm install && npm run dev
```

## Layout

- `probe/` — generation, scoring and chart scripts
- `runs/` — raw model output, one JSONL per sweep
- `derived/` — scored grids and rendered charts
- `blog/` — the post, a Svelte page
- `docs/` — results, methods, known limitations, published chart index
- `labels/` — hand-labelled reasoning traces
- `AGENTS.md` — how coding agents work in this repo

## Notes

Long multiplication is the instrument, not the subject. Every number here is
reproducible from a recorded seed and a pinned model revision, and the failures
are reported alongside the results — a run that failed, a cell that was skipped
and a prediction that missed are all outcomes.
