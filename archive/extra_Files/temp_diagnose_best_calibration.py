#!/usr/bin/env python
"""
Temporary diagnostic script:
1. Run best-calibrated params once; print individual target errors
2. Count trips by provider type (grocery, corner, pantry, delivery)
3. Answer: How do food pantries work? (see docstring below)

Use: python temp_diagnose_best_calibration.py
"""
import sys
import os
import io
import contextlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Targets (user-specified; calibration uses 5300, 9000, 17000)
TARGETS = {
    'avg_spend_low':  5278,
    'avg_spend_med':  8989,
    'avg_spend_high': 16996,
    'avg_dist_car':   5.6,
    'avg_dist_nocar': 0.8,
    'corner_share':    0.25,
}

# =============================================================================
# Q1: HOW FOOD PANTRIES WORK IN THIS MODEL
# =============================================================================
# Pantries do NOT work every day. Each of the 19 real HZ1 pantries has:
#   - operating_days: list of weekdays (0=Mon .. 6=Sun) when it COULD be open
#   - frequency: 'weekly' | 'biweekly' | 'monthly_2nd' | 'monthly_3rd' | 'quarterly'
#
# A pantry is active_today only when BOTH conditions hold:
#   1. current_day's weekday is in operating_days
#   2. current week matches frequency:
#      - weekly: every week
#      - biweekly: every 2 weeks (week_num % 2 == 0)
#      - monthly_2nd: 2nd week of month (week_num % 4 == 1)
#      - monthly_3rd: 3rd week of month (week_num % 4 == 2)
#      - quarterly: every 13 weeks
#
# Example: "Johnson_Family_YMCA" has [2,4] (Wed,Fri) and 'weekly' → open every Wed+Fri
# Example: "Celebration_Life_Center" has [0] (Mon) and 'monthly_2nd' → open only 2nd Mon of month
# =============================================================================


def load_best_params():
    """Load best params from PHASE1_RESULTS.csv or BEST_PHASE1_PARAMS_*.json"""
    import glob
    import pandas as pd

    csv_path = os.path.join(os.path.dirname(__file__), 'PHASE1_RESULTS.csv')
    json_pattern = os.path.join(os.path.dirname(__file__), 'BEST_PHASE1_PARAMS_*.json')
    json_files = glob.glob(json_pattern)

    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        if len(df) == 0:
            raise SystemExit("PHASE1_RESULTS.csv is empty. Run calibration first.")
        best = df.sort_values('error').iloc[0]
        return {
            'alpha': float(best['alpha']),
            'beta': float(best['beta']),
            'gamma': float(best['gamma']),
            'threshold_low': float(best['threshold_low']),
            'threshold_med': float(best['threshold_med']),
        }
    elif json_files:
        import json
        with open(sorted(json_files)[-1]) as f:
            data = json.load(f)
        bp = data['best_parameters']
        return {
            'alpha': float(bp['alpha_distance']),
            'beta': float(bp['beta_price_budget']),
            'gamma': float(bp['gamma_quality_variety']),
            'threshold_low': float(bp['go_shop_threshold_low']),
            'threshold_med': float(bp['go_shop_threshold_medium']),
        }
    else:
        raise SystemExit("No PHASE1_RESULTS.csv or BEST_PHASE1_PARAMS_*.json found. Run calibration first.")


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


def _count_trips_by_type(households):
    """Count trips by provider type. Returns (trips_by_type, total)."""
    trips_by_type = {'grocery': 0, 'corner': 0, 'pantry': 0, 'delivery': 0, 'food_hub': 0, 'other': 0}
    for hh in households:
        for trip in hh.shopping_history:
            ptype = trip.get('provider_type', 'unknown')
            used_delivery = trip.get('used_delivery', False)
            # Delivery overrides: if used_delivery, count as delivery (order delivered to home)
            if used_delivery:
                trips_by_type['delivery'] += 1
            elif ptype == 'grocery_store':
                trips_by_type['grocery'] += 1
            elif ptype == 'corner_store':
                trips_by_type['corner'] += 1
            elif ptype in ('mobile_pantry', 'pantry'):
                trips_by_type['pantry'] += 1
            elif ptype == 'food_hub':
                trips_by_type['food_hub'] += 1
            else:
                trips_by_type['other'] += 1
    total = sum(trips_by_type.values())
    return trips_by_type, total


