"""
Enhanced Scenario 1: New Grocery Store Impact Analysis
=====================================================

This scenario analyzes the impact of introducing a NEW grocery store
in Health Zone 1 PLUS existing baseline providers.

Comparison: Baseline + New Grocery Store vs. Baseline Only
"""

from enhanced_mesa_geo_model import (
    EnhancedMesaGeoModel, SimulationConfig, IncomeLevel, ProviderType, IncomeClassifier
)
from baseline_scenario import load_real_provider_data, add_baseline_mobile_pantries, add_baseline_delivery_service  # ⭐ NEW: Uses real data loader
from hz1_census_data_loader import HZ1CensusDataLoader  # ⭐ NEW: Real census demographics
from shapely.geometry import Point
import random
import numpy as np
from typing import Dict, Any

class EnhancedScenario1Model(EnhancedMesaGeoModel):
    """
    Enhanced Scenario 1: New Grocery Store Impact Analysis
    
    This scenario analyzes the impact of introducing a new grocery store
    in Health Zone 1 using enhanced spatial analytics.
    
    Key Features:
    - Single large grocery store with high capacity
    - Realistic demographic distribution based on Health Zone 1 data
    - Enhanced spatial accessibility analysis
    - Detailed store performance metrics
    """
    
    def __init__(self, config: SimulationConfig = None, 
                 include_baseline: bool = True,
                 use_real_data: bool = True):
        """
        Initialize Scenario 1 with baseline + new grocery store
        
        Args:
            config: Simulation configuration
            include_baseline: Whether to include existing baseline providers
            use_real_data: Whether to use real provider locations for baseline
        """
        if config is None:
            config = SimulationConfig()
        
        super().__init__(config)
        self.scenario_name = "Scenario 1: Baseline + New Grocery Store"
        self.include_baseline = include_baseline
        self.use_real_data = use_real_data
        self.new_store = None  # Will store reference to the NEW grocery store
        self.setup_scenario()
    
    def setup_scenario(self):
        """Setup scenario with baseline providers + NEW grocery store"""
        
        num_consumers = self.config.num_consumers
        new_store_capacity = self.config.grocery_store_capacity
        
        print(f"🏪 Setting up Scenario 1: Baseline + New Grocery Store")
        print(f"   Consumers: {num_consumers}")
        print(f"   New Store Capacity: {new_store_capacity}")
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
        
        print(f"   ✅ Added {len(self.consumers)} consumers")
        
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
        
        # STEP 2: Add NEW grocery store (the intervention)
        print(f"\n   🆕 Adding NEW grocery store (INTERVENTION):")
        # Find optimal location for new store (avoiding existing stores)
        new_store_location = self._find_optimal_new_store_location()
        self.new_store = self.add_grocery_store(new_store_location, new_store_capacity)
        
        print(f"      • NEW Grocery Store at ({self.new_store.geometry.x:.3f}, {self.new_store.geometry.y:.3f})")
        print(f"      • Capacity: {new_store_capacity}")
        
        print(f"\n   ✅ Scenario 1 setup complete:")
        print(f"      • Consumers: {len(self.consumers)}")
        print(f"      • Existing providers: {baseline_stores_added}")
        print(f"      • New providers: 1 (grocery store)")
        print(f"      • Total providers: {len(self.food_providers)}")
        
        # Calculate initial accessibility scores
        for consumer in self.consumers:
            consumer.update_accessibility_score()
        
        print(f"   📊 Initial average accessibility score: {np.mean([c.accessibility_score for c in self.consumers]):.2f}")
    
    def _find_optimal_new_store_location(self) -> Point:
        """
        Find optimal location for new grocery store
        - Avoid placing on top of existing stores
        - Target area with poor coverage
        """
        # Get bounds of health zone
        bounds = self.health_zone_polygon.bounds
        min_lon, min_lat, max_lon, max_lat = bounds
        
        # If no existing stores, use centroid
        if not self.food_providers:
            return self.health_zone_polygon.centroid
        
        # Optional regional constraint from dashboard (north/west/east/south/center)
        region = str(getattr(self.config, "scenario1_store_region", "optimal") or "optimal").lower()
        mid_lon = (min_lon + max_lon) / 2.0
        mid_lat = (min_lat + max_lat) / 2.0
        lon_span = max_lon - min_lon
        lat_span = max_lat - min_lat

        def _candidate_in_region(candidate: Point) -> bool:
            if region == "north":
                return candidate.y >= mid_lat
            if region == "south":
                return candidate.y <= mid_lat
            if region == "east":
                return candidate.x >= mid_lon
            if region == "west":
                return candidate.x <= mid_lon
            if region == "center":
                return (
                    abs(candidate.x - mid_lon) <= lon_span * 0.20 and
                    abs(candidate.y - mid_lat) <= lat_span * 0.20
                )
            return True  # "optimal" searches whole polygon

        # Create a grid of candidate locations
        num_candidates = 20
        lon_range = np.linspace(min_lon + 0.01, max_lon - 0.01, int(np.sqrt(num_candidates)))
        lat_range = np.linspace(min_lat + 0.01, max_lat - 0.01, int(np.sqrt(num_candidates)))
        
        best_location = None
        best_score = -float('inf')
        
        for lon in lon_range:
            for lat in lat_range:
                candidate = Point(lon, lat)
                
                # Check if within health zone
                if not self.health_zone_polygon.contains(candidate):
                    continue
                if not _candidate_in_region(candidate):
                    continue
                
                # Calculate score: maximize distance to existing stores, minimize distance to underserved consumers
                min_dist_to_store = float('inf')
                for provider in self.food_providers:
                    dist = candidate.distance(provider.geometry)
                    min_dist_to_store = min(min_dist_to_store, dist)
                
                # Avoid placing too close to existing stores
                if min_dist_to_store < 0.01:  # ~1km minimum separation
                    continue
                
                # Calculate avg distance to consumers (want to be accessible)
                avg_dist_to_consumers = np.mean([candidate.distance(c.geometry) for c in self.consumers])
                
                # Score: balance being away from existing stores but close to consumers
                score = min_dist_to_store * 2.0 - avg_dist_to_consumers
                
                if score > best_score:
                    best_score = score
                    best_location = candidate
        
        # If no valid location found, offset from centroid
        if best_location is None:
            centroid = self.health_zone_polygon.centroid
            # Offset by 0.02 degrees (~2km) to avoid existing store
            best_location = Point(centroid.x + 0.02, centroid.y + 0.02)
            print(f"      ⚠️  Using offset from centroid (no optimal location found in region '{region}')")
        
        return best_location
    
    def analyze_scenario_outcomes(self) -> Dict[str, Any]:
        """Analyze scenario-specific outcomes with detailed grocery store metrics"""
        summary = self.get_simulation_summary()
        
        # Use the new_store reference (the actual intervention store added last)
        # food_providers[0] would be the first baseline store, which is wrong when include_baseline=True
        grocery_store = self.new_store if self.new_store is not None else self.food_providers[0]
        
        scenario_analysis = {
            'scenario_type': 'grocery_store',
            'store_performance': {
                'total_customers_served': len(grocery_store.customer_history),
                'avg_daily_utilization': np.mean(grocery_store.utilization_history) if grocery_store.utilization_history else 0,
                'customer_satisfaction': grocery_store.customer_satisfaction,
                'service_area_coverage': self._calculate_service_area_coverage(),
                'peak_capacity_reached': max(grocery_store.utilization_history) if grocery_store.utilization_history else 0
            },
            'consumer_impact': {
                'within_walking_distance': self._count_consumers_within_distance(2.0),
                'within_driving_distance': self._count_consumers_within_distance(10.0),
                'avg_accessibility_improvement': self._calculate_accessibility_improvement(),
                'consumers_served_percentage': self._calculate_consumers_served_percentage()
            },
            'equity_analysis': {
                'low_income_satisfaction': self._calculate_satisfaction_by_income(IncomeLevel.LOW),
                'medium_income_satisfaction': self._calculate_satisfaction_by_income(IncomeLevel.MEDIUM),
                'high_income_satisfaction': self._calculate_satisfaction_by_income(IncomeLevel.HIGH),
                'car_vs_no_car_satisfaction': self._compare_car_ownership_satisfaction()
            }
        }
        
        summary['scenario_analysis'] = scenario_analysis
        return summary
    
    def _calculate_service_area_coverage(self) -> float:
        """Calculate what percentage of consumers are within service area"""
        grocery_store = self.new_store if self.new_store is not None else self.food_providers[0]
        within_service = 0
        
        for consumer in self.consumers:
            distance = self.calculate_distance(consumer.geometry, grocery_store.geometry)
            if distance <= consumer.max_travel_distance:
                within_service += 1
        
        return within_service / len(self.consumers) if self.consumers else 0
    
    def _count_consumers_within_distance(self, max_distance: float) -> int:
        """Count consumers within specified distance of grocery store"""
        grocery_store = self.new_store if self.new_store is not None else self.food_providers[0]
        count = 0
        
        for consumer in self.consumers:
            distance = self.calculate_distance(consumer.geometry, grocery_store.geometry)
            if distance <= max_distance:
                count += 1
        
        return count
    
    def _calculate_accessibility_improvement(self) -> float:
        """Calculate average accessibility improvement"""
        # This represents the current accessibility score (in a real comparison,
        # you'd compare against a baseline scenario without the store)
        return np.mean([c.accessibility_score for c in self.consumers])
    
    def _calculate_consumers_served_percentage(self) -> float:
        """Calculate what percentage of consumers were served during simulation"""
        grocery_store = self.new_store if self.new_store is not None else self.food_providers[0]
        served_consumer_ids = set(record['customer_id'] for record in grocery_store.customer_history)
        return len(served_consumer_ids) / len(self.consumers) if self.consumers else 0
    
    def _calculate_satisfaction_by_income(self, income_level: IncomeLevel) -> float:
        """Calculate satisfaction rate for specific income level"""
        income_consumers = [c for c in self.consumers if c.income == income_level]
        if not income_consumers:
            return 0.0
        
        satisfied = sum(1 for c in income_consumers if c.satisfied_today)
        return satisfied / len(income_consumers)
    
    def _compare_car_ownership_satisfaction(self) -> Dict[str, float]:
        """Compare satisfaction rates between car owners and non-car owners"""
        car_owners = [c for c in self.consumers if c.vehicle_available]
        non_car_owners = [c for c in self.consumers if not c.vehicle_available]
        
        car_satisfaction = (sum(1 for c in car_owners if c.satisfied_today) / len(car_owners)) if car_owners else 0
        no_car_satisfaction = (sum(1 for c in non_car_owners if c.satisfied_today) / len(non_car_owners)) if non_car_owners else 0
        
        return {
            'with_car': car_satisfaction,
            'without_car': no_car_satisfaction,
            'difference': car_satisfaction - no_car_satisfaction
        }
    
    def get_detailed_report(self) -> str:
        """Generate a detailed text report for Scenario 1"""
        results = self.analyze_scenario_outcomes()
        
        report = f"""
Enhanced Scenario 1: New Grocery Store Analysis Report
=====================================================

Simulation Parameters:
- Consumers: {len(self.consumers)}
- Simulation Days: {self.current_day}
- New Grocery Store Capacity: {(self.new_store if self.new_store is not None else self.food_providers[0]).capacity}

Overall Performance:
- Average Satisfaction Rate: {results['overall_metrics']['avg_satisfaction_rate']:.2%}
- Average Food Insecurity Rate: {results['overall_metrics']['avg_food_insecurity_rate']:.2%}
- Average Travel Distance: {results['overall_metrics']['avg_travel_distance']:.2f} km
- Spatial Equity Index: {results['overall_metrics']['spatial_equity_index']:.3f}

Store Performance:
- Total Customers Served: {results['scenario_analysis']['store_performance']['total_customers_served']}
- Average Daily Utilization: {results['scenario_analysis']['store_performance']['avg_daily_utilization']:.2%}
- Service Area Coverage: {results['scenario_analysis']['store_performance']['service_area_coverage']:.2%}
- Customer Satisfaction: {results['scenario_analysis']['store_performance']['customer_satisfaction']:.2f}/1.0

Consumer Impact:
- Within Walking Distance (2km): {results['scenario_analysis']['consumer_impact']['within_walking_distance']}
- Within Driving Distance (10km): {results['scenario_analysis']['consumer_impact']['within_driving_distance']}
- Consumers Served Overall: {results['scenario_analysis']['consumer_impact']['consumers_served_percentage']:.2%}

Equity Analysis:
- Low Income Satisfaction: {results['scenario_analysis']['equity_analysis']['low_income_satisfaction']:.2%}
- Medium Income Satisfaction: {results['scenario_analysis']['equity_analysis']['medium_income_satisfaction']:.2%}
- High Income Satisfaction: {results['scenario_analysis']['equity_analysis']['high_income_satisfaction']:.2%}
- Car Owners vs Non-Car Owners: {results['scenario_analysis']['equity_analysis']['car_vs_no_car_satisfaction']['difference']:+.2%} difference
"""
        
        return report

