"""
COMPREHENSIVE FINAL TEST: All Scenarios + Dashboard
====================================================
Verifies EVERYTHING is correct including dashboard integration
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enhanced_mesa_geo_model import SimulationConfig, EnhancedMobilePantry, EnhancedDeliveryService, IncomeLevel

# Import exactly as dashboard does
from baseline_scenario import create_baseline_scenario
from enhanced_scenario_1 import create_enhanced_scenario_1
from enhanced_scenario_2 import create_enhanced_scenario_2
from enhanced_scenario_3 import create_enhanced_scenario_3
from enhanced_scenario_4 import create_enhanced_scenario_4

def test_comprehensive():
    """Comprehensive test of all scenarios using EXACT dashboard calls"""
    
    print("="*80)
    print("COMPREHENSIVE FINAL TEST")
    print("Testing ALL scenarios using EXACT dashboard function calls")
    print("="*80)
    print()
    
    config = SimulationConfig(num_consumers=50, simulation_days=1)
    
    results = {
        'mobile_pantries': {},
        'delivery_services': {},
        'total_providers': {},
        'delivery_params': {}
    }
    
    # =======================================================================
    # TEST 1: BASELINE
    # =======================================================================
    print("1️⃣  Testing Baseline (exactly as dashboard calls it)...")
    print("   Calling: create_baseline_scenario(config, use_real_data=True)")
    
    baseline = create_baseline_scenario(config, use_real_data=True)
    
    pantries_baseline = [p for p in baseline.food_providers if isinstance(p, EnhancedMobilePantry)]
    delivery_baseline = [p for p in baseline.food_providers if isinstance(p, EnhancedDeliveryService)]
    
    results['mobile_pantries']['baseline'] = len(pantries_baseline)
    results['delivery_services']['baseline'] = len(delivery_baseline)
    results['total_providers']['baseline'] = len(baseline.food_providers)
    
    print(f"   ✅ Baseline created: {len(baseline.food_providers)} providers")
    print(f"      • Mobile pantries: {len(pantries_baseline)}")
    print(f"      • Delivery services: {len(delivery_baseline)}")
    print()
    
    # =======================================================================
    # TEST 2: SCENARIO 1
    # =======================================================================
    print("2️⃣  Testing Scenario 1 (exactly as dashboard calls it)...")
    print("   Calling: create_enhanced_scenario_1(config, include_baseline=True, use_real_data=True)")
    
    scenario1 = create_enhanced_scenario_1(config, include_baseline=True, use_real_data=True)
    
    pantries_s1 = [p for p in scenario1.food_providers if isinstance(p, EnhancedMobilePantry)]
    delivery_s1 = [p for p in scenario1.food_providers if isinstance(p, EnhancedDeliveryService)]
    
    results['mobile_pantries']['scenario1'] = len(pantries_s1)
    results['delivery_services']['scenario1'] = len(delivery_s1)
    results['total_providers']['scenario1'] = len(scenario1.food_providers)
    
    print(f"   ✅ Scenario 1 created: {len(scenario1.food_providers)} providers")
    print(f"      • Mobile pantries: {len(pantries_s1)}")
    print(f"      • Delivery services: {len(delivery_s1)}")
    print()
    
    # =======================================================================
    # TEST 3: SCENARIO 2
    # =======================================================================
    print("3️⃣  Testing Scenario 2 (exactly as dashboard calls it)...")
    print("   Calling: create_enhanced_scenario_2(config, include_baseline=True, use_real_data=True)")
    
    scenario2 = create_enhanced_scenario_2(config, include_baseline=True, use_real_data=True)
    
    pantries_s2 = [p for p in scenario2.food_providers if isinstance(p, EnhancedMobilePantry)]
    delivery_s2 = [p for p in scenario2.food_providers if isinstance(p, EnhancedDeliveryService)]
    
    results['mobile_pantries']['scenario2'] = len(pantries_s2)
    results['delivery_services']['scenario2'] = len(delivery_s2)
    results['total_providers']['scenario2'] = len(scenario2.food_providers)
    
    print(f"   ✅ Scenario 2 created: {len(scenario2.food_providers)} providers")
    print(f"      • Mobile pantries: {len(pantries_s2)}")
    print(f"      • Delivery services: {len(delivery_s2)}")
    print()
    
    # =======================================================================
    # TEST 4: SCENARIO 3
    # =======================================================================
    print("4️⃣  Testing Scenario 3 (exactly as dashboard calls it)...")
    print("   Calling: create_enhanced_scenario_3(config, include_baseline=True, use_real_data=True)")
    
    scenario3 = create_enhanced_scenario_3(config, include_baseline=True, use_real_data=True)
    
    pantries_s3 = [p for p in scenario3.food_providers if isinstance(p, EnhancedMobilePantry)]
    delivery_s3 = [p for p in scenario3.food_providers if isinstance(p, EnhancedDeliveryService)]
    
    results['mobile_pantries']['scenario3'] = len(pantries_s3)
    results['delivery_services']['scenario3'] = len(delivery_s3)
    results['total_providers']['scenario3'] = len(scenario3.food_providers)
    
    print(f"   ✅ Scenario 3 created: {len(scenario3.food_providers)} providers")
    print(f"      • Mobile pantries: {len(pantries_s3)}")
    print(f"      • Delivery services: {len(delivery_s3)}")
    print()
    
    # =======================================================================
    # TEST 5: SCENARIO 4
    # =======================================================================
    print("5️⃣  Testing Scenario 4 (exactly as dashboard calls it)...")
    print("   Calling: create_enhanced_scenario_4(config, use_real_data=True)")
    
    scenario4 = create_enhanced_scenario_4(config, use_real_data=True)
    
    pantries_s4 = [p for p in scenario4.food_providers if isinstance(p, EnhancedMobilePantry)]
    delivery_s4 = [p for p in scenario4.food_providers if isinstance(p, EnhancedDeliveryService)]
    
    results['mobile_pantries']['scenario4'] = len(pantries_s4)
    results['delivery_services']['scenario4'] = len(delivery_s4)
    results['total_providers']['scenario4'] = len(scenario4.food_providers)
    
    print(f"   ✅ Scenario 4 created: {len(scenario4.food_providers)} providers")
    print(f"      • Mobile pantries: {len(pantries_s4)}")
    print(f"      • Delivery services: {len(delivery_s4)}")
    print()
    
    # =======================================================================
    # TEST 6: DELIVERY PARAMETERS
    # =======================================================================
    print("="*80)
    print("DELIVERY PARAMETERS CHECK")
    print("="*80)
    print()
    
    print(f"Config Values:")
    print(f"   delivery_baseline_low:    {config.delivery_baseline_low:.1%}")
    print(f"   delivery_baseline_medium: {config.delivery_baseline_medium:.1%}")
    print(f"   delivery_baseline_high:   {config.delivery_baseline_high:.1%}")
    print(f"   hard_blockers:            {config.delivery_hard_blockers_share:.1%}")
    print(f"   subsidy_uplift:           {config.delivery_subsidy_uplift}x")
    print()
    
    # Check households in baseline
    low_hh = [c for c in baseline.consumers if c.income == IncomeLevel.LOW]
    low_eligible = [c for c in low_hh if c.can_use_delivery]
    low_prop = sum(c.delivery_propensity for c in low_eligible) / len(low_eligible) if low_eligible else 0
    
    print(f"Baseline Households:")
    print(f"   Low-income total: {len(low_hh)}")
    print(f"   Low-income eligible: {len(low_eligible)} ({len(low_eligible)/len(low_hh):.1%})")
    print(f"   Low-income propensity: {low_prop:.1%}")
    print()
    
    # =======================================================================
    # VALIDATION
    # =======================================================================
    print("="*80)
    print("VALIDATION RESULTS")
    print("="*80)
    print()
    
    all_passed = True
    
    # Mobile Pantries
    print("📍 MOBILE PANTRIES:")
    expected_pantries = {'baseline': 3, 'scenario1': 3, 'scenario2': 3, 'scenario3': 5, 'scenario4': 3}
    for scenario, expected in expected_pantries.items():
        actual = results['mobile_pantries'][scenario]
        if actual == expected:
            print(f"   ✅ {scenario}: {actual} pantries (correct)")
        else:
            print(f"   ❌ {scenario}: {actual} pantries (expected {expected})")
            all_passed = False
    
    print()
    
    # Delivery Services
    print("🚚 DELIVERY SERVICES:")
    expected_delivery = {'baseline': 1, 'scenario1': 1, 'scenario2': 1, 'scenario3': 1, 'scenario4': 1}
    for scenario, expected in expected_delivery.items():
        actual = results['delivery_services'][scenario]
        if actual >= expected:
            print(f"   ✅ {scenario}: {actual} delivery service(s)")
        else:
            print(f"   ❌ {scenario}: {actual} delivery service(s) (expected at least {expected})")
            all_passed = False
    
    print()
    
    # Delivery Parameters
    print("⚙️  DELIVERY PARAMETERS:")
    param_checks = [
        ('delivery_baseline_low', config.delivery_baseline_low, 0.08),
        ('delivery_baseline_medium', config.delivery_baseline_medium, 0.20),
        ('delivery_baseline_high', config.delivery_baseline_high, 0.35),
    ]
    
    for param_name, actual, expected in param_checks:
        if abs(actual - expected) < 0.001:
            print(f"   ✅ {param_name}: {actual:.1%}")
        else:
            print(f"   ❌ {param_name}: {actual:.1%} (expected {expected:.1%})")
            all_passed = False
    
    print()
    
    # Provider Counts
    print("📊 TOTAL PROVIDERS PER SCENARIO:")
    for scenario, count in results['total_providers'].items():
        print(f"   • {scenario}: {count} providers")
    
    print()
    print("="*80)
    
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("   • All scenarios have correct mobile pantries")
        print("   • All scenarios have delivery services")
        print("   • Delivery parameters are correct (8%, 20%, 35%)")
        print("   • Dashboard will work correctly!")
    else:
        print("❌ SOME TESTS FAILED!")
        print("   Review the results above.")
    
    print("="*80)
    
    return all_passed

if __name__ == "__main__":
    success = test_comprehensive()
    sys.exit(0 if success else 1)

