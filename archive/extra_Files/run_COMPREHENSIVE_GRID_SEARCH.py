"""
COMPREHENSIVE GRID SEARCH CALIBRATION
======================================

Complete grid search over ALL parameters to find best calibration.
Shows progress after each configuration completes.
Estimated time: 3-6 hours depending on parameter space.
"""

import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime
import json
import random
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enhanced_mesa_geo_model import SimulationConfig, IncomeLevel, EnhancedHouseholdAgent
from baseline_scenario import create_baseline_scenario

def run_single_config(alpha, beta, gamma, delta, threshold_low, threshold_med, threshold_high, 
                      num_seeds=3, num_days=365):
    """Run a single configuration with multiple seeds"""
    
    all_metrics = []
    
    for seed in range(num_seeds):
        random.seed(seed)
        np.random.seed(seed)
        
        config = SimulationConfig(
            num_consumers=200,  # Larger for better statistics
            simulation_days=num_days,
            alpha_distance=alpha,
            beta_price_budget=beta,
            gamma_quality_variety=gamma,
            delta_convenience=delta,
            go_shop_threshold_low=threshold_low,
            go_shop_threshold_medium=threshold_med,
            go_shop_threshold_high=threshold_high
        )
        
        model = create_baseline_scenario(config=config)
        
        for _ in range(num_days):
            model.step()
        
        # Collect metrics
        households = [a for a in model.schedule.agents if isinstance(a, EnhancedHouseholdAgent)]
        
        # Annual spending by income
        spend_by_income = {IncomeLevel.LOW: [], IncomeLevel.MEDIUM: [], IncomeLevel.HIGH: []}
        
        for hh in households:
            if len(hh.shopping_history) > 0:
                total_spend = sum(trip.get('basket_cost', trip.get('basket_size', 0)) 
                                for trip in hh.shopping_history)
                annual_spend = total_spend * (365.0 / num_days)
                spend_by_income[hh.income].append(annual_spend)
        
        avg_spend_low = np.mean(spend_by_income[IncomeLevel.LOW]) if spend_by_income[IncomeLevel.LOW] else 0
        avg_spend_med = np.mean(spend_by_income[IncomeLevel.MEDIUM]) if spend_by_income[IncomeLevel.MEDIUM] else 0
        avg_spend_high = np.mean(spend_by_income[IncomeLevel.HIGH]) if spend_by_income[IncomeLevel.HIGH] else 0
        
        # Corner usage
        corner_trips = sum(1 for hh in households for trip in hh.shopping_history 
                          if trip.get('is_corner_shop', False))
        total_trips = sum(len(hh.shopping_history) for hh in households)
        corner_share = corner_trips / total_trips if total_trips > 0 else 0
        
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
            'avg_spend_low': avg_spend_low,
            'avg_spend_med': avg_spend_med,
            'avg_spend_high': avg_spend_high,
            'corner_share': corner_share,
            'avg_dist_car': avg_dist_car,
            'avg_dist_nocar': avg_dist_nocar,
            'total_trips': total_trips
        })
    
    # Average across seeds
    avg_metrics = {}
    for key in all_metrics[0].keys():
        avg_metrics[key] = np.mean([m[key] for m in all_metrics])
    
    return avg_metrics

def calculate_error(metrics):
    """Calculate calibration error"""
    targets = {
        'avg_spend_low': 5300,
        'avg_spend_med': 9000,
        'avg_spend_high': 17000,
        'corner_share': 0.10,
        'avg_dist_car': 5.6,
        'avg_dist_nocar': 0.8
    }
    
    errors = []
    for key, target in targets.items():
        if target > 0 and key in metrics:
            rel_error = abs(metrics[key] - target) / target
            errors.append(rel_error)
    
    return np.mean(errors) if errors else 999.0

