"""
RUN ALL SCENARIOS WITH CALIBRATED PARAMETERS
=============================================
Runs Baseline + Scenarios 1-4 using the calibrated parameters loaded
automatically from the most recent FINAL_CALIBRATED_PARAMS_*.json.

Settings:
- 200 households (full population from HZ1 census)
- 365 days (full year)
- 5 seeds (robustness check)
- Mean ± std for all metrics
"""

import sys
import json
import time
import gc
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List

from enhanced_mesa_geo_model import SimulationConfig, IncomeLevel, EnhancedHouseholdAgent, get_calibrated_params
from baseline_scenario import create_baseline_scenario
from enhanced_scenario_1 import create_enhanced_scenario_1
from enhanced_scenario_2 import create_enhanced_scenario_2
from enhanced_scenario_3 import create_enhanced_scenario_3
from enhanced_scenario_4 import create_enhanced_scenario_4


def run_scenario_with_seeds(scenario_name: str, create_func, num_seeds: int = 5, num_days: int = 365):
    """
    Run a scenario with multiple seeds and collect metrics
    
    Args:
        scenario_name: Name of the scenario
        create_func: Function to create the scenario model
        num_seeds: Number of random seeds to run
        num_days: Number of simulation days
        
    Returns:
        Dictionary with mean, std, and individual seed results
    """
    print(f"\n{'='*80}")
    print(f"RUNNING: {scenario_name}")
    print(f"{'='*80}")
    print(f"Settings: {num_seeds} seeds × {num_days} days")
    print("")
    
    all_metrics = []
    
    for seed in range(num_seeds):
        print(f"  Seed {seed+1}/{num_seeds}...", flush=True)
        seed_start = time.time()
        
        # Create config (will use calibrated defaults)
        config = SimulationConfig()
        config.num_consumers = 200
        config.simulation_days = num_days
        
        # Set seed
        import random
        random.seed(seed)
        np.random.seed(seed)
        
        # Create model
        model = create_func(config=config)
        
        # Run simulation
        for day in range(num_days):
            model.step()
            if (day + 1) % 100 == 0:
                print(f"    Day {day+1}/{num_days}", flush=True)
        
        # Collect metrics
        households = [a for a in model.schedule.agents if isinstance(a, EnhancedHouseholdAgent)]
        
        # Annual spending by income
        spend_by_income = {IncomeLevel.LOW: [], IncomeLevel.MEDIUM: [], IncomeLevel.HIGH: []}
        satisfied_by_income = {IncomeLevel.LOW: [], IncomeLevel.MEDIUM: [], IncomeLevel.HIGH: []}
        
        for hh in households:
            if len(hh.shopping_history) > 0:
                total_spend = sum(trip.get('basket_cost', trip.get('basket_size', 0)) 
                                for trip in hh.shopping_history)
                spend_by_income[hh.income].append(total_spend)
                
                # Calculate satisfaction
                satisfied_days = sum(1 for trip in hh.shopping_history if trip.get('satisfied', True))
                satisfaction = satisfied_days / len(hh.shopping_history) if len(hh.shopping_history) > 0 else 0
                satisfied_by_income[hh.income].append(satisfaction)
        
        avg_spend_low = np.mean(spend_by_income[IncomeLevel.LOW]) if spend_by_income[IncomeLevel.LOW] else 0
        avg_spend_med = np.mean(spend_by_income[IncomeLevel.MEDIUM]) if spend_by_income[IncomeLevel.MEDIUM] else 0
        avg_spend_high = np.mean(spend_by_income[IncomeLevel.HIGH]) if spend_by_income[IncomeLevel.HIGH] else 0
        
        avg_sat_low = np.mean(satisfied_by_income[IncomeLevel.LOW]) if satisfied_by_income[IncomeLevel.LOW] else 0
        avg_sat_med = np.mean(satisfied_by_income[IncomeLevel.MEDIUM]) if satisfied_by_income[IncomeLevel.MEDIUM] else 0
        avg_sat_high = np.mean(satisfied_by_income[IncomeLevel.HIGH]) if satisfied_by_income[IncomeLevel.HIGH] else 0
        
        # Store types
        store_type_counts = {}
        for hh in households:
            for trip in hh.shopping_history:
                store_type = trip.get('provider_type', 'unknown')
                store_type_counts[store_type] = store_type_counts.get(store_type, 0) + 1
        
        total_trips = sum(store_type_counts.values())
        corner_trips = store_type_counts.get('corner_store', 0)
        pantry_trips = (store_type_counts.get('mobile_pantry', 0) + 
                       store_type_counts.get('pantry', 0) + 
                       store_type_counts.get('food_hub', 0))
        
        corner_share = corner_trips / total_trips if total_trips > 0 else 0
        pantry_share = pantry_trips / total_trips if total_trips > 0 else 0
        
        # Travel distance (use 'travel_distance' = 0 for delivery, actual km for physical trips)
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
        
        # Food insecurity (% of HH with low satisfaction)
        food_insecure = sum(1 for hh in households 
                           if np.mean([trip.get('satisfied', True) for trip in hh.shopping_history]) < 0.7)
        food_insecurity_rate = food_insecure / len(households) if len(households) > 0 else 0
        
        seed_time = time.time() - seed_start
        
        metrics = {
            'seed': seed,
            'spend_low': avg_spend_low,
            'spend_med': avg_spend_med,
            'spend_high': avg_spend_high,
            'satisfaction_low': avg_sat_low,
            'satisfaction_med': avg_sat_med,
            'satisfaction_high': avg_sat_high,
            'corner_share': corner_share,
            'pantry_share': pantry_share,
            'distance_car_km': avg_dist_car,
            'distance_nocar_km': avg_dist_nocar,
            'food_insecurity_rate': food_insecurity_rate,
            'total_trips': total_trips,
            'time_seconds': seed_time
        }
        
        all_metrics.append(metrics)
        
        print(f"    ✓ Seed {seed+1} done in {seed_time:.1f}s", flush=True)
        print(f"      Spend: L=${avg_spend_low:.0f} M=${avg_spend_med:.0f} H=${avg_spend_high:.0f}", flush=True)
        print(f"      Satisfaction: L={avg_sat_low:.1%} M={avg_sat_med:.1%} H={avg_sat_high:.1%}", flush=True)
        print(f"      Corner: {corner_share:.1%}, Pantry: {pantry_share:.1%}", flush=True)
        
        # Clean up
        del model
        del households
        gc.collect()
    
    # Calculate statistics across seeds
    results = {}
    for key in ['spend_low', 'spend_med', 'spend_high', 
                'satisfaction_low', 'satisfaction_med', 'satisfaction_high',
                'corner_share', 'pantry_share', 
                'distance_car_km', 'distance_nocar_km',
                'food_insecurity_rate', 'total_trips']:
        values = [m[key] for m in all_metrics]
        results[f'{key}_mean'] = np.mean(values)
        results[f'{key}_std'] = np.std(values)
    
    results['seed_data'] = all_metrics
    results['scenario_name'] = scenario_name
    
    print(f"\n  📊 SUMMARY (mean ± std):")
    print(f"    Spending:")
    print(f"      Low:    ${results['spend_low_mean']:.0f} ± ${results['spend_low_std']:.0f}")
    print(f"      Medium: ${results['spend_med_mean']:.0f} ± ${results['spend_med_std']:.0f}")
    print(f"      High:   ${results['spend_high_mean']:.0f} ± ${results['spend_high_std']:.0f}")
    print(f"    Satisfaction:")
    print(f"      Low:    {results['satisfaction_low_mean']:.1%} ± {results['satisfaction_low_std']:.1%}")
    print(f"      Medium: {results['satisfaction_med_mean']:.1%} ± {results['satisfaction_med_std']:.1%}")
    print(f"      High:   {results['satisfaction_high_mean']:.1%} ± {results['satisfaction_high_std']:.1%}")
    print(f"    Food Insecurity: {results['food_insecurity_rate_mean']:.1%} ± {results['food_insecurity_rate_std']:.1%}")
    print(f"    Corner Share: {results['corner_share_mean']:.1%} ± {results['corner_share_std']:.1%}")
    print(f"    Pantry Share: {results['pantry_share_mean']:.1%} ± {results['pantry_share_std']:.1%}")
    
    return results


