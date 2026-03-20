"""
Baseline Scenario: Current Food Access Situation
================================================

This scenario represents the CURRENT state of food access in Health Zone 1
with existing grocery stores, corner stores, and market-rate online delivery.

UPDATED (Oct 28, 2025): Now includes MARKET-RATE delivery service (unsubsidized)
to enable calibration of delivery parameters and comparison with Scenario 4.

This baseline is used as the comparison point for all intervention scenarios.
"""

from enhanced_mesa_geo_model import (
    EnhancedMesaGeoModel, SimulationConfig, IncomeLevel, ProviderType,
    IncomeClassifier, CensusTractData, EnhancedDeliveryService, EnhancedMobilePantry
)
from real_supermarket_loader import get_stores_for_model
from hz1_census_data_loader import HZ1CensusDataLoader
from shapely.geometry import Point
import random
import random as _random
import numpy as np
from typing import Dict, Any, List, Tuple

# ============================================================================
# REAL FOOD PROVIDER DATA FOR HEALTH ZONE 1, JACKSONVILLE
# ============================================================================
# Curated store list: 11 corner stores + 9 grocery stores.
# Loader maps categories to provider types and assigns capacities.
# ============================================================================

from config import get_supermarket_csv
REAL_SUPERMARKET_CSV = get_supermarket_csv()

# Fallback when use_real_data=False (e.g. testing) — same as load_real_provider_data fallback
EXISTING_GROCERY_STORES = [
    ("Walmart Neighborhood Market", -81.6892, 30.3575, 800),
    ("Save-A-Lot", -81.7012, 30.3425, 400),
]
EXISTING_CORNER_STORES = [
    ("Corner Store - Moncrief", -81.6750, 30.3650, 60),
    ("Corner Store - Phoenix", -81.7100, 30.3500, 50),
]

