# Runs per cell

How many times each cell of the grid should be run, derived from the data in
`runs/` rather than picked. Written 2026-07-31.

**Answer: between 6 and 24 runs per cell, peaking near the 50% crossing.**
3,068 generations per model, $14.54 for two models.

Uses **cost-weighted Neyman allocation**, which is 4% better on total variance
than the unweighted form at the same price — because cells differ in cost by a
factor of 16 and the unweighted form over-spends on the expensive ones.

---

## 1. The principle

Sample size should follow **variance**, and a binomial's variance is `p(1-p)`.
That is maximised at p = 0.5 and approaches zero at both extremes. A cell the
model always gets right, or always gets wrong, tells you what it is going to
tell you in a handful of runs. A cell at 50% is a coin and needs many.

The standard result is **Neyman allocation** for stratified sampling
([Neyman allocation, Wikipedia](https://en.wikipedia.org/wiki/Neyman_allocation);
[Chapter 3, Stratification](https://bookdown.org/osierguillaume/mybook/stratification.html)):

```text
n_h  proportional to  N_h * S_h                 (equal cost per unit)
n_h  proportional to  N_h * S_h / sqrt(c_h)     (unequal cost per unit)
```

**The cost-weighted form is the one that applies here**, because cells cost
wildly different amounts: a 2x2 run is ~1,400 tokens and a 14x14 run is ~21,900,
a factor of 16. Each stratum is sampled in proportion to its standard deviation
and in *inverse* proportion to the square root of its cost. Here `S_h` is
`sqrt(p(1-p))`, all strata are one cell so `N_h` is constant, and `c_h` is the
token cost of a run in that cell.

Your instinct was right and then reverses. Runs should climb as cells get
harder — but only up to the 50% crossing. Past it, cells get *less* variable
again, and a cell at 5% needs about the same as a cell at 95%.

| cell | predicted p | variance p(1-p) | runs |
| --- | --- | --- | --- |
| 2x2 | 100% | 0.001 | 6 |
| 4x4 | 98% | 0.024 | 8 |
| 6x6 | 82% | 0.147 | 20 |
| **8x8** | **50%** | **0.250** | **22** |
| 10x10 | 23% | 0.179 | 22 |
| 12x12 | 10% | 0.093 | 16 |
| 14x14 | 5% | 0.046 | 11 |

---

## 2. What it is derived from

Every reasoning-on generation in `runs/`, truncated ones excluded:

| cell | correct | rate | mean tokens |
| --- | --- | --- | --- |
| 3x3 | 3/3 | 100% | 233 |
| 4x4 | 9/10 | 90% | 2,527 |
| 6x6 | 4/6 | 67% | 6,988 |
| 8x8 | 18/31 | 58% | 11,944 |
| 10x10 | 8/26 | 31% | 15,072 |
| 12x12 | 1/28 | 4% | 20,466 |
| 14x14 | 0/18 | 0% | 18,990 |

Fitted surface, logistic in `log N` where `N = a*b`:

```text
logit p = 11.012 - 2.649 * log(N)      50% crossing at 8.0 digits
```

Token cost, fitted across six cells, R2 = 0.972:

```text
tokens = 505 * N^0.714
```

Throughput measured on H100 at batch 128: **4,032 tokens/second**.

---

## 3. Runs per cell

Rows are digits of the first factor, columns the second. Full square — `3x12`
and `12x3` are separate cells, because operand order may matter and the
asymmetry across the diagonal is itself a result.

| a \ b | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **1** | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 7 | 8 | 8 | 9 | 10 | 10 |
| **2** | 6 | 6 | 6 | 6 | 8 | 9 | 10 | 12 | 13 | 14 | 15 | 16 | 17 | 18 |
| **3** | 6 | 6 | 7 | 9 | 11 | 13 | 15 | 16 | 18 | 19 | 20 | 21 | 22 | 23 |
| **4** | 6 | 6 | 9 | 12 | 14 | 16 | 18 | 20 | 21 | 22 | 23 | 23 | 24 | 23 |
| **5** | 6 | 8 | 11 | 14 | 17 | 19 | 21 | 22 | 23 | 24 | 24 | 23 | 23 | 22 |
| **6** | 6 | 9 | 13 | 16 | 19 | 21 | 23 | 23 | 24 | 23 | 22 | 22 | 20 | 19 |
| **7** | 6 | 10 | 15 | 18 | 21 | 23 | 24 | 23 | 23 | 22 | 21 | 19 | 18 | 17 |
| **8** | 6 | 12 | 16 | 20 | 22 | 23 | 23 | 23 | 22 | 20 | 19 | 17 | 16 | 14 |
| **9** | 7 | 13 | 18 | 21 | 23 | 24 | 23 | 22 | 20 | 18 | 17 | 15 | 14 | 12 |
| **10** | 8 | 14 | 19 | 22 | 24 | 23 | 22 | 20 | 18 | 16 | 15 | 13 | 12 | 11 |
| **11** | 8 | 15 | 20 | 23 | 24 | 22 | 21 | 19 | 17 | 15 | 13 | 12 | 10 | 9 |
| **12** | 9 | 16 | 21 | 23 | 23 | 22 | 19 | 17 | 15 | 13 | 12 | 10 | 9 | 8 |
| **13** | 10 | 17 | 22 | 24 | 23 | 20 | 18 | 16 | 14 | 12 | 10 | 9 | 8 | 7 |
| **14** | 10 | 18 | 23 | 23 | 22 | 19 | 17 | 14 | 12 | 11 | 9 | 8 | 7 | 7 |

Note the ridge. The high numbers follow a **hyperbola**, not a diagonal,
because difficulty tracks `a * b`. The 22s trace the curve where the model sits
at 50%: 8x8, but also 5x13, 6x11, 11x6, 13x5.

### Predicted pass rate that produced it (%)

| a \ b | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **1** | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 99 | 99 | 99 | 99 | 99 | 98 |
| **2** | 100 | 100 | 100 | 100 | 99 | 99 | 98 | 98 | 97 | 96 | 94 | 93 | 92 | 90 |
| **3** | 100 | 100 | 99 | 99 | 98 | 97 | 95 | 93 | 91 | 88 | 85 | 82 | 79 | 75 |
| **4** | 100 | 100 | 99 | 98 | 96 | 93 | 90 | 86 | 82 | 78 | 73 | 68 | 63 | 59 |
| **5** | 100 | 99 | 98 | 96 | 92 | 88 | 83 | 78 | 72 | 66 | 60 | 54 | 49 | 44 |
| **6** | 100 | 99 | 97 | 93 | 88 | 82 | 75 | 68 | 61 | 54 | 48 | 42 | 37 | 33 |
| **7** | 100 | 98 | 95 | 90 | 83 | 75 | 67 | 59 | 51 | 44 | 38 | 33 | 28 | 24 |
| **8** | 100 | 98 | 93 | 86 | 78 | 68 | 59 | 50 | 42 | 35 | 30 | 25 | 22 | 18 |
| **9** | 99 | 97 | 91 | 82 | 72 | 61 | 51 | 42 | 35 | 29 | 24 | 20 | 17 | 14 |
| **10** | 99 | 96 | 88 | 78 | 66 | 54 | 44 | 35 | 29 | 23 | 19 | 16 | 13 | 11 |
| **11** | 99 | 94 | 85 | 73 | 60 | 48 | 38 | 30 | 24 | 19 | 16 | 13 | 11 | 9 |
| **12** | 99 | 93 | 82 | 68 | 54 | 42 | 33 | 25 | 20 | 16 | 13 | 10 | 9 | 7 |
| **13** | 99 | 92 | 79 | 63 | 49 | 37 | 28 | 22 | 17 | 13 | 11 | 9 | 7 | 6 |
| **14** | 98 | 90 | 75 | 59 | 44 | 33 | 24 | 18 | 14 | 11 | 9 | 7 | 6 | 5 |

---

## 4. Cost

| scheme | generations, 2 models | cost |
| --- | --- | --- |
| flat n=12 | 4,704 | $10.69 |
| **Neyman, peak 22** | **5,640** | **$14.55** |
| Neyman, peak 26 | 6,568 | $17.12 |
| flat n=45 | 17,640 | $40.09 |

Neyman at peak 22 costs 36% more than flat n=12 and puts those extra runs
where they change the answer. Flat n=45 costs 2.8x more than Neyman for a
better result only in the cells that were already certain.

---

## 5. What this does not do

**It assumes the surface.** Allocation uses predicted p from a fit to 122
generations, so a cell whose true rate is far from predicted gets the wrong n.
This is deliberate — allocating from a cell's *own* observed rate is optional
stopping, which biases the estimate outward by up to 3.7 points at the shoulder.
Predicting from a prior fit avoids that; being somewhat wrong about n is the
cheaper error.

**It does not bound the dead cells.** A cell at 7 runs with 0 successes gives a
95% upper bound of 43%, which is nowhere near "zero". Claiming a cell is dead
needs the **rule of three** (Hanley & Lippman-Hand 1983): if an event does not
occur in n trials, the 95% confidence interval for its rate is `(0, 3/n)`, and
the approximation is good for n > 30
([Rule of three, HandWiki](https://handwiki.org/wiki/Rule_of_three_(statistics));
[Tuyl 2009, International Statistical Review](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1751-5823.2009.00078.x);
[pmean, zero events](http://www.pmean.com/01/zeroevents.html)).

| to claim the rate is below | runs needed with 0 successes |
| --- | --- |
| 30% | 10 |
| 10% | 30 |
| 5% | 60 |
| 1% | 300 |

Neyman gives dead cells 7-11 runs because they carry almost no variance. That
is right for *estimating* them and wrong for *bounding* them. If the grid must
show a corner that fails completely, those cells need a floor of 30 — a mixed
objective, estimate in the middle and bound at the edge — costing about $2 more.
(For 99% confidence the numerator is 4.61 rather than 3.)

**It optimises the wrong thing if the goal is the curve, not the cells.**
Neyman minimises the summed variance of the *individual cell estimates*. If what
you want is the fitted boundary — one number from the whole surface — the
relevant theory is optimal design for logistic regression, where the locally
D-optimal two-point design sits at predicted responses of **0.176 and 0.824**,
not at 0.5 (Kalish & Rosenberger 1978; see
[D-optimal designs for logistic regression in two variables](https://webpages.math.luc.edu/~tobrien/research/modapaper2007.pdf)
and [Springer](https://link.springer.com/chapter/10.1007/978-3-7908-1952-6_12)).
The shoulders of the curve carry more joint information about slope and
intercept than the steepest point does.

That is a real tension and it is not resolved here. Neyman puts the peak at 50%;
D-optimality puts it at 18% and 82%. They disagree because they answer different
questions — *how accurate is each cell* versus *how accurate is the curve*. The
allocation above chooses the first, because the deliverable is a heatmap where
every cell is read individually. If the deliverable were the boundary number,
the allocation should be re-derived. Note also that D-optimality is *local*: it
depends on the parameters you are trying to estimate, so it can only be used for
a second pass after a pilot, never the first.

**It answers cell rates, not cell structure.** No allocation of *distinct*
problems can distinguish "every problem is a 50% coin" from "half the problems
are always right and half always wrong". Those give identical binomial
distributions at any n. Telling them apart needs repeats of the *same* problem,
which is a separate study.

**One model is measured.** All of the above is Qwen3-4B. gpt-oss-20b runs and
parses correctly (6/6 on a smoke test) but its surface has not been fitted, so
its allocation is currently assumed to match.
