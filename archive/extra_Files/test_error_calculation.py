"""
Test error calculation to verify against user's results
"""

from calibration_framework import calculate_calibration_error, CalibrationTargets

# User's targets (use defaults from CalibrationTargets which are now corrected)
targets = CalibrationTargets()
# Should already have:
# annual_spend_low = 5300.0
# annual_spend_medium = 9000.0
# annual_spend_high = 17000.0
# distance_car = 3.48 miles (5.6 km)
# distance_no_car = 0.50 miles (0.8 km)

# User's BEST results from the past
user_metrics = {
    'annual_spend_low': 7078.0,
    'annual_spend_medium': 9344.0,
    'annual_spend_high': 11715.0,
    'weekly_share': 0.40,  # Assume matched
    'subweekly_share': 0.22,  # Assume matched
    'distance_car_mi': 2.49 * 0.621371,  # Convert km to miles
    'distance_no_car_mi': 1.3 * 0.621371,  # Convert km to miles
    'small_store_share': 0.084,
    'pantry_user_share': 0.0
}

print("=" * 80)
print("USER'S PAST RESULTS - ERROR CALCULATION")
print("=" * 80)
print("\nTargets:")
print(f"  Low income:  ${targets.annual_spend_low:,.0f}")
print(f"  Med income:  ${targets.annual_spend_medium:,.0f}")
print(f"  High income: ${targets.annual_spend_high:,.0f}")
print(f"  Distance (car):    {targets.distance_car:.2f} mi (5.6 km)")
print(f"  Distance (no-car): {targets.distance_no_car:.2f} mi (0.8 km)")
print(f"  Corner share: {targets.small_store_share:.1%}")

print("\nUser's Results:")
print(f"  Low income:  ${user_metrics['annual_spend_low']:,.0f}")
print(f"  Med income:  ${user_metrics['annual_spend_medium']:,.0f}")
print(f"  High income: ${user_metrics['annual_spend_high']:,.0f}")
print(f"  Distance (car):    {2.49:.2f} km = {user_metrics['distance_car_mi']:.2f} mi")
print(f"  Distance (no-car): {1.3:.2f} km = {user_metrics['distance_no_car_mi']:.2f} mi")
print(f"  Corner share: {user_metrics['small_store_share']:.1%}")

# Calculate error using MY function
total_error, individual_errors = calculate_calibration_error(user_metrics, targets)

print("\n" + "=" * 80)
print("CALCULATED ERROR (using my function):")
print("=" * 80)
print(f"\nTotal Error: {total_error:.4f}")
print("\nIndividual Errors:")
for key, val in individual_errors.items():
    print(f"  {key:20s}: {val:.4f} ({100*val:.1f}%)")

print("\n" + "=" * 80)
print(f"USER REPORTED ERROR: 0.282")
print(f"MY CALCULATED ERROR: {total_error:.4f}")
print(f"DIFFERENCE: {abs(total_error - 0.282):.4f}")
print("=" * 80)

if abs(total_error - 0.282) > 0.05:
    print("\n🚨 ERROR CALCULATION IS WRONG!")
    print("   There's a bug in the calibration_framework.py")
else:
    print("\n✅ Error calculation matches!")

