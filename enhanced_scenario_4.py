"""
Enhanced Scenario 4: Subsidized Grocery Delivery Service
=========================================================

INTERVENTION: Subsidized online grocery delivery for low-income households

This scenario models the impact of providing subsidized grocery delivery services
to improve food access for households in Health Zone 1, Jacksonville, FL.

Key Features:
- Baseline providers (2 grocery stores + 5 corner stores) remain
- NEW: Subsidized delivery service covering entire health zone
- Low-income households: FREE delivery ($0 fee)
- Medium-income households: 50% off delivery fee ($2.98 vs $5.95)
- High-income households: Full delivery fee ($5.95)
- Households with internet/technology access can adopt delivery
- Delivery propensity increased by subsidy uplift multiplier (2.0x baseline)

Research Questions:
1. Does subsidized delivery reduce food insecurity for low-income households?
2. How does adoption differ by income level?
3. Does delivery reduce travel burden (especially for no-car households)?
4. What's the total cost of the subsidy program?
5. Which households benefit most from delivery vs. new physical stores?

Author: Enhanced Mesa-Geo Food Access ABM
Date: October 2025
"""

import random
from typing import List, Tuple
from shapely.geometry import Point
import mesa

from enhanced_mesa_geo_model import (
    EnhancedMesaGeoModel,
    EnhancedHouseholdAgent,
    EnhancedGroceryStore,
    EnhancedCornerStore,
    EnhancedDeliveryService,
    SimulationConfig,
    ProviderType
)
from real_supermarket_loader import get_stores_for_model  # ⭐ NEW: Load real data
from hz1_census_data_loader import HZ1CensusDataLoader  # ⭐ NEW: Real census demographics
from baseline_scenario import add_baseline_mobile_pantries, add_baseline_delivery_service, REAL_SUPERMARKET_CSV  # ⭐ Real mobile pantries + delivery + curated CSV path

