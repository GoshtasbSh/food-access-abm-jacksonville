"""
FINAL CALIBRATION - Using Previously Successful Parameter Ranges
But WITH mobile pantries and delivery included

Previous good results (without pantries/delivery):
- α = 2.5, β = 0.7, γ = 1.0, threshold_low = 7.0
- Error = 0.520

Now testing these ranges WITH pantries and delivery to see if we can
achieve similar calibration quality.
"""

import sys
import json
import time
import gc
from datetime import datetime
from itertools import product
from baseline_scenario import create_baseline_scenario
from calibration_framework import run_multi_seed, calculate_calibration_error, CalibrationTargets
from enhanced_mesa_geo_model import SimulationConfig

print("=" * 80)
print("🎯 FINAL CALIBRATION - With Pantries & Delivery")
print("   Using Previously Successful Parameter Ranges")
print("=" * 80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Calibration targets (FROM YOUR TABLE)
targets = CalibrationTargets()
targets.annual_spend_low = 5270.0        
targets.annual_spend_medium = 8989.0     
targets.annual_spend_high = 16996.0      
targets.distance_car = 3.4               
targets.distance_no_car = 1.0            
targets.small_store_share = 0.10         
targets.weekly_frequency_share = 0.40    
targets.subweekly_frequency_share = 0.22 

# GRID SEARCH around YOUR successful parameters
# 3 × 3 × 3 × 3 = 81 configs
param_grid = {
    'alpha': [2.0, 2.5, 3.0],           # Around YOUR 2.5
    'beta': [0.6, 0.7, 0.8],            # Around YOUR 0.7  
    'gamma': [0.8, 1.0, 1.2],           # Around YOUR 1.0
    'threshold_low': [6.0, 7.0, 8.0]    # Around YOUR 7.0
}

param_names = list(param_grid.keys())
param_values = list(param_grid.values())
all_configs = list(product(*param_values))

total_configs = len(all_configs)
print(f"📊 Grid around YOUR successful parameters:")
print(f"   α (distance): {param_grid['alpha']}")
print(f"   β (price): {param_grid['beta']}")
print(f"   γ (quality): {param_grid['gamma']}")
print(f"   Threshold (low): {param_grid['threshold_low']}")
print(f"\n   Total: {' × '.join([str(len(v)) for v in param_values])} = {total_configs} configs")
print(f"⚙️  Settings: 50 HH, 90 days, 1 seed")
print(f"⏱️  Expected time: ~{total_configs * 2 / 60:.0f} minutes (~{total_configs * 2 / 60 / 60:.1f} hours)")
print(f"\n🎯 Goal: Achieve error < 1.0 (YOUR error was 0.520)")
print(f"   Previous best WITHOUT pantries: Error = 0.520")
print(f"   Current best WITH pantries: Error = 3.285")
print(f"   Target: Get closer to 0.520!\n")

# Store results
results = []
best_error = float('inf')
best_params = None

print("🔄 Starting calibration...\n")
print("-" * 80)

for i, config_values in enumerate(all_configs, 1):
    # Create config with this parameter set
    config = SimulationConfig()
    config.num_consumers = 50
    config.simulation_days = 90
    
    # Apply parameters from grid
    alpha, beta, gamma, threshold_low = config_values
    config.alpha_distance = alpha
    config.beta_price_budget = beta
    config.gamma_quality_variety = gamma
    config.go_shop_threshold_low = threshold_low
    
    # Keep other parameters at defaults
    config.delta_convenience = 0.4
    config.go_shop_threshold_medium = 7.0
    config.go_shop_threshold_high = 18.0
    
    # Run simulation
    try:
        start_time = time.time()
        metrics = run_multi_seed(
            config=config,
            num_seeds=1,
            num_days=90,
            parallel=False
        )
        elapsed = time.time() - start_time
        
        # Calculate calibration error
        error, individual_errors = calculate_calibration_error(metrics, targets)
        
        # Store result
        param_dict = {
            'alpha': alpha,
            'beta': beta,
            'gamma': gamma,
            'threshold_low': threshold_low
        }
        result = {
            'config_id': i,
            'parameters': param_dict,
            'metrics': metrics,
            'calibration_error': error,
            'individual_errors': individual_errors,
            'time_seconds': elapsed
        }
        results.append(result)
        
        # Update best
        if error < best_error:
            best_error = error
            best_params = param_dict
            print(f"✨ NEW BEST! Config {i}/{total_configs}: Error = {error:.4f}")
            print(f"   Params: α={alpha:.1f}, β={beta:.1f}, γ={gamma:.1f}, T_low={threshold_low:.1f}")
            print(f"   Spend: Low=${metrics['annual_spend_low']:.0f}, Med=${metrics['annual_spend_medium']:.0f}, High=${metrics['annual_spend_high']:.0f}")
            print(f"   Errors: Low={100*individual_errors['spend_low']:.1f}%, Med={100*individual_errors['spend_medium']:.1f}%, High={100*individual_errors['spend_high']:.1f}%")
            print(f"   Corner: {metrics['small_store_share']:.1%}, Pantry: {metrics.get('pantry_user_share', 0):.1%}\n")
        elif i % 10 == 0:
            print(f"   Progress: {i}/{total_configs} ({100*i/total_configs:.0f}%) - Best so far: {best_error:.4f}")
        
        # Garbage collection
        if i % 10 == 0:
            gc.collect()
            
    except Exception as e:
        print(f"   ❌ Config {i} FAILED: {e}")
        continue

# Sort by error
results.sort(key=lambda x: x['calibration_error'])

print("\n" + "=" * 80)
print("📊 FINAL CALIBRATION COMPLETE")
print("=" * 80)

print(f"\n🏆 BEST CONFIGURATION:\n")
best = results[0]
print(f"Parameters:")
print(f"   α (distance):    {best['parameters']['alpha']:.2f} (YOUR previous: 2.5)")
print(f"   β (price):       {best['parameters']['beta']:.2f} (YOUR previous: 0.7)")
print(f"   γ (quality):     {best['parameters']['gamma']:.2f} (YOUR previous: 1.0)")
print(f"   Threshold (low): {best['parameters']['threshold_low']:.1f} (YOUR previous: 7.0)")
print(f"\nCalibration Error: {best['calibration_error']:.4f}")
print(f"   YOUR previous (no pantries): 0.520")
print(f"   MY previous (with pantries):  3.285")
print(f"   THIS result:                  {best['calibration_error']:.4f}")

if best['calibration_error'] < 1.0:
    print(f"   ✅ EXCELLENT! Better than 1.0!")
elif best['calibration_error'] < 1.5:
    print(f"   ✅ VERY GOOD! Close to YOUR 0.520!")
elif best['calibration_error'] < 2.5:
    print(f"   ⚠️  GOOD - Significantly better than before!")
else:
    print(f"   ⚠️  Still needs improvement")

m = best['metrics']
e = best['individual_errors']

print(f"\n📈 SPENDING RESULTS:")
print(f"   Low-income:    ${m['annual_spend_low']:7.0f} (target: $5,270) - Error: {100*e['spend_low']:6.1f}%")
print(f"   Medium-income: ${m['annual_spend_medium']:7.0f} (target: $8,989) - Error: {100*e['spend_medium']:6.1f}%")
print(f"   High-income:   ${m['annual_spend_high']:7.0f} (target: $16,996) - Error: {100*e['spend_high']:6.1f}%")

print(f"\n📊 OTHER METRICS:")
print(f"   Travel (car):    {m['distance_car_mi']:.2f} mi (target: 3.4 mi)")
print(f"   Travel (no-car): {m['distance_no_car_mi']:.2f} mi (target: 1.0 mi)")
print(f"   Weekly shoppers: {m['weekly_share']:.1%} (target: 40%)")
print(f"   Sub-weekly:      {m['subweekly_share']:.1%} (target: 22%)")
print(f"   Small stores:    {m['small_store_share']:.1%} (target: ≤10%)")
print(f"   Pantry users:    {m.get('pantry_user_share', 0):.1%} (target: 12.5%)")

# Save results
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"FINAL_calibration_with_pantries_{timestamp}.json"

with open(output_file, 'w') as f:
    json.dump({
        'timestamp': timestamp,
        'total_configs': total_configs,
        'targets': {
            'annual_spend_low': targets.annual_spend_low,
            'annual_spend_medium': targets.annual_spend_medium,
            'annual_spend_high': targets.annual_spend_high,
            'distance_car': targets.distance_car,
            'distance_no_car': targets.distance_no_car
        },
        'best_error': best_error,
        'best_params': best_params,
        'previous_best_without_pantries': {
            'error': 0.520,
            'params': {'alpha': 2.5, 'beta': 0.7, 'gamma': 1.0, 'threshold_low': 7.0}
        },
        'top_10': results[:10]
    }, f, indent=2)

print(f"\n💾 Results saved to: {output_file}")
print("\n" + "=" * 80)

