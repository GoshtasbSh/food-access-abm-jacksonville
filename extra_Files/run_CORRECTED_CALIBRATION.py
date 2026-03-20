"""
CORRECTED CALIBRATION WITH REAL TARGET VALUES
==============================================
Using the ACTUAL targets from the user's table:

REAL TARGETS:
- Low-Income Spending: $5,276/year
- Medium-Income Spending: $8,989/year  
- High-Income Spending: $16,996/year
- Corner Store: ≤10% (target 5%)
- Travel (car): 5.5 km
- Travel (no-car): 0.8 km
- Pantry Usage: 12.5%
- Delivery: 3-20% (target ~10%)

STRATEGY:
- Lower α (distance sensitivity) to allow longer travel
- Keep β, γ around previous best values
- Grid: 27 configurations (3^3)
- Time: ~20 minutes total
"""

import sys
import numpy as np
import pandas as pd
from datetime import datetime
import json
import random
import time
import gc
import itertools

sys.path.append('/Users/goshtasbshahriari/Desktop/Code/GeoMesa_Food_Access')

from enhanced_mesa_geo_model import SimulationConfig, IncomeLevel, EnhancedHouseholdAgent
from baseline_scenario import create_baseline_scenario

def calculate_calibration_error(metrics, targets):
    """Calculate weighted calibration error with REAL targets"""
    errors = []
    
    # Spending errors (normalized by target)
    spend_error_low = abs(metrics['avg_spend_low'] - targets['spend_low']) / targets['spend_low']
    spend_error_med = abs(metrics['avg_spend_med'] - targets['spend_med']) / targets['spend_med']
    spend_error_high = abs(metrics['avg_spend_high'] - targets['spend_high']) / targets['spend_high']
    errors.extend([spend_error_low, spend_error_med, spend_error_high])
    
    # Corner share error
    corner_error = abs(metrics['corner_share'] - targets['corner_share']) / targets['corner_share']
    errors.append(corner_error)
    
    # Distance errors
    dist_car_error = abs(metrics['avg_dist_car'] - targets['dist_car']) / targets['dist_car']
    dist_nocar_error = abs(metrics['avg_dist_nocar'] - targets['dist_nocar']) / targets['dist_nocar']
    errors.extend([dist_car_error, dist_nocar_error])
    
    # Pantry usage error
    pantry_error = abs(metrics['pantry_usage'] - targets['pantry_usage']) / targets['pantry_usage']
    errors.append(pantry_error)
    
    return np.mean(errors)

def run_lightweight_calibration(alpha, beta, gamma, delta, threshold_low, threshold_med, threshold_high):
    """Run with lightweight settings: 50 HH, 90 days, 1 seed"""
    
    random.seed(42)
    np.random.seed(42)
    
    config = SimulationConfig(
        num_consumers=50,
        simulation_days=90,
        alpha_distance=alpha,
        beta_price_budget=beta,
        gamma_quality_variety=gamma,
        delta_convenience=delta,
        go_shop_threshold_low=threshold_low,
        go_shop_threshold_medium=threshold_med,
        go_shop_threshold_high=threshold_high
    )
    
    model = create_baseline_scenario(config=config, use_real_data=True)
    
    # Run simulation
    for day in range(90):
        model.step()
    
    # Collect metrics
    households = [a for a in model.schedule.agents if isinstance(a, EnhancedHouseholdAgent)]
    
    # Annual spending (extrapolate from 90 days)
    spend_by_income = {IncomeLevel.LOW: [], IncomeLevel.MEDIUM: [], IncomeLevel.HIGH: []}
    
    for hh in households:
        if len(hh.shopping_history) > 0:
            total_spend = sum(trip.get('basket_cost', trip.get('basket_size', 0)) 
                            for trip in hh.shopping_history)
            annual_spend = total_spend * (365 / 90)
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
    
    # Mobile pantry usage
    pantry_users = sum(1 for hh in households 
                      if any(trip.get('provider_type') == 'pantry' for trip in hh.shopping_history))
    pantry_usage_rate = pantry_users / len(households) if households else 0
    
    # Delivery usage
    delivery_users = sum(1 for hh in households 
                        if any(trip.get('provider_type') == 'delivery' for trip in hh.shopping_history))
    delivery_usage_rate = delivery_users / len(households) if households else 0
    
    # Clean up
    del model
    gc.collect()
    
    return {
        'avg_spend_low': avg_spend_low,
        'avg_spend_med': avg_spend_med,
        'avg_spend_high': avg_spend_high,
        'corner_share': corner_share,
        'avg_dist_car': avg_dist_car,
        'avg_dist_nocar': avg_dist_nocar,
        'pantry_usage': pantry_usage_rate,
        'delivery_usage': delivery_usage_rate
    }

