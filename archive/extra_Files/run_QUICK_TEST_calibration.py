"""
QUICK TEST CALIBRATION
Tests a SMALL focused grid (8 configs) to verify logic before full run

Goal: Verify that calibration can hit targets WITHOUT changing literature values
"""

from calibration_framework import grid_search_calibration, CalibrationTargets
from datetime import datetime

print("=" * 80)
print("🧪 QUICK TEST CALIBRATION (8 configs)")
print("=" * 80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Define calibration targets (FROM YOUR TABLE)
targets = CalibrationTargets()
targets.annual_spend_low = 5270.0        
targets.annual_spend_medium = 8989.0     
targets.annual_spend_high = 16996.0      
targets.distance_car = 3.4               
targets.distance_no_car = 1.0            
targets.small_store_share = 0.10         
targets.weekly_frequency_share = 0.40    
targets.subweekly_frequency_share = 0.22 

# QUICK TEST: Just 2×2×2 = 8 configs
alpha_values = [0.8, 1.2]              # Distance weight (wider range)
gamma_values = [0.5, 0.7]              # Quality weight (focused)
threshold_low_values = [2.5, 3.5]      # Shopping frequency (wider range)

print(f"📊 QUICK Grid: {len(alpha_values)} × {len(gamma_values)} × {len(threshold_low_values)} = {len(alpha_values)*len(gamma_values)*len(threshold_low_values)} configs")
print(f"⚙️  Settings: 50 HH, 90 days, 1 seed")
print(f"⏱️  Expected time: ~10-15 minutes\n")
print("🎯 Testing if we can hit targets with current parameter ranges...")
print("   If yes → run full grid")
print("   If no → need to rethink approach\n")

# Run grid search
results_df = grid_search_calibration(
    alpha_values=alpha_values,
    gamma_values=gamma_values,
    threshold_low_values=threshold_low_values,
    targets=targets,
    num_seeds=1,
    num_days=90,
    num_consumers=50
)

# Save results
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"QUICK_TEST_results_{timestamp}.csv"
results_df.to_csv(output_file, index=False)

print("\n" + "=" * 80)
print("✅ QUICK TEST COMPLETE")
print("=" * 80)
print(f"💾 Results saved to: {output_file}")
print(f"\n🏆 BEST CONFIGURATION:\n")
print(results_df.head(1).to_string())

# Analysis
best = results_df.iloc[0]
print(f"\n📊 BEST CONFIG ANALYSIS:")
print(f"   Total Error: {best['total_error']:.3f}")
print(f"   Metrics Passed: {sum([best[f'pass_{m}'] for m in ['spend_low', 'spend_medium', 'spend_high', 'weekly_freq', 'subweekly_freq', 'distance_car', 'distance_no_car', 'small_store']])}/8")
print(f"\n   Spending:")
print(f"      Low:    ${best['annual_spend_low']:.0f} (target: $5,270) - Error: {100*(best['annual_spend_low']-5270)/5270:.1f}%")
print(f"      Medium: ${best['annual_spend_medium']:.0f} (target: $8,989) - Error: {100*(best['annual_spend_medium']-8989)/8989:.1f}%")
print(f"      High:   ${best['annual_spend_high']:.0f} (target: $16,996) - Error: {100*(best['annual_spend_high']-16996)/16996:.1f}%")
print(f"\n   Travel:")
print(f"      Car:    {best['distance_car_mi']:.2f} mi (target: 3.4 mi)")
print(f"      No-car: {best['distance_no_car_mi']:.2f} mi (target: 1.0 mi)")
print(f"\n   Frequency:")
print(f"      Weekly:     {best['weekly_share']:.1%} (target: 40%)")
print(f"      Sub-weekly: {best['subweekly_share']:.1%} (target: 22%)")
print(f"\n   Small stores: {best['small_store_share']:.1%} (target: ≤10%)")

print("\n" + "=" * 80)
print("🤔 DECISION:")
if best['total_error'] < 2.0:
    print("   ✅ GOOD! Error < 2.0 → Proceed with FULL grid search")
elif best['total_error'] < 3.5:
    print("   ⚠️  MODERATE. Error < 3.5 → May proceed, but check specific metrics")
else:
    print("   ❌ HIGH ERROR. Need to rethink approach before full calibration")
print("=" * 80)

