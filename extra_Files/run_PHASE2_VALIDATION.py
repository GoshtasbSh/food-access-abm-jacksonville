"""
PHASE 2: VALIDATION WITH FULL SETTINGS
=======================================
Takes the TOP 10 parameter sets from Phase 1 and validates them with:
- 500 households (full population)
- 365 days (full year)
- 5 seeds (seeds 0, 1, 2, 3, 4)

Same 4 targets: $3,707 / $4,672 / 42% / 33%
Same error function: mean of 4 relative errors

Features: progress bar, incremental save, resume (Ctrl+C then re-run to continue)
Estimated time: ~10-20 min per config × 10 configs = 1.5-3.5 hours total (spatial analytics disabled for speed)
"""

import sys

# Force unbuffered output so progress shows immediately (same as Phase 1)
try:
    sys.stdout.reconfigure(line_buffering=True)
except (AttributeError, OSError):
    pass

import os
import io
import contextlib
import argparse
import numpy as np
import pandas as pd
from datetime import datetime
import json
import random
import time
import gc

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enhanced_mesa_geo_model import SimulationConfig, IncomeLevel, EnhancedHouseholdAgent
from baseline_scenario import create_baseline_scenario


@contextlib.contextmanager
def _quiet():
    """Suppress stdout/stderr (same as Phase 1)."""
    out, err = io.StringIO(), io.StringIO()
    old_stdout, old_stderr = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = out, err
        yield
    finally:
        sys.stdout, sys.stderr = old_stdout, old_stderr


def run_full_validation(alpha, beta, gamma, delta, threshold_low, threshold_med, threshold_high, 
                        num_seeds=5, num_days=365, num_households=500):
    """Run with FULL settings: 500 HH, 365 days, 5 seeds (0,1,2,3,4)"""
    
    all_metrics = []
    
    for seed in range(num_seeds):
        random.seed(seed)
        np.random.seed(seed)
        
        config = SimulationConfig(
            num_consumers=num_households,
            simulation_days=num_days,
            alpha_distance=alpha,
            beta_price_budget=beta,
            gamma_quality_variety=gamma,
            delta_convenience=delta,
            go_shop_threshold_low=threshold_low,
            go_shop_threshold_medium=threshold_med,
            go_shop_threshold_high=threshold_high,
            enable_spatial_analytics=False,  # Disable for speed; not needed for validation metrics
        )
        
        with _quiet():
            model = create_baseline_scenario(config=config)
            for day in range(num_days):
                model.step()
        
        # Collect metrics
        households = [a for a in model.schedule.agents if isinstance(a, EnhancedHouseholdAgent)]
        
        # Annual spending by income
        spend_by_income = {IncomeLevel.LOW: [], IncomeLevel.MEDIUM: [], IncomeLevel.HIGH: []}
        
        for hh in households:
            if len(hh.shopping_history) > 0:
                total_spend = sum(trip.get('basket_cost', trip.get('basket_size', 0)) 
                                for trip in hh.shopping_history)
                spend_by_income[hh.income].append(total_spend)
        
        avg_spend_low = np.mean(spend_by_income[IncomeLevel.LOW]) if spend_by_income[IncomeLevel.LOW] else 0
        avg_spend_med = np.mean(spend_by_income[IncomeLevel.MEDIUM]) if spend_by_income[IncomeLevel.MEDIUM] else 0
        avg_spend_high = np.mean(spend_by_income[IncomeLevel.HIGH]) if spend_by_income[IncomeLevel.HIGH] else 0
        
        # Corner usage
        corner_trips = sum(1 for hh in households for trip in hh.shopping_history 
                          if trip.get('is_corner_shop', False))
        total_trips = sum(len(hh.shopping_history) for hh in households)
        corner_share = corner_trips / total_trips if total_trips > 0 else 0

        food_insecure = sum(1 for hh in households
                           if hh.unmet_need > 0
                           or any(trip.get('unmet_need', 0) > 0
                                  for trip in hh.shopping_history))
        food_insecurity_share = food_insecure / len(households) if households else 0
        
        # Travel distance
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
            'seed': seed,
            'avg_spend_low': avg_spend_low,
            'avg_spend_med': avg_spend_med,
            'avg_spend_high': avg_spend_high,
            'corner_share': corner_share,
            'food_insecurity_share': food_insecurity_share,
            'avg_dist_car': avg_dist_car,
            'avg_dist_nocar': avg_dist_nocar,
            'total_trips': total_trips
        })
        
        del model
        del households
        gc.collect()

    # Calculate mean and std across seeds
    avg_metrics = {}
    std_metrics = {}
    for key in ['avg_spend_low', 'avg_spend_med', 'avg_spend_high', 
                'corner_share', 'food_insecurity_share', 'avg_dist_car', 'avg_dist_nocar', 'total_trips']:
        values = [m[key] for m in all_metrics]
        avg_metrics[key] = np.mean(values)
        std_metrics[key] = np.std(values)
    
    return avg_metrics, std_metrics, all_metrics

