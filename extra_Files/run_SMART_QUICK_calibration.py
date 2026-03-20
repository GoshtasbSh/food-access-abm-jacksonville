"""
SMART QUICK CALIBRATION - Tune ALL THREE Shopping Thresholds
Tests a focused grid to control spending for ALL income groups

Key Insight: We need to control shopping frequency for EACH income group separately!
- threshold_low → controls low-income spending
- threshold_medium → controls medium-income spending  
- threshold_high → controls high-income spending
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
print("🎯 SMART QUICK CALIBRATION - All Three Thresholds")
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

# SMART GRID: Tune the things that matter for spending
# 2 alpha × 2 gamma × 2 threshold_low × 2 threshold_medium × 2 threshold_high = 32 configs
param_grid = {
    'alpha': [1.0, 1.2],                    # Distance weight
    'gamma': [0.6, 0.8],                    # Quality weight
    'threshold_low': [3.0, 4.0],            # Low-income: currently underspending → reduce frequency
    'threshold_medium': [6.0, 7.0],         # Medium-income: perfect → keep similar
    'threshold_high': [18.0, 24.0]          # High-income: OVERSPENDING → reduce frequency!
}

param_names = list(param_grid.keys())
param_values = list(param_grid.values())
all_configs = list(product(*param_values))

total_configs = len(all_configs)
print(f"📊 SMART Grid: {' × '.join([str(len(v)) for v in param_values])} = {total_configs} configs")
print(f"⚙️  Settings: 50 HH, 90 days, 1 seed")
print(f"⏱️  Expected time: ~{total_configs * 2 / 60:.0f} minutes")
print(f"\n🎯 Key Strategy:")
print(f"   - Increase threshold_low (3→4 days): Low-income shops LESS often")
print(f"   - Keep threshold_medium (6-7 days): Medium is already good")
print(f"   - Increase threshold_high (18-24 days): High-income shops MUCH less")
print(f"\n🔍 Expected Impact:")
print(f"   - Low-income: -18% → closer to target (shop less = spend less)")
print(f"   - Medium: +2% → stay perfect")
print(f"   - High-income: +43% → bring down to target (shop less!)\n")

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
    alpha, gamma, threshold_low, threshold_medium, threshold_high = config_values
    config.alpha_distance = alpha
    config.gamma_quality_variety = gamma
    config.go_shop_threshold_low = threshold_low
    config.go_shop_threshold_medium = threshold_medium
    config.go_shop_threshold_high = threshold_high
    
    # Keep other parameters at defaults
    config.beta_price_budget = 1.0
    config.delta_convenience = 0.4
    
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
            'gamma': gamma,
            'threshold_low': threshold_low,
            'threshold_medium': threshold_medium,
            'threshold_high': threshold_high
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
            print(f"   Params: α={alpha:.1f}, γ={gamma:.1f}, T_low={threshold_low:.1f}, T_med={threshold_medium:.1f}, T_high={threshold_high:.1f}")
            print(f"   Spend: Low=${metrics['annual_spend_low']:.0f}, Med=${metrics['annual_spend_medium']:.0f}, High=${metrics['annual_spend_high']:.0f}")
            print(f"   Errors: Low={100*individual_errors['spend_low']:.1f}%, Med={100*individual_errors['spend_medium']:.1f}%, High={100*individual_errors['spend_high']:.1f}%\n")
        elif i % 5 == 0:
            print(f"   Progress: {i}/{total_configs} ({100*i/total_configs:.0f}%) - Current error: {error:.4f}")
        
        # Garbage collection
        if i % 5 == 0:
            gc.collect()
            
    except Exception as e:
        print(f"   ❌ Config {i} FAILED: {e}")
        continue

# Sort by error
results.sort(key=lambda x: x['calibration_error'])

print("\n" + "=" * 80)
print("📊 SMART CALIBRATION COMPLETE")
print("=" * 80)

print(f"\n🏆 BEST CONFIGURATION:\n")
best = results[0]
print(f"Parameters: {best['parameters']}")
print(f"Total Error: {best['calibration_error']:.4f}")

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

# Save results
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"SMART_QUICK_results_{timestamp}.json"

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
        'top_5': results[:5]
    }, f, indent=2)

print(f"\n💾 Results saved to: {output_file}")

print("\n" + "=" * 80)
print("🎯 RECOMMENDATION:")
if best_error < 2.0:
    print("   ✅ EXCELLENT! Error < 2.0")
    print("   → Use these parameters for scenario analysis!")
elif best_error < 2.5:
    print("   ✅ GOOD! Error < 2.5")
    print("   → Can proceed with full calibration or use these parameters")
elif best_error < 3.0:
    print("   ⚠️  ACCEPTABLE. Error < 3.0")
    print("   → Consider running full grid search for refinement")
else:
    print("   ⚠️  MODERATE. Error > 3.0")
    print("   → May need to adjust approach or relax some constraints")
print("=" * 80)

