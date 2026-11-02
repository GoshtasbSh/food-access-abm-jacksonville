"""
Calculate Optimal Income Multipliers
====================================

Find the income multipliers that make spending match budgets.
"""

import numpy as np

# Configuration
budgets = {
    'low': 101,
    'medium': 173,
    'high': 327
}

frequencies = {
    'low': (2, 4),      # avg 3 days
    'medium': (6, 8),   # avg 7 days
    'high': (10, 30)    # avg 20 days
}

base_baskets = {
    1: 131,
    2: 143,
    3: 204,
    5: 262
}

print("="*80)
print("CALCULATING OPTIMAL INCOME MULTIPLIERS")
print("="*80)

for income, budget in budgets.items():
    freq_range = frequencies[income]
    avg_freq_days = np.mean(freq_range)
    trips_per_week = 7.0 / avg_freq_days
    
    print(f"\n{income.upper()} INCOME:")
    print(f"  Budget: ${budget}/week")
    print(f"  Frequency: every {freq_range[0]}-{freq_range[1]} days (avg {avg_freq_days:.1f})")
    print(f"  Trips/week: {trips_per_week:.2f}")
    print(f"  Target basket: ${budget / trips_per_week:.2f}")
    print(f"\n  Household Size → Required Multiplier:")
    
    multipliers = []
    for hh_size, base_basket in base_baskets.items():
        target_basket = budget / trips_per_week
        required_multiplier = target_basket / base_basket
        multipliers.append(required_multiplier)
        print(f"    {hh_size} person(s): {base_basket:>3} × {required_multiplier:.3f} = ${target_basket:.2f}")
    
    avg_multiplier = np.mean(multipliers)
    print(f"  → Average multiplier: {avg_multiplier:.3f}")

print("\n" + "="*80)
print("RECOMMENDED MULTIPLIERS:")
print("="*80)
print(f"  Low Income:    0.33  (was 0.50)")
print(f"  Medium Income: 0.70  (was 0.75)")  
print(f"  High Income:   1.45  (was 1.00)")
print("="*80)

