#!/usr/bin/env python
"""Phase 1 calibration - minimal output, progress bar only."""
import sys
import os

# Force unbuffered output so progress shows immediately in terminals
try:
    sys.stdout.reconfigure(line_buffering=True)
except (AttributeError, OSError):
    pass
import io
import contextlib

"""
MEMORY-OPTIMIZED CALIBRATION
=============================
Phase 1 settings:
- 100 households (reduced for Phase 1 speed)
- 90 days (scaled to annual for targets)
- 2 seeds per config (42, 123)
- Fixed: delta_convenience=0.4, go_shop_threshold_high=14.0
- Aggressive garbage collection
- Write results immediately to disk
"""

import sys
import numpy as np
import pandas as pd
from datetime import datetime
import json
import random
import time
import gc  # Garbage collection
import argparse
import itertools

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Suppress verbose model setup (stores, pantries, demographics) during calibration
print("Loading model (may take 30–60s)...", flush=True)


@contextlib.contextmanager
def _quiet():
    out = io.StringIO()
    err = io.StringIO()
    old_stdout, old_stderr = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = out, err
        yield
    finally:
        sys.stdout, sys.stderr = old_stdout, old_stderr

from enhanced_mesa_geo_model import SimulationConfig, IncomeLevel, EnhancedHouseholdAgent
from baseline_scenario import create_baseline_scenario

print("Model loaded.", flush=True)

FIXED_DELTA = 0.4
FIXED_THRESHOLD_HIGH = 14.0


def _run_single_seed(alpha, beta, gamma, threshold_low, threshold_med, seed,
                     n_households, n_days):
    """Run one configuration with one seed; returns metrics dict."""
    random.seed(seed)
    np.random.seed(seed)

    config = SimulationConfig(
        num_consumers=n_households,
        simulation_days=n_days,
        alpha_distance=alpha,
        beta_price_budget=beta,
        gamma_quality_variety=gamma,
        delta_convenience=FIXED_DELTA,
        go_shop_threshold_low=threshold_low,
        go_shop_threshold_medium=threshold_med,
        go_shop_threshold_high=FIXED_THRESHOLD_HIGH
    )

    with _quiet():
        model = create_baseline_scenario(config=config)
        for _ in range(n_days):
            model.step()

    households = [a for a in model.schedule.agents if isinstance(a, EnhancedHouseholdAgent)]

    spend_by_income = {IncomeLevel.LOW: [], IncomeLevel.MEDIUM: [], IncomeLevel.HIGH: []}

    for hh in households:
        if len(hh.shopping_history) > 0:
            total_spend = sum(trip.get('basket_cost', trip.get('basket_size', 0))
                              for trip in hh.shopping_history)
            annual_spend = total_spend * (365.0 / n_days)
            spend_by_income[hh.income].append(annual_spend)

    avg_spend_low = np.mean(spend_by_income[IncomeLevel.LOW]) if spend_by_income[IncomeLevel.LOW] else 0
    avg_spend_med = np.mean(spend_by_income[IncomeLevel.MEDIUM]) if spend_by_income[IncomeLevel.MEDIUM] else 0
    avg_spend_high = np.mean(spend_by_income[IncomeLevel.HIGH]) if spend_by_income[IncomeLevel.HIGH] else 0

    corner_trips = sum(1 for hh in households for trip in hh.shopping_history
                       if trip.get('is_corner_shop', False))
    total_trips = sum(len(hh.shopping_history) for hh in households)
    corner_share = corner_trips / total_trips if total_trips > 0 else 0

    food_insecure = sum(1 for hh in households
                        if hh.unmet_need > 0
                        or any(trip.get('unmet_need', 0) > 0
                               for trip in hh.shopping_history))
    food_insecurity_share = food_insecure / len(households) if households else 0

    # TEMPORARY DEBUG — remove after one run
    for level in [IncomeLevel.LOW, IncomeLevel.MEDIUM, IncomeLevel.HIGH]:
        grp = [hh for hh in households if hh.income == level]
        insecure = sum(1 for hh in grp
                       if hh.unmet_need > 0 or
                       any(t.get('unmet_need', 0) > 0 for t in hh.shopping_history))
        print(f"  {level.value.upper():6s} insecurity: {insecure}/{len(grp)} = "
              f"{insecure/len(grp):.1%}" if grp else f"  {level.value.upper():6s}: no households")

    all_trips = [trip for hh in households for trip in hh.shopping_history]
    grocery_trips = [t for t in all_trips
                     if t.get('provider_type') in
                     ('GROCERY_STORE', 'ProviderType.GROCERY_STORE', 'grocery_store')]
    grocery_share = len(grocery_trips) / len(all_trips) if all_trips else 0

    car_distances = []
    nocar_distances = []
    for hh in households:
        for trip in hh.shopping_history:
            if trip.get('travel_distance', 0) > 0:
                if hh.vehicle_available:
                    car_distances.append(trip['travel_distance'])
                else:
                    nocar_distances.append(trip['travel_distance'])

    avg_dist_car = np.mean(car_distances) if car_distances else 0
    avg_dist_nocar = np.mean(nocar_distances) if nocar_distances else 0

    metrics = {
        'avg_spend_low': avg_spend_low,
        'avg_spend_med': avg_spend_med,
        'avg_spend_high': avg_spend_high,
        'corner_share': corner_share,
        'food_insecurity_share': food_insecurity_share,
        'grocery_share': grocery_share,
        'avg_dist_car': avg_dist_car,
        'avg_dist_nocar': avg_dist_nocar,
        'total_trips': total_trips
    }

    del model
    del households
    gc.collect()

    return metrics


