"""Emit observed repeated measurement, for the figure about what one score hides.

Nothing here is simulated. Every number is a count of generations on disk.

SCORES is what the page renders: 6,000 generations of one cell cut into
non-overlapping groups of twelve, each group an independent benchmark score of
that cell, counted by the value it returned.

PAIRS, REMEASURED and REPEATS are kept because they are cheap to compute and
each one answers a question a reader might ask, but nothing renders them today.
REPEATS in particular was cut from the figure on 2026-08-04: twenty problems at
five repeats is a true and interesting fact that did not earn the space beside
five hundred scores of twelve.

## The pool, and why it is smaller than the archive

Fifteen thousand generations are on disk. This uses the ones that are
comparable: one model, one temperature, reasoning on, and the full token
allowance. Pooling without those filters mixes a reasoning-off sweep and a
truncated-budget sweep into the rates and produces orderings that are artefacts
of the mixture. It cost an order of magnitude of sample size and it is not
optional.

## The confound, stated

PAIRS assumes a*b captures difficulty, so a gap between `a x b` and `b x a` is
sampling noise. Operand order might genuinely matter, which is why
docs/PREREGISTRATION-order-symmetry.md exists. This data cannot separate the
two and the figure must not claim it can. That ambiguity is the point rather
than a flaw in it: one score per cell leaves a reader unable to tell noise from
effect.

Run: python3 probe/build_sampling.py
"""

from __future__ import annotations

import glob
import json
from collections import defaultdict

MODEL = "Qwen/Qwen3-4B"
TEMP = 0.7
VARIANCE = "runs/variance-Qwen3-4B-l40s-532rec-02837a70.jsonl"
OUT = "blog/src/lib/data/sampling.ts"

# A pair needs enough on both sides to be worth showing. Below this a gap is
# unreadable rather than surprising.
MIN_PER_SIDE = 18

# A cell has to have been scored this many separate times, over this many
# generations, before its disagreement means anything.
#
# MIN_PER_SWEEP is the one that matters and it was missing at first. Without it
# a sweep contributing ONE generation counts as a score, and one generation can
# only read 0% or 100%, so the widest "disagreements" in the output were
# manufactured out of single draws. 11x8 came back with a 67% spread built on a
# 1/1 and a 2/2.
MIN_SWEEPS = 3
MIN_PER_SWEEP = 6
MIN_TOTAL_REMEASURED = 20

# Bootstrap: resample a cell's OBSERVED outcomes to show what a smaller score
# drawn from them would look like. Every point in the result traces to a
# generation that ran. This is not the same as flipping a weighted coin, and the
# figure says which it is.
BOOTSTRAP_CELL_MIN = 24
BOOTSTRAP_DRAWS = 20000
BOOTSTRAP_SIZES = [3, 6, 12]
BOOTSTRAP_SEED = 20260803

# The observed histogram: 6,000 generations of one cell, reasoning off, cut into
# non-overlapping groups of twelve. Each group is an independent benchmark score
# of that cell. Nothing resampled, nothing simulated.
SCORE_SWEEPS = "runs/21-*5x5-nothink*.jsonl"
SCORE_GROUP = 12

REPEAT_CELL = (4, 4)
# The grid ran at 0.7 but that arm of the variance sweep is only 8 generations.
# The 1.0 arm has 20 problems at 5 repeats each, so the repeats come from there.
# A real difference between this view and the other two, stated rather than
# smoothed over.
REPEAT_TEMP = 1.0


def load(*patterns: str) -> list[dict]:
    """Every record under these globs, each file read exactly once.

    The dedupe is not tidiness. `runs/**/*.jsonl` with recursive=True already
    matches the top-level files, so pairing it with `runs/*.jsonl` reads those
    twice and doubles every count they contribute.
    """
    paths = sorted({p for pat in patterns for p in glob.glob(pat, recursive=True)})
    rows: list[dict] = []
    for path in paths:
        with open(path) as fh:
            rows.extend(json.loads(line) for line in fh if line.strip())
    return rows


def clean(rows: list[dict]) -> list[dict]:
    return [
        r for r in rows
        if r.get("model") == MODEL
        and r.get("temperature") == TEMP
        and r.get("thinking_observed")
        and r.get("budget_mode") == "max"
    ]


