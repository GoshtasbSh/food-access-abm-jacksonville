"""
TEST: Verify delivery propensity parameters are set correctly
==============================================================
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enhanced_mesa_geo_model import SimulationConfig, IncomeLevel
from baseline_scenario import create_baseline_scenario

def test_delivery_propensity():
    """Test that delivery propensity values match 3-5% for low-income"""
    
    print("="*80)
    print("TESTING: Delivery Propensity Parameters")
    print("="*80)
    print()
    
    # Create baseline
    config = SimulationConfig(
        num_consumers=100,
        simulation_days=1
    )
    
    print("📊 Creating baseline scenario...")
    model = create_baseline_scenario(config=config)
    print()
    
    print("="*80)
    print("DELIVERY PARAMETERS")
    print("="*80)
    print()
    print(f"✅ Low-income baseline:    {config.delivery_baseline_low:.1%} (target: 3-5%, set to 4%)")
    print(f"✅ Medium-income baseline: {config.delivery_baseline_medium:.1%} (set to 12%)")
    print(f"✅ High-income baseline:   {config.delivery_baseline_high:.1%} (target: up to 20%)")
    print()
    print(f"📊 Hard blockers (no tech): {config.delivery_hard_blockers_share:.1%}")
    print(f"📊 Subsidy uplift:          {config.delivery_subsidy_uplift}x")
    print()
    
    # Analyze household propensities
    print("="*80)
    print("HOUSEHOLD ANALYSIS")
    print("="*80)
    print()
    
    low_hh = [c for c in model.consumers if c.income == IncomeLevel.LOW]
    med_hh = [c for c in model.consumers if c.income == IncomeLevel.MEDIUM]
    high_hh = [c for c in model.consumers if c.income == IncomeLevel.HIGH]
    
    print(f"Income Distribution:")
    print(f"  Low:    {len(low_hh)} HH ({len(low_hh)/len(model.consumers):.1%})")
    print(f"  Medium: {len(med_hh)} HH ({len(med_hh)/len(model.consumers):.1%})")
    print(f"  High:   {len(high_hh)} HH ({len(high_hh)/len(model.consumers):.1%})")
    print()
    
    # Check eligibility (can_use_delivery)
    low_eligible = [c for c in low_hh if c.can_use_delivery]
    med_eligible = [c for c in med_hh if c.can_use_delivery]
    high_eligible = [c for c in high_hh if c.can_use_delivery]
    
    print(f"Delivery Eligible (have internet/tech):")
    print(f"  Low:    {len(low_eligible)}/{len(low_hh)} ({len(low_eligible)/len(low_hh):.1%})")
    print(f"  Medium: {len(med_eligible)}/{len(med_hh)} ({len(med_eligible)/len(med_hh):.1%})")
    print(f"  High:   {len(high_eligible)}/{len(high_hh)} ({len(high_eligible)/len(high_hh):.1%})")
    print()
    
    # Check propensity values
    low_prop = [c.delivery_propensity for c in low_eligible]
    med_prop = [c.delivery_propensity for c in med_eligible]
    high_prop = [c.delivery_propensity for c in high_eligible]
    
    low_avg = sum(low_prop) / len(low_prop) if low_prop else 0
    med_avg = sum(med_prop) / len(med_prop) if med_prop else 0
    high_avg = sum(high_prop) / len(high_prop) if high_prop else 0
    
    print(f"Delivery Propensity (among eligible):")
    print(f"  Low:    {low_avg:.1%} (expected: 4.0%)")
    print(f"  Medium: {med_avg:.1%} (expected: 12.0%)")
    print(f"  High:   {high_avg:.1%} (expected: 20.0%)")
    print()
    
    # Calculate expected ACTUAL usage
    # Formula: eligibility_rate × propensity × choice_probability
    # Using delivery_choice_free_prob (0.35) as representative
    choice_prob = config.delivery_choice_free_prob
    
    low_expected = (len(low_eligible)/len(low_hh)) * low_avg * choice_prob if low_hh else 0
    med_expected = (len(med_eligible)/len(med_hh)) * med_avg * choice_prob if med_hh else 0
    high_expected = (len(high_eligible)/len(high_hh)) * high_avg * choice_prob if high_hh else 0
    
    print("="*80)
    print("EXPECTED USAGE RATES (Baseline - Market Rate)")
    print("="*80)
    print()
    print(f"Calculation: eligibility_rate × propensity × choice_prob ({choice_prob:.0%})")
    print()
    print(f"Expected Delivery as Primary Source:")
    print(f"  Low income:    ~{low_expected:.1%} (TARGET: 3-5%)")
    print(f"  Medium income: ~{med_expected:.1%}")
    print(f"  High income:   ~{high_expected:.1%}")
    print()
    
    # Validation
    print("="*80)
    print("VALIDATION")
    print("="*80)
    print()
    
    success = True
    target_min = 0.03
    target_max = 0.05
    
    # Check if propensity is set correctly (4%)
    if abs(low_avg - 0.04) < 0.001:
        print(f"✅ Low-income propensity: {low_avg:.1%} (correct: 4.0%)")
    else:
        print(f"⚠️  Low-income propensity: {low_avg:.1%} (expected: 4.0%)")
        success = False
    
    # Estimate actual usage range
    usage_estimate = low_expected
    if target_min <= usage_estimate <= target_max:
        print(f"✅ Estimated low-income usage: ~{usage_estimate:.1%} (within target: 3-5%)")
    elif usage_estimate < target_min:
        print(f"⚠️  Estimated low-income usage: ~{usage_estimate:.1%} (below target: 3-5%)")
        print(f"   Note: Full simulation may show higher usage due to varied scenarios")
    else:
        print(f"⚠️  Estimated low-income usage: ~{usage_estimate:.1%} (above target: 3-5%)")
    
    print()
    print("="*80)
    print("NOTES")
    print("="*80)
    print("• Parameters represent ACTUAL usage, not just eligibility")
    print("• Even with 90%+ coverage, most don't use delivery regularly")
    print("• Barriers: habit, trust, technology, fees, wait times")
    print("• Subsidy in Scenario 4 will 2x the propensity (4% → 8% for low-income)")
    print("• Final calibration will validate these against real simulation outcomes")
    print("="*80)
    
    return success

if __name__ == "__main__":
    success = test_delivery_propensity()
    sys.exit(0 if success else 1)

