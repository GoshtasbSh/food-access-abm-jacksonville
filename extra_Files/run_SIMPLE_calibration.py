"""
SIMPLE Sequential Calibration for IDEA #1
==========================================

This version runs sequentially (no parallel processing) to avoid sandbox restrictions.
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

def run_calibration_single_config(alpha, gamma, threshold_low, num_seeds=3, num_days=365):
    """Run a single configuration with multiple seeds (sequential)"""
    
    all_metrics = []
    
    for seed in range(num_seeds):
        random.seed(seed)
        np.random.seed(seed)
        
        # Create config
        config = SimulationConfig(
            num_consumers=100,  # Smaller for faster testing
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
    """Run simple sequential calibration"""
    
    print("="*80)
    print("SIMPLE SEQUENTIAL CALIBRATION - IDEA #1")
    print("="*80)
    
    # Focused search space (smaller for speed)
    alpha_values = [1.5, 2.0, 2.5]
    gamma_values = [1.5, 2.0, 2.5]
    threshold_low_values = [5.0, 6.0, 7.0]
    
    total_configs = len(alpha_values) * len(gamma_values) * len(threshold_low_values)
    
    print(f"\nTesting {total_configs} configurations")
    print(f"  3 seeds × 365 days × 100 households each")
    print(f"  Estimated time: ~{total_configs * 5:.0f} minutes")
    print("\n" + "="*80)
    
    results = []
    current = 0
    
    for alpha in alpha_values:
        for gamma in gamma_values:
            for threshold_low in threshold_low_values:
                current += 1
                print(f"\n[{current}/{total_configs}] α={alpha:.1f}, γ={gamma:.1f}, thresh={threshold_low:.1f}")
                
                metrics = run_calibration_single_config(alpha, gamma, threshold_low, num_seeds=3, num_days=365)
                error = calculate_error(metrics)
                
                result = {
                    'alpha': alpha,
                    'gamma': gamma,
                    'threshold_low': threshold_low,
                    'error': error,
                    **metrics
                }
                results.append(result)
                
                print(f"  Spend: Low=${metrics['avg_spend_low']:.0f} Med=${metrics['avg_spend_med']:.0f} High=${metrics['avg_spend_high']:.0f}")
                print(f"  Corner: {metrics['corner_share']*100:.1f}%")
                print(f"  Distance: Car={metrics['avg_dist_car']:.2f}km NoC ar={metrics['avg_dist_nocar']:.2f}km")
                print(f"  Error: {error:.4f}")
    
    # Sort by error
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('error')
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = f"calibration_SIMPLE_results_{timestamp}.csv"
    results_df.to_csv(csv_file, index=False)
    
    # Save best
    best = results_df.iloc[0]
    json_file = f"BEST_SIMPLE_params_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump({
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
            }
        }, f, indent=2)
    
    print("\n" + "="*80)
    print("CALIBRATION COMPLETE!")
    print("="*80)
    print(f"\nBest Configuration:")
    print(f"  alpha: {best['alpha']:.1f}")
    print(f"  gamma: {best['gamma']:.1f}")
    print(f"  threshold_low: {best['threshold_low']:.1f}")
    print(f"  Error: {best['error']:.4f}")
    print(f"\n✅ Results saved to: {csv_file}")
    print(f"✅ Best params saved to: {json_file}")

if __name__ == "__main__":
    main()

