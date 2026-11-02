#!/usr/bin/env python
"""
Summarise a 50-seed scenario run into the manuscript's Tables 4 and 5.

Reads the per-seed JSON files written by run_journal_50seeds.py and prints

  Table 4  final-day mean +/- SD (over seeds) of food insecurity, travel
           distance, spatial equity, corner / pantry / delivery share and the
           income equity ratio (low-income / high-income spending), plus the
           cumulative burden (food-insecurity rate averaged over the 365 days);
  Table 5  Cohen's d (pooled SD) and Welch's t-test p-value of each scenario
           against the baseline, with Holm-adjusted significance over the
           16 tests (4 scenarios x 4 outcomes).

Usage
  python summarize_results.py                                   # paper results
  python summarize_results.py --results results/my_rerun        # your rerun
  python summarize_results.py --csv table4.csv                  # also save CSV
"""
import argparse
import glob
import json
import os

import numpy as np
from scipy import stats

_trapz = getattr(np, "trapezoid", None) or np.trapz   # numpy 2 renamed trapz

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DIR = os.path.join(HERE, "results", "journal_results_50seeds_paper")

SCENARIOS = {  # label -> file-name prefix written by run_journal_50seeds.py
    "Baseline": "baseline_500hh_365d",
    "S1 North Grocery": "scenario1_north_500hh_365d",
    "S2 Hub + Corner": "scenario2_1_4_500hh_365d",
    "S3 Mobile Pantries": "scenario3_2_fixed_500hh_365d",
    "S4 Delivery": "scenario4_500_500hh_365d",
}
T4_METRICS = ["food_insecurity_rate", "avg_travel_distance", "spatial_equity_index",
              "corner_share", "pantry_share", "delivery_share"]
T5_OUTCOMES = {"food_insecurity": "food_insecurity_rate",
               "avg_travel": "avg_travel_distance",
               "spatial_equity": "spatial_equity_index",
               "income_equity": None}  # None -> income equity ratio


def load(results_dir):
    runs = {}
    for label, prefix in SCENARIOS.items():
        files = sorted(f for f in glob.glob(os.path.join(results_dir, f"{prefix}_seed*_*.json"))
                       if "summary" not in os.path.basename(f))
        runs[label] = [json.load(open(f, encoding="utf-8")) for f in files]
    return runs


def col(runs, metric):
    return np.array([r["final_metrics"][metric] for r in runs
                     if r["final_metrics"].get(metric) is not None], float)


def equity_ratio(runs):
    return np.array([r["final_metrics"]["spend_low"] / r["final_metrics"]["spend_high"]
                     for r in runs
                     if r["final_metrics"].get("spend_low") and r["final_metrics"].get("spend_high")],
                    float)


def burden(runs):
    """Normalised area under the daily food-insecurity curve (dashboard definition)."""
    vals = []
    for r in runs:
        series = [h["food_insecurity_rate"] for h in r.get("metrics_history", [])
                  if "food_insecurity_rate" in h]
        if series:
            vals.append(_trapz(series) / len(series))
    return np.array(vals, float)


def cohen_welch(a, b):
    ps = float(np.sqrt((a.std(ddof=1) ** 2 + b.std(ddof=1) ** 2) / 2))
    d = float((a.mean() - b.mean()) / ps) if ps > 0 else float("nan")
    p = float(stats.ttest_ind(a, b, equal_var=False).pvalue)
    return d, p


def holm(pvals, alpha=0.05):
    order = sorted(range(len(pvals)), key=lambda i: pvals[i])
    keep = [False] * len(pvals)
    m = len(pvals)
    for rank, i in enumerate(order):
        if pvals[i] <= alpha / (m - rank):
            keep[i] = True
        else:
            break
    return keep


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", default=DEFAULT_DIR, help="folder of per-seed JSON files")
    ap.add_argument("--csv", default=None, help="optional path for a Table 4 CSV")
    args = ap.parse_args()

    runs = load(args.results)
    n = {k: len(v) for k, v in runs.items()}
    print(f"Results folder: {args.results}")
    print("Seeds per scenario: " + ", ".join(f"{k}={v}" for k, v in n.items()))
    if min(n.values()) == 0:
        raise SystemExit("A scenario has no result files in this folder.")

    # ---- Table 4
    cols = T4_METRICS + ["income_equity_ratio", "cumulative_burden"]
    print("\nTable 4 - final-day mean +/- SD over seeds")
    print(f"{'Scenario':<20}" + "".join(f"{c:>26}" for c in cols))
    rows = []
    for label, r in runs.items():
        vals = {m: col(r, m) for m in T4_METRICS}
        vals["income_equity_ratio"] = equity_ratio(r)
        vals["cumulative_burden"] = burden(r)
        rows.append((label, {c: (vals[c].mean(), vals[c].std(ddof=1)) for c in cols}))
        print(f"{label:<20}" + "".join(f"{vals[c].mean():>17.4f} +/- {vals[c].std(ddof=1):.4f}"
                                        for c in cols))

    # ---- Table 5
    base = runs["Baseline"]
    tests = []
    for label, r in runs.items():
        if label == "Baseline":
            continue
        for oname, metric in T5_OUTCOMES.items():
            a = equity_ratio(r) if metric is None else col(r, metric)
            b = equity_ratio(base) if metric is None else col(base, metric)
            d, p = cohen_welch(a, b)
            tests.append((label, oname, d, p))
    keep = holm([t[3] for t in tests])
    print("\nTable 5 - Cohen's d and Welch p vs Baseline (* = survives Holm, 16 tests)")
    print(f"{'Scenario':<20}" + "".join(f"{o:>26}" for o in T5_OUTCOMES))
    for label in [k for k in runs if k != "Baseline"]:
        cells = []
        for (lab, o, d, p), k in zip(tests, keep):
            if lab == label:
                cells.append(f"d={d:+.2f}, p={p:.2g}{'*' if k else ' '}")
        print(f"{label:<20}" + "".join(f"{c:>26}" for c in cells))
    print(f"\nHolm survivors: {sum(keep)} of {len(keep)}")

    if args.csv:
        import csv
        with open(args.csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["scenario", "n_seeds"] + [f"{c}_{s}" for c in cols for s in ("mean", "sd")])
            for label, v in rows:
                w.writerow([label, n[label]] + [x for c in cols for x in v[c]])
        print(f"Table 4 written to {args.csv}")


if __name__ == "__main__":
    main()