def create_enhanced_scenario_4(config: SimulationConfig = None,
                               use_real_data: bool = True,
                               delivery_capacity: int = 500,
                               base_service_fee: float = 2.00,
                               distance_fee_per_km: float = 0.75,
                               delivery_area_km: float = 20.0) -> EnhancedMesaGeoModel:
    """
    Create Scenario 4: Subsidized Grocery Delivery Service
    
    This scenario adds a subsidized delivery service to baseline providers.
    
    Delivery fee formula: base_service_fee + (distance_km × distance_fee_per_km)
    Example: $2.00 + (5 km × $0.75/km) = $5.75 total fee
    
    Args:
        config: Simulation configuration
        use_real_data: Whether to use real provider locations
        delivery_capacity: Daily delivery capacity (orders per day)
        base_service_fee: Base delivery fee (fixed component, e.g., $2.00)
        distance_fee_per_km: Per-kilometer fee (variable component, e.g., $0.75/km)
        delivery_area_km: Maximum delivery radius in km
    
    Returns:
        Configured EnhancedMesaGeoModel ready for simulation
    """
    
    if config is None:
        config = SimulationConfig()
    
    print("🚚 Setting up Scenario 4: Subsidized Grocery Delivery")
    print(f"   Consumers: {config.num_consumers}")
    print(f"   Delivery Capacity: {delivery_capacity} orders/day")
    print(f"   Delivery Area: {delivery_area_km} km radius")
    print(f"   Fee Structure: ${base_service_fee:.2f} base + ${distance_fee_per_km:.2f}/km")
    print(f"   Include Baseline Providers: {use_real_data}")
    
    # Create model
    model = EnhancedMesaGeoModel(config)
    
    # ========================================================================
    # Add Consumers (Households) USING REAL HZ1 CENSUS DATA
    # ========================================================================
    from hz1_census_data_loader import HZ1CensusDataLoader
    from enhanced_mesa_geo_model import IncomeClassifier
    
    print(f"   👥 Creating {config.num_consumers} households from REAL HZ1 census data:")
    
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
    households_data = real_census.generate_household_demographics(config.num_consumers)
    
    for hh_demo in households_data:
        # Add household to model using household method
        model.add_household(
            income=hh_demo['income'],
            vehicle_available=hh_demo['vehicle_available'],
            household_size=hh_demo['household_size'],
            race=hh_demo['race'],
            snap_eligible=hh_demo['snap_eligible'],
            annual_income=hh_demo['annual_income'],
            census_tract=hh_demo['census_tract'],
            zip_code=hh_demo.get('zip_code')
        )
    
    print(f"   ✅ Added {len(model.consumers)} households")
    
    # ========================================================================
    # Add EXISTING Baseline Providers (REAL DATA)
    # ========================================================================
    if use_real_data:
        print("\n   📍 Adding EXISTING baseline providers (REAL DATA):")
        
        # Load REAL supermarket data from the curated CSV (same source as all other scenarios)
        try:
            grocery_stores_data, corner_stores_data = get_stores_for_model(REAL_SUPERMARKET_CSV, use_geocoding=False)
            
            print(f"   ✅ Loaded {len(grocery_stores_data)} grocery stores from CSV")
            
            # Add grocery stores
            for name, lon, lat, capacity in grocery_stores_data:
                store = EnhancedGroceryStore(
                    model=model,
                    geometry=Point(lon, lat),
                    capacity=capacity
                )
                store.name = name
                model.space.add_agents(store)
                model.schedule.add(store)
                model.food_providers.append(store)
                print(f"      • {name} (capacity: {capacity})")
            
            # CRITICAL FIX: Rebuild spatial index after adding all grocery stores
            model._build_spatial_index()
            
            print(f"\n   ✅ Loaded {len(corner_stores_data)} corner/convenience stores from CSV")
            
            # Add corner stores
            for name, lon, lat, capacity in corner_stores_data:
                store = EnhancedCornerStore(
                    model=model,
                    geometry=Point(lon, lat),
                    capacity=capacity
                )
                store.name = name
                model.space.add_agents(store)
                model.schedule.add(store)
                model.food_providers.append(store)
                print(f"      • {name} (capacity: {capacity})")
            
            # CRITICAL FIX: Rebuild spatial index after adding all corner stores
            model._build_spatial_index()
            
            # ⭐ ADD REAL MOBILE PANTRIES (same as baseline)
            add_baseline_mobile_pantries(model)
            
            # ⭐ ADD MARKET-RATE DELIVERY (same as baseline) — agents can choose market-rate OR subsidized
            add_baseline_delivery_service(model)
        
        except Exception as e:
            print(f"   ⚠️  Error loading real data: {e}")
            print(f"   Using fallback minimal data")
            
            # Fallback to minimal data
            grocery_stores = [
                {"name": "Walmart Neighborhood Market", "lon": -81.6892, "lat": 30.3575, "capacity": 800},
                {"name": "Save-A-Lot", "lon": -81.7012, "lat": 30.3425, "capacity": 400}
            ]
            
            for store_info in grocery_stores:
                store = EnhancedGroceryStore(
                    model=model,
                    geometry=Point(store_info["lon"], store_info["lat"]),
                    capacity=store_info["capacity"]
                )
                store.name = store_info["name"]
                model.space.add_agents(store)
                model.schedule.add(store)
                model.food_providers.append(store)
                print(f"      • {store.name} (capacity: {store.capacity})")
            
            model._build_spatial_index()
    
    # ========================================================================
    # Add NEW INTERVENTION: Subsidized Delivery Service
    # ========================================================================
    print("\n   🆕 Adding SUBSIDIZED DELIVERY SERVICE (INTERVENTION):")
    
    # Place delivery service hub centrally in Health Zone 1
    # Using approximate center of the health zone
    delivery_location = Point(-81.690, 30.355)
    
    delivery_service = EnhancedDeliveryService(
        model=model,
        geometry=delivery_location,
        capacity=delivery_capacity,
        base_service_fee=base_service_fee,
        distance_fee_per_km=distance_fee_per_km,
        delivery_area_km=delivery_area_km
    )
    
    # CRITICAL: Mark as subsidized (this triggers tiered pricing)
    delivery_service.subsidized = True
    delivery_service.name = "FreshCart Delivery (Subsidized)"
    
    model.space.add_agents(delivery_service)
    model.schedule.add(delivery_service)
    model.food_providers.append(delivery_service)
    
    # CRITICAL FIX: Rebuild spatial index after adding delivery service
    model._build_spatial_index()
    
    print(f"      • NEW: {delivery_service.name}")
    print(f"        - Location: ({delivery_location.x:.3f}, {delivery_location.y:.3f})")
    print(f"        - Capacity: {delivery_capacity} deliveries/day")
    print(f"        - Delivery area: {delivery_area_km} km radius")
    print(f"        - Fee formula: ${base_service_fee:.2f} + (distance × ${distance_fee_per_km:.2f}/km)")
    print(f"        - Example fees (5 km): ${base_service_fee + 5*distance_fee_per_km:.2f} full")
    print(f"        - Subsidy structure:")
    print(f"          * Low income: $0.00 (FREE)")
    print(f"          * Medium income: 50% off (half of distance-based fee)")
    print(f"          * High income: Full price (distance-based fee)")
    
    # Store reference for analysis
    model.delivery_service = delivery_service
    
    # ========================================================================
    # Calculate Initial Metrics
    # ========================================================================
    accessibility_scores = [c.accessibility_score for c in model.consumers]
    avg_accessibility = sum(accessibility_scores) / len(accessibility_scores) if accessibility_scores else 0
    
    # Count households by delivery capability
    can_deliver = sum(1 for c in model.consumers if c.can_use_delivery)
    cannot_deliver = len(model.consumers) - can_deliver
    
    # Count by income level
    low_income = sum(1 for c in model.consumers if c.income.value == 'low')
    med_income = sum(1 for c in model.consumers if c.income.value == 'medium')
    high_income = sum(1 for c in model.consumers if c.income.value == 'high')
    
    print("\n   ✅ Scenario 4 setup complete:")
    print(f"      • Consumers: {len(model.consumers)}")
    print(f"      • Existing providers: {len(model.food_providers) - 1}")
    print(f"      • New providers: 1 (subsidized delivery)")
    print(f"      • Total providers: {len(model.food_providers)}")
    print(f"      • Initial avg accessibility: {avg_accessibility:.2f}")
    print(f"\n      • Delivery capable households: {can_deliver} ({can_deliver/len(model.consumers)*100:.1f}%)")
    print(f"      • Hard blockers (no tech): {cannot_deliver} ({cannot_deliver/len(model.consumers)*100:.1f}%)")
    print(f"\n      • Income distribution:")
    print(f"        - Low: {low_income} ({low_income/len(model.consumers)*100:.1f}%)")
    print(f"        - Medium: {med_income} ({med_income/len(model.consumers)*100:.1f}%)")
    print(f"        - High: {high_income} ({high_income/len(model.consumers)*100:.1f}%)")
    
    return model


