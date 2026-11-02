"""
Test Budget Fix with Actual Household Agents
============================================
"""

import os
import sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enhanced_mesa_geo_model import SimulationConfig, IncomeLevel, EnhancedHouseholdAgent
from baseline_scenario import create_baseline_scenario

def test_actual_households():
    """Test baskets from actual household agents"""
    
    print("="*80)
    print("TESTING ACTUAL HOUSEHOLD BASKET SIZES")
    print("="*80)
    
    config = SimulationConfig(
        num_consumers=100,
        alpha_distance=2.5,
        gamma_quality_variety=1.5,
        go_shop_threshold_low=6.5
    )
    
    model = create_baseline_scenario(config=config)
    
    # Get all households
    households = [a for a in model.schedule.agents if isinstance(a, EnhancedHouseholdAgent)]
    
    # Group by income and household size
    test_groups = {
        ('LOW', 1): [],
        ('LOW', 5): [],
        ('MEDIUM', 1): [],
        ('MEDIUM', 5): [],
        ('HIGH', 1): [],
        ('HIGH', 5): []
    }
    
    for hh in households:
        key = (hh.income.value.upper(), hh.household_size)
        if key in test_groups:
            test_groups[key].append(hh)
    
    print("\nActual Household Baskets vs Budgets:")
    print("-" * 90)
    print(f"{'Income':<10} {'Size':<6} {'Count':<7} {'Budget':<10} {'Basket':<12} {'Trips/wk':<10} {'Weekly$':<12} {'Ratio':<8}")
    print("-" * 90)
    
    all_pass = True
    
    for (income_str, size), hhs in test_groups.items():
        if not hhs:
            continue
        
        # Calculate averages
        budgets = [hh.weekly_budget for hh in hhs]
        baskets = [hh.mean_basket_size for hh in hhs]
        freqs = [hh.shopping_frequency for hh in hhs]
        
        avg_budget = np.mean(budgets)
        avg_basket = np.mean(baskets)
        avg_freq = np.mean(freqs)
        trips_per_week = 7.0 / avg_freq
        weekly_spend = trips_per_week * avg_basket
        ratio = weekly_spend / avg_budget
        
        status = "✓" if 0.8 <= ratio <= 1.3 else "✗"
        if ratio < 0.8 or ratio > 1.3:
            all_pass = False
        
        print(f"{status} {income_str:<10} {size:<6} {len(hhs):<7} ${avg_budget:<9.0f} ${avg_basket:<11.0f} {trips_per_week:<10.2f} ${weekly_spend:<11.0f} {ratio:.2f}x")
    
    print("-" * 90)
    
    if all_pass:
        print("\n✅ ALL PASS: Baskets align with budgets!")
    else:
        print("\n⚠️  SOME FAIL: Check ratios")
    
    # Show annual spending projections
    print("\n" + "="*80)
    print("PROJECTED ANNUAL SPENDING (by income):")
    print("="*80)
    
    income_groups = {
        'LOW': [],
        'MEDIUM': [],
        'HIGH': []
    }
    
    for hh in households:
        income_groups[hh.income.value.upper()].append(hh)
    
    print(f"\n{'Income':<10} {'Count':<8} {'Avg Budget':<15} {'Annual':<15} {'Target':<15}")
    print("-" * 70)
    
    targets = {
        'LOW': 5300,
        'MEDIUM': 9000,
        'HIGH': 17000
    }
    
    for income_str, hhs in income_groups.items():
        if not hhs:
            continue
        
        avg_weekly = np.mean([hh.weekly_budget for hh in hhs])
        annual = avg_weekly * 52
        target = targets[income_str]
        diff_pct = ((annual - target) / target) * 100
        
        status = "✓" if abs(diff_pct) < 15 else "✗"
        
        print(f"{status} {income_str:<10} {len(hhs):<8} ${avg_weekly:<14.0f} ${annual:<14,.0f} ${target:<14,.0f} ({diff_pct:+.1f}%)")
    
    print("="*80)
    
    return all_pass

if __name__ == "__main__":
    success = test_actual_households()
    sys.exit(0 if success else 1)