def run_single_config(alpha, beta, gamma, threshold_low, threshold_med,
                     seeds, n_households, n_days):
    """Run a single configuration with given seeds; returns averaged metrics."""
    all_metrics = []
    for seed in seeds:
        m = _run_single_seed(alpha, beta, gamma, threshold_low, threshold_med, seed,
                             n_households, n_days)
        all_metrics.append(m)
    keys = ['avg_spend_low', 'avg_spend_med', 'avg_spend_high',
            'corner_share', 'food_insecurity_share', 'grocery_share', 'avg_dist_car', 'avg_dist_nocar', 'total_trips']
    return {k: np.mean([m[k] for m in all_metrics]) for k in keys}


CALIBRATION_TARGETS = {
    'avg_spend_low': 3707,   # BLS CES 2023, food-at-home, lowest quintile
                             # FRED CXUFOODHOMELB0102M (exact)
    'avg_spend_med': 4672,   # BLS CES 2023, food-at-home, second quintile
                             # BLS USDL-24-1862 Table D: $4,302 × 1.086
    'corner_share': 0.42,    # Chrisinger 2018 + Widener 2013 + LZ 2025
    'food_insecurity_share': 0.33,  # USDA FARA + Feeding America, zip 32209
}


def calculate_error(metrics):
    """Calculate calibration error"""
    errors = []
    for key, target in CALIBRATION_TARGETS.items():
        if target > 0 and key in metrics:
            rel_error = abs(metrics[key] - target) / target
            errors.append(rel_error)

    return np.mean(errors) if errors else 999.0


def _progress_bar(done, total, width=30, best_err=None, eta_str=None):
    """Return a one-line progress string like [████████░░░░] 123/2250 (5.5%)"""
    pct = done / total if total > 0 else 0.0
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    s = f"  [{bar}] {done}/{total} ({100*pct:.1f}%)"
    if best_err is not None:
        s += f"  Best err: {best_err:.4f}"
    if eta_str:
        s += f"  ETA: {eta_str}"
    return s


def parse_args():
    parser = argparse.ArgumentParser(description="Memory-optimized phase-1 calibration grid search")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick sanity check (144 runs, ~20 min)",
    )
    parser.add_argument(
        "--output-csv",
        default=None,
        help="CSV path to save all combinations (and resume if exists). "
             "Default: PHASE1_RESULTS.csv",
    )
    parser.add_argument(
        "--output-best-json",
        default=None,
        help="JSON path for best parameters summary.",
    )
    return parser.parse_args()


