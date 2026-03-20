"""
Enhanced Mesa-Geo Food Access Simulation
=======================================

This is a PROPER enhancement of your existing Mesa food access simulation using:
- Mesa + mesa_geo for agent-based modeling (like your original)
- Enhanced spatial analytics using GeoPandas and Shapely
- Better performance optimizations for larger simulations
- Advanced geospatial features and analytics

This maintains your existing structure but with significant improvements!
"""

import mesa
import mesa_geo as mg
import numpy as np
import pandas as pd
import geopandas as gpd
import random
import json
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Any
from enum import Enum

# Enhanced geospatial libraries
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import nearest_points
from geopy.distance import geodesic
import networkx as nx
from scipy.spatial import KDTree
from sklearn.cluster import DBSCAN

# Performance optimization
import warnings
warnings.filterwarnings('ignore')

def _load_calibrated_params_from_json():
    """
    Load calibrated parameters from the most recent FINAL_CALIBRATED_PARAMS JSON.
    Falls back to BEST_PHASE1_PARAMS if no Phase 2 file exists.
    Result is cached so the file is read at most once per process.
    """
    import glob as _glob
    import os as _os

    script_dir = _os.path.dirname(_os.path.abspath(__file__))
    search_dirs = [script_dir, '.', _os.path.join(script_dir, 'extra_Files'), 'extra_Files']
    patterns = [
        'FINAL_CALIBRATED_PARAMS_*.json',
        'BEST_PHASE1_PARAMS_*.json',
    ]

    files = []
    for d in search_dirs:
        if not _os.path.isdir(d):
            continue
        for p in patterns:
            files.extend(_glob.glob(_os.path.join(d, p)))

    if not files:
        return None

    latest = max(files, key=lambda f: _os.path.getmtime(f))
    try:
        with open(latest, 'r') as fh:
            data = json.load(fh)
        params = data.get('final_parameters', data.get('best_parameters', {}))
        _CALIBRATION_PARAM_KEYS = [
            'alpha_distance', 'beta_price_budget', 'gamma_quality_variety',
            'delta_convenience', 'go_shop_threshold_low',
            'go_shop_threshold_medium', 'go_shop_threshold_high',
        ]
        center = {k: params[k] for k in _CALIBRATION_PARAM_KEYS if k in params}
        if len(center) < len(_CALIBRATION_PARAM_KEYS):
            return None
        return center
    except Exception:
        return None


_CACHED_CALIBRATED_PARAMS = None
_CACHED_CALIBRATED_PARAMS_LOADED = False


def get_calibrated_params():
    """Return cached calibrated parameters dict (loaded once per process)."""
    global _CACHED_CALIBRATED_PARAMS, _CACHED_CALIBRATED_PARAMS_LOADED
    if not _CACHED_CALIBRATED_PARAMS_LOADED:
        _CACHED_CALIBRATED_PARAMS = _load_calibrated_params_from_json()
        _CACHED_CALIBRATED_PARAMS_LOADED = True
    return _CACHED_CALIBRATED_PARAMS


class IncomeLevel(Enum):
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"

class ProviderType(Enum):
    """Food provider types with detailed store classifications"""
    # Original types
    GROCERY_STORE = "grocery_store"
    CORNER_STORE = "corner_store"
    FOOD_HUB = "food_hub"
    MOBILE_PANTRY = "mobile_pantry"
    
    # Detailed store types for choice model
    SUPERCENTER = "supercenter"        # e.g., Walmart Supercenter, Target
    SUPERMARKET = "supermarket"        # e.g., Publix, Kroger
    CONVENIENCE = "convenience"        # e.g., 7-Eleven, gas station stores
    CLUB_STORE = "club_store"          # e.g., Costco, Sam's Club
    DISCOUNT = "discount"              # e.g., Aldi, Save-A-Lot
    SPECIALTY = "specialty"            # e.g., Whole Foods, Trader Joe's
    
    # Delivery/alternative options
    DELIVERY_SERVICE = "delivery"      # Online grocery delivery
    PANTRY = "pantry"                  # Food pantry/bank

# Store type mapping for backward compatibility
STORE_TYPE_MAPPING = {
    ProviderType.GROCERY_STORE: ProviderType.SUPERMARKET,
    ProviderType.CORNER_STORE: ProviderType.CONVENIENCE,
}

# ========================================================================
# HOUSEHOLD INCOME CLASSIFICATION (2023 Cutoffs)
# ========================================================================

class IncomeClassifier:
    """
    Classifies household income into Low/Medium/High based on 2023 cutoffs
    
    Cutoffs (Jacksonville, FL 2023):
    - Low: < $28,262
    - Medium: $28,262 - $90,239
    - High: > $90,239
    """
    
    LOW_THRESHOLD = 28262.0
    HIGH_THRESHOLD = 90239.0
    
    @classmethod
    def classify_income(cls, annual_income: float) -> IncomeLevel:
        """
        Classify household income into IncomeLevel enum
        
        Args:
            annual_income: Annual household income in dollars
            
        Returns:
            IncomeLevel enum (LOW, MEDIUM, or HIGH)
        """
        if annual_income < cls.LOW_THRESHOLD:
            return IncomeLevel.LOW
        elif annual_income <= cls.HIGH_THRESHOLD:
            return IncomeLevel.MEDIUM
        else:
            return IncomeLevel.HIGH
    
    @classmethod
    def get_income_category_bounds(cls, category: IncomeLevel) -> tuple:
        """Get min/max income bounds for a category"""
        if category == IncomeLevel.LOW:
            return (0, cls.LOW_THRESHOLD)
        elif category == IncomeLevel.MEDIUM:
            return (cls.LOW_THRESHOLD, cls.HIGH_THRESHOLD)
        else:  # HIGH
            return (cls.HIGH_THRESHOLD, float('inf'))
    
    @classmethod
    def generate_random_income(cls, category: IncomeLevel) -> float:
        """Generate random income within category bounds"""
        if category == IncomeLevel.LOW:
            return random.uniform(15000, cls.LOW_THRESHOLD - 1)
        elif category == IncomeLevel.MEDIUM:
            return random.uniform(cls.LOW_THRESHOLD, cls.HIGH_THRESHOLD)
        else:  # HIGH
            return random.uniform(cls.HIGH_THRESHOLD + 1, 150000)

@dataclass
class CensusTractData:
    """
    Structure for census tract demographic data
    
    This will be populated from actual census data files
    """
    tract_id: str = ""
    
    # Income distribution (percentages that sum to 1.0)
    pct_low_income: float = 0.45
    pct_medium_income: float = 0.35
    pct_high_income: float = 0.20
    
    # Household size distribution
    avg_household_size: float = 2.5
    pct_size_1: float = 0.30
    pct_size_2: float = 0.30
    pct_size_3: float = 0.20
    pct_size_4: float = 0.12
    pct_size_5_plus: float = 0.08
    
    # Vehicle availability by income
    pct_vehicle_low: float = 0.40
    pct_vehicle_medium: float = 0.70
    pct_vehicle_high: float = 0.90
    
    # SNAP/Pantry eligibility by race
    snap_eligible_by_race: Dict[str, float] = None
    
    # Race distribution
    pct_white: float = 0.35
    pct_black: float = 0.55
    pct_hispanic: float = 0.05
    pct_asian: float = 0.03
    pct_other: float = 0.02
    
    def __post_init__(self):
        if self.snap_eligible_by_race is None:
            self.snap_eligible_by_race = {
                'white': 0.25,
                'black': 0.45,
                'hispanic': 0.40,
                'asian': 0.20,
                'other': 0.30
            }

@dataclass
class SpatialBounds:
    """Spatial bounds for Health Zone 1"""
    min_lon: float = -81.8
    max_lon: float = -81.5
    min_lat: float = 30.2
    max_lat: float = 30.5