def run_full_validation(alpha, beta, gamma, delta, threshold_low, threshold_med, threshold_high, 
                        num_seeds=5, num_days=365, num_households=200):
    """Run with FULL settings: 200 HH, 365 days, 5 seeds"""
    
    all_metrics = []
    
    for seed in range(num_seeds):
        print(f"    Seed {seed+1}/{num_seeds}...", flush=True)
        
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
            go_shop_threshold_high=threshold_high
        )
        
        model = create_baseline_scenario(config=config, use_real_data=True)
        
        # Run full year
        for day in range(num_days):
            model.step()
            if (day + 1) % 100 == 0:
                print(f"      Day {day+1}/{num_days}", flush=True)
        
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
        
        # Mobile pantry usage
        pantry_users = sum(1 for hh in households 
                          if any(trip.get('provider_type') == 'pantry' for trip in hh.shopping_history))
        pantry_usage_rate = pantry_users / len(households) if households else 0
        
        # Delivery usage
        delivery_users = sum(1 for hh in households 
                            if any(trip.get('provider_type') == 'delivery' for trip in hh.shopping_history))
        delivery_usage_rate = delivery_users / len(households) if households else 0
        
        all_metrics.append({
            'seed': seed,
            'avg_spend_low': avg_spend_low,
            'avg_spend_med': avg_spend_med,
            'avg_spend_high': avg_spend_high,
            'corner_share': corner_share,
            'avg_dist_car': avg_dist_car,
            'avg_dist_nocar': avg_dist_nocar,
            'pantry_usage': pantry_usage_rate,
            'delivery_usage': delivery_usage_rate
        })
        
        # Clean up
        del model
        gc.collect()
    
    # Aggregate across seeds
    df = pd.DataFrame(all_metrics)
    return {
        'avg_spend_low': df['avg_spend_low'].mean(),
        'avg_spend_med': df['avg_spend_med'].mean(),
        'avg_spend_high': df['avg_spend_high'].mean(),
        'corner_share': df['corner_share'].mean(),
        'avg_dist_car': df['avg_dist_car'].mean(),
        'avg_dist_nocar': df['avg_dist_nocar'].mean(),
        'pantry_usage': df['pantry_usage'].mean(),
        'delivery_usage': df['delivery_usage'].mean(),
        'std_spend_low': df['avg_spend_low'].std(),
        'std_spend_med': df['avg_spend_med'].std(),
        'std_spend_high': df['avg_spend_high'].std(),
        'std_corner_share': df['corner_share'].std(),
        'std_dist_car': df['avg_dist_car'].std(),
        'std_dist_nocar': df['avg_dist_nocar'].std()
    }