def analyze_delivery_scenario_results(model: EnhancedMesaGeoModel) -> dict:
    """
    Analyze results of delivery subsidy scenario
    
    Returns detailed metrics on delivery adoption, costs, and equity impacts
    """
    
    if not hasattr(model, 'delivery_service'):
        return {"error": "Model does not have delivery service"}
    
    delivery_service = model.delivery_service
    
    # Overall delivery metrics
    total_deliveries = delivery_service.total_deliveries
    deliveries_by_income = delivery_service.deliveries_by_income
    
    # Analyze household shopping patterns
    delivery_users = []
    physical_only_users = []
    
    for consumer in model.consumers:
        delivery_count = sum(1 for event in consumer.shopping_history 
                            if event.get('used_delivery', False))
        physical_count = sum(1 for event in consumer.shopping_history 
                            if not event.get('used_delivery', False))
        
        if delivery_count > 0:
            delivery_users.append({
                'id': consumer.unique_id,
                'income': consumer.income.value if hasattr(consumer.income, 'value') else str(consumer.income),
                'vehicle': consumer.vehicle_available,
                'delivery_trips': delivery_count,
                'physical_trips': physical_count,
                'total_trips': delivery_count + physical_count,
                'delivery_share': delivery_count / (delivery_count + physical_count) if (delivery_count + physical_count) > 0 else 0
            })
        elif physical_count > 0:
            physical_only_users.append({
                'id': consumer.unique_id,
                'income': consumer.income.value if hasattr(consumer.income, 'value') else str(consumer.income),
                'vehicle': consumer.vehicle_available
            })
    
    # Calculate adoption rates by income
    total_low = sum(1 for c in model.consumers if c.income.value == 'low')
    total_med = sum(1 for c in model.consumers if c.income.value == 'medium')
    total_high = sum(1 for c in model.consumers if c.income.value == 'high')
    
    low_adopters = sum(1 for u in delivery_users if u['income'] == 'low')
    med_adopters = sum(1 for u in delivery_users if u['income'] == 'medium')
    high_adopters = sum(1 for u in delivery_users if u['income'] == 'high')
    
    # Estimate subsidy cost using actual fee formula: base_service_fee + (distance_km × distance_fee_per_km)
    # Use 5 km as typical delivery distance for cost estimation (matches docstring example)
    typical_fee = delivery_service.base_service_fee + (5.0 * delivery_service.distance_fee_per_km)
    # Low income: full subsidy (program covers full fee)
    # Medium income: 50% subsidy (program covers half)
    # High income: no subsidy ($0)
    subsidy_cost = (
        deliveries_by_income.get('low', 0) * typical_fee +
        deliveries_by_income.get('medium', 0) * (typical_fee * 0.5)
    )
    
    results = {
        'total_deliveries': total_deliveries,
        'deliveries_by_income': deliveries_by_income,
        'total_delivery_users': len(delivery_users),
        'adoption_rate_low': low_adopters / total_low if total_low > 0 else 0,
        'adoption_rate_medium': med_adopters / total_med if total_med > 0 else 0,
        'adoption_rate_high': high_adopters / total_high if total_high > 0 else 0,
        'avg_delivery_share': sum(u['delivery_share'] for u in delivery_users) / len(delivery_users) if delivery_users else 0,
        'subsidy_cost_total': subsidy_cost,
        'subsidy_cost_per_delivery': subsidy_cost / total_deliveries if total_deliveries > 0 else 0,
        'delivery_users': delivery_users,
        'physical_only_users': physical_only_users
    }
    
    return results


