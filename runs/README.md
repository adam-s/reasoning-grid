# runs/ — the raw record

One JSON object per line, one line per generation, exactly as the model produced
it. **Nothing in here is ever edited.** Scores, rates, boundaries and charts are
all derived from these files by scripts in [`probe/`](../probe/), and can be
regenerated at any time.

That matters more than it sounds. The answer parser in this project has shipped
broken four times, each time in a different direction, and each time it was
fixed the old runs were rescored rather than re-run. If only the scores had been
kept, every one of those bugs would have been permanent. If you disagree with
how an answer was parsed, reparse it — the text is here.

7,554 records, 63 files, ~124 MB (~24 MB packed).

## What a record contains

| field | |
|---|---|
| `model`, `gpu` | what produced it |
| `a`, `b` | digits in each operand — the grid coordinates |
| `x`, `y`, `truth` | the operands in canonical order, and the correct product |
| `presented_as` | `xy` or `yx` — which order the model actually saw |
| `instance_uid` | `sha256(seed·a·b·x·y)[:16]`. Two records are the same problem **iff** this matches. This is what makes cross-model and cross-condition pairing possible, and it cannot be reconstructed later |
| `instance_id`, `trial_index` | position in the seeded pool; the pool is a fixed prefix, so instance 3 means the same problem at every n |
| `raw_text` | the complete generation, including the reasoning trace |
| `answer`, `parse_method`, `correct` | what the parser said **on the day it ran** — stale by design, rescore from `raw_text` |
| `outcome` | `converged_right` / `converged_wrong` / `quit` / `grind` |
| `finish_reason` | `stop` or `length`; `length` means it used the whole context without answering |
| `completion_tokens`, `max_tokens`, `tokens_wanted`, `engine_max_len` | the budget granted against the budget asked for |
| `temperature`, `top_p`, `seed` | sampling |
| `thinking_requested`, `thinking_observed`, `thinking_marker` | requested is what we asked for; **observed is what the text shows**, and they have differed |
| `prompt_text`, `prompt_sha256`, `problem_seed` | enough to regenerate the input exactly |
| `sweep_id`, `submit_index`, `batch_seq` | provenance and position in the queue |

## Reading it correctly

**Score from `raw_text`, not from `correct`.** `probe/reduce_grid.py` does this
by default.

**Pool by condition, never by filename.** Two runs are comparable when
temperature, `top_p`, thinking and the context ceiling match — not when their
names look related. Records from different sweeps at identical settings are
extra trials of the same quantity and may be added together.

**`thinking_observed` is the one to filter on.** Some families emit no `<think>`
tag at all (gpt-oss uses harmony channels), and one model silently ignored the
request entirely, producing 144 non-reasoning records that claimed otherwise.

**A `length` finish means the model never answered.** Sweeps from 10 onward
granted each model its own native context, so running out is the model's limit
and counts as incorrect. Earlier sweeps ran against an arbitrary cap and must be
read the other way — `cells(grind_is_wrong=False)` recovers that.

**Older records predate some fields.** `thinking_observed` is absent on the
earliest runs; it can be recovered by searching `raw_text` for the markers in
`probe/bakeoff.py`.

## Regenerating everything

```sh
python probe/reduce_grid.py --sweep 10-grid12 --pool 11-ext14 --out derived
python probe/render_grid.py derived/10-grid12.json -o derived/grid.html
# ... see docs/ARTIFACTS.md for the rest
```
