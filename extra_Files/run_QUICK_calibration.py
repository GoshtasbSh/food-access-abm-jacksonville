"""
QUICK Calibration for IDEA #1 (20-30 minutes)
==============================================

This is a minimal calibration to test the implementation quickly.
For full calibration, use run_SIMPLE_calibration.py later.
"""

import numpy as np
import pandas as pd
from datetime import datetime
import json
import random
import sys

sys.path.append('/Users/goshtasbshahriari/Desktop/Code/GeoMesa_Food_Access')

from enhanced_mesa_geo_model import SimulationConfig, IncomeLevel
from baseline_scenario import create_baseline_scenario

def run_calibration_single_config(alpha, gamma, threshold_low, num_seeds=2, num_days=180):
    """Run a single configuration with multiple seeds (sequential)"""
    
    all_metrics = []
    
    for seed in range(num_seeds):
        random.seed(seed)
        np.random.seed(seed)
        
        # Create config
        config = SimulationConfig(
            num_consumers=100,  # Small for speed
            simulation_days=num_days,
            alpha_distance=alpha,
            gamma_quality_variety=gamma,
            go_shop_threshold_low=threshold_low,
            beta_price_budget=1.0,
            delta_convenience=0.4,
            go_shop_threshold_medium=7.0,
            go_shop_threshold_high=14.0
        )
        
        # Run simulation
        model = create_baseline_scenario(config=config)
        
        for _ in range(num_days):
            model.step()
        
        # Collect metrics
        from enhanced_mesa_geo_model import EnhancedHouseholdAgent
        households = [a for a in model.schedule.agents if isinstance(a, EnhancedHouseholdAgent)]
        
        # 1. Annual spend by income
        spend_by_income = {IncomeLevel.LOW: [], IncomeLevel.MEDIUM: [], IncomeLevel.HIGH: []}
        
        for hh in households:
            if len(hh.shopping_history) > 0:
                total_spend = sum(trip.get('basket_cost', trip.get('basket_size', 0)) for trip in hh.shopping_history)
                annual_spend = total_spend * (365.0 / num_days)
                spend_by_income[hh.income].append(annual_spend)
        
        avg_spend_low = np.mean(spend_by_income[IncomeLevel.LOW]) if spend_by_income[IncomeLevel.LOW] else 0
        avg_spend_med = np.mean(spend_by_income[IncomeLevel.MEDIUM]) if spend_by_income[IncomeLevel.MEDIUM] else 0
        avg_spend_high = np.mean(spend_by_income[IncomeLevel.HIGH]) if spend_by_income[IncomeLevel.HIGH] else 0
        
        # 2. Store type share
        corner_trips = sum(1 for hh in households for trip in hh.shopping_history if trip.get('is_corner_shop', False))
        total_trips = sum(len(hh.shopping_history) for hh in households)
        corner_share = corner_trips / total_trips if total_trips > 0 else 0
        
        # 3. Travel distance
        car_distances = []
        nocar_distances = []
        for hh in households:
            for trip in hh.shopping_history:
                if trip.get('travel_distance', 0) > 0:  # Exclude delivery
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
            'avg_dist_nocar': avg_dist_nocar
        })
    
    # Average across seeds
    avg_metrics = {}
    for key in all_metrics[0].keys():
        avg_metrics[key] = np.mean([m[key] for m in all_metrics])
    
    return avg_metrics

def calculate_error(metrics):
    """Calculate total calibration error"""
    
    targets = {
        'avg_spend_low': 5300,
        'avg_spend_med': 9000,
        'avg_spend_high': 17000,
        'corner_share': 0.10,  # Target ≤10%
        'avg_dist_car': 5.6,  # 3.5 mi = 5.6 km
        'avg_dist_nocar': 0.8  # 0.5 mi = 0.8 km
    }
    
    errors = []
    for key, target in targets.items():
        if target > 0:
            rel_error = abs(metrics[key] - target) / target
            errors.append(rel_error)
    
    return np.mean(errors)