def run_single(best_params):
    """Run one config with best params (2 seeds, averaged). Returns (metrics dict, trips_by_type, total)."""
    import numpy as np
    import gc
    from enhanced_mesa_geo_model import SimulationConfig, IncomeLevel, EnhancedHouseholdAgent
    from baseline_scenario import create_baseline_scenario

    alpha = best_params['alpha']
    beta = best_params['beta']
    gamma = best_params['gamma']
    threshold_low = best_params['threshold_low']
    threshold_med = best_params['threshold_med']
    delta = 0.4
    threshold_high = 14.0
    seeds = [42, 123]

    all_metrics = []
    trips_by_type = {'grocery': 0, 'corner': 0, 'pantry': 0, 'delivery': 0, 'food_hub': 0, 'other': 0}
    total_trips_all = 0

    for seed in seeds:
        import random
        random.seed(seed)
        np.random.seed(seed)

        config = SimulationConfig(
            num_consumers=100,
            simulation_days=90,
            alpha_distance=alpha,
            beta_price_budget=beta,
            gamma_quality_variety=gamma,
            delta_convenience=delta,
            go_shop_threshold_low=threshold_low,
            go_shop_threshold_medium=threshold_med,
            go_shop_threshold_high=threshold_high
        )

        with _quiet():
            model = create_baseline_scenario(config=config)
            for _ in range(90):
                model.step()

        households = [a for a in model.schedule.agents if isinstance(a, EnhancedHouseholdAgent)]
        typs, tot = _count_trips_by_type(households)
        for k in trips_by_type:
            trips_by_type[k] += typs.get(k, 0)
        total_trips_all += tot

        spend_by_income = {IncomeLevel.LOW: [], IncomeLevel.MEDIUM: [], IncomeLevel.HIGH: []}
        for hh in households:
            if len(hh.shopping_history) > 0:
                total_spend = sum(trip.get('basket_cost', trip.get('basket_size', 0)) for trip in hh.shopping_history)
                annual_spend = total_spend * (365.0 / 90.0)
                spend_by_income[hh.income].append(annual_spend)

        avg_spend_low = np.mean(spend_by_income[IncomeLevel.LOW]) if spend_by_income[IncomeLevel.LOW] else 0
        avg_spend_med = np.mean(spend_by_income[IncomeLevel.MEDIUM]) if spend_by_income[IncomeLevel.MEDIUM] else 0
        avg_spend_high = np.mean(spend_by_income[IncomeLevel.HIGH]) if spend_by_income[IncomeLevel.HIGH] else 0

        corner_trips = sum(1 for hh in households for trip in hh.shopping_history if trip.get('is_corner_shop', False))
        total_trips = sum(len(hh.shopping_history) for hh in households)
        corner_share = corner_trips / total_trips if total_trips > 0 else 0

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

        all_metrics.append({
            'avg_spend_low': avg_spend_low, 'avg_spend_med': avg_spend_med, 'avg_spend_high': avg_spend_high,
            'corner_share': corner_share, 'avg_dist_car': avg_dist_car, 'avg_dist_nocar': avg_dist_nocar,
        })
        del model
        del households
        gc.collect()

    keys = ['avg_spend_low', 'avg_spend_med', 'avg_spend_high', 'corner_share', 'avg_dist_car', 'avg_dist_nocar']
    metrics = {k: np.mean([m[k] for m in all_metrics]) for k in keys}
    return metrics, trips_by_type, total_trips_all


def main():
    print("Loading model...", flush=True)
    best_params = load_best_params()
    print(f"Best params: α={best_params['alpha']:.2f} β={best_params['beta']:.2f} γ={best_params['gamma']:.2f} "
          f"TL={best_params['threshold_low']:.1f} TM={best_params['threshold_med']:.1f}", flush=True)
    print("", flush=True)

    print("Running single simulation (2 seeds, 100 HH, 90 days)...", flush=True)
    metrics, trips_by_type, total = run_single(best_params)
    print("", flush=True)

    # --- Trip counts by provider type ---
    print("=" * 60, flush=True)
    print("TRIPS BY PROVIDER TYPE", flush=True)
    print("=" * 60, flush=True)
    if total > 0:
        print(f"  Grocery trips: {trips_by_type['grocery']:5d} ({trips_by_type['grocery']/total:6.1%})", flush=True)
        print(f"  Corner trips:  {trips_by_type['corner']:5d} ({trips_by_type['corner']/total:6.1%})", flush=True)
        print(f"  Pantry trips: {trips_by_type['pantry']:5d} ({trips_by_type['pantry']/total:6.1%})", flush=True)
        print(f"  Delivery:     {trips_by_type['delivery']:5d} ({trips_by_type['delivery']/total:6.1%})", flush=True)
        if trips_by_type.get('food_hub', 0) > 0 or trips_by_type.get('other', 0) > 0:
            print(f"  Food hub:     {trips_by_type.get('food_hub', 0):5d} ({trips_by_type.get('food_hub', 0)/total:6.1%})", flush=True)
            print(f"  Other:        {trips_by_type.get('other', 0):5d} ({trips_by_type.get('other', 0)/total:6.1%})", flush=True)
        print(f"  TOTAL:        {total:5d}", flush=True)
    else:
        print("  No trips recorded.", flush=True)
    print("", flush=True)

    # --- Individual target errors ---
    print("=" * 60, flush=True)
    print("INDIVIDUAL TARGET ERRORS (simulated vs target)", flush=True)
    print("=" * 60, flush=True)

    for key, target in TARGETS.items():
        sim = metrics[key]
        err_abs = abs(sim - target)
        err_rel = (err_abs / target * 100) if target != 0 else 0
        print(f"  {key:18s}: sim={sim:10.2f}  vs  target={target:8.2f}  |  "
              f"rel_err={err_rel:5.1f}%", flush=True)

    mean_rel = sum(abs(metrics[k] - t) / t for k, t in TARGETS.items() if t != 0) / len(TARGETS)
    print("", flush=True)
    print(f"Mean relative error (calibration metric): {mean_rel:.4f}", flush=True)
    print("=" * 60, flush=True)

    # --- Food pantry scheduling reminder ---
    print("", flush=True)
    print("NOTE: Food pantries operate on specific days (not all days).", flush=True)
    print("      See script docstring for details.", flush=True)


if __name__ == "__main__":
    main()
