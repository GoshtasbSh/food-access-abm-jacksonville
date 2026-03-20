"""
Enhanced Scenario 3: Mobile Food Pantries (Street Delivery)
==========================================================

This scenario adds MOBILE food pantries to BASELINE providers.
Mobile pantries operate on specific days and locations with strategies:
- fixed: predefined street locations
- rotating: different fixed area each day
- needs_based: place near unsatisfied consumer clusters

Comparison: Baseline + Mobile Pantries vs. Baseline Only
"""

from enhanced_mesa_geo_model import (
    EnhancedMesaGeoModel, SimulationConfig, IncomeLevel, ProviderType,
    EnhancedMobilePantry, IncomeClassifier
)
from baseline_scenario import load_real_provider_data, add_baseline_mobile_pantries, add_baseline_delivery_service  # ⭐ NEW: Uses real data loader
from hz1_census_data_loader import HZ1CensusDataLoader  # ⭐ NEW: Real census demographics
from shapely.geometry import Point
import random
import numpy as np
from typing import Dict, Any, List

class EnhancedScenario3Model(EnhancedMesaGeoModel):
    """
    Scenario 3: Baseline + Mobile Food Pantries
    
    Adds mobile food pantries to existing baseline providers
    """
    def __init__(self, config: SimulationConfig = None,
                 include_baseline: bool = True,
                 use_real_data: bool = True):
        """
        Initialize Scenario 3 with baseline + mobile pantries
        
        Args:
            config: Simulation configuration
            include_baseline: Whether to include existing baseline providers
            use_real_data: Whether to use real provider locations for baseline
        """
        if config is None:
            config = SimulationConfig()
        super().__init__(config)
        self.scenario_name = "Scenario 3: Baseline + Mobile Pantries"
        self.include_baseline = include_baseline
        self.use_real_data = use_real_data
        self.mobile_pantries = []  # References to NEW mobile pantries
        self.setup_scenario()
    
    def setup_scenario(self):
        num_consumers = self.config.num_consumers
        num_mobile = self.config.num_mobile_pantries
        pantry_capacity = self.config.mobile_pantry_capacity
        strategy = getattr(self.config, 'mobile_pantry_strategy', 'fixed')
        
        print(f"🚚 Setting up Scenario 3: Baseline + Mobile Pantries")
        print(f"   Consumers: {num_consumers}")
        print(f"   NEW Mobile Pantries: {num_mobile} (capacity {pantry_capacity})")
        print(f"   Strategy: {strategy}")
        print(f"   Include Baseline Providers: {self.include_baseline}")
        
        # ===================================================================
        # ADD HOUSEHOLDS USING REAL CENSUS TRACT DATA (same as baseline)
        # ===================================================================
        print(f"\n   👥 Creating {num_consumers} households from REAL HZ1 census data:")
        
        # ⭐ USE REAL CENSUS DATA from Health Zone 1 (same as baseline)
        real_census = HZ1CensusDataLoader()
        
        print(f"      Income cutoffs (2023):")
        print(f"         Low: < ${IncomeClassifier.LOW_THRESHOLD:,.0f}")
        print(f"         Medium: ${IncomeClassifier.LOW_THRESHOLD:,.0f} - ${IncomeClassifier.HIGH_THRESHOLD:,.0f}")
        print(f"         High: > ${IncomeClassifier.HIGH_THRESHOLD:,.0f}")
        print(f"      REAL Demographics from HZ1 (37 tracts, 48,044 households):")
        print(f"         Low income: {real_census.real_data.income_distribution['low']:.1%}")
        print(f"         Medium income: {real_census.real_data.income_distribution['medium']:.1%}")
        print(f"         High income: {real_census.real_data.income_distribution['high']:.1%}")
        print(f"         No vehicle: {real_census.real_data.no_vehicle_rate:.1%}")
        print(f"         SNAP eligible: {real_census.real_data.snap_rate_overall:.1%}")
        print(f"         Black: {real_census.real_data.race_distribution['black']:.1%}, White: {real_census.real_data.race_distribution['white']:.1%}")
        
        # Generate and add households using REAL data (same as baseline)
        households_data = real_census.generate_household_demographics(num_consumers)
        
        for hh_demo in households_data:
            # Add household to model using household method
            self.add_household(
                income=hh_demo['income'],
                vehicle_available=hh_demo['vehicle_available'],
                household_size=hh_demo['household_size'],
                race=hh_demo['race'],
                snap_eligible=hh_demo['snap_eligible'],
                annual_income=hh_demo['annual_income'],
                census_tract=hh_demo['census_tract'],
                zip_code=hh_demo.get('zip_code')
            )
        
        print(f"   ✅ Added {len(self.consumers)} households")
        
        # STEP 1: Add existing baseline providers (if enabled)
        baseline_stores_added = 0
        if self.include_baseline:
            print(f"\n   📍 Adding EXISTING baseline providers:")
            provider_data = load_real_provider_data(use_geocoding=False)
            
            # Add existing grocery stores
            for name, lon, lat, capacity in provider_data['grocery_stores']:
                location = Point(lon, lat)
                store = self.add_grocery_store(location, capacity)
                store.name = name  # Set actual store name
                print(f"      • Existing: {name} (capacity: {capacity})")
                baseline_stores_added += 1
            
            # Add existing corner stores
            for name, lon, lat, capacity in provider_data['corner_stores']:
                location = Point(lon, lat)
                store = self.add_corner_store(location, capacity)
                store.name = name  # Set actual store name
                print(f"      • Existing: {name} (capacity: {capacity})")
                baseline_stores_added += 1
            
            # ⭐ ADD REAL MOBILE PANTRIES (same as baseline)
            pantries_added = add_baseline_mobile_pantries(self)
            baseline_stores_added += pantries_added
            
            # ⭐ ADD BASELINE DELIVERY SERVICE (same as baseline)
            delivery_added = add_baseline_delivery_service(self)
            baseline_stores_added += delivery_added
        
        # STEP 2: Add NEW mobile pantries (the intervention)
        print(f"\n   🆕 Adding {num_mobile} NEW mobile pantries (INTERVENTION):")
        for i in range(num_mobile):
            pantry = self.add_mobile_pantry(capacity=pantry_capacity)
            self.mobile_pantries.append(pantry)
            print(f"      • NEW Mobile Pantry {i+1} (capacity: {pantry_capacity}, strategy: {strategy})")
        
        print(f"\n   ✅ Scenario 3 setup complete:")
        print(f"      • Consumers: {len(self.consumers)}")
        print(f"      • Existing providers: {baseline_stores_added}")
        print(f"      • New providers: {num_mobile} (mobile pantries)")
        print(f"      • Total providers: {len(self.food_providers)}")
        
        # Initial accessibility computation
        for consumer in self.consumers:
            consumer.update_accessibility_score()
        initial_access = np.mean([c.accessibility_score for c in self.consumers])
        print(f"      • Initial avg accessibility: {initial_access:.2f}")
    
    def analyze_mobile_pantry_performance(self) -> Dict[str, Any]:
        summary = self.get_simulation_summary()
        pantries = [p for p in self.food_providers if getattr(p, 'provider_type', None) == ProviderType.MOBILE_PANTRY]
        if not pantries:
            summary['mobile_pantry_analysis'] = {}
            return summary
        
        utilizations = [np.mean(p.utilization_history) if p.utilization_history else 0 for p in pantries]
        total_customers = sum(len(p.customer_history) for p in pantries)
        avg_distance = self._calculate_avg_travel_distance()
        
        summary['mobile_pantry_analysis'] = {
            'pantry_count': len(pantries),
            'avg_utilization': float(np.mean(utilizations) if utilizations else 0),
            'total_customers_served': total_customers,
            'avg_travel_distance': avg_distance,
            'strategy': getattr(self.config, 'mobile_pantry_strategy', 'fixed')
        }
        return summary
    
    def get_detailed_report(self) -> str:
        res = self.analyze_mobile_pantry_performance()
        m = res.get('mobile_pantry_analysis', {})
        return f"""
Enhanced Scenario 3: Mobile Pantry Deployment Report
===================================================
Pantries: {m.get('pantry_count', 0)}
Average Utilization: {m.get('avg_utilization', 0):.2%}
Total Customers Served: {m.get('total_customers_served', 0)}
Average Travel Distance: {m.get('avg_travel_distance', 0):.2f} km
Strategy: {m.get('strategy', 'fixed')}
"""