def main() -> None:
    rows = clean(load("runs/**/*.jsonl"))
    if not rows:
        raise SystemExit("no clean records found")

    by_cell: dict[tuple[int, int], list[bool]] = defaultdict(list)
    by_cell_sweep: dict[tuple[int, int], dict[str, list[bool]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for r in rows:
        k = (r["a"], r["b"])
        ok = bool(r.get("correct"))
        by_cell[k].append(ok)
        by_cell_sweep[k][r.get("sweep_id", "?")].append(ok)

    # ---- pairs at equal N ---------------------------------------------------
    pairs = []
    for (a, b), got in sorted(by_cell.items()):
        if a >= b:
            continue
        other = by_cell.get((b, a))
        if not other or len(got) < MIN_PER_SIDE or len(other) < MIN_PER_SIDE:
            continue
        pairs.append({
            "n": a * b,
            "a": a, "b": b,
            "hitsAB": sum(got), "ofAB": len(got),
            "hitsBA": sum(other), "ofBA": len(other),
        })
    pairs.sort(key=lambda d: d["n"])

    # ---- one cell, scored several times -------------------------------------
    remeasured = []
    for k, sweeps in by_cell_sweep.items():
        usable = [v for v in sweeps.values() if len(v) >= MIN_PER_SWEEP]
        if len(usable) < MIN_SWEEPS or len(by_cell[k]) < MIN_TOTAL_REMEASURED:
            continue
        scores = sorted(
            ({"hits": sum(v), "of": len(v)} for v in usable),
            key=lambda s: s["hits"] / s["of"],
        )
        spread = scores[-1]["hits"] / scores[-1]["of"] - scores[0]["hits"] / scores[0]["of"]
        remeasured.append({"a": k[0], "b": k[1], "scores": scores, "spread": spread})
    # Widest disagreement first. The figure is about disagreement.
    remeasured.sort(key=lambda d: -d["spread"])
    remeasured = remeasured[:6]

    # ---- observed scores: 6,000 generations cut into groups of twelve -------
    score_rows = load(SCORE_SWEEPS)
    score_rows.sort(key=lambda r: r["instance_id"])
    G = SCORE_GROUP
    groups = [score_rows[i:i + G] for i in range(0, len(score_rows) - G + 1, G)]
    score_counts = [0] * (G + 1)
    for g in groups:
        score_counts[sum(bool(x.get("correct")) for x in g)] += 1
    s_hits = sum(bool(r.get("correct")) for r in score_rows)
    s_n = len(score_rows)

    # ---- bootstrap the best-sampled cell ------------------------------------
    #
    # Draw `size` outcomes WITH REPLACEMENT from what that cell actually
    # produced, score the draw, repeat. The spread that appears is the spread
    # the evidence supports. No rate is assumed and no coin is flipped, which is
    # the whole reason to do it this way rather than the obvious way.
    import random

    # NEAREST A COIN FLIP, not best sampled. The first version took the cell with
    # the most generations, which was 4x12 at 87%, and a rate that high has
    # almost no room to vary -- the figure came out looking reassuring. Spread is
    # widest at 50% and that is where a single score is least worth trusting, so
    # that is the cell worth showing. Sample size is a floor, not the objective.
    eligible = [k for k in by_cell if len(by_cell[k]) >= BOOTSTRAP_CELL_MIN]
    if not eligible:
        raise SystemExit(f"no cell reaches {BOOTSTRAP_CELL_MIN} generations")
    boot_key = min(eligible, key=lambda k: abs(sum(by_cell[k]) / len(by_cell[k]) - 0.5))
    boot_obs = by_cell[boot_key]

    rng = random.Random(BOOTSTRAP_SEED)
    bootstrap = []
    for size in BOOTSTRAP_SIZES:
        counts = [0] * (size + 1)
        for _ in range(BOOTSTRAP_DRAWS):
            counts[sum(rng.choice(boot_obs) for _ in range(size))] += 1
        bootstrap.append({"size": size, "counts": counts})

    # ---- one problem, run five times ----------------------------------------
    var_rows = [
        r for r in load(VARIANCE)
        if (r["a"], r["b"]) == REPEAT_CELL and r["temperature"] == REPEAT_TEMP
    ]
    by_problem: dict[str, list[bool]] = defaultdict(list)
    for r in var_rows:
        by_problem[str(r.get("instance_id"))].append(bool(r.get("correct")))
    repeats = sorted((sum(v), len(v)) for v in by_problem.values())

    def js(obj) -> str:
        return json.dumps(obj, separators=(", ", ": "))

    with open(OUT, "w") as fh:
        fh.write(
            "/**\n"
            " * GENERATED by probe/build_sampling.py. Do not edit.\n"
            " *\n"
            " * OBSERVED COUNTS ONLY. Nothing in this file is simulated.\n"
            " * Pool: %s at temperature %s, reasoning on, full token allowance.\n"
            " *\n"
            " * PAIRS      a x b against b x a. Same difficulty under N = a*b.\n"
            " * REMEASURED one cell scored in several separate sweeps.\n"
            " * REPEATS    one problem run five times, at %dx%d, temperature %s.\n"
            " */\n"
            "export const POOL_LABEL = %s;\n\n"
            "export type Pair = {\n"
            "  readonly n: number; readonly a: number; readonly b: number;\n"
            "  readonly hitsAB: number; readonly ofAB: number;\n"
            "  readonly hitsBA: number; readonly ofBA: number;\n"
            "};\n"
            "export const PAIRS: readonly Pair[] = %s;\n\n"
            "export type Score = { readonly hits: number; readonly of: number };\n"
            "export type Remeasured = {\n"
            "  readonly a: number; readonly b: number;\n"
            "  readonly scores: readonly Score[]; readonly spread: number;\n"
            "};\n"
            "export const REMEASURED: readonly Remeasured[] = %s;\n\n"
            "export const REPEAT_LABEL = %s;\n"
            "export const REPEATS: readonly Score[] = %s;\n\n"
            "/** Resampled from one cell's OBSERVED outcomes, with replacement.\n"
            " *  counts[k] = how many draws of `size` came back with k correct. */\n"
            "export type Bootstrap = { readonly size: number; readonly counts: readonly number[] };\n"
            "/** OBSERVED. counts[k] = how many independent groups of `group`\n"
            " *  came back with k correct. No resampling. */\n"
            "export const SCORES_LABEL = %s;\n"
            "export const SCORES_GROUP = %d;\n"
            "export const SCORES_RATE = %s;\n"
            "export const SCORES: readonly number[] = %s;\n\n"
            "export const BOOTSTRAP_LABEL = %s;\n"
            "export const BOOTSTRAP: readonly Bootstrap[] = %s;\n"
            % (
                MODEL, TEMP,
                REPEAT_CELL[0], REPEAT_CELL[1], REPEAT_TEMP,
                js(f"{MODEL.split('/')[-1]}, temperature {TEMP}, "
                   f"{len(rows):,} generations"),
                js(pairs),
                js(remeasured),
                js(f"{REPEAT_CELL[0]}x{REPEAT_CELL[1]}, {len(repeats)} problems, "
                   f"{repeats[0][1] if repeats else 0} runs each"),
                js([{"hits": h, "of": n} for h, n in repeats]),
                js(f"{score_rows[0]['a']}x{score_rows[0]['b']} reasoning off, "
                   f"{s_n:,} generations in {len(groups)} groups of {G}"),
                G,
                round(s_hits / s_n, 5),
                js(score_counts),
                js(f"{boot_key[0]}x{boot_key[1]}, resampled from "
                   f"{sum(boot_obs)} correct of {len(boot_obs)} generations"),
                js(bootstrap),
            )
        )

    print(f"wrote {OUT}  ({len(rows)} clean generations)")
    print(f"  {len(pairs)} equal-N pairs")
    for p in pairs:
        ab = p["hitsAB"] / p["ofAB"]
        ba = p["hitsBA"] / p["ofBA"]
        print(f"    N={p['n']:>3}  {p['a']}x{p['b']} {ab:>4.0%}  {p['b']}x{p['a']} {ba:>4.0%}"
              f"   {abs(ab - ba):>4.0%} apart")
    print(f"  {len(remeasured)} remeasured cells")
    for r in remeasured:
        s = " ".join(f"{x['hits']}/{x['of']}" for x in r["scores"])
        print(f"    {r['a']}x{r['b']:<4} {s}   spread {r['spread']:.0%}")


if __name__ == "__main__":
    main()