@dataclass
class SimulationConfig:
    """Comprehensive configuration for Enhanced Mesa-Geo simulation"""
    # Basic simulation parameters
    num_consumers: int = 500
    simulation_days: int = 30
    
    # Store/Provider configurations
    grocery_store_capacity: int = 600
    scenario1_store_region: str = "optimal"  # optimal|north|south|east|west|center
    corner_store_capacity: int = 60
    food_hub_capacity: int = 300
    mobile_pantry_capacity: int = 120
    num_corner_stores: int = 6
    num_food_hubs: int = 1
    num_mobile_pantries: int = 2
    
    # ===================================================================
    # REALISTIC HOUSEHOLD ECONOMIC & BEHAVIORAL PARAMETERS
    # ===================================================================
    
    # Weekly food budget by income level (dollars)
    weekly_budget_low: float = 75.0      # BLS CES 2023: $3,707/yr food-at-home
                                         # ÷52=$71.29/wk; $75 adds 5% buffer
                                         # for corner-store cap losses
    weekly_budget_medium: float = 90.0   # BLS CES 2023: $4,672/yr food-at-home
                                         # ÷52=$89.85/wk → $90
    weekly_budget_high: float = 327.0    # Not a calibration target; kept for
                                         # face validity (high income unconstrained)
    budget_sigma: float = 0.25  # Lognormal σ (±25% variability)
    
    # Mean basket size by household size (dollars per trip)
    # These are BASE values - will be multiplied by income-based multipliers
    basket_size_1: float = 131.0
    basket_size_2: float = 143.0
    basket_size_3_4: float = 204.0
    basket_size_5_plus: float = 262.0
    basket_sigma: float = 0.30  # Lognormal σ (±30% variability)
    
    # Income-based basket multipliers (applied to base basket sizes)
    # These ensure spending aligns with USER'S CORRECTED TARGETS from table
    # Low: $51 × 2 trips/week = $102/week ≈ $5,304/year ≈ target $5,270 ✓
    # Medium: $173 × 1 trip/week = $173/week ≈ $9,004/year ≈ target $8,989 ✓
    # High: $363 × 0.9 trips/week = $327/week ≈ $17,004/year ≈ target $16,996 ✓
    basket_multiplier_low_income: float = 0.39    # Low income: 39% of base (enables $3,707/yr target)
    basket_multiplier_medium_income: float = 0.85  # Medium income: 85% of base (e.g., $204 → $173)
    basket_multiplier_high_income: float = 1.78    # High income: 178% of base (e.g., $204 → $363)
    
    # Shopping frequency by income level (days between trips)
    # Format: (min_days, max_days) - uniform random int in range
    # CORRECTED: Low-income shops LESS frequently with smaller baskets to match $101/week
    freq_low_income: Tuple[int, int] = (3, 5)      # Every 3-5 days (not 2-4)
    freq_medium_income: Tuple[int, int] = (6, 8)   # Every 6-8 days  
    freq_high_income: Tuple[int, int] = (10, 30)   # Every 10-30 days
    freq_jitter_days: int = 1  # ±1 day jitter per trip
    
    # Max practical distance to primary store (km)
    max_distance_car: float = 5.5       # 3.4 miles with car
    max_distance_no_car: float = 0.8    # 0.5 miles without car, Ver Ploeg et al. 2015
    distance_noise_pct: float = 0.10    # ±10% uniform noise
    
    # ===================================================================
    # DISCRETE CHOICE MODEL PARAMETERS - CALIBRATED (Phase 2, Error ≈ 0.0946)
    # Source: FINAL_CALIBRATED_PARAMS_20260228_050319.json
    # Auto-loaded from JSON in __post_init__; defaults here are a safety net.
    # ===================================================================
    
    # Utility weights (CALIBRATED - DO NOT CHANGE without re-calibration)
    alpha_distance: float = 3.0         # Distance disutility weight
    beta_price_budget: float = 0.5      # Price/budget consciousness weight
    gamma_quality_variety: float = 0.6  # Quality/variety preference weight
    delta_convenience: float = 0.4      # Convenience factor weight
    
    # Store-type biases by income level (additive offsets to utility)
    # Format: {store_type: bias_value}
    store_bias_low_income: Dict[str, float] = None
    store_bias_medium_income: Dict[str, float] = None
    store_bias_high_income: Dict[str, float] = None
    
    # Go-shop threshold (days since last shop that triggers shopping need) - CALIBRATED
    go_shop_threshold_low: float = 4.0      # Low income
    go_shop_threshold_medium: float = 6.0   # Medium income (Phase 2 calibrated)
    go_shop_threshold_high: float = 14.0    # High income
    
    # Pantry propensity (probability of using food pantry when available)
    # INCREASED SIGNIFICANTLY to achieve 12.5% target usage (after diagnostics showed 3.5%)
    pantry_propensity_eligible: float = 0.12    # SNAP-eligible HH: Bertmann et al. (2021)
                                                # 14.5% of HH use pantries, ~2x/month.
                                                # Low-income agents ~15 trips/90 days →
                                                # per-trip probability = 0.27 × 0.40 ≈ 0.12
    pantry_propensity_ineligible: float = 0.02  # Non-SNAP: ~5% ever use pantries (Bertmann 2021)
                                                # per-trip probability ≈ 0.02
    
    # Delivery propensity (probability of ELIGIBLE household using delivery as main source)
    # NOTE: Target is 3-20% depending on income level
    # CORRECTED values to match actual HZ1 usage rates (accounting for 50% hard blockers)
    delivery_baseline_low: float = 0.08         # Low income: 8% → ~4% actual (after 50% blockers)
    delivery_baseline_medium: float = 0.20      # Medium income: 20% → ~10% actual
    delivery_baseline_high: float = 0.35        # High income: 35% → ~17-20% actual
    delivery_subsidy_uplift: float = 2.5        # Multiplier under subsidy
    snap_delivery_discount: float = 0.50
    # SNAP-eligible households get 50% off delivery fee
    # Source: Ashley 2024 (DoorDash SNAP discount); Shepard 2024
    delivery_hard_blockers_share: float = 0.5   # Share that never adopts (no internet, etc.)
    
    # Delivery choice probabilities (when delivery is considered AND available)
    # REDUCED to prevent over-selection of delivery
    delivery_choice_free_prob: float = 0.20      # Prob. of using FREE delivery (reduced from 0.35)
    delivery_choice_nocar_far_prob: float = 0.15 # Prob. of using delivery (no car, physical >1km) (reduced from 0.25)
    delivery_choice_accessible_prob: float = 0.04 # Prob. of using delivery (physical nearby) (reduced from 0.08)
    
    # ===================================================================
    # PROVIDER/STORE CONFIGURATION PARAMETERS
    # ===================================================================
    
    # Operating hours by provider type (start_hour, end_hour)
    operating_hours: Dict[str, Tuple[int, int]] = None
    
    # Service area radius by provider type (km)
    service_areas: Dict[str, float] = None
    
    # Income modifiers for transaction amounts
    income_modifiers: Dict[str, float] = None
    
    # Market days for food hubs (0=Monday, 6=Sunday)
    food_hub_market_days: List[int] = None
    # Schedule for mobile pantries: dict[weekday]->list of location names or dynamic
    mobile_pantry_schedule: Dict[int, Any] = None
    # Strategy for mobile pantry placement: fixed|rotating|needs_based
    mobile_pantry_strategy: str = "fixed"
    # Fixed named street locations for mobile pantries (optional)
    fixed_pantry_locations: Dict[str, Tuple[float, float]] = None
    
    # Technical/spatial parameters (use config for defaults)
    health_zone_shapefile: str = None
    roads_shapefile: str = None
    use_road_network: bool = True
    enable_spatial_analytics: bool = True
    spatial_cluster_eps: float = 0.01
    spatial_cluster_min_samples: int = 5
    
    def __post_init__(self):
        """Set default values for complex parameters"""
        from config import get_health_zone_shapefile, get_roads_shapefile
        if self.health_zone_shapefile is None:
            self.health_zone_shapefile = get_health_zone_shapefile()
        if self.roads_shapefile is None:
            self.roads_shapefile = get_roads_shapefile()

        # Apply calibrated parameters from the most recent JSON file.
        # This ensures every SimulationConfig instance uses calibrated values
        # regardless of which file creates it.  Values set via setattr after
        # construction (e.g. SA sweeps) will still override these.
        _cal = get_calibrated_params()
        if _cal is not None:
            self.alpha_distance = _cal['alpha_distance']
            self.beta_price_budget = _cal['beta_price_budget']
            self.gamma_quality_variety = _cal['gamma_quality_variety']
            self.delta_convenience = _cal['delta_convenience']
            self.go_shop_threshold_low = _cal['go_shop_threshold_low']
            self.go_shop_threshold_medium = _cal['go_shop_threshold_medium']
            self.go_shop_threshold_high = _cal['go_shop_threshold_high']

        # Set default store-type biases for discrete choice model
        if self.store_bias_low_income is None:
            self.store_bias_low_income = {
                'supercenter': 0.1,      # Low income prefers supercenters (low prices)
                'convenience': 0.05,     # Slight preference for nearby convenience
                'discount': 0.15,        # Strong preference for discount stores
                'supermarket': 0.0,      # Neutral
                'club_store': -0.1,      # Membership cost barrier
                'specialty': -0.2        # Too expensive
            }
        
        if self.store_bias_medium_income is None:
            self.store_bias_medium_income = {
                'supercenter': 0.05,
                'convenience': 0.0,
                'discount': 0.05,
                'supermarket': 0.05,     # Slight preference
                'club_store': 0.0,
                'specialty': 0.0
            }
        
        if self.store_bias_high_income is None:
            self.store_bias_high_income = {
                'supercenter': 0.0,
                'convenience': 0.0,
                'discount': -0.05,       # Slight aversion
                'supermarket': 0.1,      # Preference for quality
                'club_store': 0.05,      # Can afford membership
                'specialty': 0.1         # Quality/variety preference
            }
        
        if self.operating_hours is None:
            self.operating_hours = {
                'grocery_store': (6, 22),
                'corner_store': (7, 21),
                'food_hub': (8, 18),
                'mobile_pantry': (9, 17)
            }
        
        if self.service_areas is None:
            self.service_areas = {
                'grocery_store': 10.0,
                'corner_store': 3.0,
                'food_hub': 15.0,
                'mobile_pantry': 5.0
            }
        
        # INCOME MODIFIERS: Used for transaction amounts only (not travel distance!)
        # Travel distance is fixed: car=5.5km, no-car=0.8km with ±10% noise
        if self.income_modifiers is None:
            self.income_modifiers = {
                'low': 0.7,     # Lower transaction amounts
                'medium': 1.0,  # Base transaction amounts
                'high': 1.3     # Higher transaction amounts
            }
        
        if self.food_hub_market_days is None:
            self.food_hub_market_days = [0, 2, 4]  # Monday, Wednesday, Friday
        if self.mobile_pantry_schedule is None:
            # Default: Tue/Thu/Sat
            self.mobile_pantry_schedule = {1: 'fixed', 3: 'fixed', 5: 'fixed'}
        if self.fixed_pantry_locations is None:
            # Example named streets with approximate lon/lat inside HZ1 (placeholders ~ centroid offsets)
            centroid = ( -81.6892, 30.3575 )
            self.fixed_pantry_locations = {
                'Main St & 8th': (centroid[0] - 0.01, centroid[1] + 0.005),
                'Phoenix Ave & 21st': (centroid[0] + 0.012, centroid[1] + 0.006),
                'Pearl St & 44th': (centroid[0] - 0.008, centroid[1] + 0.02)
            }