# ─────────────────────────────────────────────────────────────────────────────
# Real HZ1 Food Pantries — Baseline Infrastructure
# Sources: Cook (2024), Hall (2024), Shepard (2024), HZ1 food pantry database
#
# Format per entry:
#   (name, longitude, latitude, zip_code,
#    operating_days,   ← list of ints: 0=Mon,1=Tue,2=Wed,3=Thu,4=Fri,5=Sat,6=Sun
#    frequency,        ← 'weekly'|'biweekly'|'monthly_2nd'|'monthly_3rd'|'quarterly'
#    capacity,         ← int or None (None → random 100-200 at runtime)
#    address_notes)    ← human-readable address for dissertation reference
# ─────────────────────────────────────────────────────────────────────────────
HZ1_FOOD_PANTRIES = [
    # ── ZIP 32209 ─────────────────────────────────────────────────────────────
    # Highest SNAP concentration in Jacksonville (Shepard DCF 2024)
    ('Northside_Community_Involvement',
     -81.7241, 30.3701, '32209',
     [3], 'weekly', None,
     '4990 Avenue B — Thu 10:00-11:30am'),
    ('Chef_AL_Harvey_Food_Pantry',
     -81.6817, 30.3540, '32209',
     [0, 2, 4], 'weekly', None,
     '2100 W 45th St — call 904-684-6606 for schedule'),
    ('Celebration_Life_Center',
     -81.7121, 30.3661, '32209',
     [0], 'monthly_2nd', None,
     '5010 Cleveland Rd — Mon 10am-12pm, 2nd of month; TEFAP Program'),
    ('Love_Missionary_Baptist',
     -81.7121, 30.3678, '32209',
     [5], 'monthly_2nd', None,
     '5220 Cleveland Rd — Sat 10am-2pm, 2nd Saturday; closes early when food runs out'),
    ('Infinity_Food_Pantry',
     -81.7044, 30.3710, '32209',
     [6], 'weekly', None,
     '3365 New Kings Rd — Sun 10:00-11:00am'),
    ('Johnson_Family_YMCA',
     -81.7121, 30.3717, '32209',
     [2, 4], 'weekly', None,
     '5700 Cleveland Rd — Wed 3-5pm, Fri 12-2pm; Emergency Pantry + Diabetes Prevention'),
    ('FOSCI_Families_Slain_Children',
     -81.6714, 30.3337, '32209',
     [0], 'weekly', 180,
     '2212 N Myrtle Ave — Mon 12-1pm weekly; Cook (2024): 100-180 families per event'),
    ('New_Bethel_AME_Church',
     -81.6729, 30.3400, '32209',
     [2], 'weekly', None,
     '1231 Tyler St — Wed 10:00-11:30am'),
    ('Mt_Olive_Primitive_Baptist',
     -81.6714, 30.3278, '32209',
     [3], 'biweekly', None,
     '1301 N Myrtle Ave — Thu 12-2pm, 2nd and 4th of month'),
    ('The_Synagogue_Center',
     -81.6741, 30.3258, '32209',
     [5], 'monthly_2nd', None,
     '1408 W State St — Sat 11am-12pm, 1st of month; syncenter1408.org'),
    # ── ZIP 32208 ─────────────────────────────────────────────────────────────
    ('Disciples_of_Christ',
     -81.6950, 30.3298, '32208',
     [2], 'monthly_2nd', None,
     '2061 Edgewood Ave W — Wed 11am-2pm, 2nd of month'),
    ('St_Paul_Missionary_Baptist',
     -81.6711, 30.3714, '32208',
     [0, 5], 'biweekly', None,
     '3738 Winton Dr — Mon 3-4:30pm + Sat 11:30am-1pm, 2nd and 4th of month; TEFAP'),
    ('First_Coast_No_More_Homeless_Pets',
     -81.6452, 30.3968, '32208',
     [1, 3], 'weekly', None,
     '6817 Norwood Ave — Tue 10-11am; Thu 1-2pm by appointment'),
    ('Ribault_Full_Service_Schools',
     -81.6711, 30.3711, '32208',
     [0, 1, 2, 3, 4], 'weekly', None,
     '3701 Winton Dr — Mon-Fri various programs; multiple community partners'),
    # ── ZIP 32206 ─────────────────────────────────────────────────────────────
    ('Bridge_The_Gap',
     -81.6653, 30.3401, '32206',
     [1, 2, 3], 'weekly', None,
     '561 W 25th St — Tue-Thu 10am-12pm; TEFAP Program; bridgethegapjax.org'),
    ('Community_Rehab_Center',
     -81.6439, 30.3271, '32206',
     [2], 'biweekly', None,
     '623 Beechwood St — Wed pantry 2:30-3:30pm, 2nd and 4th; Mon-Fri soup kitchen'),
    ('Safe_Future_Foundation',
     -81.6646, 30.3271, '32206',
     [5], 'monthly_2nd', None,
     '515 W 6th St — Sat 9:00-10:00am, 2nd of month'),
    # ── ZIP 32204 ─────────────────────────────────────────────────────────────
    ('Agape_Family_Health',
     -81.6791, 30.3151, '32204',
     [5], 'monthly_3rd', None,
     '120 King St — 3rd Saturday, call for hours'),
    # ── ZIP 32254 ─────────────────────────────────────────────────────────────
    ('Inman_Methodist_Food_Pantry',
     -81.7330, 30.3430, '32254',
     [1, 2, 3], 'weekly', None,
     '2954 Lucoma Dr — Tue-Thu 10:00-11:50am; TEFAP Program'),
]


def _get_pantry_capacity(specified):
    """If capacity is None, draw random integer between 100 and 200."""
    if specified is not None:
        return specified
    return _random.randint(100, 200)


def _make_active_fn(operating_days, frequency):
    """
    Returns a closure: is_active(current_model_day) -> bool.
    """
    def is_active(current_model_day):
        if not operating_days:
            return False
        weekday = current_model_day % 7
        if weekday not in operating_days:
            return False
        week_num = current_model_day // 7
        if frequency == 'weekly':
            return True
        if frequency == 'biweekly':
            return week_num % 2 == 0
        if frequency == 'monthly_2nd':
            return week_num % 4 == 1
        if frequency == 'monthly_3rd':
            return week_num % 4 == 2
        if frequency == 'quarterly':
            return week_num % 13 == 0
        return True
    return is_active


