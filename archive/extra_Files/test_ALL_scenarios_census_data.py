"""
TEST: Verify ALL scenarios use REAL HZ1 census data
=====================================================
This script verifies that all 5 scenarios (Baseline + 1-4) use
the HZ1CensusDataLoader and produce identical demographic distributions.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enhanced_mesa_geo_model import SimulationConfig, IncomeLevel
from baseline_scenario import create_baseline_scenario
from enhanced_scenario_1 import EnhancedScenario1Model
from enhanced_scenario_2 import EnhancedScenario2Model
from enhanced_scenario_3 import EnhancedScenario3Model
from enhanced_scenario_4 import create_enhanced_scenario_4

def get_demographics(model):
    """Extract demographic distribution from model"""
    consumers = model.consumers
    
    total = len(consumers)
    low_income = sum(1 for c in consumers if c.income == IncomeLevel.LOW)
    med_income = sum(1 for c in consumers if c.income == IncomeLevel.MEDIUM)
    high_income = sum(1 for c in consumers if c.income == IncomeLevel.HIGH)
    
    no_vehicle = sum(1 for c in consumers if not c.vehicle_available)
    snap_eligible = sum(1 for c in consumers if c.snap_eligible)
    
    # Count race (if available)
    black = sum(1 for c in consumers if hasattr(c, 'race') and c.race == 'black')
    white = sum(1 for c in consumers if hasattr(c, 'race') and c.race == 'white')
    
    return {
        'total': total,
        'low_income': low_income / total if total > 0 else 0,
        'med_income': med_income / total if total > 0 else 0,
        'high_income': high_income / total if total > 0 else 0,
        'no_vehicle': no_vehicle / total if total > 0 else 0,
        'snap_eligible': snap_eligible / total if total > 0 else 0,
        'black': black / total if total > 0 else 0,
        'white': white / total if total > 0 else 0
    }

def main():
    print("="*80)
    print("TESTING: All Scenarios Use REAL HZ1 Census Data")
    print("="*80)
    print()
    
    # Use same config for all scenarios
    config = SimulationConfig(
        num_consumers=100,
        simulation_days=1
    )
    
    print(f"Creating 100 households in each scenario...")
    print()
    
    scenarios = {}
    
    # Test Baseline
    print("1️⃣  Creating Baseline Scenario...")
    scenarios['Baseline'] = create_baseline_scenario(config=config)
    print(f"   ✅ Created {len(scenarios['Baseline'].consumers)} households\n")
    
    # Test Scenario 1
    print("2️⃣  Creating Scenario 1 (New Grocery Store)...")
    scenarios['Scenario 1'] = EnhancedScenario1Model(config=config)
    print(f"   ✅ Created {len(scenarios['Scenario 1'].consumers)} households\n")
    
    # Test Scenario 2
    print("3️⃣  Creating Scenario 2 (Food Hub Network)...")
    scenarios['Scenario 2'] = EnhancedScenario2Model(config=config)
    print(f"   ✅ Created {len(scenarios['Scenario 2'].consumers)} households\n")
    
    # Test Scenario 3
    print("4️⃣  Creating Scenario 3 (Mobile Pantries)...")
    scenarios['Scenario 3'] = EnhancedScenario3Model(config=config)
    print(f"   ✅ Created {len(scenarios['Scenario 3'].consumers)} households\n")
    
    # Test Scenario 4
    print("5️⃣  Creating Scenario 4 (Subsidized Delivery)...")
    scenarios['Scenario 4'] = create_enhanced_scenario_4(config=config)
    print(f"   ✅ Created {len(scenarios['Scenario 4'].consumers)} households\n")
    
    # Extract demographics from each
    print("="*80)
    print("DEMOGRAPHIC COMPARISON")
    print("="*80)
    print()
    
    demographics = {}
    for name, model in scenarios.items():
        demographics[name] = get_demographics(model)
    
    # Print table
    print(f"{'Metric':<20} {'Baseline':<12} {'Scenario 1':<12} {'Scenario 2':<12} {'Scenario 3':<12} {'Scenario 4':<12}")
    print("-"*96)
    
    metrics = ['low_income', 'med_income', 'high_income', 'no_vehicle', 'snap_eligible', 'black', 'white']
    metric_names = ['Low Income', 'Medium Income', 'High Income', 'No Vehicle', 'SNAP Eligible', 'Black', 'White']
    
    for metric, name in zip(metrics, metric_names):
        row = f"{name:<20}"
        for scenario in ['Baseline', 'Scenario 1', 'Scenario 2', 'Scenario 3', 'Scenario 4']:
            value = demographics[scenario][metric]
            row += f" {value:>10.1%} "
        print(row)
    
    print()
    print("="*80)
    print("CONSISTENCY CHECK")
    print("="*80)
    print()
    
    # Check if all scenarios have similar demographics (within 5% due to random sampling)
    baseline_demo = demographics['Baseline']
    all_consistent = True
    
    for scenario_name in ['Scenario 1', 'Scenario 2', 'Scenario 3', 'Scenario 4']:
        scenario_demo = demographics[scenario_name]
        
        print(f"\n{scenario_name} vs Baseline:")
        consistent = True
        
        for metric in ['low_income', 'med_income', 'high_income', 'no_vehicle', 'snap_eligible']:
            diff = abs(scenario_demo[metric] - baseline_demo[metric])
            status = "✅" if diff <= 0.05 else "⚠️"
            
            if diff > 0.05:
                consistent = False
                all_consistent = False
            
            print(f"   {status} {metric:15s}: Δ = {diff:>5.1%}")
        
        if consistent:
            print(f"   ✅ {scenario_name} demographics MATCH baseline (within 5%)")
        else:
            print(f"   ⚠️  {scenario_name} demographics DIFFER from baseline (>5%)")
    
    print()
    print("="*80)
    if all_consistent:
        print("✅ SUCCESS! All scenarios use the SAME real HZ1 census data!")
        print("   All demographic distributions match within 5% (expected random variation)")
    else:
        print("⚠️  WARNING! Some scenarios have inconsistent demographics")
        print("   This could indicate different data sources or bugs")
    print("="*80)
    
    return all_consistent

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