class EnhancedHouseholdAgent(mg.GeoAgent):
    """
    Enhanced Mesa-Geo HOUSEHOLD agent with advanced spatial capabilities
    
    Represents a household (not individual) with:
    - Income classification based on 2023 cutoffs
    - Household size (1-5+ members)
    - Vehicle availability
    - SNAP/Pantry eligibility
    - Race (primary household race)
    """
    
    def __init__(self, model: mesa.Model, geometry: Point, 
                 income: IncomeLevel, vehicle_available: bool, 
                 household_size: int = 2, **demographics):
        """
        Initialize household agent
        
        Args:
            model: Mesa model instance
            geometry: Point location (lat/lon)
            income: IncomeLevel (LOW/MEDIUM/HIGH) based on 2023 cutoffs
            vehicle_available: Whether household has vehicle access
            household_size: Number of people in household (default: 2)
            **demographics: race, snap_eligible, annual_income, census_tract, etc.
        """
        # Mesa-geo initialization
        super().__init__(model, geometry, crs="EPSG:4326")
        
        # ===== HOUSEHOLD CHARACTERISTICS =====
        self.income = income
        self.vehicle_available = vehicle_available  # Renamed from car_ownership
        self.household_size = max(1, household_size)  # Ensure at least 1
        
        # Annual income (actual dollar amount)
        self.annual_income = demographics.get('annual_income', 
                                             IncomeClassifier.generate_random_income(income))
        
        # Race (primary household race for demographic analysis)
        self.race = demographics.get('race', random.choice(
            ['white', 'black', 'hispanic', 'asian', 'other']
        ))
        
        # SNAP/Pantry eligibility
        self.snap_eligible = demographics.get('snap_eligible', False)
        
        # Census tract ID (for spatial analysis)
        self.census_tract = demographics.get('census_tract', 'unknown')
        self.zip_code = demographics.get('zip_code', '32206')
        
        # Get configuration from model
        self.config = getattr(model, 'config', SimulationConfig())
        
        # ===== REALISTIC ECONOMIC & BEHAVIORAL PARAMETERS =====
        
        # Weekly food budget (lognormal distribution)
        budget_mean = self._get_weekly_budget_mean()
        self.weekly_budget = generate_lognormal_value(budget_mean, self.config.budget_sigma)
        
        # Mean basket size per shopping trip (lognormal distribution)
        basket_mean = self._get_basket_size_mean()
        self.mean_basket_size = generate_lognormal_value(basket_mean, self.config.basket_sigma)
        
        # Shopping frequency (days between trips) - integer with jitter
        self.base_shopping_frequency = self._calculate_shopping_frequency_days()
        self.shopping_frequency = self.base_shopping_frequency  # Will add jitter per trip
        
        # Max practical distance with ±10% noise
        base_distance = (self.config.max_distance_car if self.vehicle_available 
                        else self.config.max_distance_no_car)
        self.max_travel_distance = add_uniform_noise(base_distance, self.config.distance_noise_pct)
        
        # Ensure constraint: weekly_spend ≈ trips × mean_basket
        # Calculate expected trips per week
        self.trips_per_week = 7.0 / self.shopping_frequency
        self.expected_weekly_spend = self.trips_per_week * self.mean_basket_size
        
        # Track actual spending
        self.weekly_spent = 0.0
        self.trip_count_this_week = 0
        
        # ===== FULL-SHOP vs TOP-UP TRACKING (Idea #1) =====
        self.spent_this_week = 0.0  # Same as weekly_spent, but more explicit
        self.unmet_need = 0.0  # Carry-forward when full shop fails
        self.week_number = 0  # Track week number for resets
        self.last_full_shop_step = -999  # Track when last full shop occurred
        
        # ===== FOOD ACCESS PARAMETERS (SCALED BY HOUSEHOLD SIZE) =====
        self.shopping_threshold = self._calculate_shopping_threshold()
        # Initialize with varied food supply (1-5 days worth) for dynamic visualization
        # This ensures households start in different states and we see satisfaction changes from day 1
        self.food_supply = random.randint(1, 5) * self.household_size
        # Note: max_travel_distance now set above with realistic values
        
        # ===== SIMULATION TRACKING =====
        self.satisfied_today = False
        self.travel_distance = 0.0
        self.unsatisfied = False
        self.needed_to_shop_today = False
        self.no_active_provider_today = False
        self.shopping_history = []
        
        # ===== CHOICE MODEL PARAMETERS =====
        # Days since last shopping trip (triggers go-shop threshold)
        self.days_since_last_shop = 0
        self.last_shop_day = -random.randint(1, self.base_shopping_frequency)  # Stagger first trip
        
        # Go-shop threshold based on income
        self.go_shop_threshold = self._get_go_shop_threshold()
        
        # Pantry access propensity
        self.pantry_propensity = (self.config.pantry_propensity_eligible if self.snap_eligible 
                                 else self.config.pantry_propensity_ineligible)
        
        # Digital access (No Kid Hungry 2021): income-specific probability of having
        # internet + device + skills to order groceries online.
        # This REPLACES the old delivery_hard_blockers_share (flat 50%) with
        # empirically-grounded income-specific rates.
        dig_prob = (0.50 if self.income == IncomeLevel.LOW else
                    0.80 if self.income == IncomeLevel.MEDIUM else 0.95)
        self.has_digital_access = random.random() < dig_prob

        # Delivery capability now gates solely on digital access
        self.can_use_delivery = self.has_digital_access
        self.delivery_propensity = self._get_delivery_propensity()

        # Determine if this household is a "delivery user" ONCE at initialization
        # Prevents rolling dice every shopping trip (which inflated usage to 60%)
        self.is_delivery_user = (self.can_use_delivery and
                                 random.random() < self.delivery_propensity)
        
        # Store type biases for utility calculation
        self.store_type_biases = self._get_store_type_biases()
        
        # ===== ENHANCED SPATIAL TRACKING =====
        self.accessibility_score = 0.0
        self.spatial_cluster_id = None
        self.nearest_providers_cache = None
        self.last_cache_update = None
    
    def _calculate_shopping_threshold(self) -> int:
        """
        Calculate shopping threshold based on income and household size
        
        Threshold represents food supply level that triggers shopping
        Scaled by household size (larger households need more food buffer)
        """
        if self.income == IncomeLevel.LOW:
            base_threshold = random.randint(0, 1)
        elif self.income == IncomeLevel.HIGH:
            base_threshold = random.randint(1, 2)
        else:
            base_threshold = random.randint(0, 2)
        
        # Scale by household size (larger households shop when have less per person)
        return base_threshold * self.household_size
    
    def _calculate_max_travel_distance(self) -> float:
        """
        Calculate max travel distance for household
        
        Based on vehicle availability ONLY (fixed distances as specified by user)
        - Car: 5.5 km with ±10% noise per household
        - No-car: 0.8 km with ±10% noise per household
        
        NOTE: This method is for backward compatibility with old scenarios.
        New code uses max_distance_car/max_distance_no_car directly in __init__.
        """
        # Fixed distance based on vehicle availability (NO income multiplier!)
        if self.vehicle_available:
            base_distance = self.config.max_distance_car
        else:
            base_distance = self.config.max_distance_no_car
        
        # Apply ±10% uniform noise per household (as specified)
        return add_uniform_noise(base_distance, self.config.distance_noise_pct)
    
    def _get_weekly_budget_mean(self) -> float:
        """
        Get mean weekly food budget based on income level
        
        Returns:
            Mean weekly budget in dollars
        """
        if self.income == IncomeLevel.LOW:
            return self.config.weekly_budget_low
        elif self.income == IncomeLevel.MEDIUM:
            return self.config.weekly_budget_medium
        else:  # HIGH
            return self.config.weekly_budget_high
    
    def _get_basket_size_mean(self) -> float:
        """
        Get mean basket size based on household size AND income
        
        Returns:
            Mean basket size in dollars per shopping trip (income-adjusted)
        """
        # Get base basket size by household size
        if self.household_size == 1:
            base_basket = self.config.basket_size_1
        elif self.household_size == 2:
            base_basket = self.config.basket_size_2
        elif self.household_size in [3, 4]:
            base_basket = self.config.basket_size_3_4
        else:  # 5+
            base_basket = self.config.basket_size_5_plus
        
        # Apply income-based multiplier to align spending with budgets
        if self.income == IncomeLevel.LOW:
            multiplier = self.config.basket_multiplier_low_income
        elif self.income == IncomeLevel.MEDIUM:
            multiplier = self.config.basket_multiplier_medium_income
        else:  # HIGH
            multiplier = self.config.basket_multiplier_high_income
        
        return base_basket * multiplier
    
    def _calculate_shopping_frequency_days(self) -> int:
        """
        Calculate shopping frequency in days based on income level
        Uses realistic frequency bands
        
        Returns:
            Days between shopping trips (integer)
        """
        if self.income == IncomeLevel.LOW:
            freq_range = self.config.freq_low_income
        elif self.income == IncomeLevel.MEDIUM:
            freq_range = self.config.freq_medium_income
        else:  # HIGH
            freq_range = self.config.freq_high_income
        
        # Random integer in range
        return random.randint(freq_range[0], freq_range[1])
    
    def _apply_frequency_jitter(self) -> int:
        """
        Apply ±1 day jitter to shopping frequency
        
        Returns:
            Jittered frequency (minimum 1 day)
        """
        jitter = random.randint(-self.config.freq_jitter_days, self.config.freq_jitter_days)
        return max(1, self.base_shopping_frequency + jitter)
    
    def _get_go_shop_threshold(self) -> float:
        """Get go-shop threshold (days since last shop) based on income"""
        if self.income == IncomeLevel.LOW:
            return self.config.go_shop_threshold_low
        elif self.income == IncomeLevel.MEDIUM:
            return self.config.go_shop_threshold_medium
        else:  # HIGH
            return self.config.go_shop_threshold_high
    
    def _determine_delivery_capability(self) -> bool:
        """
        Determine if household can use delivery service
        Some households are hard blockers (no internet, no device, etc.)
        """
        # Random draw - some households can never use delivery
        return random.random() >= self.config.delivery_hard_blockers_share
    
    def _get_delivery_propensity(self) -> float:
        """Get baseline delivery propensity based on income"""
        if not self.can_use_delivery:
            return 0.0
        
        if self.income == IncomeLevel.LOW:
            return self.config.delivery_baseline_low
        elif self.income == IncomeLevel.MEDIUM:
            return self.config.delivery_baseline_medium
        else:  # HIGH
            return self.config.delivery_baseline_high
    
    def _should_use_delivery_today(self) -> bool:
        """Decide if household will use delivery today (stochastic choice)"""
        if not self.can_use_delivery:
            return False
        
        # Check if any delivery services available
        delivery_services = [p for p in self.model.food_providers 
                            if isinstance(p, EnhancedDeliveryService)]
        if not delivery_services:
            return False
        
        # Stochastic choice based on propensity
        # If subsidized delivery exists, increase propensity by uplift multiplier
        has_subsidy = any(d.subsidized for d in delivery_services)
        effective_propensity = self.delivery_propensity
        if has_subsidy:
            effective_propensity *= self.config.delivery_subsidy_uplift
            effective_propensity = min(effective_propensity, 0.95)  # Cap at 95%
        
        return random.random() < effective_propensity
    
    def _find_best_delivery_service(self) -> Tuple[Optional['EnhancedDeliveryService'], float, float]:
        """
        Find best delivery service within delivery area.

        CRITICAL: Distance is calculated from BEST GROCERY STORE to household,
        not from delivery hub to household. This reflects how delivery services work:
        - Delivery picks up from a grocery store
        - Delivers to household
        - Fee is based on store-to-household distance

        Returns:
            Tuple of (best_service, delivery_distance_km, delivery_utility)
            - best_service: The EnhancedDeliveryService or None
            - delivery_distance_km: Distance from best grocery store to HH
            - delivery_utility: Comparable to calculate_utility() for physical stores
        """
        delivery_services = [p for p in self.model.food_providers
                            if isinstance(p, EnhancedDeliveryService)]

        if not delivery_services:
            return None, float('inf'), -float('inf')

        # STEP 1: Find best GROCERY STORE for this household
        grocery_stores = [p for p in self.model.food_providers
                         if p.provider_type == ProviderType.GROCERY_STORE]

        if not grocery_stores:
            return None, float('inf'), -float('inf')

        best_grocery = None
        best_grocery_utility = -float('inf')
        best_grocery_distance = float('inf')

        for store in grocery_stores:
            if store.current_inventory <= 0:
                continue
            distance_degrees = self.geometry.distance(store.geometry)
            distance_km = distance_degrees * 111
            utility = self.calculate_utility(store, distance_km)
            if utility > best_grocery_utility:
                best_grocery_utility = utility
                best_grocery = store
                best_grocery_distance = distance_km

        if not best_grocery:
            return None, float('inf'), -float('inf')

        # STEP 2: Find best delivery service that covers household AND grocery store
        best_service = None
        best_delivery_utility = -float('inf')
        best_delivery_distance = float('inf')

        for service in delivery_services:
            if service.current_inventory <= 0:
                continue

            hub_to_household_degrees = self.geometry.distance(service.geometry)
            hub_to_household_km = hub_to_household_degrees * 111

            if hub_to_household_km > service.delivery_area_km:
                continue

            delivery_distance_km = best_grocery_distance

            # Calculate delivery fee (with SNAP discount applied here)
            delivery_fee = service.get_effective_fee_for_household(self, delivery_distance_km)
            if self.snap_eligible and self.income == IncomeLevel.LOW:
                delivery_fee *= self.config.snap_delivery_discount

            fee_fraction = delivery_fee / max(self.weekly_budget, 1.0)

            # Friction penalty: treat delivery wait/planning as equivalent to 2 km
            # travel using FIXED reference (max_distance_car) so no-car agents are
            # not penalised more than car agents (Yao et al. 2023)
            friction_penalty = self.config.alpha_distance * (2.0 / self.config.max_distance_car)

            budget_weight = (1.0 if self.income == IncomeLevel.LOW else
                             0.7 if self.income == IncomeLevel.MEDIUM else 0.5)

            delivery_utility = (
                - friction_penalty
                + self.config.gamma_quality_variety * service.quality_score
                + self.config.beta_price_budget * (1.0 - fee_fraction) * budget_weight
                - fee_fraction * 10.0
            )

            if service.subsidized and self.snap_eligible:
                delivery_utility += 0.20

            if delivery_utility > best_delivery_utility:
                best_delivery_utility = delivery_utility
                best_service = service
                best_delivery_distance = delivery_distance_km

        if best_service is None:
            return None, float('inf'), -float('inf')
        return best_service, best_delivery_distance, best_delivery_utility
    
    def _get_store_type_biases(self) -> Dict[str, float]:
        """Get store type biases based on income level"""
        if self.income == IncomeLevel.LOW:
            return self.config.store_bias_low_income.copy()
        elif self.income == IncomeLevel.MEDIUM:
            return self.config.store_bias_medium_income.copy()
        else:  # HIGH
            return self.config.store_bias_high_income.copy()
    
    def calculate_utility(self, provider, distance: float) -> float:
        """
        Calculate utility for a provider using discrete choice model
        
        Utility = α*distance_term + β*price_term + γ*quality_term + δ*convenience_term + store_bias
        
        Args:
            provider: Food provider
            distance: Distance to provider in km
            
        Returns:
            Utility value (higher is better)
        """
        # Distance disutility (negative, scaled by distance relative to max)
        distance_term = -self.config.alpha_distance * (distance / self.max_travel_distance)
        
        # Price/budget term (better for stores that match budget constraints)
        # Estimate: lower-priced stores get higher utility for budget-constrained HH
        # Use store type as proxy for price level
        price_score = 1.0  # Default neutral
        store_type_str = provider.provider_type.value if hasattr(provider.provider_type, 'value') else str(provider.provider_type)
        
        # MOBILE PANTRIES ARE FREE! Massive price advantage, especially for low-income
        if store_type_str in ['mobile_pantry', 'pantry', 'food_pantry']:
            price_score = 3.0  # HUGE advantage (free food!)
        # IDEA #1: Corner stores have 1.16x price premium (makes them less attractive)
        elif store_type_str == 'corner_store':
            price_score = 1.0 / 1.16  # Lower utility due to higher prices (≈0.86)
        elif store_type_str in ['discount', 'supercenter']:
            price_score = 1.2  # Lower prices
        elif store_type_str in ['specialty', 'club_store']:
            price_score = 0.8  # Higher prices
        
        # Budget consciousness varies by income (pantries especially attractive for low-income!)
        budget_weight = 1.0 if self.income == IncomeLevel.LOW else (0.7 if self.income == IncomeLevel.MEDIUM else 0.5)
        price_term = self.config.beta_price_budget * price_score * budget_weight
        
        # Quality/variety term (from provider's quality_score)
        quality_score = getattr(provider, 'quality_score', 0.7)
        quality_term = self.config.gamma_quality_variety * quality_score
        
        # Convenience term (inventory availability + operating hours)
        availability = getattr(provider, 'current_inventory', 100) / getattr(provider, 'capacity', 100)
        convenience_score = availability * 0.5 + 0.5  # Range [0.5, 1.0]
        convenience_term = self.config.delta_convenience * convenience_score
        
        # Store type bias (income-specific preferences)
        store_bias = self.store_type_biases.get(store_type_str, 0.0)
        
        # Total utility
        utility = distance_term + price_term + quality_term + convenience_term + store_bias
        
        # CRITICAL FIX: Add MASSIVE utility boost for mobile pantries to encourage usage
        # Pantries are FREE and provide essential food - should be highly attractive
        # Especially for SNAP-eligible and low-income households
        # INCREASED FURTHER after diagnostics showed 3.5% usage (target: 12.5%)
        if store_type_str in ['mobile_pantry', 'pantry', 'food_pantry']:
            pantry_boost = 10.0  # Base boost for all households (increased from 5.0)
            # Extra boost for low-income and SNAP-eligible
            if self.income == IncomeLevel.LOW:
                pantry_boost += 5.0  # Total +15.0 for low income (increased from +7.0)
            if self.snap_eligible:
                pantry_boost += 3.0  # Additional +3.0 for SNAP-eligible (increased from +1.5)
            utility += pantry_boost
        
        return utility
    
    def update_accessibility_score(self):
        """
        Calculate accessibility score based on nearby providers
        Uses discrete choice model utility for scoring
        """
        nearby_providers = self.model.get_providers_within_distance(self, self.max_travel_distance)
        # Consider only providers that can currently serve
        available_nearby = []
        for provider, distance in nearby_providers:
            try:
                if provider.can_serve_customer():
                    available_nearby.append((provider, distance))
            except Exception:
                # Fallback to availability factor if method not present
                if getattr(provider, 'current_inventory', 0) > 0:
                    available_nearby.append((provider, distance))
        
        if not available_nearby:
            self.accessibility_score = 0.0
            return
        
        # Score based on discrete choice model utility
        total_score = 0.0
        for provider, distance in available_nearby:
            # Use the same utility calculation as shopping decisions
            utility = self.calculate_utility(provider, distance)
            # Convert utility to positive score (utility can be negative)
            provider_score = max(0, utility + 2.0)  # Shift to make positive
            total_score += provider_score
        
        self.accessibility_score = min(total_score, 10.0)  # Cap at 10
    
    def step(self):
        """Enhanced Mesa agent step with better spatial logic"""
        self.satisfied_today = False
        self.unsatisfied = False
        self.travel_distance = 0.0
        self.needed_to_shop_today = False
        self.no_active_provider_today = False
        
        # Reset weekly spending counters (every 7 days)
        if self.model.schedule.steps % 7 == 0:
            self.weekly_spent = 0.0
            self.spent_this_week = 0.0  # Reset for Idea #1 tracking
            self.trip_count_this_week = 0
            self.week_number += 1
            # Update accessibility score
            self.update_accessibility_score()
            # Apply jitter to shopping frequency for this week
            self.shopping_frequency = self._apply_frequency_jitter()
        
        # Update days since last shop
        current_day = self.model.schedule.steps
        self.days_since_last_shop = current_day - self.last_shop_day
        
        # ===================================================================
        # IDEA #1: FULL-SHOP vs TOP-UP DETERMINATION
        # ===================================================================
        # Calculate needed basket size based on budget depletion
        needed = max(0, self.weekly_budget - self.spent_this_week + self.unmet_need)
        
        # Full-shop threshold: max(0.5 × weekly_budget, $50)
        full_shop_threshold = max(0.5 * self.weekly_budget, 50.0)
        
        # Determine shop type
        is_full_shop = (needed >= full_shop_threshold)
        
        # CHOICE MODEL: Shopping trigger based on go-shop threshold
        # Shop if days_since_last_shop >= threshold OR food_supply critically low
        needs_to_shop = (self.days_since_last_shop >= self.go_shop_threshold or 
                        self.food_supply <= self.shopping_threshold)
        
        if needs_to_shop:
            self.needed_to_shop_today = True
            # Pre-check available providers to mark reason if none
            try:
                available = self.model.get_available_providers_for_consumer(self)
                self.no_active_provider_today = (len(available) == 0)
            except Exception:
                self.no_active_provider_today = False
            
            # ===================================================================
            # DELIVERY vs. PHYSICAL STORE DECISION
            # ===================================================================
            # SIMPLIFIED LOGIC: Physical stores are DEFAULT, delivery is OPTION
            # This ensures households can use BOTH delivery and physical stores
            
            # Step 1: Find best physical store
            best_provider, distance, physical_utility = self.find_best_provider(
                exclude_corners=is_full_shop)
            if best_provider is None and is_full_shop:
                best_provider, distance, physical_utility = self.find_best_provider(
                    exclude_corners=False)
            used_delivery = False

            # Step 2: Consider delivery (uses _should_use_delivery_today so subsidy
            # uplift is applied when subsidized delivery exists; otherwise uses baseline propensity)
            if self._should_use_delivery_today():
                best_delivery, delivery_distance, delivery_util = (
                    self._find_best_delivery_service())

                if best_delivery:
                    if best_provider is None:
                        # No physical store reachable — delivery user uses
                        # their delivery service as primary shopping method.
                        # Non-delivery-users fall through to unmet need.
                        best_provider = best_delivery
                        distance = delivery_distance
                        used_delivery = True
                    else:
                        # Both options available: utility comparison.
                        # habit_penalty reflects revealed preference for
                        # in-person shopping (Briesch et al. 2009).
                        habit_penalty = 0.15
                        if delivery_util > (physical_utility + habit_penalty):
                            best_provider = best_delivery
                            distance = delivery_distance
                            used_delivery = True
            
            # ===================================================================
            # ATTEMPT TO SHOP (delivery or physical)
            # ===================================================================
            # For delivery: household doesn't travel, so no distance check
            # For physical: check if within max_travel_distance
            can_use_provider = False
            if used_delivery:
                # Delivery: no travel by household, distance is hub-to-home for fee calculation
                can_use_provider = (best_provider is not None)
            else:
                # Physical store: check if within travel distance
                can_use_provider = (best_provider is not None and distance <= self.max_travel_distance)
            
            if can_use_provider:
                # For delivery services, pass distance for fee calculation
                if used_delivery and isinstance(best_provider, EnhancedDeliveryService):
                    success = best_provider.serve_customer(self, distance_km=distance)
                else:
                    success = best_provider.serve_customer(self)
                
                if success:
                    self.satisfied_today = True
                    # Household travel distance (0 for delivery, actual for physical)
                    self.travel_distance = 0.0 if used_delivery else distance
                    
                    # Update last shop day (for go-shop threshold)
                    self.last_shop_day = current_day
                    self.days_since_last_shop = 0
                    
                    # Budget-constrained basket: agent spends what remains of weekly budget
                    # This ensures annual spend ≈ weekly_budget × 52 (matches BLS targets)
                    remaining_budget = max(self.weekly_budget - self.spent_this_week, 20.0)
                    lognormal_draw = generate_lognormal_value(self.mean_basket_size, 0.10)
                    actual_basket = min(lognormal_draw, remaining_budget)
                    
                    # ===================================================================
                    # IDEA #1: CORNER STORE BASKET CAP & PRICE INDEX
                    # ===================================================================
                    is_corner_shop = (best_provider.provider_type == ProviderType.CORNER_STORE)
                    corner_basket_cap = 25.0  # $25 cap for corner stores
                    corner_price_index = 1.16  # Corners are 1.16x more expensive
                    
                    if is_corner_shop:
                        # Apply corner basket cap
                        actual_basket = min(actual_basket, corner_basket_cap)
                        
                        # Apply price index (corners cost more for same goods)
                        actual_basket_cost = actual_basket * corner_price_index
                        
                        # If this was a full-shop day but only corner was available
                        # Mark as partially satisfied and carry forward unmet need
                        if is_full_shop:
                            unmet_this_trip = max(0, needed - actual_basket)
                            # Cap unmet need at 1.5× weekly budget to prevent infinite accumulation
                            self.unmet_need = min(unmet_this_trip, 1.5 * self.weekly_budget)
                        else:
                            self.unmet_need = 0  # Top-up was sufficient
                    else:
                        # Non-corner store (grocery, etc.)
                        actual_basket_cost = actual_basket
                        self.unmet_need = 0  # Full shop succeeded
                        
                        # Track last successful full shop
                        if is_full_shop:
                            self.last_full_shop_step = current_day
                    
                    # Calculate delivery fee if using delivery (distance-based)
                    delivery_fee = 0.0
                    if used_delivery and isinstance(best_provider, EnhancedDeliveryService):
                        delivery_fee = best_provider.get_effective_fee_for_household(self, distance)
                    
                    # Track spending (basket cost + delivery fee)
                    # Note: actual_basket_cost includes corner price premium if applicable
                    self.weekly_spent += (actual_basket_cost + delivery_fee)
                    self.spent_this_week += (actual_basket_cost + delivery_fee)
                    self.trip_count_this_week += 1
                    
                    # Restock food (scaled by household size)
                    base_restock = random.randint(5, 8)
                    self.food_supply = base_restock * self.household_size
                    
                    # Record shopping event
                    shopping_event = {
                        'day': self.model.schedule.steps,
                        'provider_id': best_provider.unique_id,
                        'provider_type': best_provider.provider_type.value,
                        'distance': distance,  # Hub-to-home for delivery, travel for physical
                        'travel_distance': 0.0 if used_delivery else distance,  # Actual household travel
                        'satisfied': True,
                        'accessibility_score': self.accessibility_score,
                        'basket_size': actual_basket,
                        'basket_cost': actual_basket_cost,  # Actual cost (includes corner premium)
                        'delivery_fee': delivery_fee,
                        'used_delivery': used_delivery,
                        'weekly_spent_so_far': self.weekly_spent,
                        'is_full_shop': is_full_shop,  # IDEA #1: Track shop type
                        'is_corner_shop': is_corner_shop,  # IDEA #1: Track corner usage
                        'unmet_need': self.unmet_need  # IDEA #1: Track unmet needs
                    }
                    self.shopping_history.append(shopping_event)
                else:
                    self.unsatisfied = True
            else:
                # No reachable provider (physical or delivery) — record unmet need
                self.unsatisfied = True
                self.no_active_provider_today = True
                self.unmet_need = min(
                    self.unmet_need + needed,
                    1.5 * self.weekly_budget)
        else:
            # Did not need to shop OR did not shop successfully
            # Satisfaction based on remaining food supply (not accessibility)
            # Household is satisfied if they have at least 2 days of food remaining
            food_threshold = self.household_size * 2  # 2 days worth of food
            self.satisfied_today = self.food_supply >= food_threshold
            if not self.satisfied_today:
                self.unsatisfied = True
        
        # Consume food daily (scaled by household size)
        self.food_supply = max(0, self.food_supply - self.household_size)
    
    def find_best_provider(self, exclude_corners: bool = False) -> Tuple[Optional['EnhancedFoodProvider'], float, float]:
        """
        Enhanced provider selection using spatial optimization.

        Args:
            exclude_corners: If True, exclude corner stores from choice set (for full shops)

        Returns:
            Tuple of (best_provider, best_distance, best_utility)
        """
        available_providers = self.model.get_available_providers_for_consumer(self)

        # Exclude delivery services — delivery is handled separately via
        # is_delivery_user gate in _find_best_delivery_service()
        available_providers = [(p, d) for p, d in available_providers
                              if not isinstance(p, EnhancedDeliveryService)]

        if exclude_corners:
            available_providers = [(p, d) for p, d in available_providers
                                  if p.provider_type != ProviderType.CORNER_STORE]

        if not available_providers:
            return None, float('inf'), -float('inf')

        best_provider = None
        best_utility = -float('inf')
        best_distance = float('inf')

        for provider, distance in available_providers:
            utility = self.calculate_utility(provider, distance)
            if utility > best_utility:
                best_utility = utility
                best_provider = provider
                best_distance = distance

        return best_provider, best_distance, best_utility