def main():
    """Run MEMORY-OPTIMIZED grid search"""
    args = parse_args()

    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _project_root = os.path.dirname(_script_dir)

    if args.quick:
        PARAM_GRID = {
            'alpha': [1.0, 2.0, 3.0],
            'beta': [0.5, 0.9, 1.3],
            'gamma': [0.6, 1.4, 2.2, 2.6],
            'threshold_low': [5.0, 7.0],
            'threshold_med': [6.0, 8.0],
        }
        SEEDS = [42]
        N_HOUSEHOLDS = 100
        N_DAYS = 30
        RESULTS_FILE = 'PHASE1_QUICK_CHECK.csv'
        print("QUICK MODE: 144 runs × 1 seed = 144 total (~20 min)", flush=True)
    else:
        PARAM_GRID = {
            'alpha': [1.0, 1.5, 2.0, 2.5, 3.0],
            'beta': [0.5, 0.7, 0.9, 1.1, 1.3],
            'gamma': [0.6, 1.0, 1.4, 1.8, 2.2, 2.6],
            'threshold_low': [3.0, 4.0, 5.0, 6.0, 7.0],
            'threshold_med': [6.0, 7.0, 8.0],
        }
        SEEDS = [42, 123]
        N_HOUSEHOLDS = 100
        N_DAYS = 90
        RESULTS_FILE = 'PHASE1_RESULTS.csv'
        print("FULL MODE: 2,250 runs × 2 seeds = 4,500 total (~13h)", flush=True)

    alpha_values = PARAM_GRID['alpha']
    beta_values = PARAM_GRID['beta']
    gamma_values = PARAM_GRID['gamma']
    threshold_low_values = PARAM_GRID['threshold_low']
    threshold_med_values = PARAM_GRID['threshold_med']

    total_configs = (len(alpha_values) * len(beta_values) * len(gamma_values) *
                     len(threshold_low_values) * len(threshold_med_values))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = args.output_csv or os.path.join(_project_root, RESULTS_FILE)
    csv_written = os.path.exists(csv_file) and os.path.getsize(csv_file) > 0

    tested = set()
    if csv_written:
        try:
            prev = pd.read_csv(csv_file, usecols=[
                "alpha", "beta", "gamma",
                "threshold_low", "threshold_med"
            ])
            for _, row in prev.iterrows():
                tested.add((
                    round(float(row["alpha"]), 3),
                    round(float(row["beta"]), 3),
                    round(float(row["gamma"]), 3),
                    round(float(row["threshold_low"]), 3),
                    round(float(row["threshold_med"]), 3),
                ))
            pass  # tested count shown in header
        except Exception as e:
            print(f"⚠️ Could not parse existing CSV for resume ({e}). Starting fresh append.", flush=True)
            tested = set()

    current = 0
    start_time = time.time()
    best_error = 999.0
    best_params = None
    if csv_written and tested:
        try:
            prev_df = pd.read_csv(csv_file)
            if len(prev_df) > 0 and 'error' in prev_df.columns:
                best_error = float(prev_df['error'].min())
        except Exception:
            pass

    total_runs = total_configs * len(SEEDS)
    print("PHASE 1 CALIBRATION", flush=True)
    print(f"  {total_configs} configs × {len(SEEDS)} seed(s) = {total_runs} runs", flush=True)
    if tested:
        print(f"  Resume: skipping {len(tested)} done", flush=True)
        if best_error < 999.0:
            print(f"  Best so far (from CSV): {best_error:.4f}", flush=True)
    print("", flush=True)

    all_combos = list(itertools.product(
        alpha_values, beta_values, gamma_values,
        threshold_low_values, threshold_med_values
    ))

    for combo_idx, (alpha, beta, gamma, threshold_low, threshold_med) in enumerate(all_combos, 1):
        combo_key = (
            round(float(alpha), 3),
            round(float(beta), 3),
            round(float(gamma), 3),
            round(float(threshold_low), 3),
            round(float(threshold_med), 3),
        )
        if combo_key in tested:
            continue

        current += 1
        config_start = time.time()

        # Show immediate progress so user knows it's running
        print(f"  Running config {current}/{total_configs} (α={alpha} β={beta} γ={gamma})...", flush=True)

        try:
            metrics = run_single_config(alpha, beta, gamma, threshold_low, threshold_med,
                                        SEEDS, N_HOUSEHOLDS, N_DAYS)

            error = calculate_error(metrics)

            result = {
                'config_num': combo_idx,
                'alpha': alpha,
                'beta': beta,
                'gamma': gamma,
                'delta': FIXED_DELTA,
                'threshold_low': threshold_low,
                'threshold_med': threshold_med,
                'threshold_high': FIXED_THRESHOLD_HIGH,
                'error': error,
                **metrics
            }

            df_result = pd.DataFrame([result])
            if not csv_written:
                df_result.to_csv(csv_file, index=False, mode='w')
                csv_written = True
            else:
                df_result.to_csv(csv_file, index=False, mode='a', header=False)

            tested.add(combo_key)
            config_time = time.time() - config_start

            if error < best_error:
                best_error = error
                best_params = result

            # Progress bar (one line per completed config)
            done = len(tested)
            elapsed = time.time() - start_time
            eta_str = None
            if current > 0:
                avg_sec = elapsed / current
                remaining = max(0, total_configs - done)
                eta_sec = avg_sec * remaining
                eta_str = f"{int(eta_sec // 3600)}h {int((eta_sec % 3600) // 60)}m"
            msg = _progress_bar(done, total_configs, best_err=best_error, eta_str=eta_str)
            if error == best_error and done > 0:
                msg += "  ⭐"
            print(msg, flush=True)

            if current % 5 == 0:
                gc.collect()

        except Exception as e:
            print(f"  ✗ ERROR: {str(e)}", flush=True)
            print("", flush=True)
            continue

    # Final results
    print("\n" + "=" * 80, flush=True)
    print("CALIBRATION COMPLETE!", flush=True)
    print("=" * 80, flush=True)

    total_time = time.time() - start_time
    print(f"Total time: {total_time/60:.1f} minutes ({total_time/3600:.2f} hours)", flush=True)
    print(f"Configurations tested: {len(tested)}/{total_configs}", flush=True)

    if csv_written:
        all_df = pd.read_csv(csv_file)
        all_df = all_df.sort_values("error")
        best = all_df.iloc[0].to_dict()
        completed = len(all_df)
        json_file = args.output_best_json or f"BEST_PHASE1_PARAMS_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump({
                'best_parameters': {
                    'alpha_distance': float(best['alpha']),
                    'beta_price_budget': float(best['beta']),
                    'gamma_quality_variety': float(best['gamma']),
                    'delta_convenience': FIXED_DELTA,
                    'go_shop_threshold_low': float(best['threshold_low']),
                    'go_shop_threshold_medium': float(best['threshold_med']),
                    'go_shop_threshold_high': FIXED_THRESHOLD_HIGH
                },
                'calibration_error': float(best['error']),
                'metrics': {
                    'avg_spend_low': float(best['avg_spend_low']),
                    'avg_spend_med': float(best['avg_spend_med']),
                    'avg_spend_high': float(best['avg_spend_high']),
                    'corner_share': float(best['corner_share']),
                    'avg_dist_car': float(best['avg_dist_car']),
                    'avg_dist_nocar': float(best['avg_dist_nocar'])
                },
                'fixed_parameters': {
                    'delta_convenience': FIXED_DELTA,
                    'go_shop_threshold_high': FIXED_THRESHOLD_HIGH
                },
                'grid_values': PARAM_GRID,
                'total_possible_combinations': total_configs,
                'total_configs_tested': completed,
                'total_time_hours': total_time / 3600,
                'timestamp': timestamp
            }, f, indent=2)

        print(f"\n📊 BEST CONFIGURATION:", flush=True)
        print(f"  alpha:         {best['alpha']:.2f}", flush=True)
        print(f"  beta:          {best['beta']:.2f}", flush=True)
        print(f"  gamma:         {best['gamma']:.2f}", flush=True)
        print(f"  delta:         {FIXED_DELTA} (fixed)", flush=True)
        print(f"  threshold_low: {best['threshold_low']:.1f}", flush=True)
        print(f"  threshold_med: {best['threshold_med']:.1f}", flush=True)
        print(f"  threshold_high: {FIXED_THRESHOLD_HIGH} (fixed)", flush=True)
        print(f"  Total Error:   {best['error']:.4f}", flush=True)

        print(f"\n📈 BEST METRICS:", flush=True)
        print(f"  Spending: Low=${best['avg_spend_low']:.0f} Med=${best['avg_spend_med']:.0f} High=${best['avg_spend_high']:.0f}", flush=True)
        print(f"  Corner Share: {best['corner_share']*100:.1f}%", flush=True)
        print(f"  Distance: Car={best['avg_dist_car']:.2f}km NoCar={best['avg_dist_nocar']:.2f}km", flush=True)

        print(f"\n✅ Results saved:", flush=True)
        print(f"  {csv_file}", flush=True)
        print(f"  {json_file}", flush=True)

    print("=" * 80, flush=True)

if __name__ == "__main__":
    main()