def main():
    """Run comprehensive grid search"""
    
    print("="*80)
    print("COMPREHENSIVE GRID SEARCH CALIBRATION")
    print("="*80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Define parameter grid (optimized for ~6 hours)
    alpha_values = [1.5, 2.0, 2.5]               # Distance sensitivity
    beta_values = [0.7, 1.0, 1.3]                # Price sensitivity
    gamma_values = [1.0, 1.5, 2.0, 2.5]          # Quality preference (key for corners)
    delta_values = [0.4]                         # Convenience (fixed)
    threshold_low_values = [4.0, 5.5, 7.0]       # Low-income shopping freq
    threshold_med_values = [7.0]                 # Medium-income (fixed)
    threshold_high_values = [14.0]               # High-income (fixed)
    
    total_configs = (len(alpha_values) * len(beta_values) * len(gamma_values) * 
                    len(delta_values) * len(threshold_low_values) * 
                    len(threshold_med_values) * len(threshold_high_values))
    
    print("Parameter Grid:")
    print(f"  alpha (distance):     {alpha_values}")
    print(f"  beta (price):         {beta_values}")
    print(f"  gamma (quality):      {gamma_values}")
    print(f"  delta (convenience):  {delta_values}")
    print(f"  threshold_low:        {threshold_low_values}")
    print(f"  threshold_medium:     {threshold_med_values}")
    print(f"  threshold_high:       {threshold_high_values}")
    print()
    print(f"TOTAL CONFIGURATIONS: {total_configs}")
    print(f"Seeds per config: 3")
    print(f"Days per run: 365")
    print(f"Households: 200")
    print(f"Estimated time: {total_configs * 4:.0f} minutes (~{total_configs * 4 / 60:.1f} hours)")
    print("="*80)
    print()
    print("🚀 Starting calibration automatically...")
    print()
    
    results = []
    current = 0
    start_time = time.time()
    
    # Grid search
    for alpha in alpha_values:
        for beta in beta_values:
            for gamma in gamma_values:
                for delta in delta_values:
                    for threshold_low in threshold_low_values:
                        for threshold_med in threshold_med_values:
                            for threshold_high in threshold_high_values:
                                current += 1
                                config_start = time.time()
                                
                                # Print progress BEFORE running
                                elapsed = time.time() - start_time
                                if current > 1:
                                    avg_time_per_config = elapsed / (current - 1)
                                    remaining_configs = total_configs - current + 1
                                    estimated_remaining = avg_time_per_config * remaining_configs
                                else:
                                    estimated_remaining = 0
                                
                                print(f"[{current}/{total_configs}] Testing: α={alpha:.1f} β={beta:.1f} γ={gamma:.1f} δ={delta:.1f} TL={threshold_low:.0f} TM={threshold_med:.0f} TH={threshold_high:.0f}")
                                print(f"  Elapsed: {elapsed/60:.1f}m | Remaining: ~{estimated_remaining/60:.1f}m")
                                
                                # Run configuration
                                try:
                                    metrics = run_single_config(
                                        alpha, beta, gamma, delta,
                                        threshold_low, threshold_med, threshold_high,
                                        num_seeds=3, num_days=365
                                    )
                                    
                                    error = calculate_error(metrics)
                                    
                                    result = {
                                        'config_num': current,
                                        'alpha': alpha,
                                        'beta': beta,
                                        'gamma': gamma,
                                        'delta': delta,
                                        'threshold_low': threshold_low,
                                        'threshold_med': threshold_med,
                                        'threshold_high': threshold_high,
                                        'error': error,
                                        **metrics
                                    }
                                    results.append(result)
                                    
                                    config_time = time.time() - config_start
                                    
                                    # Print results
                                    print(f"  ✓ COMPLETE in {config_time/60:.1f}m")
                                    print(f"    Spend: L=${metrics['avg_spend_low']:.0f} M=${metrics['avg_spend_med']:.0f} H=${metrics['avg_spend_high']:.0f}")
                                    print(f"    Corner: {metrics['corner_share']*100:.1f}% | Distance: Car={metrics['avg_dist_car']:.2f}km NoCar={metrics['avg_dist_nocar']:.2f}km")
                                    print(f"    ERROR: {error:.4f}")
                                    
                                    # Save intermediate results every 10 configs
                                    if current % 10 == 0:
                                        df_temp = pd.DataFrame(results)
                                        df_temp = df_temp.sort_values('error')
                                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                        df_temp.to_csv(f'calibration_progress_{timestamp}.csv', index=False)
                                        print(f"  💾 Progress saved (best error so far: {df_temp.iloc[0]['error']:.4f})")
                                    
                                    print()
                                    
                                except Exception as e:
                                    print(f"  ✗ ERROR: {str(e)}")
                                    print()
                                    continue
    
    # Final results
    print("\n" + "="*80)
    print("CALIBRATION COMPLETE!")
    print("="*80)
    
    total_time = time.time() - start_time
    print(f"Total time: {total_time/60:.1f} minutes ({total_time/3600:.2f} hours)")
    print(f"Configurations tested: {len(results)}/{total_configs}")
    
    if results:
        # Sort by error
        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values('error')
        
        # Save final results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = f"COMPREHENSIVE_CALIBRATION_RESULTS_{timestamp}.csv"
        results_df.to_csv(csv_file, index=False)
        
        # Save best parameters
        best = results_df.iloc[0]
        json_file = f"BEST_COMPREHENSIVE_PARAMS_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump({
                'best_parameters': {
                    'alpha_distance': float(best['alpha']),
                    'beta_price_budget': float(best['beta']),
                    'gamma_quality_variety': float(best['gamma']),
                    'delta_convenience': float(best['delta']),
                    'go_shop_threshold_low': float(best['threshold_low']),
                    'go_shop_threshold_medium': float(best['threshold_med']),
                    'go_shop_threshold_high': float(best['threshold_high'])
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
                'total_configs_tested': len(results),
                'total_time_hours': total_time / 3600,
                'timestamp': timestamp
            }, f, indent=2)
        
        print(f"\n📊 BEST CONFIGURATION:")
        print(f"  alpha:         {best['alpha']:.2f}")
        print(f"  beta:          {best['beta']:.2f}")
        print(f"  gamma:         {best['gamma']:.2f}")
        print(f"  delta:         {best['delta']:.2f}")
        print(f"  threshold_low: {best['threshold_low']:.1f}")
        print(f"  threshold_med: {best['threshold_med']:.1f}")
        print(f"  threshold_high: {best['threshold_high']:.1f}")
        print(f"  Total Error:   {best['error']:.4f}")
        
        print(f"\n📈 BEST METRICS:")
        print(f"  Spending: Low=${best['avg_spend_low']:.0f} Med=${best['avg_spend_med']:.0f} High=${best['avg_spend_high']:.0f}")
        print(f"  Corner Share: {best['corner_share']*100:.1f}%")
        print(f"  Distance: Car={best['avg_dist_car']:.2f}km NoCar={best['avg_dist_nocar']:.2f}km")
        
        print(f"\n✅ Results saved:")
        print(f"  {csv_file}")
        print(f"  {json_file}")
    
    print("="*80)

if __name__ == "__main__":
    main()

