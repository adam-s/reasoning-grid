#!/usr/bin/env python3
"""Does Phi rescue Qwen more than a second Qwen sample would?

    python probe/self_rescue.py

THE ANSWER IS NO, AND THIS IS WHY SECTION 03 OF THE BLOG IS PULLED.

The blind-spot claim was that Phi-4-reasoning solves problems Qwen3-4B cannot,
so running two vendors buys coverage one vendor cannot reach. The competing
explanation is sampling. Qwen averages 1.50 attempts per problem and Phi 1.14,
so Qwen misses plenty it would have solved on another try, and ANY second
sampler picks some of those up.

Null hypothesis: inside a cell every problem is equally hard, so a model's
per-trial success probability on any problem in cell c is that model's pooled
rate for c. Under that null a rescue is luck and the expected count is closed
form. Rates are pooled by TRIAL rather than by problem, because the null is
about the chance one generation succeeds.

Result at the sampling on disk, 1,062 paired problems:

    Phi solves what Qwen missed    observed  82   expected  74.0 (sd 7.9)  z +1.01
    Qwen solves what Phi missed    observed 257   expected 248.4 (sd 12.4) z +0.69

Both inside noise. And the number that settles it: a second QWEN sample of
Phi's trial size would have rescued 102.7, against Phi's actual 82. The other
vendor's model did worse than running the same model twice.

The cause is visible in the trial counts. Of the 261 problems Qwen never
solved, 212 were single attempts and 4 got three. A problem missed once is not
a blind spot, and nearly the whole rescue set is built from single misses.

This design cannot identify the quantity, which per AGENTS.md makes it a
different experiment rather than a cheaper one. Settling it needs one problem
sampled many times, not many problems sampled once: take the problems Qwen
missed, run Qwen a few hundred times on each, and keep the ones that stay at
zero. Those are the only candidates for a real blind spot.

Note: docs/ARTIFACTS.md quotes 104 rescues and coverage 71.0% -> 80.8% from
render_blindspots.py, against 82 and 75.4% -> 83.1% here. The two scripts are
selecting differently and that is unreconciled. It does not change the verdict
in either version.
"""
import collections
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paired  # noqa: E402


def analyse(inst, rate, label, miss_key, rescue_key, miss_n, rescue_n,
            miss_idx, rescue_idx):
    """One direction. Returns (observed, expected, expected_if_same_model)."""
    obs = exp = var = 0.0
    self_exp = self_var = 0.0
    for r in inst:
        q, p = rate[r["cell"]][miss_idx], rate[r["cell"]][rescue_idx]
        n_miss, n_res = r[miss_n], r[rescue_n]
        if r[miss_key] == 0.0 and r[rescue_key] > 0.0:
            obs += 1
        # P(misser goes 0-for-n) * P(rescuer lands at least one)
        pr = (1 - q) ** n_miss * (1 - (1 - p) ** n_res)
        exp += pr
        var += pr * (1 - pr)
        # the same, with the rescuer replaced by another sample of the misser
        ps = (1 - q) ** n_miss * (1 - (1 - q) ** n_res)
        self_exp += ps
        self_var += ps * (1 - ps)
    sd = math.sqrt(var) or 1e-9
    print(f"\n{label}")
    print(f"  observed                       {obs:.0f}")
    print(f"  expected under null            {exp:.1f}  (sd {sd:.1f})")
    print(f"  z                              {(obs - exp) / sd:+.2f}")
    print(f"  expected if the second sampler {self_exp:.1f}  "
          f"(sd {math.sqrt(self_var):.1f})")
    print(f"    were the same model")
    return obs, exp, self_exp


def main(runs="runs"):
    inst, gens = paired.load(runs)
    print(f"problems paired: {len(inst)}")
    print(f"qwen generations {gens[1]}  correct {gens[0]}  "
          f"rate {gens[0]/gens[1]:.4f}")
    print(f"phi  generations {gens[3]}  correct {gens[2]}  "
          f"rate {gens[2]/gens[3]:.4f}")

    na = [r["na"] for r in inst]
    nb = [r["nb"] for r in inst]
    print(f"qwen trials/problem  mean {sum(na)/len(na):.2f}  "
          f"min {min(na)}  max {max(na)}")
    print(f"phi  trials/problem  mean {sum(nb)/len(nb):.2f}  "
          f"min {min(nb)}  max {max(nb)}")

    hit = collections.defaultdict(lambda: [0.0, 0, 0.0, 0])
    for r in inst:
        c = r["cell"]
        hit[c][0] += r["pa"] * r["na"]; hit[c][1] += r["na"]
        hit[c][2] += r["pb"] * r["nb"]; hit[c][3] += r["nb"]
    rate = {c: (v[0] / v[1], v[2] / v[3]) for c, v in hit.items()}

    analyse(inst, rate, "Phi solves what Qwen missed",
            "pa", "pb", "na", "nb", 0, 1)
    analyse(inst, rate, "Qwen solves what Phi missed",
            "pb", "pa", "nb", "na", 1, 0)

    n = len(inst)
    q = sum(1 for r in inst if r["pa"] > 0) / n
    p = sum(1 for r in inst if r["pb"] > 0) / n
    e = sum(1 for r in inst if r["pa"] > 0 or r["pb"] > 0) / n
    print(f"\ncoverage  qwen {q:.3f}  phi {p:.3f}  either {e:.3f}")

    # How thin is the evidence behind each zero? A problem missed on one
    # attempt carries no information, and that is most of them.
    z = collections.Counter(r["na"] for r in inst if r["pa"] == 0.0)
    r_ = collections.Counter(r["na"] for r in inst
                             if r["pa"] == 0.0 and r["pb"] > 0.0)
    print(f"\nqwen zero-problems by trial count: {dict(sorted(z.items()))}")
    print(f"of those, phi rescued:             {dict(sorted(r_.items()))}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "runs")
