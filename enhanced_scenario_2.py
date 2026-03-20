"""
Enhanced Scenario 2: Food Hub + Corner Stores Network Analysis
==============================================================

This scenario analyzes a distributed food access network with BASELINE providers
plus a NEW central food hub and ADDITIONAL corner stores in Health Zone 1.

Comparison: Baseline + Food Hub Network vs. Baseline Only
"""

from enhanced_mesa_geo_model import (
    EnhancedMesaGeoModel, SimulationConfig, IncomeLevel, ProviderType, IncomeClassifier
)
from baseline_scenario import load_real_provider_data, add_baseline_mobile_pantries, add_baseline_delivery_service  # ⭐ NEW: Uses real data loader
from hz1_census_data_loader import HZ1CensusDataLoader  # ⭐ NEW: Real census demographics
from shapely.geometry import Point
import random
import numpy as np
from typing import Dict, Any, List

class EnhancedScenario2Model(EnhancedMesaGeoModel):
    """
    Enhanced Scenario 2: Food Hub + Corner Stores Network
    
    This scenario analyzes a distributed food access network with
    a central food hub supplying multiple corner stores.
    
    Key Features:
    - Central food hub operating on market days (Mon, Wed, Fri)
    - Multiple corner stores distributed across Health Zone 1
    - Network redundancy and accessibility analysis
    - Spatial optimization for store placement
    - Advanced network performance metrics
    """
    
    def __init__(self, config: SimulationConfig = None,
                 include_baseline: bool = True,
                 use_real_data: bool = True):
        """
        Initialize Scenario 2 with baseline + food hub network
        
        Args:
            config: Simulation configuration
            include_baseline: Whether to include existing baseline providers
            use_real_data: Whether to use real provider locations for baseline
        """
        if config is None:
            config = SimulationConfig()
        
        super().__init__(config)
        self.scenario_name = "Scenario 2: Baseline + Food Hub Network"
        self.include_baseline = include_baseline
        self.use_real_data = use_real_data
        self.new_food_hub = None  # Reference to NEW food hub
        self.new_corner_stores = []  # References to NEW corner stores
        self.setup_scenario()
    
    def setup_scenario(self):
        """Setup distributed food network scenario with baseline + NEW food hub network"""
        
        num_consumers = self.config.num_consumers
        num_new_corner_stores = self.config.num_corner_stores  # NEW corner stores to add
        food_hub_capacity = self.config.food_hub_capacity
        corner_store_capacity = self.config.corner_store_capacity
        
        print(f"🏬 Setting up Scenario 2: Baseline + Food Hub Network")
        print(f"   Consumers: {num_consumers}")
        print(f"   NEW Corner Stores: {num_new_corner_stores}")
        print(f"   NEW Food Hub Capacity: {food_hub_capacity}")
        print(f"   Corner Store Capacity: {corner_store_capacity}")
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
        
        # STEP 2: Add NEW food hub (the intervention)
        print(f"\n   🆕 Adding NEW food hub (INTERVENTION):")
        self.new_food_hub = self.add_food_hub(capacity=food_hub_capacity)
        print(f"      • NEW Food Hub at ({self.new_food_hub.geometry.x:.3f}, {self.new_food_hub.geometry.y:.3f})")
        print(f"      • Capacity: {food_hub_capacity}")
        print(f"      • Market days: {self.config.food_hub_market_days}")
        
        # STEP 3: Add NEW corner stores using spatial optimization
        print(f"\n   🆕 Adding {num_new_corner_stores} NEW corner stores (INTERVENTION):")
        corner_store_locations = self._optimize_corner_store_locations(num_new_corner_stores)
        
        for i, location in enumerate(corner_store_locations):
            corner_store = self.add_corner_store(location, corner_store_capacity)
            self.new_corner_stores.append(corner_store)
            print(f"      • NEW Corner Store {i+1} at ({location.x:.3f}, {location.y:.3f})")
        
        print(f"\n   ✅ Scenario 2 setup complete:")
        print(f"      • Consumers: {len(self.consumers)}")
        print(f"      • Existing providers: {baseline_stores_added}")
        print(f"      • New providers: {1 + num_new_corner_stores} (1 food hub + {num_new_corner_stores} corner stores)")
        print(f"      • Total providers: {len(self.food_providers)}")
        
        # Calculate initial accessibility scores
        for consumer in self.consumers:
            consumer.update_accessibility_score()
        
        initial_accessibility = np.mean([c.accessibility_score for c in self.consumers])
        print(f"   📊 Initial average accessibility score: {initial_accessibility:.2f}")
        print(f"   🗺️  Average distance to nearest store: {self._calculate_avg_distance_to_nearest():.2f} km")
    
    def _optimize_corner_store_locations(self, num_stores: int) -> List[Point]:
        """Optimize corner store locations using spatial analysis"""
        print(f"   🎯 Optimizing locations for {num_stores} corner stores...")
        
        bounds = self.health_zone_polygon.bounds
        
        # Create a grid of potential locations
        grid_size = int(np.sqrt(num_stores * 3)) + 1  # More options than needed
        x_range = np.linspace(bounds[0], bounds[2], grid_size)
        y_range = np.linspace(bounds[1], bounds[3], grid_size)
        
        potential_locations = []
        for x in x_range:
            for y in y_range:
                point = Point(x, y)
                if self.health_zone_polygon.contains(point):
                    potential_locations.append(point)
        
        if len(potential_locations) <= num_stores:
            print(f"   ⚠️  Only {len(potential_locations)} valid locations found")
            return potential_locations
        
        # Simple but effective approach: spread stores evenly across the area
        selected_locations = []
        step = len(potential_locations) // num_stores
        
        for i in range(0, len(potential_locations), step):
            if len(selected_locations) < num_stores:
                selected_locations.append(potential_locations[i])
        
        # Ensure we have exactly the requested number
        while len(selected_locations) < num_stores and len(potential_locations) > len(selected_locations):
            remaining = [loc for loc in potential_locations if loc not in selected_locations]
            if remaining:
                selected_locations.append(random.choice(remaining))
        
        print(f"   ✅ Optimized {len(selected_locations)} store locations")
        return selected_locations[:num_stores]
    
    def analyze_network_performance(self) -> Dict[str, Any]:
        """Analyze comprehensive network-specific performance metrics"""
        summary = self.get_simulation_summary()
        
        # Get network components
        food_hub = [p for p in self.food_providers if p.provider_type == ProviderType.FOOD_HUB][0]
        corner_stores = [p for p in self.food_providers if p.provider_type == ProviderType.CORNER_STORE]
        
        # Comprehensive network analysis
        network_analysis = {
            'scenario_type': 'food_hub_network',
            'network_composition': {
                'food_hubs': 1,
                'corner_stores': len(corner_stores),
                'total_capacity': sum(p.capacity for p in self.food_providers)
            },
            'network_performance': {
                'food_hub_utilization': np.mean(food_hub.utilization_history) if food_hub.utilization_history else 0,
                'avg_corner_store_utilization': np.mean([
                    np.mean(store.utilization_history) if store.utilization_history else 0
                    for store in corner_stores
                ]),
                'network_redundancy': self._calculate_network_redundancy(),
                'spatial_coverage': self._calculate_spatial_coverage(),
                'load_distribution': self._analyze_load_distribution()
            },
            'accessibility_metrics': {
                'avg_distance_to_nearest_store': self._calculate_avg_distance_to_nearest(),
                'consumers_with_multiple_options': self._count_consumers_with_multiple_options(),
                'network_efficiency': self._calculate_network_efficiency(),
                'coverage_gaps': self._identify_coverage_gaps()
            },
            'temporal_analysis': {
                'market_day_performance': self._analyze_market_day_performance(),
                'non_market_day_performance': self._analyze_non_market_day_performance(),
                'weekly_pattern_analysis': self._analyze_weekly_patterns()
            },
            'equity_analysis': {
                'low_income_network_access': self._calculate_network_access_by_income(IncomeLevel.LOW),
                'medium_income_network_access': self._calculate_network_access_by_income(IncomeLevel.MEDIUM),
                'high_income_network_access': self._calculate_network_access_by_income(IncomeLevel.HIGH),
                'car_vs_no_car_network_benefit': self._compare_network_access_by_car_ownership()
            }
        }
        
        summary['network_analysis'] = network_analysis
        return summary
    
    def _calculate_network_redundancy(self) -> float:
        """Calculate network redundancy (avg number of stores within reach per consumer)"""
        redundancy_scores = []
        
        for consumer in self.consumers:
            accessible_stores = 0
            for provider in self.food_providers:
                distance = self.calculate_distance(consumer.geometry, provider.geometry)
                if distance <= consumer.max_travel_distance:
                    accessible_stores += 1
            redundancy_scores.append(accessible_stores)
        
        return np.mean(redundancy_scores) if redundancy_scores else 0
    
    def _calculate_spatial_coverage(self) -> float:
        """Calculate what percentage of consumers have access to at least one store"""
        consumers_with_access = 0
        
        for consumer in self.consumers:
            has_access = False
            for provider in self.food_providers:
                distance = self.calculate_distance(consumer.geometry, provider.geometry)
                if distance <= consumer.max_travel_distance:
                    has_access = True
                    break
            if has_access:
                consumers_with_access += 1
        
        return consumers_with_access / len(self.consumers) if self.consumers else 0
    
    def _analyze_load_distribution(self) -> Dict[str, float]:
        """Analyze how load is distributed across corner stores"""
        corner_stores = [p for p in self.food_providers if p.provider_type == ProviderType.CORNER_STORE]
        
        if not corner_stores:
            return {'balance_index': 0, 'max_utilization': 0, 'min_utilization': 0}
        
        utilizations = []
        for store in corner_stores:
            if store.utilization_history:
                avg_util = np.mean(store.utilization_history)
                utilizations.append(avg_util)
            else:
                utilizations.append(0)
        
        if not utilizations:
            return {'balance_index': 0, 'max_utilization': 0, 'min_utilization': 0}
        
        # Balance index: lower coefficient of variation = better balance
        mean_util = np.mean(utilizations)
        balance_index = 1 - (np.std(utilizations) / mean_util if mean_util > 0 else 0)
        
        return {
            'balance_index': max(0, balance_index),  # 0-1, higher is better
            'max_utilization': np.max(utilizations),
            'min_utilization': np.min(utilizations)
        }
    
    def _calculate_avg_distance_to_nearest(self) -> float:
        """Calculate average distance to nearest store"""
        distances = []
        
        for consumer in self.consumers:
            min_distance = float('inf')
            for provider in self.food_providers:
                distance = self.calculate_distance(consumer.geometry, provider.geometry)
                min_distance = min(min_distance, distance)
            if min_distance != float('inf'):
                distances.append(min_distance)
        
        return np.mean(distances) if distances else 0
    
    def _count_consumers_with_multiple_options(self) -> int:
        """Count consumers with access to multiple stores"""
        count = 0
        
        for consumer in self.consumers:
            accessible_stores = 0
            for provider in self.food_providers:
                distance = self.calculate_distance(consumer.geometry, provider.geometry)
                if distance <= consumer.max_travel_distance:
                    accessible_stores += 1
            if accessible_stores > 1:
                count += 1
        
        return count
    
    def _calculate_network_efficiency(self) -> float:
        """Calculate network efficiency metric"""
        total_capacity = sum(p.capacity for p in self.food_providers)
        satisfied_consumers = sum(1 for c in self.consumers if c.satisfied_today)
        
        return satisfied_consumers / total_capacity if total_capacity > 0 else 0
    
    def _identify_coverage_gaps(self) -> Dict[str, Any]:
        """Identify areas with poor coverage"""
        unserved_consumers = 0
        poorly_served_consumers = 0  # More than 5km to nearest store
        
        for consumer in self.consumers:
            min_distance = float('inf')
            for provider in self.food_providers:
                distance = self.calculate_distance(consumer.geometry, provider.geometry)
                min_distance = min(min_distance, distance)
            
            if min_distance > consumer.max_travel_distance:
                unserved_consumers += 1
            elif min_distance > 5.0:  # 5km threshold for "poorly served"
                poorly_served_consumers += 1
        
        return {
            'unserved_consumers': unserved_consumers,
            'poorly_served_consumers': poorly_served_consumers,
            'unserved_percentage': unserved_consumers / len(self.consumers) if self.consumers else 0,
            'poorly_served_percentage': poorly_served_consumers / len(self.consumers) if self.consumers else 0
        }
    
    def _analyze_market_day_performance(self) -> Dict[str, float]:
        """Analyze performance specifically on market days (when food hub is open)"""
        # This would require tracking daily performance over time
        # For now, return current metrics as approximation
        food_hub = [p for p in self.food_providers if p.provider_type == ProviderType.FOOD_HUB][0]
        
        return {
            'food_hub_utilization': np.mean(food_hub.utilization_history) if food_hub.utilization_history else 0,
            'market_day_satisfaction_estimate': self._calculate_satisfaction_rate()
        }
    
    def _analyze_non_market_day_performance(self) -> Dict[str, float]:
        """Analyze performance on non-market days (corner stores only)"""
        corner_stores = [p for p in self.food_providers if p.provider_type == ProviderType.CORNER_STORE]
        
        if not corner_stores:
            return {'corner_store_utilization': 0, 'non_market_day_satisfaction_estimate': 0}
        
        avg_utilization = np.mean([
            np.mean(store.utilization_history) if store.utilization_history else 0
            for store in corner_stores
        ])
        
        return {
            'corner_store_utilization': avg_utilization,
            'non_market_day_satisfaction_estimate': self._calculate_satisfaction_rate() * 0.8  # Estimate
        }
    
    def _analyze_weekly_patterns(self) -> Dict[str, Any]:
        """Analyze weekly patterns in the network"""
        # Simplified analysis based on market day frequency
        market_days_per_week = 3  # Mon, Wed, Fri
        non_market_days_per_week = 4
        
        return {
            'market_days_per_week': market_days_per_week,
            'non_market_days_per_week': non_market_days_per_week,
            'weekly_coverage_estimate': 7 / 7,  # Full week coverage with corner stores
            'peak_capacity_days': market_days_per_week
        }
    
    def _calculate_network_access_by_income(self, income_level: IncomeLevel) -> Dict[str, float]:
        """Calculate network access metrics for specific income level"""
        income_consumers = [c for c in self.consumers if c.income == income_level]
        if not income_consumers:
            return {'satisfaction_rate': 0, 'avg_accessibility_score': 0, 'avg_store_options': 0}
        
        satisfaction_rate = sum(1 for c in income_consumers if c.satisfied_today) / len(income_consumers)
        avg_accessibility = np.mean([c.accessibility_score for c in income_consumers])
        
        # Calculate average number of accessible stores for this income group
        store_options = []
        for consumer in income_consumers:
            accessible_stores = sum(1 for provider in self.food_providers 
                                  if self.calculate_distance(consumer.geometry, provider.geometry) <= consumer.max_travel_distance)
            store_options.append(accessible_stores)
        
        return {
            'satisfaction_rate': satisfaction_rate,
            'avg_accessibility_score': avg_accessibility,
            'avg_store_options': np.mean(store_options) if store_options else 0
        }
    
    def _compare_network_access_by_car_ownership(self) -> Dict[str, Any]:
        """Compare network access between car owners and non-car owners"""
        car_owners = [c for c in self.consumers if c.vehicle_available]
        non_car_owners = [c for c in self.consumers if not c.vehicle_available]
        
        def calculate_group_metrics(group):
            if not group:
                return {'satisfaction': 0, 'avg_options': 0, 'avg_distance': 0}
            
            satisfaction = sum(1 for c in group if c.satisfied_today) / len(group)
            
            options = []
            distances = []
            for consumer in group:
                accessible_stores = 0
                min_distance = float('inf')
                for provider in self.food_providers:
                    distance = self.calculate_distance(consumer.geometry, provider.geometry)
                    if distance <= consumer.max_travel_distance:
                        accessible_stores += 1
                    min_distance = min(min_distance, distance)
                
                options.append(accessible_stores)
                if min_distance != float('inf'):
                    distances.append(min_distance)
            
            return {
                'satisfaction': satisfaction,
                'avg_options': np.mean(options) if options else 0,
                'avg_distance': np.mean(distances) if distances else 0
            }
        
        car_metrics = calculate_group_metrics(car_owners)
        no_car_metrics = calculate_group_metrics(non_car_owners)
        
        return {
            'with_car': car_metrics,
            'without_car': no_car_metrics,
            'network_equity_benefit': {
                'satisfaction_difference': car_metrics['satisfaction'] - no_car_metrics['satisfaction'],
                'options_difference': car_metrics['avg_options'] - no_car_metrics['avg_options']
            }
        }
    
    def get_detailed_report(self) -> str:
        """Generate a detailed text report for Scenario 2"""
        results = self.analyze_network_performance()
        
        network_perf = results['network_analysis']['network_performance']
        accessibility = results['network_analysis']['accessibility_metrics']
        equity = results['network_analysis']['equity_analysis']
        
        report = f"""
Enhanced Scenario 2: Food Hub + Corner Stores Network Analysis Report
====================================================================

Simulation Parameters:
- Consumers: {len(self.consumers)}
- Simulation Days: {self.current_day}
- Food Hub Capacity: {[p.capacity for p in self.food_providers if p.provider_type == ProviderType.FOOD_HUB][0]}
- Corner Stores: {len([p for p in self.food_providers if p.provider_type == ProviderType.CORNER_STORE])}
- Total Network Capacity: {results['network_analysis']['network_composition']['total_capacity']}

Overall Performance:
- Average Satisfaction Rate: {results['overall_metrics']['avg_satisfaction_rate']:.2%}
- Average Food Insecurity Rate: {results['overall_metrics']['avg_food_insecurity_rate']:.2%}
- Average Travel Distance: {results['overall_metrics']['avg_travel_distance']:.2f} km
- Spatial Equity Index: {results['overall_metrics']['spatial_equity_index']:.3f}

Network Performance:
- Food Hub Utilization: {network_perf['food_hub_utilization']:.2%}
- Average Corner Store Utilization: {network_perf['avg_corner_store_utilization']:.2%}
- Network Redundancy (avg stores per consumer): {network_perf['network_redundancy']:.1f}
- Spatial Coverage: {network_perf['spatial_coverage']:.2%}
- Load Balance Index: {network_perf['load_distribution']['balance_index']:.3f}

Accessibility Metrics:
- Average Distance to Nearest Store: {accessibility['avg_distance_to_nearest_store']:.2f} km
- Consumers with Multiple Options: {accessibility['consumers_with_multiple_options']}
- Network Efficiency: {accessibility['network_efficiency']:.3f}
- Coverage Gaps: {accessibility['coverage_gaps']['unserved_percentage']:.2%} unserved

Equity Analysis:
- Low Income Network Access: {equity['low_income_network_access']['satisfaction_rate']:.2%} satisfaction
- Medium Income Network Access: {equity['medium_income_network_access']['satisfaction_rate']:.2%} satisfaction  
- High Income Network Access: {equity['high_income_network_access']['satisfaction_rate']:.2%} satisfaction
- Car vs No Car Satisfaction Gap: {equity['car_vs_no_car_network_benefit']['network_equity_benefit']['satisfaction_difference']:+.2%}
"""
        
        return report

