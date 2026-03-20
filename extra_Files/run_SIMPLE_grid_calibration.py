"""
SIMPLE GRID SEARCH CALIBRATION
Uses existing calibration_framework.grid_search_calibration()

All fixes verified:
- Delivery: 8%, 20%, 35%
- Pantries: Monthly (real data)
- Utility boosts: +10-18 for pantries
- Basket multipliers: 0.5, 0.85, 1.3
"""

from calibration_framework import grid_search_calibration, CalibrationTargets
from datetime import datetime

print("=" * 80)
print("🎯 SIMPLIFIED GRID SEARCH CALIBRATION")
print("=" * 80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Define calibration targets (FROM YOUR TABLE)
targets = CalibrationTargets()
targets.annual_spend_low = 5270.0        # USD/year (USDA ERS 2023)
targets.annual_spend_medium = 8989.0     # USD/year (USDA ERS 2023)
targets.annual_spend_high = 16996.0      # USD/year (USDA ERS 2023)
targets.distance_car = 3.4               # miles (5.5 km) - USDA ERS 2015
targets.distance_no_car = 1.0            # miles (1.6 km) - YOU SPECIFIED 1 mile
targets.small_store_share = 0.10         # ≤10% of trips (hard constraint)
targets.weekly_frequency_share = 0.40    # 40% shop weekly (Consumer surveys)
targets.subweekly_frequency_share = 0.22 # 22% shop sub-weekly (Consumer surveys)

# Define parameter grid (FOCUSED)
alpha_values = [0.8, 1.0, 1.2]  # Distance weight
gamma_values = [0.4, 0.6, 0.8]  # Quality/variety weight
threshold_low_values = [2.0, 2.5, 3.0]  # Low-income go-shop threshold

print(f"📊 Grid: {len(alpha_values)} × {len(gamma_values)} × {len(threshold_low_values)} = {len(alpha_values)*len(gamma_values)*len(threshold_low_values)} configs")
print(f"⚙️  Settings: 50 HH, 90 days, 1 seed")
print(f"⏱️  Expected time: ~3-4 hours\n")

# Run grid search
results_df = grid_search_calibration(
    alpha_values=alpha_values,
    gamma_values=gamma_values,
    threshold_low_values=threshold_low_values,
    targets=targets,
    num_seeds=1,  # Phase 1: quick exploration
    num_days=90,
    num_consumers=50  # CRITICAL: Memory-efficient (not 500!)
)

# Save results
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"grid_calibration_results_{timestamp}.csv"
results_df.to_csv(output_file, index=False)

print("\n" + "=" * 80)
print("✅ CALIBRATION COMPLETE")
print("=" * 80)
print(f"💾 Results saved to: {output_file}")
print(f"\n🏆 TOP 5 CONFIGURATIONS:\n")
print(results_df.head(5).to_string())
print("\n" + "=" * 80)