def create_enhanced_scenario_3(config: SimulationConfig = None,
                              include_baseline: bool = True,
                              use_real_data: bool = True) -> EnhancedScenario3Model:
    """
    Create and return Enhanced Scenario 3 model
    
    Args:
        config: Simulation configuration object with all parameters
        include_baseline: Whether to include existing baseline providers
        use_real_data: Whether to use real provider locations
    
    Returns:
        Configured EnhancedScenario3Model ready for simulation
    """
    return EnhancedScenario3Model(config, include_baseline, use_real_data)


# Example usage and testing
if __name__ == "__main__":
    print("🚀 Enhanced Scenario 3: Mobile Food Pantries")
    print("=" * 60)
    
    # Create configuration
    config = SimulationConfig(
        num_consumers=300,
        simulation_days=14,
        num_mobile_pantries=3,
        mobile_pantry_capacity=100
    )
    
    # Create and run scenario
    scenario3 = create_enhanced_scenario_3(config, include_baseline=True)
    
    print("\n⏳ Running simulation...")
    for day in range(14):
        scenario3.step()
        if day % 3 == 0:
            satisfaction = scenario3._calculate_satisfaction_rate()
            print(f"   Day {day + 1}: Satisfaction Rate {satisfaction:.2%}")
    
    # Analyze results
    print("\n📊 Analyzing mobile pantry performance...")
    results = scenario3.analyze_mobile_pantry_performance()
    
    print(f"\n📈 Final Results:")
    print(f"   Satisfaction Rate: {results['overall_metrics']['avg_satisfaction_rate']:.2%}")
    print(f"   Food Insecurity Rate: {results['overall_metrics']['avg_food_insecurity_rate']:.2%}")
    print(f"   Average Travel Distance: {results['overall_metrics']['avg_travel_distance']:.2f} km")
    print(f"   Spatial Equity Index: {results['overall_metrics']['spatial_equity_index']:.3f}")
    
    print("\n🚚 Mobile Pantry Metrics:")
    if 'mobile_pantry_metrics' in results:
        for pantry_metrics in results['mobile_pantry_metrics']:
            print(f"   Total Customers Served: {pantry_metrics.get('total_customers_served', 0)}")
    else:
        print(f"   Mobile pantries added: {config.num_mobile_pantries}")
    
    print("\n✅ Enhanced Scenario 3 simulation complete!")