def create_enhanced_scenario_2(config: SimulationConfig = None,
                              include_baseline: bool = True,
                              use_real_data: bool = True) -> EnhancedScenario2Model:
    """
    Create and return Enhanced Scenario 2 model
    
    Args:
        config: Simulation configuration object with all parameters
        include_baseline: Whether to include existing baseline providers
        use_real_data: Whether to use real provider locations
    
    Returns:
        Configured EnhancedScenario2Model ready for simulation
    """
    return EnhancedScenario2Model(config, include_baseline, use_real_data)

# Example usage and testing
if __name__ == "__main__":
    print("🚀 Enhanced Scenario 2: Food Hub + Corner Stores Network")
    print("=" * 60)
    
    # Create configuration and run scenario
    config = SimulationConfig(num_consumers=300, num_corner_stores=5, simulation_days=14)
    scenario2 = create_enhanced_scenario_2(config)
    
    print("\n⏳ Running simulation...")
    for day in range(14):
        scenario2.step()
        if day % 3 == 0:  # Progress update every 3 days
            satisfaction = scenario2._calculate_satisfaction_rate()
            network_redundancy = scenario2._calculate_network_redundancy()
            print(f"   Day {day + 1}: Satisfaction {satisfaction:.2%}, Network Redundancy {network_redundancy:.1f}")
    
    # Analyze results
    print("\n📊 Analyzing network performance...")
    results = scenario2.analyze_network_performance()
    
    # Print summary
    print(f"\n📈 Final Results:")
    print(f"   Satisfaction Rate: {results['overall_metrics']['avg_satisfaction_rate']:.2%}")
    print(f"   Food Insecurity Rate: {results['overall_metrics']['avg_food_insecurity_rate']:.2%}")
    print(f"   Average Travel Distance: {results['overall_metrics']['avg_travel_distance']:.2f} km")
    print(f"   Spatial Equity Index: {results['overall_metrics']['spatial_equity_index']:.3f}")
    
    # Network-specific metrics
    network_perf = results['network_analysis']['network_performance']
    print(f"\n🏬 Network Performance:")
    print(f"   Spatial Coverage: {network_perf['spatial_coverage']:.2%}")
    print(f"   Network Redundancy: {network_perf['network_redundancy']:.1f} stores/consumer")
    print(f"   Food Hub Utilization: {network_perf['food_hub_utilization']:.2%}")
    print(f"   Avg Corner Store Utilization: {network_perf['avg_corner_store_utilization']:.2%}")
    
    # Accessibility metrics
    accessibility = results['network_analysis']['accessibility_metrics']
    print(f"\n🗺️  Accessibility:")
    print(f"   Avg Distance to Nearest: {accessibility['avg_distance_to_nearest_store']:.2f} km")
    print(f"   Consumers with Multiple Options: {accessibility['consumers_with_multiple_options']}")
    print(f"   Network Efficiency: {accessibility['network_efficiency']:.3f}")
    
    # Equity analysis
    equity = results['network_analysis']['equity_analysis']
    print(f"\n⚖️  Equity Analysis:")
    print(f"   Low Income Access: {equity['low_income_network_access']['satisfaction_rate']:.2%}")
    print(f"   Medium Income Access: {equity['medium_income_network_access']['satisfaction_rate']:.2%}")
    print(f"   High Income Access: {equity['high_income_network_access']['satisfaction_rate']:.2%}")
    
    print("\n✅ Enhanced Scenario 2 network simulation complete!")
    
    # Optionally print detailed report
    # print(scenario2.get_detailed_report()) 