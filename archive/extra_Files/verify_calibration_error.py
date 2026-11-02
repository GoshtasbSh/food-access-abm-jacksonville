"""
Verify that the 2-phase calibration error is consistent with calibration_framework.py
"""

# Best result from Phase 2
metrics = {
    'avg_spend_low': 3698,
    'avg_spend_med': 8766,
    'avg_spend_high': 20151,
    'corner_share': 0.084,
    'avg_dist_car': 2.49,
    'avg_dist_nocar': 0.96
}

targets = {
    'avg_spend_low': 5300,
    'avg_spend_med': 9000,
    'avg_spend_high': 17000,
    'corner_share': 0.10,
    'avg_dist_car': 5.6,
    'avg_dist_nocar': 0.8
}

print("="*80)
print("CALIBRATION ERROR VERIFICATION")
print("="*80)
print("\nBest configuration from Phase 2 (Config #73):")
print("  α=2.5, β=0.7, γ=1.0, δ=0.4, TL=4.0, TM=7.0, TH=14.0")
print("\nReported error: 0.2382")
print("\n" + "="*80)

errors = {}
for key, target in targets.items():
    if target > 0 and key in metrics:
        rel_error = abs(metrics[key] - target) / target
        errors[key] = rel_error
        print(f"{key:20s}: {metrics[key]:8.2f} vs {target:8.2f} → Error: {rel_error:.4f} ({rel_error*100:.1f}%)")

print("\n" + "="*80)
print("ERROR CALCULATION METHODS:")
print("="*80)

# Method 1: MEAN (used in run_MEMORY_OPTIMIZED_calibration.py)
mean_error = sum(errors.values()) / len(errors)
print(f"\nMethod 1 (MEAN): {mean_error:.4f}")
print(f"  Formula: sum(errors) / count")
print(f"  Used in: run_MEMORY_OPTIMIZED_calibration.py, run_PHASE2_VALIDATION.py")
print(f"  Phase 2 reported: 0.2382")
print(f"  Calculated here: {mean_error:.4f}")
print(f"  Match? {'✅ YES' if abs(mean_error - 0.2382) < 0.01 else '❌ NO'}")

# Method 2: SUM (used in calibration_framework.py)
sum_error = sum(errors.values())
print(f"\nMethod 2 (SUM): {sum_error:.4f}")
print(f"  Formula: sum(errors)")
print(f"  Used in: calibration_framework.py")
print(f"  My previous results: 1.4-2.6")
print(f"  Calculated here: {sum_error:.4f}")

print("\n" + "="*80)
print("CONCLUSION:")
print("="*80)
if abs(mean_error - 0.2382) < 0.01:
    print("✅ The 2-phase calibration is CORRECT!")
    print("   It uses MEAN (average) of errors, not SUM.")
    print("\n⚠️  BUT: My previous calibrations used SUM instead of MEAN!")
    print(f"   Using SUM method, this config has error = {sum_error:.4f}")
    print(f"   Using MEAN method, this config has error = {mean_error:.4f}")
    print("\n🔧 SOLUTION: Update calibration_framework.py to use MEAN instead of SUM")
    print("   OR: Keep them consistent (both use SUM or both use MEAN)")
else:
    print("❌ Something is wrong with the calculation!")

print("="*80)

