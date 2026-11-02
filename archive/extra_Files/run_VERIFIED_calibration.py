"""
FINAL VERIFIED CALIBRATION RUN
Date: November 24, 2025

All critical fixes applied and verified:
- Delivery parameters corrected (8%, 20%, 35%)
- Mobile pantry schedules set to real monthly data
- Utility boosts for pantries implemented
- Basket size income multipliers added
- All scenarios verified

This script runs a focused grid search to find optimal parameters.
"""

import sys
import json
import time
import gc
from datetime import datetime
from itertools import product
from baseline_scenario import create_baseline_scenario
from calibration_framework import run_multi_seed, calculate_calibration_error
from enhanced_mesa_geo_model import SimulationConfig

# ============================================================================
# CALIBRATION TARGETS (From USDA ERS Food Expenditure Series)
# ============================================================================
TARGETS = {
    'annual_spend_low': 5254.0,      # <$25K: $101/week
    'annual_spend_medium': 9004.0,   # $25K-$99K: $173/week
    'annual_spend_high': 17004.0,    # ≥$100K: $327/week
    'corner_share': 0.08,            # ~8% of spending at corner stores (after Idea #1)
    'avg_distance_car': 5.0,         # ~3.1 miles with car
    'avg_distance_no_car': 2.8,      # ~1.7 miles without car
    'pantry_prevalence': 0.035,      # 3.5% realistic (monthly availability)
    'delivery_low': 0.04,            # 4% for low income
    'delivery_medium': 0.10,         # 10% for medium income
    'delivery_high': 0.18            # 18% for high income
}

# ============================================================================
# PHASE 1: FOCUSED GRID SEARCH
# ============================================================================
print("=" * 80)
print("🎯 FINAL VERIFIED CALIBRATION - PHASE 1: FOCUSED GRID SEARCH")
print("=" * 80)
print(f"\n📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Parameter ranges (focused around expected good values)
param_grid = {
    'alpha_distance': [0.8, 1.0, 1.2],
    'beta_price_budget': [0.6, 0.8, 1.0],
    'gamma_quality_variety': [0.4, 0.6, 0.8],
    'go_shop_threshold_low': [2.0, 2.5, 3.0],
    'go_shop_threshold_medium': [5.5, 6.5, 7.5],
    'go_shop_threshold_high': [12.0, 14.0, 16.0]
}

# Generate all combinations
param_names = list(param_grid.keys())
param_values = list(param_grid.values())
all_configs = list(product(*param_values))

total_configs = len(all_configs)
print(f"📊 Total configurations to test: {total_configs}")
print(f"⚙️  Phase 1 Settings:")
print(f"   - Households: 50")
print(f"   - Days: 90")
print(f"   - Seeds: 1")
print(f"   - Expected time: ~{total_configs * 2 / 60:.1f} hours\n")

# Phase 1 simulation settings (lightweight for exploration)
phase1_config = SimulationConfig()
phase1_config.num_consumers = 50
phase1_config.simulation_days = 90

# Store results
results = []
best_error = float('inf')
best_params = None

print("🔄 Starting grid search...\n")
print("-" * 80)

for i, config_values in enumerate(all_configs, 1):
    # Create config with this parameter set
    config = SimulationConfig()
    config.num_consumers = 50
    config.simulation_days = 90
    
    # Apply parameters from grid
    for param_name, param_value in zip(param_names, config_values):
        setattr(config, param_name, param_value)
    
    # Run simulation
    try:
        start_time = time.time()
        metrics = run_multi_seed(
            config=config,
            num_seeds=1,
            num_days=90,
            parallel=False  # Sequential to avoid sandbox issues
        )
        elapsed = time.time() - start_time
        
        # Calculate calibration error
        error = calculate_calibration_error(metrics, TARGETS)
        
        # Store result
        param_dict = {name: value for name, value in zip(param_names, config_values)}
        result = {
            'config_id': i,
            'parameters': param_dict,
            'metrics': metrics,
            'calibration_error': error,
            'time_seconds': elapsed
        }
        results.append(result)
        
        # Update best
        if error < best_error:
            best_error = error
            best_params = param_dict
            print(f"✨ NEW BEST! Config {i}/{total_configs}: Error = {error:.4f}")
            print(f"   Params: {param_dict}")
            print(f"   Spend (L/M/H): ${metrics['annual_spend_low']:.0f}/${metrics['annual_spend_medium']:.0f}/${metrics['annual_spend_high']:.0f}")
            print(f"   Corner share: {metrics['corner_share']:.1%}, Pantry: {metrics['pantry_prevalence']:.1%}")
            print(f"   Delivery (L/M/H): {metrics.get('delivery_low', 0):.1%}/{metrics.get('delivery_medium', 0):.1%}/{metrics.get('delivery_high', 0):.1%}\n")
        elif i % 50 == 0:
            print(f"   Progress: {i}/{total_configs} configs ({100*i/total_configs:.1f}%) - Current error: {error:.4f}")
        
        # Aggressive garbage collection
        if i % 10 == 0:
            gc.collect()
            
    except Exception as e:
        print(f"   ❌ Config {i} FAILED: {e}")
        continue

# ============================================================================
# SAVE PHASE 1 RESULTS
# ============================================================================
print("\n" + "=" * 80)
print("📊 PHASE 1 COMPLETE - RESULTS SUMMARY")
print("=" * 80)

# Sort by calibration error
results.sort(key=lambda x: x['calibration_error'])

print(f"\n🏆 TOP 10 CONFIGURATIONS:\n")
for i, result in enumerate(results[:10], 1):
    print(f"{i}. Error: {result['calibration_error']:.4f}")
    print(f"   Parameters: {result['parameters']}")
    m = result['metrics']
    print(f"   Spend (L/M/H): ${m['annual_spend_low']:.0f}/${m['annual_spend_medium']:.0f}/${m['annual_spend_high']:.0f}")
    print(f"   Corner: {m['corner_share']:.1%}, Pantry: {m['pantry_prevalence']:.1%}, Delivery: {m.get('delivery_low', 0):.1%}\n")

# Save to file
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"PHASE1_calibration_results_{timestamp}.json"

with open(output_file, 'w') as f:
    json.dump({
        'phase': 1,
        'timestamp': timestamp,
        'total_configs': total_configs,
        'targets': TARGETS,
        'best_error': best_error,
        'best_params': best_params,
        'top_10': results[:10],
        'all_results': results
    }, f, indent=2)

print(f"💾 Results saved to: {output_file}")
print(f"✅ Best calibration error: {best_error:.4f}")
print(f"✅ Best parameters: {best_params}\n")

print("=" * 80)
print("🎯 NEXT STEP: Review results, then run Phase 2 validation with top configs")
print("=" * 80)