def print_delivery_scenario_summary(model: EnhancedMesaGeoModel):
    """Print a formatted summary of delivery scenario results"""
    
    results = analyze_delivery_scenario_results(model)
    
    if 'error' in results:
        print(f"Error: {results['error']}")
        return
    
    print("\n" + "="*80)
    print("SCENARIO 4: SUBSIDIZED DELIVERY - RESULTS SUMMARY")
    print("="*80)
    
    print(f"\n📦 Total Deliveries: {results['total_deliveries']}")
    print(f"   • Low income: {results['deliveries_by_income'].get('low', 0)}")
    print(f"   • Medium income: {results['deliveries_by_income'].get('medium', 0)}")
    print(f"   • High income: {results['deliveries_by_income'].get('high', 0)}")
    
    print(f"\n👥 Adoption Rates:")
    print(f"   • Low income: {results['adoption_rate_low']:.1%}")
    print(f"   • Medium income: {results['adoption_rate_medium']:.1%}")
    print(f"   • High income: {results['adoption_rate_high']:.1%}")
    
    print(f"\n💰 Subsidy Cost:")
    print(f"   • Total: ${results['subsidy_cost_total']:.2f}")
    print(f"   • Per delivery: ${results['subsidy_cost_per_delivery']:.2f}")
    
    print(f"\n🛒 Shopping Patterns:")
    print(f"   • Delivery users: {results['total_delivery_users']}")
    print(f"   • Physical store only: {len(results['physical_only_users'])}")
    print(f"   • Avg delivery share (among users): {results['avg_delivery_share']:.1%}")
    
    # Final metrics
    if model.metrics_history:
        final = model.metrics_history[-1]
        print(f"\n📊 Final Outcomes:")
        print(f"   • Satisfaction rate: {final.get('satisfaction_rate', 0):.1%}")
        print(f"   • Food insecurity: {final.get('food_insecurity_rate', 0):.1%}")
        print(f"   • Avg travel distance: {final.get('avg_travel_distance', 0):.2f} km")
    
    print("="*80)


# ============================================================================
# Main Execution
# ============================================================================

if __name__ == "__main__":
    print("="*80)
    print("SCENARIO 4: SUBSIDIZED GROCERY DELIVERY SERVICE")
    print("="*80)
    
    # Create configuration
    config = SimulationConfig(
        num_consumers=100,
        simulation_days=30
    )
    
    # Create scenario
    model = create_enhanced_scenario_4(config, use_real_data=True)
    
    # Run simulation
    print(f"\n🔄 Running simulation for {config.simulation_days} days...")
    for day in range(config.simulation_days):
        model.step()
        if (day + 1) % 7 == 0:
            print(f"   Day {day + 1}/{config.simulation_days} complete")
    
    # Print results
    print_delivery_scenario_summary(model)
    
    print("\n✅ Scenario 4 simulation complete!")

