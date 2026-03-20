"""
RE-CALIBRATION WITH MOBILE PANTRIES AND DELIVERY
================================================
Now that we've added:
- 3 Real Mobile Pantries (JaxPAL, Bethany Ministries, Paxon Revival)
- Market-Rate Delivery Service (with tuned propensity parameters)

We need to re-calibrate the model to find optimal parameters that account for these new providers.

APPROACH:
---------
Phase 1: Lightweight Grid Search (50 HH, 90 days, 1 seed)
  - Explores parameter space quickly
  - Identifies top 5 candidate parameter sets
  - Estimated time: 30-45 minutes

Phase 2: Full Validation (200 HH, 365 days, 5 seeds)
  - Validates top candidates with full settings
  - Produces dissertation-ready calibrated parameters
  - Estimated time: 20-30 minutes

TOTAL ESTIMATED TIME: 50-75 minutes

CALIBRATION TARGETS:
-------------------
Annual Spending by Income:
  - Low: $2,400 (range: $2,160 - $2,640)
  - Medium: $5,200 (range: $4,680 - $5,720)
  - High: $8,800 (range: $7,920 - $9,680)

Corner Store Share: 3-8% (target: ~5%)

Travel Distance:
  - With car: 5-8 km (target: ~6.5 km)
  - Without car: 1-3 km (target: ~2 km)

Mobile Pantry Usage: 10-15% of low-income households
Delivery Usage: 
  - Low income: 3-5%
  - Medium income: 8-12%
  - High income: 15-25%
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

# ============================================================================
# PHASE 1: LIGHTWEIGHT GRID SEARCH
# ============================================================================

def calculate_calibration_error(metrics, targets):
    """Calculate weighted calibration error"""
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
            # Extrapolate to annual
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

# ============================================================================
# PHASE 2: FULL VALIDATION
# ============================================================================

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

# ============================================================================
# MAIN CALIBRATION
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("RE-CALIBRATION WITH MOBILE PANTRIES AND DELIVERY")
    print("=" * 80)
    print()
    print("Updated Baseline Includes:")
    print("  • 9 Grocery Stores")
    print("  • 11 Corner Stores")
    print("  • 3 Mobile Pantries (JaxPAL, Bethany, Paxon)")
    print("  • 1 Market-Rate Delivery Service")
    print()
    print("=" * 80)
    print()
    
    # Calibration targets
    targets = {
        'spend_low': 2400,
        'spend_med': 5200,
        'spend_high': 8800,
        'corner_share': 0.05,  # 5%
        'dist_car': 6.5,
        'dist_nocar': 2.0
    }
    
    # ========================================================================
    # PHASE 1: LIGHTWEIGHT GRID SEARCH
    # ========================================================================
    
    print("🔍 PHASE 1: LIGHTWEIGHT GRID SEARCH")
    print("=" * 80)
    print("Settings: 50 households, 90 days, 1 seed")
    print("Estimated time: 30-45 minutes")
    print()
    
    # Parameter grid (focused based on previous calibration knowledge)
    param_grid = {
        'alpha': [1.2, 1.5, 1.8],
        'beta': [0.6, 0.8, 1.0],
        'gamma': [0.4, 0.6, 0.8],
        'delta': [0.3, 0.5, 0.7],
        'threshold_low': [0.25, 0.30, 0.35],
        'threshold_med': [0.40, 0.45, 0.50],
        'threshold_high': [0.55, 0.60, 0.65]
    }
    
    # Generate all combinations
    keys = param_grid.keys()
    values = param_grid.values()
    combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
    
    print(f"Total configurations to test: {len(combinations)}")
    print()
    
    results_phase1 = []
    start_time = time.time()
    
    for i, params in enumerate(combinations):
        config_start = time.time()
        
        print(f"[{i+1}/{len(combinations)}] Testing configuration:")
        print(f"  α={params['alpha']:.2f}, β={params['beta']:.2f}, γ={params['gamma']:.2f}, δ={params['delta']:.2f}")
        print(f"  Thresholds: L={params['threshold_low']:.2f}, M={params['threshold_med']:.2f}, H={params['threshold_high']:.2f}")
        
        try:
            metrics = run_lightweight_calibration(
                params['alpha'], params['beta'], params['gamma'], params['delta'],
                params['threshold_low'], params['threshold_med'], params['threshold_high']
            )
            
            error = calculate_calibration_error(metrics, targets)
            
            result = {
                **params,
                **metrics,
                'error': error
            }
            results_phase1.append(result)
            
            config_time = time.time() - config_start
            elapsed = time.time() - start_time
            avg_time = elapsed / (i + 1)
            remaining = avg_time * (len(combinations) - i - 1)
            
            print(f"  ✅ Results: Spend(L=${metrics['avg_spend_low']:.0f}, M=${metrics['avg_spend_med']:.0f}, H=${metrics['avg_spend_high']:.0f})")
            print(f"            Corner={metrics['corner_share']:.1%}, Dist(car={metrics['avg_dist_car']:.2f}, nocar={metrics['avg_dist_nocar']:.2f})")
            print(f"            Pantry={metrics['pantry_usage']:.1%}, Delivery={metrics['delivery_usage']:.1%}")
            print(f"  📊 Calibration Error: {error:.4f}")
            print(f"  ⏱️  Config time: {config_time:.1f}s | Elapsed: {elapsed/60:.1f}min | Remaining: ~{remaining/60:.1f}min")
            print()
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            print()
            continue
    
    # Save Phase 1 results
    df_phase1 = pd.DataFrame(results_phase1)
    df_phase1 = df_phase1.sort_values('error')
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    phase1_file = f"RECALIBRATION_PHASE1_{timestamp}.csv"
    df_phase1.to_csv(phase1_file, index=False)
    
    print("=" * 80)
    print("🎯 PHASE 1 COMPLETE!")
    print("=" * 80)
    print(f"Results saved to: {phase1_file}")
    print()
    print("Top 5 Configurations:")
    print(df_phase1.head(5).to_string())
    print()
    
    # ========================================================================
    # PHASE 2: FULL VALIDATION OF TOP 5
    # ========================================================================
    
    print("=" * 80)
    print("🚀 PHASE 2: FULL VALIDATION OF TOP 5")
    print("=" * 80)
    print("Settings: 200 households, 365 days, 5 seeds")
    print("Estimated time: 20-30 minutes")
    print()
    
    top_5 = df_phase1.head(5)
    results_phase2 = []
    
    for i, row in top_5.iterrows():
        print(f"\n[{i+1}/5] Validating Configuration:")
        print(f"  α={row['alpha']:.2f}, β={row['beta']:.2f}, γ={row['gamma']:.2f}, δ={row['delta']:.2f}")
        print(f"  Thresholds: L={row['threshold_low']:.2f}, M={row['threshold_med']:.2f}, H={row['threshold_high']:.2f}")
        print(f"  Phase 1 Error: {row['error']:.4f}")
        print()
        
        validation_start = time.time()
        
        try:
            metrics = run_full_validation(
                row['alpha'], row['beta'], row['gamma'], row['delta'],
                row['threshold_low'], row['threshold_med'], row['threshold_high'],
                num_seeds=5, num_days=365, num_households=200
            )
            
            error = calculate_calibration_error(metrics, targets)
            
            result = {
                'alpha': row['alpha'],
                'beta': row['beta'],
                'gamma': row['gamma'],
                'delta': row['delta'],
                'threshold_low': row['threshold_low'],
                'threshold_med': row['threshold_med'],
                'threshold_high': row['threshold_high'],
                **metrics,
                'error': error
            }
            results_phase2.append(result)
            
            validation_time = time.time() - validation_start
            
            print(f"\n  ✅ VALIDATION RESULTS (mean ± std across 5 seeds):")
            print(f"     Spend: L=${metrics['avg_spend_low']:.0f}±{metrics['std_spend_low']:.0f}, " +
                  f"M=${metrics['avg_spend_med']:.0f}±{metrics['std_spend_med']:.0f}, " +
                  f"H=${metrics['avg_spend_high']:.0f}±{metrics['std_spend_high']:.0f}")
            print(f"     Corner: {metrics['corner_share']:.1%}±{metrics['std_corner_share']:.2%}")
            print(f"     Distance: car={metrics['avg_dist_car']:.2f}±{metrics['std_dist_car']:.2f}km, " +
                  f"nocar={metrics['avg_dist_nocar']:.2f}±{metrics['std_dist_nocar']:.2f}km")
            print(f"     Pantry Usage: {metrics['pantry_usage']:.1%}")
            print(f"     Delivery Usage: {metrics['delivery_usage']:.1%}")
            print(f"  📊 Final Calibration Error: {error:.4f}")
            print(f"  ⏱️  Validation time: {validation_time/60:.1f} minutes")
            
        except Exception as e:
            print(f"  ❌ Validation failed: {e}")
            continue
    
    # Save Phase 2 results and final calibrated parameters
    df_phase2 = pd.DataFrame(results_phase2)
    df_phase2 = df_phase2.sort_values('error')
    
    phase2_file = f"RECALIBRATION_PHASE2_{timestamp}.csv"
    df_phase2.to_csv(phase2_file, index=False)
    
    # Save best parameters as JSON
    best = df_phase2.iloc[0]
    final_params = {
        'calibration_date': datetime.now().isoformat(),
        'includes_mobile_pantries': True,
        'includes_delivery_service': True,
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
            'corner_share': float(best['corner_share']),
            'avg_dist_car': float(best['avg_dist_car']),
            'avg_dist_nocar': float(best['avg_dist_nocar']),
            'pantry_usage': float(best['pantry_usage']),
            'delivery_usage': float(best['delivery_usage']),
            'calibration_error': float(best['error'])
        },
        'calibration_targets': targets
    }
    
    params_file = f"FINAL_RECALIBRATED_PARAMS_{timestamp}.json"
    with open(params_file, 'w') as f:
        json.dump(final_params, f, indent=2)
    
    print("\n" + "=" * 80)
    print("🎉 CALIBRATION COMPLETE!")
    print("=" * 80)
    print(f"\nPhase 2 results saved to: {phase2_file}")
    print(f"Final parameters saved to: {params_file}")
    print("\n🏆 BEST CALIBRATED PARAMETERS:")
    print(f"   α (distance sensitivity) = {best['alpha']:.2f}")
    print(f"   β (price/budget sensitivity) = {best['beta']:.2f}")
    print(f"   γ (quality/variety weight) = {best['gamma']:.2f}")
    print(f"   δ (convenience weight) = {best['delta']:.2f}")
    print(f"   Thresholds: Low={best['threshold_low']:.2f}, Med={best['threshold_med']:.2f}, High={best['threshold_high']:.2f}")
    print("\n📊 FINAL CALIBRATION RESULTS:")
    print(f"   Annual Spending: Low=${best['avg_spend_low']:.0f} (target: $2,400)")
    print(f"                    Med=${best['avg_spend_med']:.0f} (target: $5,200)")
    print(f"                    High=${best['avg_spend_high']:.0f} (target: $8,800)")
    print(f"   Corner Share: {best['corner_share']:.1%} (target: 5%)")
    print(f"   Travel Distance: Car={best['avg_dist_car']:.2f}km (target: 6.5km)")
    print(f"                    No-car={best['avg_dist_nocar']:.2f}km (target: 2.0km)")
    print(f"   Mobile Pantry Usage: {best['pantry_usage']:.1%}")
    print(f"   Delivery Usage: {best['delivery_usage']:.1%}")
    print(f"   Calibration Error: {best['error']:.4f}")
    print("\n" + "=" * 80)
    print("✅ Model is now calibrated with mobile pantries and delivery service!")
    print("=" * 80)

