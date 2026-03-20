"""
TEST: Verify ALL scenarios include mobile pantries from baseline
=================================================================
"""

import sys
sys.path.append('/Users/goshtasbshahriari/Desktop/Code/GeoMesa_Food_Access')

from enhanced_mesa_geo_model import SimulationConfig, EnhancedMobilePantry
from baseline_scenario import create_baseline_scenario
from enhanced_scenario_1 import EnhancedScenario1Model
from enhanced_scenario_2 import EnhancedScenario2Model
from enhanced_scenario_3 import EnhancedScenario3Model
from enhanced_scenario_4 import create_enhanced_scenario_4

def count_mobile_pantries(model):
    """Count mobile pantries in a model"""
    return sum(1 for p in model.food_providers if isinstance(p, EnhancedMobilePantry))

def test_all_scenarios_have_mobile_pantries():
    """Test that all 5 scenarios include the 3 baseline mobile pantries"""
    
    print("="*80)
    print("TESTING: All Scenarios Include Baseline Mobile Pantries")
    print("="*80)
    print()
    
    # Use same config for all scenarios
    config = SimulationConfig(
        num_consumers=10,  # Small for fast testing
        simulation_days=1
    )
    
    scenarios = {}
    
    # Create all scenarios
    print("📊 Creating all scenarios...")
    print()
    
    print("1️⃣  Baseline...")
    scenarios['Baseline'] = create_baseline_scenario(config=config)
    
    print("\n2️⃣  Scenario 1 (New Grocery Store)...")
    scenarios['Scenario 1'] = EnhancedScenario1Model(config=config, include_baseline=True)
    
    print("\n3️⃣  Scenario 2 (Food Hub Network)...")
    scenarios['Scenario 2'] = EnhancedScenario2Model(config=config, include_baseline=True)
    
    print("\n4️⃣  Scenario 3 (Mobile Pantries)...")
    scenarios['Scenario 3'] = EnhancedScenario3Model(config=config, include_baseline=True)
    
    print("\n5️⃣  Scenario 4 (Subsidized Delivery)...")
    scenarios['Scenario 4'] = create_enhanced_scenario_4(config=config, use_real_data=True)
    
    # Count mobile pantries in each
    print()
    print("="*80)
    print("MOBILE PANTRY COUNT")
    print("="*80)
    print()
    
    results = {}
    for name, model in scenarios.items():
        pantry_count = count_mobile_pantries(model)
        results[name] = pantry_count
        
        # Find pantry names
        pantries = [p for p in model.food_providers if isinstance(p, EnhancedMobilePantry)]
        pantry_names = [getattr(p, 'name', 'Unnamed Pantry') for p in pantries]
        
        print(f"{name}:")
        print(f"   Mobile Pantries: {pantry_count}")
        for pname in pantry_names:
            print(f"      • {pname}")
        print()
    
    # Validation
    print("="*80)
    print("VALIDATION")
    print("="*80)
    print()
    
    success = True
    expected_baseline = 3  # 3 real mobile pantries from Feeding Northeast Florida
    expected_scenario3 = 5  # 3 baseline + 2 new = 5 total
    
    # Baseline should have 3
    if results['Baseline'] == expected_baseline:
        print(f"✅ Baseline has {results['Baseline']} mobile pantries (expected {expected_baseline})")
    else:
        print(f"⚠️  Baseline has {results['Baseline']} mobile pantries (expected {expected_baseline})")
        success = False
    
    # Scenario 1 should have 3 (baseline only)
    if results['Scenario 1'] == expected_baseline:
        print(f"✅ Scenario 1 has {results['Scenario 1']} mobile pantries (expected {expected_baseline})")
    else:
        print(f"⚠️  Scenario 1 has {results['Scenario 1']} mobile pantries (expected {expected_baseline})")
        success = False
    
    # Scenario 2 should have 3 (baseline only)
    if results['Scenario 2'] == expected_baseline:
        print(f"✅ Scenario 2 has {results['Scenario 2']} mobile pantries (expected {expected_baseline})")
    else:
        print(f"⚠️  Scenario 2 has {results['Scenario 2']} mobile pantries (expected {expected_baseline})")
        success = False
    
    # Scenario 3 should have 5 (3 baseline + 2 new)
    if results['Scenario 3'] == expected_scenario3:
        print(f"✅ Scenario 3 has {results['Scenario 3']} mobile pantries (expected {expected_scenario3} = 3 baseline + 2 new)")
    else:
        print(f"⚠️  Scenario 3 has {results['Scenario 3']} mobile pantries (expected {expected_scenario3} = 3 baseline + 2 new)")
        success = False
    
    # Scenario 4 should have 3 (baseline only)
    if results['Scenario 4'] == expected_baseline:
        print(f"✅ Scenario 4 has {results['Scenario 4']} mobile pantries (expected {expected_baseline})")
    else:
        print(f"⚠️  Scenario 4 has {results['Scenario 4']} mobile pantries (expected {expected_baseline})")
        success = False
    
    print()
    if success:
        print("✅ SUCCESS! All scenarios have correct number of mobile pantries!")
        print("   • Baseline: 3 real mobile pantries from Feeding Northeast Florida")
        print("   • Scenarios 1, 2, 4: 3 baseline mobile pantries")
        print("   • Scenario 3: 5 total (3 baseline + 2 new intervention pantries)")
    else:
        print("⚠️  FAILURE! Some scenarios have incorrect mobile pantry counts")
    print("="*80)
    
    return success

if __name__ == "__main__":
    success = test_all_scenarios_have_mobile_pantries()
    sys.exit(0 if success else 1)