def create_enhanced_scenario_1(config: SimulationConfig = None,
                              include_baseline: bool = True,
                              use_real_data: bool = True) -> EnhancedScenario1Model:
    """
    Create and return Enhanced Scenario 1 model
    
    Args:
        config: Simulation configuration object with all parameters
        include_baseline: Whether to include existing baseline providers
        use_real_data: Whether to use real provider locations
    
    Returns:
        Configured EnhancedScenario1Model ready for simulation
    """
    return EnhancedScenario1Model(config, include_baseline, use_real_data)

# Example usage and testing
if __name__ == "__main__":
    print("🚀 Enhanced Scenario 1: New Grocery Store")
    print("=" * 50)
    
    # Create configuration and run scenario
    config = SimulationConfig(num_consumers=300, grocery_store_capacity=600, simulation_days=14)
    scenario1 = create_enhanced_scenario_1(config)
    
    print("\n⏳ Running simulation...")
    for day in range(14):
        scenario1.step()
        if day % 3 == 0:  # Progress update every 3 days
            satisfaction = scenario1._calculate_satisfaction_rate()
            print(f"   Day {day + 1}: Satisfaction Rate {satisfaction:.2%}")
    
    # Analyze results
    print("\n📊 Analyzing results...")
    results = scenario1.analyze_scenario_outcomes()
    
    # Print summary
    print(f"\n📈 Final Results:")
    print(f"   Satisfaction Rate: {results['overall_metrics']['avg_satisfaction_rate']:.2%}")
    print(f"   Food Insecurity Rate: {results['overall_metrics']['avg_food_insecurity_rate']:.2%}")
    print(f"   Average Travel Distance: {results['overall_metrics']['avg_travel_distance']:.2f} km")
    print(f"   Spatial Equity Index: {results['overall_metrics']['spatial_equity_index']:.3f}")
    
    # Store-specific metrics
    store_performance = results['scenario_analysis']['store_performance']
    print(f"\n🏪 Store Performance:")
    print(f"   Service Area Coverage: {store_performance['service_area_coverage']:.2%}")
    print(f"   Average Utilization: {store_performance['avg_daily_utilization']:.2%}")
    print(f"   Total Customers Served: {store_performance['total_customers_served']}")
    
    # Equity analysis
    equity = results['scenario_analysis']['equity_analysis']
    print(f"\n⚖️  Equity Analysis:")
    print(f"   Low Income Satisfaction: {equity['low_income_satisfaction']:.2%}")
    print(f"   Medium Income Satisfaction: {equity['medium_income_satisfaction']:.2%}")
    print(f"   High Income Satisfaction: {equity['high_income_satisfaction']:.2%}")
    
    print("\n✅ Enhanced Scenario 1 simulation complete!")
    
    # Optionally print detailed report
    # print(scenario1.get_detailed_report()) 