def add_baseline_delivery_service(model) -> int:
    """
    Add REAL market-rate delivery service to the model.
    
    This function adds the baseline online grocery delivery service
    (Instacart, Walmart+, Amazon Fresh, etc.) that exists in HZ1.
    All scenarios should call this for consistency with baseline.
    
    Args:
        model: EnhancedMesaGeoModel instance to add delivery to
    
    Returns:
        Number of delivery services added (1)
    """
    print(f"\n   📦 Adding MARKET-RATE delivery service (baseline):")
    
    delivery_location = Point(-81.690, 30.355)  # Central location
    delivery_service = EnhancedDeliveryService(
        model=model,
        geometry=delivery_location,
        capacity=500,
        base_service_fee=2.00,
        distance_fee_per_km=0.75,
        delivery_area_km=20.0
    )
    
    # CRITICAL: Mark as UNSUBSIDIZED (everyone pays full price)
    delivery_service.subsidized = False
    delivery_service.name = "Market-Rate Online Grocery Delivery"
    
    model.space.add_agents(delivery_service)
    model.schedule.add(delivery_service)
    model.food_providers.append(delivery_service)
    model._build_spatial_index()
    
    print(f"      • {delivery_service.name}")
    print(f"        - Fee: $2.00 + (distance × $0.75/km)")
    print(f"        - Subsidy: NO (everyone pays full price)")
    print(f"        - Example: $5.75 for 5km delivery")
    
    return 1


def add_baseline_mobile_pantries(model) -> int:
    """
    Load real HZ1 food pantries into a model.
    Represents existing food pantry infrastructure in the baseline environment.
    
    Args:
        model: EnhancedMesaGeoModel instance to add pantries to
    
    Returns:
        Number of food pantries added
    """
    print(f"\n   🥫 Loading 19 real HZ1 food pantries (baseline infrastructure):")
    model.existing_pantries = []

    for (name, lon, lat, zipcode, op_days, freq, cap_spec, notes) in HZ1_FOOD_PANTRIES:
        pantry = model.add_mobile_pantry(
            location=Point(lon, lat),
            capacity=_get_pantry_capacity(cap_spec)
        )
        pantry.pantry_name = name
        pantry.zip_code = zipcode
        pantry.operating_days = op_days
        pantry.frequency = freq
        pantry.address_notes = notes
        pantry.is_active_today_fn = _make_active_fn(op_days, freq)
        model.existing_pantries.append(pantry)

    by_zip = {}
    for pantry_spec in HZ1_FOOD_PANTRIES:
        by_zip[pantry_spec[3]] = by_zip.get(pantry_spec[3], 0) + 1
    zip_summary = ', '.join(f'{z}={c}' for z, c in sorted(by_zip.items()))
    print(f"      • Loaded {len(model.existing_pantries)} real HZ1 food pantries")
    print(f"      • Distribution by ZIP: {zip_summary}")
    print(f"      • Sources: Cook 2024 (FOSCI), Hall 2024 (~50 pantries),")
    print(f"                 Shepard 2024 (DCF), HZ1 pantry database 2024")

    return len(model.existing_pantries)