def calculate_error(metrics):
    """Calculate calibration error"""
    targets = {
        'avg_spend_low': 3707,   # BLS CES 2023, food-at-home, lowest quintile
        'avg_spend_med': 4672,   # BLS CES 2023, food-at-home, second quintile
        'corner_share': 0.42,    # Chrisinger 2018 + Widener 2013 + LZ 2025
        'food_insecurity_share': 0.33,  # USDA FARA + Feeding America, zip 32209
    }

    errors = []
    for key, target in targets.items():
        if target > 0 and key in metrics:
            rel_error = abs(metrics[key] - target) / target
            errors.append(rel_error)
    
    return np.mean(errors) if errors else 999.0


def _progress_bar(done, total, width=20, best_err=None, eta_str=None):
    """Return a one-line progress string like [████████░░░░] 3/5 (60%)"""
    pct = done / total if total > 0 else 0.0
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    s = f"  [{bar}] {done}/{total} ({100*pct:.0f}%)"
    if best_err is not None:
        s += f"  Best err: {best_err:.4f}"
    if eta_str:
        s += f"  ETA: {eta_str}"
    return s


def parse_args():
    parser = argparse.ArgumentParser(description="Phase 2 validation (top 10 from Phase 1)")
    parser.add_argument(
        "--output-csv",
        default=None,
        help="CSV path for incremental save and resume. Default: PHASE2_RESULTS.csv",
    )
    return parser.parse_args()