if __name__ == "__main__":
    print("=" * 80)
    print("CORRECTED CALIBRATION WITH REAL TARGET VALUES")
    print("=" * 80)
    print()
    print("REAL TARGETS (from user's table):")
    print("  • Low-Income Spending: $5,276/year")
    print("  • Medium-Income Spending: $8,989/year")
    print("  • High-Income Spending: $16,996/year")
    print("  • Corner Store Usage: ≤10% (target 5%)")
    print("  • Travel Distance (car): 5.5 km")
    print("  • Travel Distance (no-car): 0.8 km")
    print("  • Pantry Usage: 12.5%")
    print("  • Delivery Usage: 3-20% (target ~10%)")
    print()
    print("=" * 80)
    print()
    
    # CORRECTED TARGETS
    targets = {
        'spend_low': 5276,      # From table
        'spend_med': 8989,      # From table
        'spend_high': 16996,    # From table
        'corner_share': 0.05,   # Target 5% (≤10% tolerance)
        'dist_car': 5.5,        # 5.5 km from table
        'dist_nocar': 0.8,      # 0.8 km from table
        'pantry_usage': 0.125   # 12.5% from table
    }
    
    # CORRECTED parameter grid - Lower α to allow longer travel
    param_grid = {
        'alpha': [0.8, 1.2, 1.6],    # Lower than before (was 2.0-3.0)
        'beta': [0.6, 0.7, 0.8],     # Keep around previous best
        'gamma': [0.8, 1.0, 1.2]     # Keep around previous best
    }
    
    # Fixed parameters
    DELTA = 0.4
    THRESHOLD_LOW = 5.5
    THRESHOLD_MED = 7.0
    THRESHOLD_HIGH = 14.0
    
    # Generate all combinations
    keys = param_grid.keys()
    values = param_grid.values()
    combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
    
    print(f"🔍 PHASE 1: GRID SEARCH WITH CORRECTED TARGETS")
    print("=" * 80)
    print(f"Total configurations: {len(combinations)}")
    print("Settings: 50 HH, 90 days, 1 seed")
    print("Estimated time: 5-8 minutes")
    print()
    
    results_phase1 = []
    start_time = time.time()
    
    for i, params in enumerate(combinations):
        config_start = time.time()
        
        print(f"[{i+1}/{len(combinations)}] α={params['alpha']:.1f}, β={params['beta']:.1f}, γ={params['gamma']:.1f}", end='', flush=True)
        
        try:
            metrics = run_lightweight_calibration(
                params['alpha'], params['beta'], params['gamma'], DELTA,
                THRESHOLD_LOW, THRESHOLD_MED, THRESHOLD_HIGH
            )
            
            error = calculate_calibration_error(metrics, targets)
            
            result = {
                'alpha': params['alpha'],
                'beta': params['beta'],
                'gamma': params['gamma'],
                'delta': DELTA,
                'threshold_low': THRESHOLD_LOW,
                'threshold_med': THRESHOLD_MED,
                'threshold_high': THRESHOLD_HIGH,
                **metrics,
                'error': error
            }
            results_phase1.append(result)
            
            config_time = time.time() - config_start
            
            print(f" → L=${metrics['avg_spend_low']:.0f}, M=${metrics['avg_spend_med']:.0f}, H=${metrics['avg_spend_high']:.0f} | Corner={metrics['corner_share']:.1%} | Dist(car={metrics['avg_dist_car']:.1f}, no={metrics['avg_dist_nocar']:.1f}) | Pantry={metrics['pantry_usage']:.1%} | Err={error:.3f} | {config_time:.1f}s")
            
        except Exception as e:
            print(f" → ❌ Error: {e}")
            continue
    
    total_phase1_time = time.time() - start_time
    
    # Save Phase 1 results
    df_phase1 = pd.DataFrame(results_phase1)
    df_phase1 = df_phase1.sort_values('error')
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    phase1_file = f"CORRECTED_CALIB_PHASE1_{timestamp}.csv"
    df_phase1.to_csv(phase1_file, index=False)
    
    print("\n" + "=" * 80)
    print(f"🎯 PHASE 1 COMPLETE! ({total_phase1_time/60:.1f} minutes)")
    print("=" * 80)
    print(f"Results saved to: {phase1_file}")
    print()
    print("Top 5 Configurations:")
    print(df_phase1[['alpha', 'beta', 'gamma', 'avg_spend_low', 'avg_spend_med', 'avg_spend_high', 'corner_share', 'avg_dist_car', 'pantry_usage', 'error']].head(5).to_string())
    print()
    
    # PHASE 2: Full validation of top 3
    print("=" * 80)
    print("🚀 PHASE 2: FULL VALIDATION OF TOP 3")
    print("=" * 80)
    print("Settings: 200 HH, 365 days, 5 seeds")
    print("Estimated time: 12-15 minutes")
    print()
    
    top_3 = df_phase1.head(3)
    results_phase2 = []
    
    for idx, (i, row) in enumerate(top_3.iterrows()):
        print(f"\n[{idx+1}/3] Validating: α={row['alpha']:.1f}, β={row['beta']:.1f}, γ={row['gamma']:.1f}")
        print(f"           Phase 1 Error: {row['error']:.4f}")
        print()
        
        validation_start = time.time()
        
        try:
            metrics = run_full_validation(
                row['alpha'], row['beta'], row['gamma'], DELTA,
                THRESHOLD_LOW, THRESHOLD_MED, THRESHOLD_HIGH,
                num_seeds=5, num_days=365, num_households=200
            )
            
            error = calculate_calibration_error(metrics, targets)
            
            result = {
                'alpha': row['alpha'],
                'beta': row['beta'],
                'gamma': row['gamma'],
                'delta': DELTA,
                'threshold_low': THRESHOLD_LOW,
                'threshold_med': THRESHOLD_MED,
                'threshold_high': THRESHOLD_HIGH,
                **metrics,
                'error': error
            }
            results_phase2.append(result)
            
            validation_time = time.time() - validation_start
            
            print(f"\n  ✅ VALIDATION COMPLETE:")
            print(f"     Spend: L=${metrics['avg_spend_low']:.0f}±{metrics['std_spend_low']:.0f} (target: $5,276)")
            print(f"            M=${metrics['avg_spend_med']:.0f}±{metrics['std_spend_med']:.0f} (target: $8,989)")
            print(f"            H=${metrics['avg_spend_high']:.0f}±{metrics['std_spend_high']:.0f} (target: $16,996)")
            print(f"     Corner: {metrics['corner_share']:.1%}±{metrics['std_corner_share']:.2%} (target: 5%)")
            print(f"     Distance: car={metrics['avg_dist_car']:.2f}±{metrics['std_dist_car']:.2f}km (target: 5.5km)")
            print(f"               nocar={metrics['avg_dist_nocar']:.2f}±{metrics['std_dist_nocar']:.2f}km (target: 0.8km)")
            print(f"     Pantry: {metrics['pantry_usage']:.1%} (target: 12.5%)")
            print(f"     Delivery: {metrics['delivery_usage']:.1%} (target: 3-20%)")
            print(f"     Error: {error:.4f} | Time: {validation_time/60:.1f}min")
            
        except Exception as e:
            print(f"  ❌ Validation failed: {e}")
            continue
    
    # Save Phase 2 results and best parameters
    df_phase2 = pd.DataFrame(results_phase2)
    df_phase2 = df_phase2.sort_values('error')
    
    phase2_file = f"CORRECTED_CALIB_PHASE2_{timestamp}.csv"
    df_phase2.to_csv(phase2_file, index=False)
    
    # Save best parameters as JSON
    best = df_phase2.iloc[0]
    final_params = {
        'calibration_date': datetime.now().isoformat(),
        'calibrated_with_correct_targets': True,
        'includes_mobile_pantries': True,
        'includes_delivery_service': True,
        'targets_used': targets,
        'parameters': {
            'alpha_distance': float(best['alpha']),
            'beta_price_budget': float(best['beta']),
            'gamma_quality_variety': float(best['gamma']),
            'delta_convenience': float(best['delta']),
            'go_shop_threshold_low': float(best['threshold_low']),
            'go_shop_threshold_medium': float(best['threshold_med']),
            'go_shop_threshold_high': float(best['threshold_high'])
        },
        'calibration_results': {
            'avg_spend_low': float(best['avg_spend_low']),
            'avg_spend_med': float(best['avg_spend_med']),
            'avg_spend_high': float(best['avg_spend_high']),
            'std_spend_low': float(best['std_spend_low']),
            'std_spend_med': float(best['std_spend_med']),
            'std_spend_high': float(best['std_spend_high']),
            'corner_share': float(best['corner_share']),
            'std_corner_share': float(best['std_corner_share']),
            'avg_dist_car': float(best['avg_dist_car']),
            'avg_dist_nocar': float(best['avg_dist_nocar']),
            'std_dist_car': float(best['std_dist_car']),
            'std_dist_nocar': float(best['std_dist_nocar']),
            'pantry_usage': float(best['pantry_usage']),
            'delivery_usage': float(best['delivery_usage']),
            'calibration_error': float(best['error'])
        }
    }
    
    params_file = f"FINAL_CORRECTED_CALIBRATED_PARAMS_{timestamp}.json"
    with open(params_file, 'w') as f:
        json.dump(final_params, f, indent=2)
    
    print("\n" + "=" * 80)
    print("🎉 CORRECTED CALIBRATION COMPLETE!")
    print("=" * 80)
    print(f"\nResults saved to: {phase2_file}")
    print(f"Parameters saved to: {params_file}")
    print("\n🏆 BEST CALIBRATED PARAMETERS:")
    print(f"   α (distance) = {best['alpha']:.2f}")
    print(f"   β (price/budget) = {best['beta']:.2f}")
    print(f"   γ (quality) = {best['gamma']:.2f}")
    print(f"   δ (convenience) = {best['delta']:.2f}")
    print(f"   Thresholds: L={best['threshold_low']:.1f}, M={best['threshold_med']:.1f}, H={best['threshold_high']:.1f}")
    print("\n📊 FINAL RESULTS vs REAL TARGETS:")
    print(f"   Spending:")
    print(f"     Low:    ${best['avg_spend_low']:.0f} ± ${best['std_spend_low']:.0f} (target: $5,276)")
    print(f"     Medium: ${best['avg_spend_med']:.0f} ± ${best['std_spend_med']:.0f} (target: $8,989)")
    print(f"     High:   ${best['avg_spend_high']:.0f} ± ${best['std_spend_high']:.0f} (target: $16,996)")
    print(f"   Corner Share: {best['corner_share']:.1%} ± {best['std_corner_share']:.2%} (target: ≤10%)")
    print(f"   Travel Distance:")
    print(f"     Car:    {best['avg_dist_car']:.2f} ± {best['std_dist_car']:.2f} km (target: 5.5 km)")
    print(f"     No-car: {best['avg_dist_nocar']:.2f} ± {best['std_dist_nocar']:.2f} km (target: 0.8 km)")
    print(f"   Pantry Usage: {best['pantry_usage']:.1%} (target: 12.5%)")
    print(f"   Delivery Usage: {best['delivery_usage']:.1%} (target: 3-20%)")
    print(f"   Calibration Error: {best['error']:.4f}")
    print("\n" + "=" * 80)