# ========================================================================
# LOGNORMAL DISTRIBUTION HELPERS
# ========================================================================

def generate_lognormal_value(mean: float, sigma: float) -> float:
    """
    Generate a lognormally-distributed value
    
    Args:
        mean: Target mean value
        sigma: Standard deviation in log space (e.g., 0.25 for ±25%)
    
    Returns:
        Random value from lognormal distribution with specified mean
    """
    # Calculate mu for lognormal to achieve target mean
    mu = np.log(mean) - 0.5 * sigma**2
    return np.random.lognormal(mu, sigma)

def add_uniform_noise(value: float, noise_pct: float) -> float:
    """
    Add uniform noise to a value
    
    Args:
        value: Base value
        noise_pct: Noise percentage (e.g., 0.10 for ±10%)
    
    Returns:
        Value with uniform noise added
    """
    noise_range = value * noise_pct
    return value + random.uniform(-noise_range, noise_range)

# ========================================================================
# BACKWARD COMPATIBILITY ALIAS
# ========================================================================
# Allow old code using "EnhancedConsumerAgent" to work with new "EnhancedHouseholdAgent"
EnhancedConsumerAgent = EnhancedHouseholdAgent

class EnhancedFoodProvider(mg.GeoAgent):
    """Enhanced Mesa-Geo food provider with advanced capabilities"""
    
    def __init__(self, model: mesa.Model, geometry: Point,
                 provider_type: ProviderType, capacity: int):
        # Fix: Mesa-geo requires model, geometry, and crs parameters
        super().__init__(model, geometry, crs="EPSG:4326")
        
        self.provider_type = provider_type
        self.capacity = capacity
        self.current_inventory = capacity
        self.customers_served_today = 0
        self.daily_revenue = 0.0
        
        # Get configuration from model
        self.config = getattr(model, 'config', SimulationConfig())
        
        # Enhanced attributes (using configuration)
        self.quality_score = self._calculate_quality_score()
        self.operating_hours = self._get_operating_hours()
        self.service_area_radius = self._calculate_service_area()
        self.customer_satisfaction = 0.8  # Start with neutral satisfaction
        
        # Performance tracking
        self.utilization_history = []
        self.customer_history = []
        self.catchment_area = None
    
    def _calculate_quality_score(self) -> float:
        """
        Calculate quality score based on provider type
        
        Scores reflect REAL differences in product variety/selection:
        - Grocery stores: 50-100× more SKUs than corner stores
        - Corner stores: Limited produce, meat, dairy variety
        - Quality difference must be substantial enough that when multiplied
          by gamma (quality preference), it can overcome distance advantages
        """
        base_scores = {
            ProviderType.GROCERY_STORE: 0.8,      # Full-service grocery (original baseline)
            ProviderType.CORNER_STORE: 0.30,      # Limited selection (Idea #1: quality penalty 0.25-0.35)
            ProviderType.FOOD_HUB: 0.9,           # Fresh, variety
            ProviderType.MOBILE_PANTRY: 0.40,     # Limited pre-packed selection (same as fixed pantries)
            ProviderType.PANTRY: 0.35,            # Pre-selected boxes, limited choice (Long et al. 2022)
            ProviderType.DELIVERY_SERVICE: 0.85   # Grocery-like variety
        }
        # Add small random noise for realism (±5%)
        return base_scores.get(self.provider_type, 0.7) + random.uniform(-0.05, 0.05)
    
    def _get_operating_hours(self) -> Tuple[int, int]:
        """Get operating hours based on provider type using configuration"""
        return self.config.operating_hours.get(self.provider_type.value, (8, 18))
    
    def _calculate_service_area(self) -> float:
        """Calculate service area radius in km using configuration"""
        return self.config.service_areas.get(self.provider_type.value, 5.0)
    
    def serve_customer(self, customer: EnhancedConsumerAgent) -> bool:
        """Serve a customer with enhanced tracking"""
        if self.current_inventory > 0:
            self.current_inventory -= 1
            self.customers_served_today += 1
            
            # Calculate transaction amount based on provider type and customer income (configurable)
            base_amount = {
                ProviderType.GROCERY_STORE: 50.0,
                ProviderType.CORNER_STORE: 25.0,
                ProviderType.FOOD_HUB: 30.0,
                ProviderType.MOBILE_PANTRY: 20.0,
                ProviderType.DELIVERY_SERVICE: 50.0,  # Delivery picks from grocery; same base amount
            }
            
            income_modifier_key = customer.income.value
            income_modifier = self.config.income_modifiers.get(income_modifier_key, 1.0)
            
            transaction_amount = (base_amount.get(self.provider_type, 40.0) * income_modifier)
            self.daily_revenue += transaction_amount
            
            # Record customer interaction
            self.customer_history.append({
                'customer_id': customer.unique_id,
                'customer_income': customer.income.value,
                'transaction_amount': transaction_amount,
                'day': self.model.schedule.steps
            })
            
            return True
        return False
    
    def get_availability_factor(self) -> float:
        """Get availability factor (0-1) based on current inventory"""
        if self.capacity == 0:
            return 0.0
        return self.current_inventory / self.capacity
    
    def can_serve_customer(self) -> bool:
        """Check if provider can serve customers"""
        return self.current_inventory > 0
    
    def step(self):
        """Enhanced provider step with performance tracking"""
        # Calculate daily utilization
        if self.capacity > 0:
            utilization = self.customers_served_today / self.capacity
            self.utilization_history.append(utilization)
        
        # Update customer satisfaction based on demand vs capacity
        demand_ratio = self.customers_served_today / max(self.capacity, 1)
        if demand_ratio > 0.9:  # High demand
            self.customer_satisfaction = max(0.5, self.customer_satisfaction - 0.05)
        elif demand_ratio < 0.3:  # Low demand
            self.customer_satisfaction = min(1.0, self.customer_satisfaction + 0.02)
        
        # Reset daily counters
        self.current_inventory = self.capacity
        self.customers_served_today = 0
        self.daily_revenue = 0.0