def main():
    """Run quick calibration (20-30 minutes)"""
    
    print("="*80)
    print("QUICK CALIBRATION - IDEA #1 (20-30 minutes)")
    print("="*80)
    
    # MINIMAL search space for quick testing
    alpha_values = [1.5, 2.5]        # 2 values (was 3)
    gamma_values = [1.5, 2.5]        # 2 values (was 3)
    threshold_low_values = [5.0, 6.5]  # 2 values (was 3)
    
    total_configs = len(alpha_values) * len(gamma_values) * len(threshold_low_values)
    
    print(f"\nQuick Test Parameters:")
    print(f"  Configs: {total_configs} (2×2×2)")
    print(f"  Seeds: 2 per config")
    print(f"  Days: 180 (half year)")
    print(f"  Households: 100")
    print(f"  Estimated time: ~{total_configs * 3:.0f} minutes")
    print("\n" + "="*80)
    
    results = []
    current = 0
    
    import time
    start_time = time.time()
    
    for alpha in alpha_values:
        for gamma in gamma_values:
            for threshold_low in threshold_low_values:
                current += 1
                config_start = time.time()
                
                print(f"\n[{current}/{total_configs}] α={alpha:.1f}, γ={gamma:.1f}, thresh={threshold_low:.1f}")
                
                metrics = run_calibration_single_config(alpha, gamma, threshold_low, num_seeds=2, num_days=180)
                error = calculate_error(metrics)
                
                result = {
                    'alpha': alpha,
                    'gamma': gamma,
                    'threshold_low': threshold_low,
                    'error': error,
                    **metrics
                }
                results.append(result)
                
                config_time = time.time() - config_start
                elapsed = time.time() - start_time
                remaining = (total_configs - current) * (elapsed / current)
                
                print(f"  Spend: Low=${metrics['avg_spend_low']:.0f} Med=${metrics['avg_spend_med']:.0f} High=${metrics['avg_spend_high']:.0f}")
                print(f"  Corner: {metrics['corner_share']*100:.1f}%")
                print(f"  Distance: Car={metrics['avg_dist_car']:.2f}km NoCar={metrics['avg_dist_nocar']:.2f}km")
                print(f"  Error: {error:.4f}")
                print(f"  Time: {config_time/60:.1f}m | Elapsed: {elapsed/60:.1f}m | Remaining: ~{remaining/60:.1f}m")
    
    # Sort by error
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('error')
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = f"calibration_QUICK_results_{timestamp}.csv"
    results_df.to_csv(csv_file, index=False)
    
    # Save best
    best = results_df.iloc[0]
    json_file = f"BEST_QUICK_params_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump({
            'note': 'Quick calibration (20-30 min). For full calibration, use run_SIMPLE_calibration.py',
            'alpha_distance': float(best['alpha']),
            'gamma_quality': float(best['gamma']),
            'threshold_low': float(best['threshold_low']),
            'error': float(best['error']),
            'metrics': {
                'avg_spend_low': float(best['avg_spend_low']),
                'avg_spend_med': float(best['avg_spend_med']),
                'avg_spend_high': float(best['avg_spend_high']),
                'corner_share': float(best['corner_share']),
                'avg_dist_car': float(best['avg_dist_car']),
                'avg_dist_nocar': float(best['avg_dist_nocar'])
            },
            'config': {
                'num_configs': total_configs,
                'seeds_per_config': 2,
                'days_per_run': 180,
                'households': 100
            }
        }, f, indent=2)
    
    total_time = time.time() - start_time
    
    print("\n" + "="*80)
    print("QUICK CALIBRATION COMPLETE!")
    print("="*80)
    print(f"\n⏱️  Total time: {total_time/60:.1f} minutes")
    print(f"\n📊 Best Configuration:")
    print(f"  alpha: {best['alpha']:.1f}")
    print(f"  gamma: {best['gamma']:.1f}")
    print(f"  threshold_low: {best['threshold_low']:.1f}")
    print(f"  Error: {best['error']:.4f}")
    
    print(f"\n📈 Best Metrics:")
    print(f"  Spending: Low=${best['avg_spend_low']:.0f} Med=${best['avg_spend_med']:.0f} High=${best['avg_spend_high']:.0f}")
    print(f"  Corner Share: {best['corner_share']*100:.1f}% (target ≤10%)")
    print(f"  Distance: Car={best['avg_dist_car']:.2f}km NoCar={best['avg_dist_nocar']:.2f}km")
    
    print(f"\n✅ Results saved to: {csv_file}")
    print(f"✅ Best params saved to: {json_file}")
    
    print("\n" + "="*80)
    print("NEXT STEPS:")
    print("="*80)
    print("1. Review quick calibration results")
    print("2. Use these parameters for initial scenario runs")
    print("3. Later: Run full calibration with run_SIMPLE_calibration.py")
    print("   (27 configs, 3 seeds, 365 days = 2-3 hours)")
    print("="*80)

if __name__ == "__main__":
    main()

