#!/usr/bin/env python
"""
Reproduce manuscript Table 3 (calibration against published literature targets).

Runs the baseline scenario with the calibrated parameters in
PAPER_PARAMS_FoodSecurity.json for five seeds (0-4) at 500 households x 365
days and scores three pattern-oriented targets:

  annual food-at-home spending, low-income households     target $3,707
  annual food-at-home spending, medium-income households  target $4,672
  annual food-insecurity prevalence (insecure on >= 1 day) target 0.33

The corner-store trip share is reported but not scored. Aggregate MAPE is the
mean of the three per-target absolute percentage errors, computed per seed and
averaged over seeds (2.93%); it is also printed on the five-seed means (1.19%).

Each seed runs in its own process; results are written to
calibration/table3_reproduced.csv and compared with the archived run in
calibration/table3_calibration_seeds.csv.

Usage
  python reproduce_table3.py               # 5 seeds in parallel (~3-5 min)
  python reproduce_table3.py --workers 1   # sequential
"""
import argparse
import contextlib
import csv
import io
import json
import multiprocessing as mp
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PARAMS_JSON = os.path.join(HERE, "PAPER_PARAMS_FoodSecurity.json")
OUT_CSV = os.path.join(HERE, "calibration", "table3_reproduced.csv")
REF_CSV = os.path.join(HERE, "calibration", "table3_calibration_seeds.csv")

SEEDS = [0, 1, 2, 3, 4]
HH, DAYS = 500, 365
TARGETS = {"spend_low": 3707.0, "spend_med": 4672.0, "fi_day": 0.33}
COLS = ["seed", "spend_low", "spend_med", "corner_trips", "fi_day", "error3"]


def _winit():
    os.chdir(HERE)
    if HERE not in sys.path:
        sys.path.insert(0, HERE)


def run_seed(seed):
    """One calibration run; same procedure as the run reported in Table 3."""
    import numpy as np
    params = json.load(open(PARAMS_JSON))["final_parameters"]
    random.seed(seed)
    np.random.seed(seed)
    from enhanced_mesa_geo_model import SimulationConfig, IncomeLevel
    from baseline_scenario import create_baseline_scenario
    config = SimulationConfig(num_consumers=HH, simulation_days=DAYS,
                              enable_spatial_analytics=False)
    # set after construction (__post_init__ loads the parameter file first)
    for k, v in params.items():
        setattr(config, k, v)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        model = create_baseline_scenario(config=config)
        if hasattr(model, "reset_randomizer"):
            model.reset_randomizer(seed)
        hhs = list(model.consumers)
        insec = {id(h): 0 for h in hhs}
        for _ in range(DAYS):
            model.step()
            for h in hhs:                      # daily poll -> annual prevalence
                if getattr(h, "unsatisfied", False):
                    insec[id(h)] += 1
    ann = 365.0 / float(DAYS)
    spend = {IncomeLevel.LOW: [], IncomeLevel.MEDIUM: [], IncomeLevel.HIGH: []}
    trips = corner = 0
    for h in hhs:
        hist = getattr(h, "shopping_history", []) or []
        if hist:
            spend[h.income].append(
                sum(t.get("basket_cost", t.get("basket_size", 0)) for t in hist) * ann)
        trips += len(hist)
        corner += sum(1 for t in hist if t.get("is_corner_shop", False))
    m = {
        "seed": seed,
        "spend_low": float(np.mean(spend[IncomeLevel.LOW])),
        "spend_med": float(np.mean(spend[IncomeLevel.MEDIUM])),
        "corner_trips": corner / trips if trips else 0.0,
        "fi_day": sum(1 for v in insec.values() if v >= 1) / len(hhs),
    }
    m["error3"] = sum(abs(m[k] - t) / t for k, t in TARGETS.items()) / 3
    return m


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=len(SEEDS))
    args = ap.parse_args()
    import numpy as np

    ctx = mp.get_context("spawn")
    with ctx.Pool(processes=max(1, args.workers), maxtasksperchild=1, initializer=_winit) as pool:
        rows = sorted(pool.map(run_seed, SEEDS), key=lambda r: r["seed"])

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)

    def ms(k):
        v = np.array([r[k] for r in rows], float)
        return v.mean(), v.std(ddof=1)

    print(f"\nTable 3 - calibration ({HH} households, {DAYS} days, seeds {SEEDS})")
    print(f"{'Target':<44}{'Empirical':>12}{'Model mean +/- SD':>26}{'MAPE':>9}")
    labels = {"spend_low": "Annual food-at-home spend, low income ($)",
              "spend_med": "Annual food-at-home spend, medium income ($)",
              "fi_day": "Annual food-insecurity prevalence"}
    mape_means = []
    for k, lab in labels.items():
        mu, sd = ms(k)
        e = abs(mu - TARGETS[k]) / TARGETS[k]
        mape_means.append(e)
        dp = 3 if k == "fi_day" else 2
        print(f"{lab:<44}{TARGETS[k]:>12.{dp}f}{mu:>17.{dp}f} +/- {sd:<7.{dp}f}{e*100:>8.2f}%")
    mu, sd = ms("corner_trips")
    print(f"{'Corner-store trip share (reported, not scored)':<44}{'':>12}{mu:>17.3f} +/- {sd:<7.3f}")
    print(f"\nAggregate MAPE, averaged per seed : {np.mean([r['error3'] for r in rows])*100:.2f}%")
    print(f"Aggregate MAPE, on five-seed means: {np.mean(mape_means)*100:.2f}%")

    if os.path.isfile(REF_CSV):
        ref = {int(float(r["seed"])): r for r in csv.DictReader(open(REF_CSV))}
        diff = max(abs(r[k] - float(ref[r["seed"]][k]))
                   for r in rows for k in ("spend_low", "spend_med", "corner_trips", "fi_day"))
        print(f"\nMax abs difference vs archived run ({os.path.basename(REF_CSV)}): {diff:.3g}")
    print(f"Per-seed results written to {OUT_CSV}")


if __name__ == "__main__":
    main()