def load_real_provider_data(data_file: str = None, use_geocoding: bool = False) -> Dict[str, List[Tuple]]:
    """
    Load REAL food provider locations from CSV file
    
    Args:
        data_file: Path to CSV file (if None, uses default path)
        use_geocoding: Whether to geocode addresses (slow, requires geopy)
                      If False (default), uses grid distribution in Health Zone 1
    
    Returns:
        Dictionary with grocery_stores and corner_stores lists
        Each store: (name, longitude, latitude, capacity)
    
    Example:
        data = load_real_provider_data()
        # Returns:
        # {
        #   'grocery_stores': [('Publix', -81.74, 30.36, 800), ...],
        #   'corner_stores': [('Corner Grocery', -81.68, 30.35, 50), ...]
        # }
    
    NOTE: This function does NOT include mobile pantries. 
          Call add_baseline_mobile_pantries(model) separately to add them.
    """
    csv_path = data_file if data_file else REAL_SUPERMARKET_CSV
    
    try:
        # Load real data using the loader
        grocery_stores, corner_stores = get_stores_for_model(csv_path, use_geocoding)
        
        print(f"   ✅ Loaded REAL data from CSV:")
        print(f"      • {len(grocery_stores)} grocery stores")
        print(f"      • {len(corner_stores)} corner/convenience stores")
        
        return {
            'grocery_stores': grocery_stores,
            'corner_stores': corner_stores
        }
    
    except Exception as e:
        print(f"   ⚠️  Error loading real data: {e}")
        print(f"   Using fallback (minimal) data")
        
        # Fallback to minimal data if loading fails
        return {
            'grocery_stores': [
                ("Walmart Neighborhood Market", -81.6892, 30.3575, 800),
                ("Save-A-Lot", -81.7012, 30.3425, 400),
            ],
            'corner_stores': [
                ("Corner Store - Moncrief", -81.6750, 30.3650, 60),
                ("Corner Store - Phoenix", -81.7100, 30.3500, 50),
            ]
        }


