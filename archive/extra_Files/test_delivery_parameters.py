"""
TEST: Verify new delivery usage parameters produce realistic adoption rates
============================================================================
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enhanced_mesa_geo_model import SimulationConfig, IncomeLevel
from baseline_scenario import create_baseline_scenario

def test_delivery_parameters():
    """Test that delivery parameters produce 3-5% usage for low-income HH"""
    
    print("="*80)
    print("TESTING: New Delivery Usage Parameters")
    print("="*80)
    print()
    
    # Create baseline with market-rate delivery
    config = SimulationConfig(
        num_consumers=200,  # Larger sample for statistics
        simulation_days=30   # 1 month
    )
    
    print("📊 Creating baseline scenario (200 HH, 30 days)...")
    model = create_baseline_scenario(config=config)
    print()
    
    # Check config values
    print("="*80)
    print("DELIVERY PARAMETERS IN CONFIG")
    print("="*80)
    print(f"Low-income baseline propensity:    {config.delivery_baseline_low:.1%} (target: 3-5%)")
    print(f"Medium-income baseline propensity: {config.delivery_baseline_medium:.1%}")
    print(f"High-income baseline propensity:   {config.delivery_baseline_high:.1%} (target: up to 20%)")
    print(f"Hard blockers (no tech):           {config.delivery_hard_blockers_share:.1%}")
    print(f"Subsidy uplift multiplier:         {config.delivery_subsidy_uplift}x")
    print()
    
    # Analyze household delivery propensities
    print("="*80)
    print("HOUSEHOLD DELIVERY PROPENSITY DISTRIBUTION")
    print("="*80)
    print()
    
    low_income_hh = [c for c in model.consumers if c.income == IncomeLevel.LOW]
    med_income_hh = [c for c in model.consumers if c.income == IncomeLevel.MEDIUM]
    high_income_hh = [c for c in model.consumers if c.income == IncomeLevel.HIGH]
    
    print(f"Total Households: {len(model.consumers)}")
    print(f"  Low income:    {len(low_income_hh)} ({len(low_income_hh)/len(model.consumers):.1%})")
    print(f"  Medium income: {len(med_income_hh)} ({len(med_income_hh)/len(model.consumers):.1%})")
    print(f"  High income:   {len(high_income_hh)} ({len(high_income_hh)/len(model.consumers):.1%})")
    print()
    
    # Check delivery eligibility
    low_eligible = sum(1 for c in low_income_hh if c.can_use_delivery)
    med_eligible = sum(1 for c in med_income_hh if c.can_use_delivery)
    high_eligible = sum(1 for c in high_income_hh if c.can_use_delivery)
    
    print(f"Delivery Eligible (can_use_delivery = True):")
    print(f"  Low income:    {low_eligible}/{len(low_income_hh)} ({low_eligible/len(low_income_hh):.1%})")
    print(f"  Medium income: {med_eligible}/{len(med_income_hh)} ({med_eligible/len(med_income_hh):.1%})")
    print(f"  High income:   {high_eligible}/{len(high_income_hh)} ({high_eligible/len(high_income_hh):.1%})")
    print()
    
    # Check delivery propensity values
    low_propensity_avg = sum(c.delivery_propensity for c in low_income_hh) / len(low_income_hh) if low_income_hh else 0
    med_propensity_avg = sum(c.delivery_propensity for c in med_income_hh) / len(med_income_hh) if med_income_hh else 0
    high_propensity_avg = sum(c.delivery_propensity for c in high_income_hh) / len(high_income_hh) if high_income_hh else 0
    
    print(f"Average Delivery Propensity (among eligible):")
    print(f"  Low income:    {low_propensity_avg:.1%}")
    print(f"  Medium income: {med_propensity_avg:.1%}")
    print(f"  High income:   {high_propensity_avg:.1%}")
    print()
    
    # Run simulation
    print("="*80)
    print("RUNNING 30-DAY SIMULATION")
    print("="*80)
    print("Running...")
    
    for day in range(config.simulation_days):
        model.step()
        if (day + 1) % 10 == 0:
            print(f"  Day {day+1}/{config.simulation_days} complete")
    
    print("✅ Simulation complete!")
    print()
    
    # Analyze delivery usage
    print("="*80)
    print("DELIVERY USAGE RESULTS")
    print("="*80)
    print()
    
    # Count households using delivery as primary source
    from enhanced_mesa_geo_model import EnhancedDeliveryService
    
    low_delivery_users = 0
    med_delivery_users = 0
    high_delivery_users = 0
    
    for hh in model.consumers:
        delivery_trips = sum(1 for p in hh.provider_visits if isinstance(p, EnhancedDeliveryService))
        total_trips = len(hh.provider_visits)
        
        if total_trips > 0 and delivery_trips / total_trips > 0.3:  # >30% of trips = "primary user"
            if hh.income == IncomeLevel.LOW:
                low_delivery_users += 1
            elif hh.income == IncomeLevel.MEDIUM:
                med_delivery_users += 1
            else:
                high_delivery_users += 1
    
    print(f"Households Using Delivery as Primary Source (>30% of trips):")
    print(f"  Low income:    {low_delivery_users}/{len(low_income_hh)} ({low_delivery_users/len(low_income_hh)*100:.1f}%)")
    print(f"  Medium income: {med_delivery_users}/{len(med_income_hh)} ({med_delivery_users/len(med_income_hh)*100:.1f}%)")
    print(f"  High income:   {high_delivery_users}/{len(high_income_hh)} ({high_delivery_users/len(high_income_hh)*100:.1f}%)")
    print()
    
    # Validation
    print("="*80)
    print("VALIDATION")
    print("="*80)
    print()
    
    low_usage_pct = low_delivery_users/len(low_income_hh)*100 if low_income_hh else 0
    target_min = 3.0
    target_max = 5.0
    
    if target_min <= low_usage_pct <= target_max:
        print(f"✅ Low-income delivery usage: {low_usage_pct:.1f}% (target: 3-5%)")
        print("   Parameters are calibrated correctly!")
        success = True
    elif low_usage_pct < target_min:
        print(f"⚠️  Low-income delivery usage: {low_usage_pct:.1f}% (target: 3-5%)")
        print(f"   Too LOW - consider increasing delivery_baseline_low or choice probabilities")
        success = False
    else:
        print(f"⚠️  Low-income delivery usage: {low_usage_pct:.1f}% (target: 3-5%)")
        print(f"   Too HIGH - consider decreasing delivery_baseline_low or choice probabilities")
        success = False
    
    print()
    print(f"📊 Medium-income usage: {med_delivery_users/len(med_income_hh)*100:.1f}% (expected: ~10-15%)")
    print(f"📊 High-income usage: {high_delivery_users/len(high_income_hh)*100:.1f}% (expected: ~15-20%)")
    print()
    
    if success:
        print("✅ SUCCESS! Delivery parameters produce realistic usage rates!")
    else:
        print("⚠️  Parameters may need fine-tuning during calibration")
    
    print("="*80)
    
    return success

if __name__ == "__main__":
    success = test_delivery_parameters()
    sys.exit(0 if success else 1)