class EnhancedGroceryStore(EnhancedFoodProvider):
    """Enhanced grocery store agent"""
    
    def __init__(self, model: mesa.Model, geometry: Point, capacity: int = 600):
        super().__init__(model, geometry, ProviderType.GROCERY_STORE, capacity)
        self.store_type = "supermarket"
        self.accepts_snap = True
        self.parking_spaces = capacity // 10

class EnhancedCornerStore(EnhancedFoodProvider):
    """Enhanced corner store agent"""
    
    def __init__(self, model: mesa.Model, geometry: Point, capacity: int = 60):
        super().__init__(model, geometry, ProviderType.CORNER_STORE, capacity)
        self.store_type = "corner_store"
        self.accepts_snap = True

class EnhancedFoodHub(EnhancedFoodProvider):
    """Enhanced food hub agent with market scheduling"""
    
    def __init__(self, model: mesa.Model, geometry: Point, capacity: int = 300):
        super().__init__(model, geometry, ProviderType.FOOD_HUB, capacity)
        # Use configurable market days
        self.market_days = getattr(model, 'config', SimulationConfig()).food_hub_market_days
        self.is_market_day = False
    
    def update_market_status(self, current_day: int):
        """Update whether it's a market day"""
        self.is_market_day = (current_day % 7) in self.market_days
        if not self.is_market_day:
            self.current_inventory = 0
    
    def can_serve_customer(self) -> bool:
        """Food hub can only serve on market days"""
        return self.is_market_day and self.current_inventory > 0

