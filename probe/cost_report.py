"""Estimate vs actual, for every sweep with a manifest.

AGENTS.md: "Estimate cost before launching, and record actual cost after. A run
whose spend was never compared to its estimate teaches nothing about the next
one." This is that comparison.

  .venv/bin/python probe/cost_report.py
"""
import glob
import json
import pathlib
import sys

RATE = {"h100": 0.001097, "l40s": 0.000542, "a100": 0.000583, "a10g": 0.000306}


def rows():
    root = pathlib.Path(__file__).resolve().parent.parent
    for m in sorted(glob.glob(str(root / "sweeps" / "*" / "manifest*.json"))):
        d = json.loads(pathlib.Path(m).read_text())
        if d.get("status") != "closed":
            continue
        gpu = d.get("gpu", "h100").lower()
        wall = sum(b.get("wall_s", 0) for b in d.get("batches", []))
        # cold start + scaledown are real and were excluded from every estimate
        overhead = 110 + 30
        est_usd = (d.get("cost") or {}).get("est_usd")
        act_usd = (wall + overhead) * RATE.get(gpu, 0.001097)
        est_tok = (d.get("cost") or {}).get("est_output_tokens")
        act_tok = d.get("actual_output_tokens")
        yield dict(sweep=d["sweep_id"], model=(d.get("model") or "?").split("/")[-1],
                   n=d.get("n_actual"), est_tok=est_tok, act_tok=act_tok,
                   est_usd=est_usd, act_usd=act_usd, wall=wall,
                   tps=act_tok / wall if wall and act_tok else None)


def main():
    rs = list(rows())
    if not rs:
        print("no closed manifests yet")
        return
    print(f"{'sweep':<24}{'model':<14}{'gens':>6}{'est tok':>10}{'act tok':>10}"
          f"{'x':>6}{'est $':>8}{'act $':>8}{'x':>6}{'tok/s':>8}")
    for r in rs:
        rt = (r["act_tok"] / r["est_tok"]) if r["est_tok"] else 0
        ru = (r["act_usd"] / r["est_usd"]) if r["est_usd"] else 0
        print(f"{r['sweep'][:23]:<24}{r['model'][:13]:<14}{r['n'] or 0:>6}"
              f"{(r['est_tok'] or 0) / 1000:>9.0f}k{(r['act_tok'] or 0) / 1000:>9.0f}k"
              f"{rt:>6.2f}{r['est_usd'] or 0:>8.2f}{r['act_usd']:>8.2f}{ru:>6.2f}"
              f"{r['tps'] or 0:>8.0f}")
    tot_e = sum(r["est_usd"] or 0 for r in rs)
    tot_a = sum(r["act_usd"] for r in rs)
    print(f"{'TOTAL (manifested runs)':<44}{'':>26}{tot_e:>8.2f}{tot_a:>8.2f}"
          f"{tot_a / tot_e if tot_e else 0:>6.2f}")
    print("\nWhy estimates miss:")
    print("  - the token model is fitted on past cells and extrapolates badly")
    print("  - throughput depends on CELL SIZE, not just batch size (RESULTS 6e)")
    print("  - cold start and scaledown are excluded from the estimate, ~$0.15/run")


if __name__ == "__main__":
    sys.exit(main())
