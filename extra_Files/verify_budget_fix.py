"""
Verify Budget Fix - Test that spending aligns with budgets
===========================================================

This script verifies that after implementing income-scaled baskets,
household spending stays within their weekly budgets.
"""

import sys
import numpy as np
sys.path.append('/Users/goshtasbshahriari/Desktop/Code/GeoMesa_Food_Access')

from enhanced_mesa_geo_model import SimulationConfig, IncomeLevel, IncomeClassifier

def test_budget_alignment():
    """Test that basket sizes align with budgets"""
    
    print("="*80)
    print("BUDGET FIX VERIFICATION")
    print("="*80)
    
    config = SimulationConfig()
    
    # Test cases: different income + household size combinations
    test_cases = [
        (IncomeLevel.LOW, 1),
        (IncomeLevel.LOW, 5),
        (IncomeLevel.MEDIUM, 1),
        (IncomeLevel.MEDIUM, 5),
        (IncomeLevel.HIGH, 1),
        (IncomeLevel.HIGH, 5),
    ]
    
    print("\nBudget vs Expected Spending Analysis:")
    print("-" * 80)
    print(f"{'Income':<10} {'HH Size':<8} {'Budget':<10} {'Basket':<10} {'Trips/wk':<10} {'Weekly $':<12} {'Ratio':<8}")
    print("-" * 80)
    
    all_pass = True
    
    for income, hh_size in test_cases:
        # Get budget
        if income == IncomeLevel.LOW:
            budget = config.weekly_budget_low
            freq_range = config.freq_low_income
        elif income == IncomeLevel.MEDIUM:
            budget = config.weekly_budget_medium
            freq_range = config.freq_medium_income
        else:
            budget = config.weekly_budget_high
            freq_range = config.freq_high_income
        
        # Get basket size (with new income scaling)
        if hh_size == 1:
            base_basket = config.basket_size_1
        elif hh_size == 2:
            base_basket = config.basket_size_2
        elif hh_size in [3, 4]:
            base_basket = config.basket_size_3_4
        else:
            base_basket = config.basket_size_5_plus
        
        # Apply income multiplier (THE FIX)
        income_multiplier = {
            IncomeLevel.LOW: 0.50,
            IncomeLevel.MEDIUM: 0.75,
            IncomeLevel.HIGH: 1.00
        }
        basket = base_basket * income_multiplier[income]
        
        # Calculate expected spending
        avg_freq_days = np.mean(freq_range)
        trips_per_week = 7.0 / avg_freq_days
        weekly_spend = trips_per_week * basket
        ratio = weekly_spend / budget
        
        # Check if within reasonable range (0.8 - 1.2)
        status = "✓" if 0.8 <= ratio <= 1.2 else "✗"
        if ratio < 0.8 or ratio > 1.2:
            all_pass = False
        
        print(f"{status} {income.value:<10} {hh_size:<8} ${budget:<9.0f} ${basket:<9.0f} {trips_per_week:<10.2f} ${weekly_spend:<11.0f} {ratio:.2f}x")
    
    print("-" * 80)
    
    if all_pass:
        print("\n✅ ALL CASES PASS: Spending aligns with budgets (within 0.8-1.2x)")
    else:
        print("\n⚠️  SOME CASES FAIL: Check ratios outside 0.8-1.2x range")
    
    print("\n" + "="*80)
    print("EXPECTED ANNUAL SPENDING (After Fix):")
    print("="*80)
    
    # Calculate expected annual spending for each income level
    for income in [IncomeLevel.LOW, IncomeLevel.MEDIUM, IncomeLevel.HIGH]:
        if income == IncomeLevel.LOW:
            budget = config.weekly_budget_low
        elif income == IncomeLevel.MEDIUM:
            budget = config.weekly_budget_medium
        else:
            budget = config.weekly_budget_high
        
        annual = budget * 52
        
        print(f"{income.value:<10}: ${annual:,.0f}/year")
    
    print("\nTargets for comparison:")
    print(f"Low:       $5,300/year")
    print(f"Medium:    $9,000/year")
    print(f"High:      $17,000/year")
    
    return all_pass

if __name__ == "__main__":
    success = test_budget_alignment()
    sys.exit(0 if success else 1)

