"""
COMPREHENSIVE VERIFICATION: Mobile Pantries + Delivery Parameters
==================================================================
Double-checking EVERYTHING per user request
"""

import sys
sys.path.append('/Users/goshtasbshahriari/Desktop/Code/GeoMesa_Food_Access')

from enhanced_mesa_geo_model import SimulationConfig, EnhancedMobilePantry, EnhancedDeliveryService, IncomeLevel
from baseline_scenario import create_baseline_scenario
from enhanced_scenario_1 import EnhancedScenario1Model
from enhanced_scenario_2 import EnhancedScenario2Model
from enhanced_scenario_3 import EnhancedScenario3Model
from enhanced_scenario_4 import create_enhanced_scenario_4

def comprehensive_verification():
    """Verify mobile pantries AND delivery parameters in all scenarios"""
    
    print("="*80)
    print("COMPREHENSIVE VERIFICATION")
    print("="*80)
    print()
    
    config = SimulationConfig(num_consumers=50, simulation_days=1)
    
    # =======================================================================
    # PART 1: MOBILE PANTRIES CHECK
    # =======================================================================
    print("="*80)
    print("PART 1: MOBILE PANTRIES IN ALL SCENARIOS")
    print("="*80)
    print()
    
    scenarios = {}
    print("Creating all scenarios...")
    scenarios['Baseline'] = create_baseline_scenario(config=config)
    scenarios['Scenario 1'] = EnhancedScenario1Model(config=config, include_baseline=True)
    scenarios['Scenario 2'] = EnhancedScenario2Model(config=config, include_baseline=True)
    scenarios['Scenario 3'] = EnhancedScenario3Model(config=config, include_baseline=True)
    scenarios['Scenario 4'] = create_enhanced_scenario_4(config=config, use_real_data=True)
    
    print()
    print("Mobile Pantry Count:")
    print("-" * 80)
    
    mobile_pantry_results = {}
    for name, model in scenarios.items():
        pantries = [p for p in model.food_providers if isinstance(p, EnhancedMobilePantry)]
        mobile_pantry_results[name] = len(pantries)
        
        pantry_names = [getattr(p, 'name', 'Unnamed') for p in pantries]
        
        print(f"\n{name}:")
        print(f"   Count: {len(pantries)}")
        for pname in pantry_names:
            print(f"      • {pname}")
    
    print()
    print("="*80)
    print("MOBILE PANTRIES VALIDATION")
    print("="*80)
    
    pantry_success = True
    expected_baseline = 3  # 3 FNEFL pantries
    expected_scenario3 = 5  # 3 baseline + 2 new
    
    if mobile_pantry_results['Baseline'] == expected_baseline:
        print(f"✅ Baseline: {mobile_pantry_results['Baseline']} pantries (correct)")
    else:
        print(f"❌ Baseline: {mobile_pantry_results['Baseline']} pantries (expected {expected_baseline})")
        pantry_success = False
    
    if mobile_pantry_results['Scenario 1'] == expected_baseline:
        print(f"✅ Scenario 1: {mobile_pantry_results['Scenario 1']} pantries (correct)")
    else:
        print(f"❌ Scenario 1: {mobile_pantry_results['Scenario 1']} pantries (expected {expected_baseline})")
        pantry_success = False
    
    if mobile_pantry_results['Scenario 2'] == expected_baseline:
        print(f"✅ Scenario 2: {mobile_pantry_results['Scenario 2']} pantries (correct)")
    else:
        print(f"❌ Scenario 2: {mobile_pantry_results['Scenario 2']} pantries (expected {expected_baseline})")
        pantry_success = False
    
    if mobile_pantry_results['Scenario 3'] == expected_scenario3:
        print(f"✅ Scenario 3: {mobile_pantry_results['Scenario 3']} pantries (correct: 3 baseline + 2 new)")
    else:
        print(f"❌ Scenario 3: {mobile_pantry_results['Scenario 3']} pantries (expected {expected_scenario3})")
        pantry_success = False
    
    if mobile_pantry_results['Scenario 4'] == expected_baseline:
        print(f"✅ Scenario 4: {mobile_pantry_results['Scenario 4']} pantries (correct)")
    else:
        print(f"❌ Scenario 4: {mobile_pantry_results['Scenario 4']} pantries (expected {expected_baseline})")
        pantry_success = False
    
    print()
    
    # =======================================================================
    # PART 2: DELIVERY SERVICES CHECK
    # =======================================================================
    print("="*80)
    print("PART 2: DELIVERY SERVICES IN ALL SCENARIOS")
    print("="*80)
    print()
    
    print("Delivery Service Count:")
    print("-" * 80)
    
    delivery_results = {}
    for name, model in scenarios.items():
        deliveries = [p for p in model.food_providers if isinstance(p, EnhancedDeliveryService)]
        delivery_results[name] = len(deliveries)
        
        print(f"\n{name}:")
        print(f"   Count: {len(deliveries)}")
        for d in deliveries:
            subsidy_status = "SUBSIDIZED" if d.subsidized else "MARKET-RATE"
            print(f"      • {getattr(d, 'name', 'Delivery Service')} ({subsidy_status})")
    
    print()
    print("="*80)
    print("DELIVERY VALIDATION")
    print("="*80)
    
    delivery_success = True
    
    # All scenarios should have delivery
    for scenario_name, count in delivery_results.items():
        if count >= 1:
            print(f"✅ {scenario_name}: {count} delivery service(s)")
        else:
            print(f"❌ {scenario_name}: {count} delivery service(s) (expected at least 1)")
            delivery_success = False
    
    print()
    
    # =======================================================================
    # PART 3: DELIVERY PARAMETERS CHECK
    # =======================================================================
    print("="*80)
    print("PART 3: DELIVERY PROPENSITY PARAMETERS")
    print("="*80)
    print()
    
    print("Configuration Values:")
    print(f"   delivery_baseline_low:    {config.delivery_baseline_low:.1%} (target: 8%)")
    print(f"   delivery_baseline_medium: {config.delivery_baseline_medium:.1%} (target: 20%)")
    print(f"   delivery_baseline_high:   {config.delivery_baseline_high:.1%} (target: 35%)")
    print(f"   delivery_hard_blockers:   {config.delivery_hard_blockers_share:.1%} (50%)")
    print(f"   delivery_subsidy_uplift:  {config.delivery_subsidy_uplift}x")
    print()
    
    # Check household propensities
    baseline_model = scenarios['Baseline']
    low_hh = [c for c in baseline_model.consumers if c.income == IncomeLevel.LOW]
    med_hh = [c for c in baseline_model.consumers if c.income == IncomeLevel.MEDIUM]
    high_hh = [c for c in baseline_model.consumers if c.income == IncomeLevel.HIGH]
    
    low_eligible = [c for c in low_hh if c.can_use_delivery]
    med_eligible = [c for c in med_hh if c.can_use_delivery]
    high_eligible = [c for c in high_hh if c.can_use_delivery]
    
    low_prop = sum(c.delivery_propensity for c in low_eligible) / len(low_eligible) if low_eligible else 0
    med_prop = sum(c.delivery_propensity for c in med_eligible) / len(med_eligible) if med_eligible else 0
    high_prop = sum(c.delivery_propensity for c in high_eligible) / len(high_eligible) if high_eligible else 0
    
    print("Household Propensities (Baseline):")
    print(f"   Low income (eligible):    {low_prop:.1%}")
    print(f"   Medium income (eligible): {med_prop:.1%}")
    print(f"   High income (eligible):   {high_prop:.1%}")
    print()
    
    print("Expected Usage (all households):")
    low_eligible_rate = len(low_eligible) / len(low_hh) if low_hh else 0
    med_eligible_rate = len(med_eligible) / len(med_hh) if med_hh else 0
    high_eligible_rate = len(high_eligible) / len(high_hh) if high_hh else 0
    
    print(f"   Low income:    {low_eligible_rate * low_prop:.1%} (target: 3-5%)")
    print(f"   Medium income: {med_eligible_rate * med_prop:.1%}")
    print(f"   High income:   {high_eligible_rate * high_prop:.1%} (target: up to 20%)")
    print()
    
    params_success = True
    if abs(config.delivery_baseline_low - 0.08) > 0.001:
        print(f"❌ delivery_baseline_low: {config.delivery_baseline_low:.1%} (expected 8%)")
        params_success = False
    else:
        print(f"✅ delivery_baseline_low: {config.delivery_baseline_low:.1%}")
    
    if abs(config.delivery_baseline_medium - 0.20) > 0.001:
        print(f"❌ delivery_baseline_medium: {config.delivery_baseline_medium:.1%} (expected 20%)")
        params_success = False
    else:
        print(f"✅ delivery_baseline_medium: {config.delivery_baseline_medium:.1%}")
    
    if abs(config.delivery_baseline_high - 0.35) > 0.001:
        print(f"❌ delivery_baseline_high: {config.delivery_baseline_high:.1%} (expected 35%)")
        params_success = False
    else:
        print(f"✅ delivery_baseline_high: {config.delivery_baseline_high:.1%}")
    
    print()
    
    # =======================================================================
    # FINAL SUMMARY
    # =======================================================================
    print("="*80)
    print("FINAL VERIFICATION SUMMARY")
    print("="*80)
    print()
    
    if pantry_success:
        print("✅ MOBILE PANTRIES: All scenarios have correct number of pantries")
    else:
        print("❌ MOBILE PANTRIES: Some scenarios have incorrect pantry counts")
    
    if delivery_success:
        print("✅ DELIVERY SERVICES: All scenarios have delivery services")
    else:
        print("❌ DELIVERY SERVICES: Some scenarios missing delivery")
    
    if params_success:
        print("✅ DELIVERY PARAMETERS: All propensity values are correct")
    else:
        print("❌ DELIVERY PARAMETERS: Some parameters are incorrect")
    
    print()
    
    overall_success = pantry_success and delivery_success and params_success
    
    if overall_success:
        print("🎉 ALL CHECKS PASSED! Model is ready for calibration!")
    else:
        print("⚠️  SOME CHECKS FAILED! Review issues above.")
    
    print("="*80)
    
    return overall_success

if __name__ == "__main__":
    success = comprehensive_verification()
    sys.exit(0 if success else 1)