class BaselineScenarioModel(EnhancedMesaGeoModel):
    """
    Baseline Scenario: Current Food Access Situation
    
    Represents the existing food environment in Health Zone 1
    without any new interventions. This is the control scenario
    for comparison.
    """
    
    def __init__(self, config: SimulationConfig = None, 
                 use_real_data: bool = True,
                 data_file: str = None,
                 census_data_file: str = None):
        """
        Initialize baseline scenario
        
        Args:
            config: Simulation configuration
            use_real_data: Whether to use real provider locations
            data_file: Optional path to data file with provider locations
            census_data_file: Optional path to census tract data file
        """
        if config is None:
            config = SimulationConfig()
        
        super().__init__(config)
        self.scenario_name = "Baseline: Current Food Access Situation (HOUSEHOLD-BASED)"
        self.use_real_data = use_real_data
        self.data_file = data_file
        self.census_data_file = census_data_file
        
        self.setup_scenario()
    
    def setup_scenario(self):
        """Setup baseline scenario with current providers using HOUSEHOLD demographics"""
        
        num_households = self.config.num_consumers  # Now interpreted as num_households
        
        print(f"📊 Setting up Baseline Scenario (HOUSEHOLD-BASED)")
        print(f"   Households: {num_households}")
        print(f"   Using real provider data: {self.use_real_data}")
        print(f"   Using census tract data: {self.census_data_file or 'Default demographics'}")
        
        # Load provider data
        if self.use_real_data:
            provider_data = load_real_provider_data(self.data_file)
            grocery_stores = provider_data['grocery_stores']
            corner_stores = provider_data['corner_stores']
        else:
            grocery_stores = EXISTING_GROCERY_STORES
            corner_stores = EXISTING_CORNER_STORES
        
        # ===================================================================
        # ADD HOUSEHOLDS USING CENSUS TRACT DATA
        # ===================================================================
        # Generate households with demographics from census tracts
        print(f"\n   👥 Creating {num_households} households from REAL HZ1 census data:")
        
        # ⭐ USE REAL CENSUS DATA from Health Zone 1
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
        
        # Generate and add households using REAL data
        households_data = real_census.generate_household_demographics(num_households)
        
        for hh_demo in households_data:
            # Add household to model using new method
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
        
        # Add existing grocery stores
        print(f"\n   📍 Adding {len(grocery_stores)} existing grocery stores:")
        for name, lon, lat, capacity in grocery_stores:
            location = Point(lon, lat)
            store = self.add_grocery_store(location, capacity)
            store.name = name  # Set the actual store name
            print(f"      • {name} at ({lon:.4f}, {lat:.4f}), capacity: {capacity}")
        
        # Add existing corner stores
        print(f"\n   📍 Adding {len(corner_stores)} existing corner stores:")
        for name, lon, lat, capacity in corner_stores:
            location = Point(lon, lat)
            store = self.add_corner_store(location, capacity)
            store.name = name  # Set the actual store name
            print(f"      • {name} at ({lon:.4f}, {lat:.4f}), capacity: {capacity}")
        
        # ===================================================================
        # ADD REAL HZ1 FOOD PANTRIES (CURRENT BASELINE INFRASTRUCTURE)
        # ===================================================================
        self._load_existing_pantries()
        
        # ===================================================================
        # ADD MARKET-RATE DELIVERY SERVICE (UNSUBSIDIZED)
        # ===================================================================
        add_baseline_delivery_service(self)
        
        print(f"\n   ✅ Baseline setup complete:")
        print(f"      • {len(self.consumers)} consumers")
        
        # Count provider types
        grocery_count = sum(1 for p in self.food_providers if p.provider_type.value == 'grocery_store')
        corner_count = sum(1 for p in self.food_providers if p.provider_type.value == 'corner_store')
        pantry_count = sum(1 for p in self.food_providers if isinstance(p, EnhancedMobilePantry))
        delivery_count = sum(1 for p in self.food_providers if isinstance(p, EnhancedDeliveryService))
        
        print(f"      • {len(self.food_providers)} total providers:")
        print(f"        - {grocery_count} grocery stores")
        print(f"        - {corner_count} corner stores")
        print(f"        - {pantry_count} real fixed food pantries")
        print(f"        - {delivery_count} delivery service (market-rate)")
        
        # Calculate initial accessibility
        for consumer in self.consumers:
            consumer.update_accessibility_score()
        
        initial_accessibility = np.mean([c.accessibility_score for c in self.consumers])
        print(f"      • Initial avg accessibility: {initial_accessibility:.2f}")

    def _load_existing_pantries(self):
        """
        Load 19 real HZ1 food pantries into the baseline model.
        Represents existing food pantry infrastructure (not a new intervention).
        Sources: Cook 2024, Hall 2024, Shepard 2024, HZ1 pantry database.
        """
        self.existing_pantries = []

        for (name, lon, lat, zipcode, op_days, freq, cap_spec, notes) in HZ1_FOOD_PANTRIES:
            pantry = self.add_mobile_pantry(
                location=Point(lon, lat),
                capacity=_get_pantry_capacity(cap_spec)
            )
            # Metadata (used for logging, validation, and dashboard display)
            pantry.pantry_name = name
            pantry.zip_code = zipcode
            pantry.operating_days = op_days
            pantry.frequency = freq
            pantry.address_notes = notes
            # Frequency-aware active function (replaces raw schedule dict)
            pantry.is_active_today_fn = _make_active_fn(op_days, freq)

            self.existing_pantries.append(pantry)

        # Print summary
        by_zip = {}
        for p in HZ1_FOOD_PANTRIES:
            by_zip[p[3]] = by_zip.get(p[3], 0) + 1
        zip_summary = ', '.join(f'{z}={c}' for z, c in sorted(by_zip.items()))
        print(f'      • Loaded {len(self.existing_pantries)} real HZ1 food pantries')
        print(f'      • Distribution by ZIP: {zip_summary}')
        print(f'      • Sources: Cook 2024 (FOSCI), Hall 2024 (~50 pantries),')
        print(f'                 Shepard 2024 (DCF), HZ1 pantry database 2024')
    
    def analyze_baseline_outcomes(self) -> Dict[str, Any]:
        """Analyze baseline scenario outcomes"""
        summary = self.get_simulation_summary()
        
        # Baseline-specific analysis
        delivery_services = [p for p in self.food_providers if isinstance(p, EnhancedDeliveryService)]
        
        baseline_analysis = {
            'scenario_type': 'baseline',
            'current_providers': {
                'total_count': len(self.food_providers),
                'grocery_stores': len([p for p in self.food_providers if p.provider_type == ProviderType.GROCERY_STORE]),
                'corner_stores': len([p for p in self.food_providers if p.provider_type == ProviderType.CORNER_STORE]),
                'delivery_services': len(delivery_services),
                'total_capacity': sum(p.capacity for p in self.food_providers)
            },
            'delivery_metrics': self._analyze_delivery_adoption() if delivery_services else {},
            'coverage_metrics': {
                'consumers_served': len([c for c in self.consumers if len(c.shopping_history) > 0]),
                'avg_shopping_events_per_consumer': np.mean([len(c.shopping_history) for c in self.consumers]),
                'consumers_never_served': len([c for c in self.consumers if len(c.shopping_history) == 0])
            },
            'equity_gaps': self._analyze_equity_gaps()
        }
        
        summary['baseline_analysis'] = baseline_analysis
        return summary
    
    def _analyze_equity_gaps(self) -> Dict[str, Any]:
        """Identify equity gaps in baseline scenario"""
        
        gaps = {}
        
        # Income-based gaps
        for income_level in IncomeLevel:
            income_consumers = [c for c in self.consumers if c.income == income_level]
            if income_consumers:
                satisfaction_rate = np.mean([c.satisfied_today for c in income_consumers])
                avg_accessibility = np.mean([c.accessibility_score for c in income_consumers])
                
                gaps[f'{income_level.value}_income'] = {
                    'satisfaction_rate': satisfaction_rate,
                    'avg_accessibility': avg_accessibility,
                    'population_share': len(income_consumers) / len(self.consumers)
                }
        
        # Car ownership gaps
        car_owners = [c for c in self.consumers if c.vehicle_available]
        no_car = [c for c in self.consumers if not c.vehicle_available]
        
        gaps['vehicle_availability_gap'] = {
            'with_car_satisfaction': np.mean([c.satisfied_today for c in car_owners]) if car_owners else 0,
            'without_car_satisfaction': np.mean([c.satisfied_today for c in no_car]) if no_car else 0,
            'gap_magnitude': (np.mean([c.satisfied_today for c in car_owners]) - np.mean([c.satisfied_today for c in no_car])) if (car_owners and no_car) else 0
        }
        
        return gaps
    
    def _analyze_delivery_adoption(self) -> Dict[str, Any]:
        """Analyze market-rate delivery adoption in baseline"""
        
        # Overall delivery adoption
        delivery_trips = sum(sum(1 for e in c.shopping_history if e.get('used_delivery', False)) 
                            for c in self.consumers)
        total_trips = sum(len(c.shopping_history) for c in self.consumers)
        
        delivery_metrics = {
            'overall_adoption': delivery_trips / total_trips if total_trips > 0 else 0,
            'delivery_trips': delivery_trips,
            'total_trips': total_trips
        }
        
        # By income
        for income_level in IncomeLevel:
            hh_in_group = [c for c in self.consumers if c.income == income_level]
            if hh_in_group:
                del_trips = sum(sum(1 for e in c.shopping_history if e.get('used_delivery', False)) 
                               for c in hh_in_group)
                tot_trips = sum(len(c.shopping_history) for c in hh_in_group)
                delivery_metrics[f'{income_level.value}_adoption'] = del_trips / tot_trips if tot_trips > 0 else 0
        
        # By car ownership
        for has_car in [True, False]:
            hh_in_group = [c for c in self.consumers if c.vehicle_available == has_car]
            if hh_in_group:
                del_trips = sum(sum(1 for e in c.shopping_history if e.get('used_delivery', False)) 
                               for c in hh_in_group)
                tot_trips = sum(len(c.shopping_history) for c in hh_in_group)
                label = "car" if has_car else "nocar"
                delivery_metrics[f'{label}_adoption'] = del_trips / tot_trips if tot_trips > 0 else 0
        
        return delivery_metrics
    
    def get_detailed_report(self) -> str:
        """Generate detailed baseline report"""
        results = self.analyze_baseline_outcomes()
        
        report = f"""
Baseline Scenario: Current Food Access Report
=============================================

Simulation Parameters:
- Consumers: {len(self.consumers)}
- Simulation Days: {self.current_day}
- Existing Providers: {len(self.food_providers)}

Current Food Environment:
- Grocery Stores: {results['baseline_analysis']['current_providers']['grocery_stores']}
- Corner Stores: {results['baseline_analysis']['current_providers']['corner_stores']}
- Total Capacity: {results['baseline_analysis']['current_providers']['total_capacity']} customers/day

Overall Performance (Current State):
- Average Satisfaction Rate: {results['overall_metrics']['avg_satisfaction_rate']:.2%}
- Average Food Insecurity Rate: {results['overall_metrics']['avg_food_insecurity_rate']:.2%}
- Average Travel Distance: {results['overall_metrics']['avg_travel_distance']:.2f} km
- Spatial Equity Index: {results['overall_metrics']['spatial_equity_index']:.3f}

Coverage Analysis:
- Consumers Ever Served: {results['baseline_analysis']['coverage_metrics']['consumers_served']}
- Consumers Never Served: {results['baseline_analysis']['coverage_metrics']['consumers_never_served']}
- Avg Shopping Events per Consumer: {results['baseline_analysis']['coverage_metrics']['avg_shopping_events_per_consumer']:.2f}

Equity Gaps Identified:
- Low Income Satisfaction: {results['baseline_analysis']['equity_gaps']['low_income']['satisfaction_rate']:.2%}
- Medium Income Satisfaction: {results['baseline_analysis']['equity_gaps']['medium_income']['satisfaction_rate']:.2%}
- High Income Satisfaction: {results['baseline_analysis']['equity_gaps']['high_income']['satisfaction_rate']:.2%}
- Vehicle Availability Gap: {results['baseline_analysis']['equity_gaps']['vehicle_availability_gap']['gap_magnitude']:+.2%}

KEY FINDINGS:
This baseline represents the CURRENT food access situation. Any improvements
in intervention scenarios should be measured against these baseline metrics.
"""
        return report