def main():
    """Run Phase 2 validation on top 10 configs from Phase 1"""
    args = parse_args()
    
    csv_file = args.output_csv or "PHASE2_RESULTS.csv"
    
    # Load Phase 1 results and get top 10 (use most recent file)
    import glob
    csv_files = (glob.glob('PHASE1_RESULTS.csv') + glob.glob('PHASE1_QUICK_CHECK.csv') +
                 glob.glob('extra_Files/PHASE1_RESULTS.csv') + glob.glob('extra_Files/PHASE1_QUICK_CHECK.csv') +
                 glob.glob('MEMORY_OPTIMIZED_RESULTS_*.csv') + glob.glob('extra_Files/MEMORY_OPTIMIZED_RESULTS_*.csv'))
    csv_files = list(dict.fromkeys(csv_files))
    if csv_files:
        phase1_file = max(csv_files, key=lambda f: os.path.getmtime(f))
    else:
        phase1_file = 'PHASE1_RESULTS.csv'
    try:
        df_phase1 = pd.read_csv(phase1_file)
        df_top10 = df_phase1.sort_values('error').head(10)
    except:
        print(f"ERROR: Could not load {phase1_file}", flush=True)
        print("Please make sure Phase 1 completed successfully.", flush=True)
        return
    
    print("PHASE 2 VALIDATION", flush=True)
    print(f"  10 configs from Phase 1 (500 HH, 365 days, 5 seeds)", flush=True)

    # Resume: load already-completed configs
    completed_config_nums = set()
    csv_written = os.path.exists(csv_file) and os.path.getsize(csv_file) > 0
    if csv_written:
        try:
            prev = pd.read_csv(csv_file, usecols=["phase1_config_num"])
            completed_config_nums = set(int(x) for x in prev["phase1_config_num"].unique())
            print(f"  Resume: skipping {len(completed_config_nums)} done", flush=True)
        except Exception:
            completed_config_nums = set()

    print("", flush=True)
    results = []
    start_time = time.time()
    best_error = 999.0
    configs_to_run = [(i, row) for i, row in df_top10.iterrows() if int(row.config_num) not in completed_config_nums]
    n_top = len(df_top10)
    for idx, (i, row) in enumerate(df_top10.iterrows(), 1):
        if int(row.config_num) in completed_config_nums:
            continue
        config_start = time.time()
        print(f"  Running config {idx}/{n_top} (α={row.alpha:.1f} β={row.beta:.1f} γ={row.gamma:.1f})...", flush=True)

        try:
            avg_metrics, std_metrics, seed_metrics = run_full_validation(
                row.alpha, row.beta, row.gamma, row.delta,
                row.threshold_low, row.threshold_med, row.threshold_high,
                num_seeds=5, num_days=365, num_households=500
            )
            
            error = calculate_error(avg_metrics)
            
            result = {
                'phase1_config_num': int(row.config_num),
                'phase1_error': row.error,
                'alpha': row.alpha,
                'beta': row.beta,
                'gamma': row.gamma,
                'delta': row.delta,
                'threshold_low': row.threshold_low,
                'threshold_med': row.threshold_med,
                'threshold_high': row.threshold_high,
                'full_error': error,
                'error_improvement': row.error - error,
                **{f'{k}_mean': v for k, v in avg_metrics.items()},
                **{f'{k}_std': v for k, v in std_metrics.items()}
            }
            
            # Store individual seed results too
            result['seed_data'] = seed_metrics
            
            results.append(result)
            if error < best_error:
                best_error = error
            
            # Incremental save — append to CSV immediately
            row_dict = {k: v for k, v in result.items() if k != 'seed_data'}
            df_row = pd.DataFrame([row_dict])
            if not csv_written:
                df_row.to_csv(csv_file, index=False, mode='w')
                csv_written = True
            else:
                df_row.to_csv(csv_file, index=False, mode='a', header=False)
            
            completed_config_nums.add(int(row.config_num))
            done = len(completed_config_nums)
            config_time = time.time() - config_start
            elapsed = time.time() - start_time
            remaining = n_top - done
            eta_str = f"~{int((config_time * remaining) // 60)}m" if remaining > 0 else None
            msg = _progress_bar(done, n_top, best_err=best_error, eta_str=eta_str)
            if error == best_error:
                msg += "  ⭐"
            print(msg, flush=True)

        except Exception as e:
            print(f"  ✗ ERROR: {str(e)}", flush=True)
            print("", flush=True)
            continue
    
    # Final results — load from main CSV (has ALL configs including resumed)
    print("\n" + "=" * 80, flush=True)
    print("VALIDATION COMPLETE!", flush=True)
    print("=" * 80, flush=True)

    total_time = time.time() - start_time
    csv_has_data = os.path.exists(csv_file) and os.path.getsize(csv_file) > 0
    if csv_has_data:
        all_df = pd.read_csv(csv_file)
        completed_count = len(all_df)
    else:
        all_df = pd.DataFrame()
        completed_count = 0
    print(f"Total time: {total_time/60:.1f} minutes ({total_time/3600:.2f} hours)", flush=True)
    print(f"Configurations validated: {completed_count}/10", flush=True)
    
    if not all_df.empty:
        # Sort by FULL error (same logic as Phase 1: use CSV for final summary)
        results_df = all_df.sort_values('full_error')
        
        # BEST parameters
        best = results_df.iloc[0].to_dict()
        best_full = next((r for r in results if r.get('phase1_config_num') == best.get('phase1_config_num')), None)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = f"FINAL_CALIBRATED_PARAMS_{timestamp}.json"
        seed_results = best_full['seed_data'] if best_full and 'seed_data' in best_full else []
        with open(json_file, 'w') as f:
            json.dump({
                'final_parameters': {
                    'alpha_distance': float(best['alpha']),
                    'beta_price_budget': float(best['beta']),
                    'gamma_quality_variety': float(best['gamma']),
                    'delta_convenience': float(best['delta']),
                    'go_shop_threshold_low': float(best['threshold_low']),
                    'go_shop_threshold_medium': float(best['threshold_med']),
                    'go_shop_threshold_high': float(best['threshold_high'])
                },
                'calibration_error_full': float(best['full_error']),
                'calibration_error_phase1': float(best['phase1_error']),
                'metrics_mean': {
                    'avg_spend_low': float(best['avg_spend_low_mean']),
                    'avg_spend_med': float(best['avg_spend_med_mean']),
                    'avg_spend_high': float(best['avg_spend_high_mean']),
                    'corner_share': float(best['corner_share_mean']),
                    'food_insecurity_share': float(best['food_insecurity_share_mean']),
                    'avg_dist_car': float(best['avg_dist_car_mean']),
                    'avg_dist_nocar': float(best['avg_dist_nocar_mean']),
                    'total_trips': float(best['total_trips_mean'])
                },
                'metrics_std': {
                    'avg_spend_low': float(best['avg_spend_low_std']),
                    'avg_spend_med': float(best['avg_spend_med_std']),
                    'avg_spend_high': float(best['avg_spend_high_std']),
                    'corner_share': float(best['corner_share_std']),
                    'food_insecurity_share': float(best['food_insecurity_share_std']),
                    'avg_dist_car': float(best['avg_dist_car_std']),
                    'avg_dist_nocar': float(best['avg_dist_nocar_std']),
                    'total_trips': float(best['total_trips_std'])
                },
                'seed_results': seed_results,
                'validation_settings': {
                    'num_households': 500,
                    'num_days': 365,
                    'num_seeds': 5
                },
                'total_time_hours': total_time / 3600,
                'timestamp': timestamp
            }, f, indent=2)
        
        print(f"\n📊 BEST CONFIGURATION:", flush=True)
        print(f"  Config #{int(best['phase1_config_num'])}, alpha: {best['alpha']:.2f} beta: {best['beta']:.2f} gamma: {best['gamma']:.2f}", flush=True)
        print(f"  delta: {best['delta']:.2f}  threshold_low: {best['threshold_low']:.1f} threshold_med: {best['threshold_med']:.1f} threshold_high: {best['threshold_high']:.1f}", flush=True)
        print(f"  Total Error (full): {best['full_error']:.4f}", flush=True)
        print(f"\n📈 BEST METRICS:", flush=True)
        print(f"  Spending: Low=${best['avg_spend_low_mean']:.0f} Med=${best['avg_spend_med_mean']:.0f} High=${best['avg_spend_high_mean']:.0f}", flush=True)
        print(f"  Corner Share: {best['corner_share_mean']*100:.1f}%  Food Insec: {best['food_insecurity_share_mean']*100:.1f}%", flush=True)
        print(f"  Distance: Car={best['avg_dist_car_mean']:.2f}km NoCar={best['avg_dist_nocar_mean']:.2f}km", flush=True)
        print(f"\n✅ Results saved:", flush=True)
        print(f"  {csv_file}", flush=True)
        print(f"  {json_file}", flush=True)

    print("=" * 80, flush=True)

if __name__ == "__main__":
    main()