def main():
    """Run all scenarios with calibrated parameters"""
    
    cal = get_calibrated_params()
    ref_config = SimulationConfig()

    print("="*80)
    print("COMPREHENSIVE SCENARIO ANALYSIS")
    print("Using Calibrated Parameters (auto-loaded from JSON)")
    print("="*80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nCALIBRATED PARAMETERS (loaded {'from JSON' if cal else 'defaults'}):")
    print(f"  α (distance):         {ref_config.alpha_distance}")
    print(f"  β (price/budget):     {ref_config.beta_price_budget}")
    print(f"  γ (quality):          {ref_config.gamma_quality_variety}")
    print(f"  δ (convenience):      {ref_config.delta_convenience}")
    print(f"  Threshold (low):      {ref_config.go_shop_threshold_low}")
    print(f"  Threshold (medium):   {ref_config.go_shop_threshold_medium}")
    print(f"  Threshold (high):     {ref_config.go_shop_threshold_high}")
    print("\nSETTINGS:")
    print("  • 200 households (real HZ1 census data)")
    print("  • 365 days (full year)")
    print("  • 5 seeds (robustness check)")
    print("\nSCENARIOS:")
    print("  1. Baseline (existing stores + 3 mobile pantries + delivery)")
    print("  2. Scenario 1: New Grocery Store")
    print("  3. Scenario 2: Food Hub + Corner Store Network")
    print("  4. Scenario 3: Additional Mobile Pantries")
    print("  5. Scenario 4: Subsidized Delivery Service")
    print("\nEstimated time: ~15-20 minutes per scenario × 5 = 75-100 minutes total")
    print("="*80)
    
    start_time = time.time()
    all_results = []
    
    # Define scenarios
    scenarios = [
        ("Baseline", create_baseline_scenario),
        ("Scenario 1: New Grocery Store", create_enhanced_scenario_1),
        ("Scenario 2: Food Hub Network", create_enhanced_scenario_2),
        ("Scenario 3: Mobile Pantries", create_enhanced_scenario_3),
        ("Scenario 4: Subsidized Delivery", create_enhanced_scenario_4)
    ]
    
    # Run each scenario
    for scenario_name, create_func in scenarios:
        try:
            results = run_scenario_with_seeds(scenario_name, create_func, num_seeds=5, num_days=365)
            all_results.append(results)
        except Exception as e:
            print(f"\n  ❌ ERROR in {scenario_name}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    total_time = time.time() - start_time
    
    # Save results
    print("\n" + "="*80)
    print("ALL SCENARIOS COMPLETE!")
    print("="*80)
    print(f"Total time: {total_time/60:.1f} minutes ({total_time/3600:.2f} hours)")
    
    # Create comparison table
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save detailed results
    json_file = f"ALL_SCENARIOS_RESULTS_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump({
            'calibrated_parameters': {
                'alpha_distance': ref_config.alpha_distance,
                'beta_price_budget': ref_config.beta_price_budget,
                'gamma_quality_variety': ref_config.gamma_quality_variety,
                'delta_convenience': ref_config.delta_convenience,
                'go_shop_threshold_low': ref_config.go_shop_threshold_low,
                'go_shop_threshold_medium': ref_config.go_shop_threshold_medium,
                'go_shop_threshold_high': ref_config.go_shop_threshold_high,
            },
            'simulation_settings': {
                'num_households': 200,
                'num_days': 365,
                'num_seeds': 5
            },
            'scenarios': all_results,
            'total_time_hours': total_time / 3600,
            'timestamp': timestamp
        }, f, indent=2)
    
    # Create comparison CSV
    comparison_data = []
    for result in all_results:
        row = {
            'Scenario': result['scenario_name'],
            'Spend_Low_Mean': result['spend_low_mean'],
            'Spend_Low_Std': result['spend_low_std'],
            'Spend_Med_Mean': result['spend_med_mean'],
            'Spend_Med_Std': result['spend_med_std'],
            'Spend_High_Mean': result['spend_high_mean'],
            'Spend_High_Std': result['spend_high_std'],
            'Satisfaction_Low_Mean': result['satisfaction_low_mean'],
            'Satisfaction_Low_Std': result['satisfaction_low_std'],
            'Satisfaction_Med_Mean': result['satisfaction_med_mean'],
            'Satisfaction_Med_Std': result['satisfaction_med_std'],
            'Satisfaction_High_Mean': result['satisfaction_high_mean'],
            'Satisfaction_High_Std': result['satisfaction_high_std'],
            'Food_Insecurity_Mean': result['food_insecurity_rate_mean'],
            'Food_Insecurity_Std': result['food_insecurity_rate_std'],
            'Corner_Share_Mean': result['corner_share_mean'],
            'Corner_Share_Std': result['corner_share_std'],
            'Pantry_Share_Mean': result['pantry_share_mean'],
            'Pantry_Share_Std': result['pantry_share_std'],
            'Distance_Car_Mean': result['distance_car_km_mean'],
            'Distance_Car_Std': result['distance_car_km_std'],
            'Distance_NoCar_Mean': result['distance_nocar_km_mean'],
            'Distance_NoCar_Std': result['distance_nocar_km_std']
        }
        comparison_data.append(row)
    
    csv_file = f"ALL_SCENARIOS_COMPARISON_{timestamp}.csv"
    pd.DataFrame(comparison_data).to_csv(csv_file, index=False)
    
    print(f"\n✅ RESULTS SAVED:")
    print(f"  {json_file}")
    print(f"  {csv_file}")
    
    print("\n📊 QUICK COMPARISON:")
    print("\nFood Insecurity Rate (lower is better):")
    for result in all_results:
        print(f"  {result['scenario_name']:35s}: {result['food_insecurity_rate_mean']:.1%} ± {result['food_insecurity_rate_std']:.1%}")
    
    print("\nOverall Satisfaction (Low-Income, higher is better):")
    for result in all_results:
        print(f"  {result['scenario_name']:35s}: {result['satisfaction_low_mean']:.1%} ± {result['satisfaction_low_std']:.1%}")
    
    print("\n" + "="*80)
    print("🎓 DISSERTATION-READY SCENARIO ANALYSIS COMPLETE!")
    print("="*80)


if __name__ == "__main__":
    main()