def create_baseline_scenario(config: SimulationConfig = None,
                            use_real_data: bool = True,
                            data_file: str = None) -> BaselineScenarioModel:
    """
    Create baseline scenario model
    
    Args:
        config: Simulation configuration
        use_real_data: Whether to use real provider locations
        data_file: Optional data file with provider locations
    
    Returns:
        Configured BaselineScenarioModel
    """
    return BaselineScenarioModel(config, use_real_data, data_file)


# Example usage
if __name__ == "__main__":
    print("🚀 Baseline Scenario: Current Food Access")
    print("=" * 50)
    
    # Create baseline
    config = SimulationConfig(num_consumers=300, simulation_days=14)
    baseline = create_baseline_scenario(config)
    
    print("\n⏳ Running baseline simulation...")
    for day in range(14):
        baseline.step()
        if day % 3 == 0:
            satisfaction = baseline._calculate_satisfaction_rate()
            print(f"   Day {day + 1}: Satisfaction Rate {satisfaction:.2%}")
    
    # Analyze baseline
    print("\n📊 Baseline Analysis:")
    results = baseline.analyze_baseline_outcomes()
    
    print(f"\n📈 Baseline Results:")
    print(f"   Satisfaction Rate: {results['overall_metrics']['avg_satisfaction_rate']:.2%}")
    print(f"   Food Insecurity: {results['overall_metrics']['avg_food_insecurity_rate']:.2%}")
    print(f"   Spatial Equity: {results['overall_metrics']['spatial_equity_index']:.3f}")
    
    print("\n✅ Baseline scenario complete!")
    print("   Use this as the comparison point for all interventions.")