class EnhancedMobilePantry(EnhancedFoodProvider):
    """Mobile pantry provider with scheduled/rotating/needs-based placement
    
    Supports both weekly and monthly schedules:
    - Weekly: operates every [weekday] (e.g., every Tuesday)
    - Monthly: operates on specific week + weekday (e.g., 3rd Tuesday of each month)
    """
    def __init__(self, model: mesa.Model, geometry: Point, capacity: int = 120,
                 monthly_schedule: tuple = None, location_name: str = None):
        super().__init__(model, geometry, ProviderType.MOBILE_PANTRY, capacity)
        self.schedule = getattr(model, 'config', SimulationConfig()).mobile_pantry_schedule or {}
        self.strategy = getattr(model, 'config', SimulationConfig()).mobile_pantry_strategy
        self.fixed_locations = getattr(model, 'config', SimulationConfig()).fixed_pantry_locations or {}
        self.current_location_name = location_name or None
        self.active_today = False
        
        # Monthly schedule: tuple of (week_of_month, weekday) or list of tuples
        # Example: (3, 1) = 3rd Tuesday, [(2, 1), (5, 1)] = 2nd and 5th Tuesday
        self.monthly_schedule = monthly_schedule
        self.fixed_location = geometry  # Store the fixed location
    
    def _choose_location_for_today(self) -> Point:
        weekday = self.model.current_day % 7
        if self.strategy == 'fixed' and self.fixed_locations:
            # Deterministically assign each pantry to a distinct fixed location
            keys = list(self.fixed_locations.keys())
            idx = int(self.unique_id) % max(1, len(keys))
            name = keys[idx]
            lon, lat = self.fixed_locations[name]
            self.current_location_name = name
            return Point(lon, lat)
        if self.strategy == 'rotating' and self.fixed_locations:
            names = list(self.fixed_locations.keys())
            # Each pantry rotates with a unique offset based on unique_id
            idx = (weekday + int(self.unique_id)) % max(1, len(names))
            name = names[idx]
            lon, lat = self.fixed_locations[name]
            self.current_location_name = name
            return Point(lon, lat)
        if self.strategy == 'needs_based':
            # Find cluster center of unsatisfied consumers
            unsatisfied = [c for c in self.model.consumers if c.unsatisfied or not c.satisfied_today]
            if not unsatisfied:
                return self.model.health_zone_polygon.centroid
            xs = [c.geometry.x for c in unsatisfied]
            ys = [c.geometry.y for c in unsatisfied]
            # Simple centroid of unsatisfied
            cx = sum(xs) / len(xs)
            cy = sum(ys) / len(ys)
            point = Point(cx, cy)
            # Ensure within polygon
            if not self.model.health_zone_polygon.contains(point):
                return self.model.health_zone_polygon.centroid
            self.current_location_name = 'Needs-based center'
            return point
        # Default: random valid point
        return self.model._random_point_in_health_zone()
    
    def update_daily_status(self):
        """Update whether pantry is active today based on schedule"""
        current_day = self.model.current_day

        # Prefer frequency-aware function if set by baseline pantry loader
        if hasattr(self, 'is_active_today_fn') and callable(self.is_active_today_fn):
            self.active_today = self.is_active_today_fn(current_day)
            if self.active_today:
                # Baseline fixed pantries stay at their configured real coordinates
                self.geometry = self.fixed_location
                self.current_inventory = self.capacity
            else:
                self.current_inventory = 0
            return
        else:
            # Original logic for scenario-added mobile pantries
            if self.monthly_schedule is not None:
                self.active_today = self._is_active_monthly()
                if self.active_today:
                    self.geometry = self.fixed_location
            else:
                weekday = current_day % 7
                self.active_today = weekday in self.schedule.keys()

        if self.active_today:
            new_point = self._choose_location_for_today()
            self.geometry = new_point
            self.current_inventory = self.capacity
        else:
            self.current_inventory = 0
    
    def _is_active_monthly(self) -> bool:
        """Check if pantry is active today based on monthly schedule"""
        current_day = self.model.current_day
        weekday = current_day % 7  # 0=Monday, 1=Tuesday, ..., 6=Sunday
        
        # Calculate which week of the month this is
        # Assume 30-day months for simplicity, day_of_month ranges 0-29
        day_of_month = current_day % 30
        week_of_month = (day_of_month // 7) + 1  # 1=1st week, 2=2nd, 3=3rd, 4=4th, 5=5th
        
        # Check if today matches any scheduled distribution
        if isinstance(self.monthly_schedule, tuple):
            # Single schedule: (week, weekday)
            target_week, target_weekday = self.monthly_schedule
            return week_of_month == target_week and weekday == target_weekday
        elif isinstance(self.monthly_schedule, list):
            # Multiple schedules: [(week1, weekday1), (week2, weekday2), ...]
            for target_week, target_weekday in self.monthly_schedule:
                if week_of_month == target_week and weekday == target_weekday:
                    return True
            return False
        return False
    
    def can_serve_customer(self) -> bool:
        return self.active_today and self.current_inventory > 0

class EnhancedDeliveryService(EnhancedFoodProvider):
    """
    Enhanced Delivery Service Agent
    
    Represents online grocery delivery services (e.g., Instacart, Amazon Fresh, Walmart+)
    Does not require physical travel by household - delivers to home.
    
    Key attributes:
    - base_service_fee: Base delivery fee (fixed component)
    - distance_fee_per_km: Fee per kilometer (distance-based component)
    - delivery_area_km: Maximum delivery radius
    - subsidized: Whether delivery is subsidized (e.g., for low-income HH)
    
    Delivery fee formula: base_service_fee + (distance_km × distance_fee_per_km)
    Example: $2.00 + (5 km × $0.75/km) = $5.75 total
    """
    
    def __init__(self, model: mesa.Model, geometry: Point, capacity: int = 1000,
                 base_service_fee: float = 2.00, distance_fee_per_km: float = 0.75,
                 delivery_area_km: float = 15.0):
        super().__init__(model, geometry, ProviderType.DELIVERY_SERVICE, capacity)
        self.base_service_fee = base_service_fee  # Base fee (e.g., $2.00)
        self.distance_fee_per_km = distance_fee_per_km  # Per-km fee (e.g., $0.75/km)
        self.delivery_area_km = delivery_area_km
        self.subsidized = False  # Set to True in subsidy scenario
        self.accepts_snap = True
        self.store_type = "delivery"
        
        # Delivery-specific metrics
        self.total_deliveries = 0
        self.deliveries_by_income = {'low': 0, 'medium': 0, 'high': 0}
    
    def serve_customer(self, consumer: 'EnhancedHouseholdAgent', distance_km: float = 0.0) -> bool:
        """
        Serve a delivery customer
        
        Args:
            consumer: The household ordering delivery
            distance_km: Distance from delivery hub to household (for fee calculation)
        
        Returns:
            True if delivery successful, False otherwise
        """
        if self.current_inventory <= 0:
            return False
        
        self.current_inventory -= 1
        self.customers_served_today += 1
        self.total_deliveries += 1
        
        # Track by income level
        income_level = consumer.income.value if hasattr(consumer.income, 'value') else str(consumer.income)
        if income_level in self.deliveries_by_income:
            self.deliveries_by_income[income_level] += 1
        
        # Calculate distance-based delivery fee
        delivery_fee = self.get_effective_fee_for_household(consumer, distance_km)
        
        # Revenue = basket + delivery fee
        self.daily_revenue += consumer.mean_basket_size + delivery_fee
        
        return True
    
    def calculate_delivery_fee(self, distance_km: float) -> float:
        """
        Calculate total delivery fee based on distance
        
        Formula: base_service_fee + (distance_km × distance_fee_per_km)
        Example: $2.00 + (5 km × $0.75/km) = $5.75
        
        Args:
            distance_km: Distance from delivery hub to household in kilometers
        
        Returns:
            Total delivery fee in dollars
        """
        return self.base_service_fee + (distance_km * self.distance_fee_per_km)
    
    def get_effective_fee_for_household(self, household: 'EnhancedHouseholdAgent', distance_km: float) -> float:
        """
        Calculate effective delivery fee for a household after subsidies
        
        Args:
            household: The household requesting delivery
            distance_km: Distance from delivery hub to household
        
        Returns:
            Effective fee after applying subsidies (based on income level)
        """
        # Calculate base delivery fee (distance-based)
        full_fee = self.calculate_delivery_fee(distance_km)
        
        if self.subsidized:
            # Apply subsidy based on income level
            if household.income == IncomeLevel.LOW:
                return 0.0  # FREE for low-income
            elif household.income == IncomeLevel.MEDIUM:
                return full_fee * 0.5  # 50% off for medium-income
            else:
                return full_fee  # Full price for high-income
        else:
            # No subsidy - everyone pays full distance-based fee
            return full_fee


def _insecurity_by_income(model, income_str):
    agents = [a for a in model.consumers if hasattr(a, 'income') and a.income.value == income_str]
    if not agents:
        return 0.0
    return sum(1 for a in agents if a.unsatisfied) / len(agents)


def _dist_by_vehicle(model, has_car):
    travelers = [
        a for a in model.consumers
        if hasattr(a, 'vehicle_available') and a.vehicle_available == has_car and a.travel_distance > 0
    ]
    if not travelers:
        return 0.0
    return sum(a.travel_distance for a in travelers) / len(travelers)


def _corner_store_share(model):
    total = sum(len(a.shopping_history) for a in model.consumers if hasattr(a, 'shopping_history'))
    if total == 0:
        return 0.0
    corners = sum(
        sum(1 for t in a.shopping_history if t.get('provider_type') == 'corner_store')
        for a in model.consumers if hasattr(a, 'shopping_history')
    )
    return corners / total


def _pantry_share(model):
    total = sum(len(a.shopping_history) for a in model.consumers if hasattr(a, 'shopping_history'))
    if total == 0:
        return 0.0
    pantry = sum(
        sum(1 for t in a.shopping_history if t.get('provider_type') in ['mobile_pantry', 'pantry'])
        for a in model.consumers if hasattr(a, 'shopping_history')
    )
    return pantry / total


def _delivery_share(model):
    total = sum(len(a.shopping_history) for a in model.consumers if hasattr(a, 'shopping_history'))
    if total == 0:
        return 0.0
    deliv = sum(
        sum(1 for t in a.shopping_history if t.get('used_delivery', False))
        for a in model.consumers if hasattr(a, 'shopping_history')
    )
    return deliv / total


def _spend_by_income(model, income_str):
    agents = [
        a for a in model.consumers
        if hasattr(a, 'income') and a.income.value == income_str
        and hasattr(a, 'shopping_history') and len(a.shopping_history) > 0
    ]
    if not agents:
        return 0.0
    return sum(sum(t.get('basket_cost', 0) for t in a.shopping_history) for a in agents) / len(agents)


class EnhancedMesaGeoModel(mesa.Model):
    """
    Enhanced Mesa-Geo model with advanced spatial analytics
    """
    
    def __init__(self, config: SimulationConfig = None):
        super().__init__()
        
        self.config = config or SimulationConfig()
        
        # Mesa model setup
        self.schedule = mesa.time.RandomActivation(self)
        
        # Load spatial data
        self.health_zone_polygon = self._load_health_zone()
        
        # Create Mesa-Geo space
        self.space = mg.GeoSpace(crs="EPSG:4326", warn_crs_conversion=False)
        
        # Enhanced spatial features
        self.road_network = self._load_road_network() if self.config.use_road_network else None
        self.spatial_index = None  # Will be built when agents are added
        
        # Model state
        self.consumers = []
        self.food_providers = []
        self.current_day = 0
        self.metrics_history = []
        
        # Enhanced analytics
        self.spatial_clusters = None
        self.accessibility_surface = None
        
        # Mesa data collector with enhanced metrics
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Satisfaction_Rate": self._calculate_satisfaction_rate,
                "Food_Insecurity_Rate": self._calculate_food_insecurity_rate,
                "Avg_Travel_Distance": self._calculate_avg_travel_distance,
                "Spatial_Equity_Index": self._calculate_spatial_equity_index,
                "Provider_Utilization": self._calculate_provider_utilization,
                "Total_Revenue": self._calculate_total_revenue,
                "Food_Insecurity_Low": lambda m: _insecurity_by_income(m, 'low'),
                "Food_Insecurity_Med": lambda m: _insecurity_by_income(m, 'medium'),
                "Food_Insecurity_High": lambda m: _insecurity_by_income(m, 'high'),
                "Avg_Dist_Car": lambda m: _dist_by_vehicle(m, True),
                "Avg_Dist_NoCar": lambda m: _dist_by_vehicle(m, False),
                "Corner_Share": lambda m: _corner_store_share(m),
                "Pantry_Share": lambda m: _pantry_share(m),
                "Delivery_Share": lambda m: _delivery_share(m),
                "Spend_Low": lambda m: _spend_by_income(m, 'low'),
                "Spend_Med": lambda m: _spend_by_income(m, 'medium'),
                "Spend_High": lambda m: _spend_by_income(m, 'high'),
            },
            agent_reporters={
                "Satisfied": lambda a: getattr(a, 'satisfied_today', False),
                "Travel_Distance": lambda a: getattr(a, 'travel_distance', 0.0),
                "Accessibility_Score": lambda a: getattr(a, 'accessibility_score', 0.0),
                "Income": lambda a: a.income.value if hasattr(a, 'income') else None
            }
        )
    
    def _load_health_zone(self) -> Polygon:
        """Load Health Zone 1 polygon"""
        try:
            gdf = gpd.read_file(self.config.health_zone_shapefile)
            gdf = gdf.to_crs(epsg=4326)
            hz1_geom = gdf[gdf["HealthZ"] == 1].geometry.iloc[0]
            return hz1_geom
        except Exception as e:
            print(f"Warning: Could not load Health Zone polygon: {e}")
            # Fallback bounding box
            bounds = SpatialBounds()
            return Polygon([
                (bounds.min_lon, bounds.min_lat),
                (bounds.max_lon, bounds.min_lat),
                (bounds.max_lon, bounds.max_lat),
                (bounds.min_lon, bounds.max_lat)
            ])
    
    def _load_road_network(self) -> Optional[nx.Graph]:
        """Load road network for enhanced routing"""
        try:
            # Placeholder - implement actual road network loading
            # This would load and process the roads shapefile
            print("📍 Road network loading not implemented yet - using Euclidean distances")
            return None
        except Exception as e:
            print(f"Warning: Could not load road network: {e}")
            return None
    
    def _build_spatial_index(self):
        """Build spatial index for fast provider lookups"""
        if not self.food_providers:
            return
        
        # Create KDTree for fast spatial queries
        provider_coords = [(p.geometry.x, p.geometry.y) for p in self.food_providers]
        self.spatial_index = KDTree(provider_coords)
    
    def _random_point_in_health_zone(self) -> Point:
        """Generate random point within Health Zone 1"""
        bounds = self.health_zone_polygon.bounds
        while True:
            x = random.uniform(bounds[0], bounds[2])
            y = random.uniform(bounds[1], bounds[3])
            point = Point(x, y)
            if self.health_zone_polygon.contains(point):
                return point
    
    def add_household(self, income: IncomeLevel, vehicle_available: bool, 
                     household_size: int = 2, location: Point = None, 
                     **demographics) -> EnhancedHouseholdAgent:
        """
        Add enhanced household agent
        
        Args:
            income: IncomeLevel (LOW/MEDIUM/HIGH)
            vehicle_available: Whether household has vehicle access
            household_size: Number of people in household (default: 2)
            location: Point location (auto-generated if None)
            **demographics: race, snap_eligible, annual_income, census_tract, etc.
        
        Returns:
            EnhancedHouseholdAgent instance
        """
        if location is None:
            location = self._random_point_in_health_zone()
        
        # Mesa 3.0: unique_id is automatically assigned, don't pass it
        household = EnhancedHouseholdAgent(
            model=self,
            geometry=location,
            income=income,
            vehicle_available=vehicle_available,
            household_size=household_size,
            **demographics
        )
        
        self.schedule.add(household)
        self.space.add_agents(household)
        self.consumers.append(household)  # Keep list name for backward compat
        
        return household
    
    # Backward compatibility alias
    def add_consumer(self, income: IncomeLevel, car_ownership: bool = None,
                    vehicle_available: bool = None, household_size: int = 2,
                    location: Point = None, **demographics) -> EnhancedHouseholdAgent:
        """Legacy method - redirects to add_household()"""
        # Handle both old (car_ownership) and new (vehicle_available) parameter names
        vehicle = vehicle_available if vehicle_available is not None else car_ownership
        if vehicle is None:
            vehicle = False
        return self.add_household(income, vehicle, household_size, location, **demographics)
    
    def add_grocery_store(self, location: Point = None, capacity: int = 600) -> EnhancedGroceryStore:
        """Add enhanced grocery store"""
        if location is None:
            location = self.health_zone_polygon.centroid
        
        # Mesa 3.0: unique_id is automatically assigned, don't pass it  
        store = EnhancedGroceryStore(self, location, capacity)
        
        self.schedule.add(store)
        self.space.add_agents(store)
        self.food_providers.append(store)
        
        # Rebuild spatial index
        self._build_spatial_index()
        
        return store
    
    def add_corner_store(self, location: Point = None, capacity: int = 60) -> EnhancedCornerStore:
        """Add enhanced corner store"""
        if location is None:
            location = self._random_point_in_health_zone()
        
        # Mesa 3.0: unique_id is automatically assigned, don't pass it  
        store = EnhancedCornerStore(self, location, capacity)
        
        self.schedule.add(store)
        self.space.add_agents(store)
        self.food_providers.append(store)
        
        # Rebuild spatial index
        self._build_spatial_index()
        
        return store
    
    def add_food_hub(self, location: Point = None, capacity: int = 300) -> EnhancedFoodHub:
        """Add enhanced food hub"""
        if location is None:
            location = self._random_point_in_health_zone()
        
        # Mesa 3.0: unique_id is automatically assigned, don't pass it  
        hub = EnhancedFoodHub(self, location, capacity)
        
        self.schedule.add(hub)
        self.space.add_agents(hub)
        self.food_providers.append(hub)
        
        # Rebuild spatial index
        self._build_spatial_index()
        
        return hub

    def add_mobile_pantry(self, location: Point = None, capacity: int = 120) -> 'EnhancedMobilePantry':
        """Add mobile pantry provider"""
        if location is None:
            location = self._random_point_in_health_zone()
        pantry = EnhancedMobilePantry(self, location, capacity)
        self.schedule.add(pantry)
        self.space.add_agents(pantry)
        self.food_providers.append(pantry)
        self._build_spatial_index()
        return pantry
    
    def calculate_distance(self, point1: Point, point2: Point) -> float:
        """Calculate distance between two points (enhanced with road network option)"""
        if self.road_network:
            # Use road network distance if available
            # This would implement actual routing
            pass
        
        # Use geodesic distance (more accurate than Euclidean)
        coord1 = (point1.y, point1.x)  # lat, lon
        coord2 = (point2.y, point2.x)
        return geodesic(coord1, coord2).kilometers
    
    def get_providers_within_distance(self, consumer: EnhancedConsumerAgent, 
                                    max_distance: float) -> List[Tuple[EnhancedFoodProvider, float]]:
        """Get PHYSICAL providers within distance (excludes delivery services).
        Delivery services are evaluated separately via _find_best_delivery_service()."""
        if not self.spatial_index or not self.food_providers:
            return []
        
        consumer_coord = [consumer.geometry.x, consumer.geometry.y]
        
        # Convert max_distance from km to approximate degrees
        max_distance_degrees = max_distance / 111.0  # 1 degree ≈ 111 km
        
        nearby_indices = self.spatial_index.query_ball_point(consumer_coord, max_distance_degrees)
        
        nearby_providers = []
        for idx in nearby_indices:
            provider = self.food_providers[idx]
            if isinstance(provider, EnhancedDeliveryService):
                continue
            distance = self.calculate_distance(consumer.geometry, provider.geometry)
            if distance <= max_distance:
                nearby_providers.append((provider, distance))
        
        return sorted(nearby_providers, key=lambda x: x[1])  # Sort by distance
    
    def get_available_providers_for_consumer(self, consumer: EnhancedConsumerAgent) -> List[Tuple[EnhancedFoodProvider, float]]:
        """Get available providers for a consumer"""
        nearby_providers = self.get_providers_within_distance(consumer, consumer.max_travel_distance)

        # Draw once per trip whether this agent considers ANY pantry today
        # This prevents 19 independent draws inflating pantry access probability
        # With 19 pantries and 12% propensity: P(>=1 pantry) = 1-0.88^19 = 91%
        # One draw per trip gives correct 12% population-level pantry consideration (Bertmann et al. 2021)
        agent_considers_pantry_today = random.random() < consumer.pantry_propensity

        # Filter for available providers
        available = []
        for provider, distance in nearby_providers:
            if provider.can_serve_customer():
                is_pantry = provider.provider_type in [
                    ProviderType.MOBILE_PANTRY, ProviderType.PANTRY
                ]
                if is_pantry and not agent_considers_pantry_today:
                    continue
                available.append((provider, distance))
        
        return available
    
    def perform_spatial_clustering(self):
        """Perform spatial clustering analysis on consumers"""
        if len(self.consumers) < self.config.spatial_cluster_min_samples:
            return
        
        # Get consumer coordinates
        coords = np.array([[c.geometry.x, c.geometry.y] for c in self.consumers])
        
        # Perform DBSCAN clustering
        clustering = DBSCAN(eps=self.config.spatial_cluster_eps, 
                          min_samples=self.config.spatial_cluster_min_samples)
        cluster_labels = clustering.fit_predict(coords)
        
        # Assign cluster IDs to consumers
        for i, consumer in enumerate(self.consumers):
            consumer.spatial_cluster_id = cluster_labels[i]
        
        self.spatial_clusters = cluster_labels
    
    def step(self):
        """Enhanced model step with spatial analytics"""
        self.current_day += 1
        
        # Update food hub market status
        for provider in self.food_providers:
            if isinstance(provider, EnhancedFoodHub):
                provider.update_market_status(self.current_day)
            if isinstance(provider, EnhancedMobilePantry):
                provider.update_daily_status()
        
        # Standard Mesa step
        self.schedule.step()
        
        # Collect data
        self.datacollector.collect(self)
        
        # Perform spatial analysis periodically
        if self.config.enable_spatial_analytics and self.current_day % 7 == 0:
            self.perform_spatial_clustering()
        
        # Calculate and store daily metrics
        daily_metrics = {
            'day': self.current_day,
            'satisfaction_rate': self._calculate_satisfaction_rate(),
            'food_insecurity_rate': self._calculate_food_insecurity_rate(),
            'avg_travel_distance': self._calculate_avg_travel_distance(),
            'spatial_equity_index': self._calculate_spatial_equity_index(),
            'total_revenue': self._calculate_total_revenue()
        }
        self.metrics_history.append(daily_metrics)
    
    # Enhanced metric calculations
    def _calculate_satisfaction_rate(self) -> float:
        """Calculate consumer satisfaction rate"""
        if not self.consumers:
            return 0.0
        satisfied = sum(1 for c in self.consumers if c.satisfied_today)
        return satisfied / len(self.consumers)
    
    def _calculate_food_insecurity_rate(self) -> float:
        """Calculate food insecurity rate (unsatisfied consumers)"""
        if not self.consumers:
            return 0.0
        unsatisfied = sum(1 for c in self.consumers if c.unsatisfied)
        return unsatisfied / len(self.consumers)
    
    def _calculate_avg_travel_distance(self) -> float:
        """Calculate average travel distance"""
        if not self.consumers:
            return 0.0
        
        travelers = [c for c in self.consumers if c.travel_distance > 0]
        if not travelers:
            return 0.0
        
        return sum(c.travel_distance for c in travelers) / len(travelers)
    
    def _calculate_spatial_equity_index(self) -> float:
        """Calculate spatial equity index (lower = more equitable)"""
        if not self.consumers:
            return 0.0
        
        accessibility_scores = [c.accessibility_score for c in self.consumers]
        if not accessibility_scores:
            return 0.0
        
        # Calculate coefficient of variation as equity measure
        mean_score = np.mean(accessibility_scores)
        if mean_score == 0:
            return 0.0
        
        std_score = np.std(accessibility_scores)
        return std_score / mean_score  # Coefficient of variation
    
    def _calculate_provider_utilization(self) -> float:
        """Calculate average provider utilization"""
        if not self.food_providers:
            return 0.0
        
        utilizations = []
        for provider in self.food_providers:
            if provider.capacity > 0:
                utilization = provider.customers_served_today / provider.capacity
                utilizations.append(utilization)
        
        return np.mean(utilizations) if utilizations else 0.0
    
    def _calculate_total_revenue(self) -> float:
        """Calculate total daily revenue"""
        return sum(p.daily_revenue for p in self.food_providers)
    
    def get_simulation_summary(self) -> Dict[str, Any]:
        """Get comprehensive simulation summary with spatial analytics"""
        if not self.metrics_history:
            return {}
        
        # Overall metrics
        avg_satisfaction = np.mean([m['satisfaction_rate'] for m in self.metrics_history])
        avg_food_insecurity = np.mean([m['food_insecurity_rate'] for m in self.metrics_history])
        avg_travel_distance = np.mean([m['avg_travel_distance'] for m in self.metrics_history])
        avg_spatial_equity = np.mean([m['spatial_equity_index'] for m in self.metrics_history])
        
        # Demographic analysis
        demographic_stats = self._analyze_demographic_outcomes()
        
        # Spatial analysis
        spatial_stats = self._analyze_spatial_patterns()
        
        return {
            'simulation_days': self.current_day,
            'num_consumers': len(self.consumers),
            'num_providers': len(self.food_providers),
            'overall_metrics': {
                'avg_satisfaction_rate': avg_satisfaction,
                'avg_food_insecurity_rate': avg_food_insecurity,
                'avg_travel_distance': avg_travel_distance,
                'spatial_equity_index': avg_spatial_equity
            },
            'demographic_analysis': demographic_stats,
            'spatial_analysis': spatial_stats,
            'provider_performance': self._analyze_provider_performance()
        }
    
    def _analyze_demographic_outcomes(self) -> Dict[str, Any]:
        """Analyze outcomes by demographic groups"""
        demographic_stats = {}
        
        # Group by income
        for income_level in IncomeLevel:
            income_consumers = [c for c in self.consumers if c.income == income_level]
            if income_consumers:
                avg_satisfaction = np.mean([c.satisfied_today for c in income_consumers])
                avg_accessibility = np.mean([c.accessibility_score for c in income_consumers])
                avg_travel = np.mean([c.travel_distance for c in income_consumers if c.travel_distance > 0])
                
                demographic_stats[f'income_{income_level.value}'] = {
                    'count': len(income_consumers),
                    'satisfaction_rate': avg_satisfaction,
                    'avg_accessibility_score': avg_accessibility,
                    'avg_travel_distance': avg_travel or 0.0
                }
        
        # Group by vehicle availability (car ownership)
        car_owners = [c for c in self.consumers if c.vehicle_available]
        non_car_owners = [c for c in self.consumers if not c.vehicle_available]
        
        demographic_stats['vehicle_availability'] = {
            'with_car': {
                'count': len(car_owners),
                'satisfaction_rate': np.mean([c.satisfied_today for c in car_owners]) if car_owners else 0,
                'avg_travel_distance': np.mean([c.travel_distance for c in car_owners if c.travel_distance > 0]) or 0
            },
            'without_car': {
                'count': len(non_car_owners),
                'satisfaction_rate': np.mean([c.satisfied_today for c in non_car_owners]) if non_car_owners else 0,
                'avg_travel_distance': np.mean([c.travel_distance for c in non_car_owners if c.travel_distance > 0]) or 0
            }
        }
        
        return demographic_stats
    
    def _analyze_spatial_patterns(self) -> Dict[str, Any]:
        """Analyze spatial patterns and clustering"""
        spatial_stats = {}
        
        if self.spatial_clusters is not None:
            unique_clusters = set(self.spatial_clusters)
            cluster_stats = {}
            
            for cluster_id in unique_clusters:
                if cluster_id == -1:  # Noise points in DBSCAN
                    continue
                
                cluster_consumers = [c for c in self.consumers if c.spatial_cluster_id == cluster_id]
                if cluster_consumers:
                    cluster_stats[f'cluster_{cluster_id}'] = {
                        'size': len(cluster_consumers),
                        'avg_satisfaction': np.mean([c.satisfied_today for c in cluster_consumers]),
                        'avg_accessibility': np.mean([c.accessibility_score for c in cluster_consumers])
                    }
            
            spatial_stats['cluster_analysis'] = cluster_stats
        
        # Distance to nearest provider analysis
        provider_distances = []
        for consumer in self.consumers:
            if self.food_providers:
                distances = [self.calculate_distance(consumer.geometry, p.geometry) for p in self.food_providers]
                provider_distances.append(min(distances))
        
        if provider_distances:
            spatial_stats['provider_accessibility'] = {
                'avg_distance_to_nearest': np.mean(provider_distances),
                'max_distance_to_nearest': np.max(provider_distances),
                'consumers_within_1km': sum(1 for d in provider_distances if d <= 1.0) / len(provider_distances)
            }
        
        return spatial_stats
    
    def _analyze_provider_performance(self) -> Dict[str, Any]:
        """Analyze provider performance metrics"""
        performance_stats = {}
        
        for provider_type in ProviderType:
            type_providers = [p for p in self.food_providers if p.provider_type == provider_type]
            
            if type_providers:
                total_served = sum(len(p.customer_history) for p in type_providers)
                avg_utilization = np.mean([len(p.utilization_history) and np.mean(p.utilization_history) or 0 
                                         for p in type_providers])
                avg_satisfaction = np.mean([p.customer_satisfaction for p in type_providers])
                
                performance_stats[provider_type.value] = {
                    'count': len(type_providers),
                    'total_customers_served': total_served,
                    'avg_utilization': avg_utilization,
                    'avg_customer_satisfaction': avg_satisfaction
                }
        
        return performance_stats

# Example usage
if __name__ == "__main__":
    print("🗺️  Enhanced Mesa-Geo Food Access Simulation")
    print("=" * 50)
    print("✅ Using Mesa + mesa_geo for ABM")
    print("✅ Enhanced spatial analytics")
    print("✅ Better performance optimization")
    print("✅ Advanced geospatial features")
    print()
    
    # Create enhanced model
    config = SimulationConfig()
    model = EnhancedMesaGeoModel(config)
    
    print("👥 Adding enhanced consumer agents...")
    for i in range(200):
        income = random.choice(list(IncomeLevel))
        car_ownership = random.random() < 0.7
        model.add_consumer(income, car_ownership)
    
    print("🏪 Adding enhanced food provider agents...")
    # Add grocery store
    model.add_grocery_store(capacity=600)
    
    # Add corner stores
    for i in range(3):
        model.add_corner_store(capacity=60)
    
    # Add food hub
    model.add_food_hub(capacity=300)
    
    print(f"   {len(model.consumers)} enhanced consumers added")
    print(f"   {len(model.food_providers)} enhanced providers added")
    
    print("\n🚀 Running enhanced Mesa-Geo simulation...")
    for day in range(14):
        model.step()
        metrics = model.metrics_history[-1] if model.metrics_history else {}
        satisfaction = metrics.get('satisfaction_rate', 0)
        equity = metrics.get('spatial_equity_index', 0)
        print(f"   Day {day + 1}: Satisfaction {satisfaction:.2%}, Spatial Equity {equity:.3f}")
    
    print("\n📊 Enhanced simulation summary:")
    summary = model.get_simulation_summary()
    
    overall = summary.get('overall_metrics', {})
    print(f"   Average Satisfaction Rate: {overall.get('avg_satisfaction_rate', 0):.2%}")
    print(f"   Average Food Insecurity Rate: {overall.get('avg_food_insecurity_rate', 0):.2%}")
    print(f"   Average Travel Distance: {overall.get('avg_travel_distance', 0):.2f} km")
    print(f"   Spatial Equity Index: {overall.get('spatial_equity_index', 0):.3f}")
    
    # Demographic analysis
    demographic = summary.get('demographic_analysis', {})
    print(f"\n📈 Demographic Analysis:")
    for income_key, stats in demographic.items():
        if income_key.startswith('income_'):
            income_level = income_key.replace('income_', '')
            print(f"   {income_level.title()} Income: {stats['satisfaction_rate']:.2%} satisfaction")
    
    print("\n✅ Enhanced Mesa-Geo simulation complete!")
    print("   🎯 Proper Mesa + mesa_geo integration")
    print("   📊 Advanced spatial analytics")
    print("   🚀 Optimized performance")
    print("   🗺️ Enhanced geospatial capabilities") 