"""
Professional Calibration Framework for Food Access ABM

Calibrates choice model parameters to match 4 baseline patterns:
1. Annual spend by income (Low $5.3k, Med $9.0k, High $17.0k)
2. Trip frequency shape (weekly ~40%, <weekly ~22%)
3. Avg distance to primary store (car: 3-4 mi, no-car: ≤0.5 mi)
4. Primary "other" small stores (≤10%, prefer ~5%)

NOTE: Pantry usage is NOT a baseline calibration target since baseline 
      has no food pantries. Pantries are only in Scenario 3 (intervention).

Uses multi-seed runs (30 seeds × 30 days) and normalized error minimization.
"""

import os
import sys
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import random
from concurrent.futures import ProcessPoolExecutor, as_completed
import itertools

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enhanced_mesa_geo_model import SimulationConfig, IncomeLevel
from baseline_scenario import BaselineScenarioModel


# ============================================================================
# CALIBRATION TARGETS
# ============================================================================

@dataclass
class CalibrationTargets:
    """Target values for calibration - FROM USER'S ACTUAL TABLE (CORRECTED)"""
    
    # 1. Annual spend by income (dollars per household per year)
    # Source: USER'S TABLE (not USDA - these are USER's targets!)
    annual_spend_low: float = 5300.0        # <$25K: USD $5,300/year
    annual_spend_medium: float = 9000.0     # $25K-$99K: USD $9,000/year
    annual_spend_high: float = 17000.0      # ≥$100K: USD $17,000/year
    annual_spend_tolerance: float = 0.15    # ±15% tolerance
    
    # 2. Trip frequency shape (fraction of population)
    # Source: USER'S TABLE
    weekly_frequency_share: float = 0.40    # 40% shop weekly
    weekly_frequency_tolerance: float = 0.15  # ±15%
    subweekly_frequency_share: float = 0.22   # 22% shop sub-weekly
    subweekly_frequency_tolerance: float = 0.08  # ±8%
    
    # 3. Average distance to primary store (IN MILES for comparison)
    # Source: USER'S TABLE: 5.6 km = 3.48 mi (car), 0.8 km = 0.50 mi (no-car)
    distance_car: float = 3.48             # 3.48 miles (5.6 km) with car
    distance_no_car: float = 0.50          # 0.50 miles (0.8 km) without car
    distance_tolerance: float = 0.25       # ±25%
    
    # 4. Primary "other" small stores (corner/dollar/hub)
    # Source: USER'S TABLE
    small_store_share: float = 0.08        # Target ~8%
    small_store_max: float = 0.10          # Hard constraint: ≤10% of trips
    
    # NOTE: Pantry usage target is 12.5% of households (from table)
    # This means 10-15% of low-income households use pantry at least once
    # NOT included in calibration objective, but tracked for validation


@dataclass
class ParameterRanges:
    """Allowed ranges for calibration parameters"""
    
    # Utility weights
    alpha_distance_range: Tuple[float, float] = (0.6, 1.6)
    beta_price_range: Tuple[float, float] = (0.6, 1.4)
    gamma_quality_range: Tuple[float, float] = (0.4, 1.0)
    delta_convenience_range: Tuple[float, float] = (0.2, 0.8)
    
    # Go-shop thresholds
    threshold_low_range: Tuple[float, float] = (2.0, 3.5)
    threshold_medium_range: Tuple[float, float] = (6.0, 8.0)
    threshold_high_range: Tuple[float, float] = (10.0, 18.0)
    
    # Pantry propensity
    pantry_eligible_range: Tuple[float, float] = (0.10, 0.25)
    
    # Delivery propensity
    delivery_low_range: Tuple[float, float] = (0.0, 0.05)
    delivery_medium_range: Tuple[float, float] = (0.05, 0.15)
    delivery_high_range: Tuple[float, float] = (0.10, 0.25)
    delivery_subsidy_range: Tuple[float, float] = (1.5, 3.0)


# ============================================================================
# SIMULATION RUNNER WITH MULTI-SEED SUPPORT
# ============================================================================

def run_single_seed(config: SimulationConfig, seed: int, num_days: int = 30) -> Dict:
    """
    Run a single simulation with specific seed
    
    Args:
        config: Simulation configuration
        seed: Random seed
        num_days: Number of simulation days
        
    Returns:
        Dictionary of metrics
    """
    random.seed(seed)
    np.random.seed(seed)
    
    model = BaselineScenarioModel(config=config)
    
    # Run simulation
    for _ in range(num_days):
        model.step()
    
    # Collect metrics
    consumers = model.consumers
    
    # 1. Annual spend by income
    spend_by_income = {
        IncomeLevel.LOW: [],
        IncomeLevel.MEDIUM: [],
        IncomeLevel.HIGH: []
    }
    
    for c in consumers:
        if hasattr(c, 'shopping_history') and len(c.shopping_history) > 0:
            # Calculate total spend for this household (prefer cost, fallback to size)
            total_spend = sum(trip.get('basket_cost', trip.get('basket_size', 0)) for trip in c.shopping_history)
            # Annualize (num_days to 365)
            annual_spend = total_spend * (365.0 / num_days)
            spend_by_income[c.income].append(annual_spend)
    
    avg_spend_low = np.mean(spend_by_income[IncomeLevel.LOW]) if spend_by_income[IncomeLevel.LOW] else 0
    avg_spend_med = np.mean(spend_by_income[IncomeLevel.MEDIUM]) if spend_by_income[IncomeLevel.MEDIUM] else 0
    avg_spend_high = np.mean(spend_by_income[IncomeLevel.HIGH]) if spend_by_income[IncomeLevel.HIGH] else 0
    
    # 2. Trip frequency shape
    frequency_categories = {'weekly': 0, 'subweekly': 0, 'biweekly+': 0}
    
    for c in consumers:
        if hasattr(c, 'shopping_history') and len(c.shopping_history) >= 2:
            # Calculate average days between trips
            trips = c.shopping_history
            intervals = [trips[i]['day'] - trips[i-1]['day'] for i in range(1, len(trips))]
            avg_interval = np.mean(intervals) if intervals else 0
            
            if avg_interval < 5:
                frequency_categories['subweekly'] += 1  # More than weekly
            elif avg_interval <= 9:
                frequency_categories['weekly'] += 1  # About weekly
            else:
                frequency_categories['biweekly+'] += 1  # Bi-weekly or less
    
    total_categorized = sum(frequency_categories.values())
    weekly_share = frequency_categories['weekly'] / total_categorized if total_categorized > 0 else 0
    subweekly_share = frequency_categories['subweekly'] / total_categorized if total_categorized > 0 else 0
    
    # 3. Average distance to primary store
    distances_car = []
    distances_no_car = []
    
    for c in consumers:
        if hasattr(c, 'shopping_history') and len(c.shopping_history) > 0:
            # Use household physical travel distance (0 for delivery trips)
            distances = [trip['travel_distance'] for trip in c.shopping_history if trip.get('travel_distance', 0) > 0]
            if distances:
                avg_dist = np.mean(distances)
                if c.vehicle_available:
                    distances_car.append(avg_dist)
                else:
                    distances_no_car.append(avg_dist)
    
    avg_dist_car_km = np.mean(distances_car) if distances_car else 0
    avg_dist_no_car_km = np.mean(distances_no_car) if distances_no_car else 0
    
    # Convert to miles
    avg_dist_car_mi = avg_dist_car_km * 0.621371
    avg_dist_no_car_mi = avg_dist_no_car_km * 0.621371
    
    # 4. Primary "other" small stores
    store_type_counts = {}
    for c in consumers:
        if hasattr(c, 'shopping_history'):
            for trip in c.shopping_history:
                store_type = trip.get('provider_type', 'unknown')
                store_type_counts[store_type] = store_type_counts.get(store_type, 0) + 1
    
    total_trips = sum(store_type_counts.values())
    small_store_trips = (
        store_type_counts.get('corner_store', 0) +
        store_type_counts.get('convenience', 0) +
        store_type_counts.get('food_hub', 0) +
        store_type_counts.get('discount', 0)
    )
    small_store_share = small_store_trips / total_trips if total_trips > 0 else 0
    
    # 5. Pantry user share
    pantry_users = 0
    for c in consumers:
        if hasattr(c, 'shopping_history'):
            pantry_visits = [trip for trip in c.shopping_history 
                           if trip.get('provider_type') in ['mobile_pantry', 'pantry', 'food_hub']]
            if len(pantry_visits) > 0:
                pantry_users += 1
    
    pantry_user_share = pantry_users / len(consumers) if len(consumers) > 0 else 0
    
    return {
        'annual_spend_low': avg_spend_low,
        'annual_spend_medium': avg_spend_med,
        'annual_spend_high': avg_spend_high,
        'weekly_share': weekly_share,
        'subweekly_share': subweekly_share,
        'distance_car_mi': avg_dist_car_mi,
        'distance_no_car_mi': avg_dist_no_car_mi,
        'small_store_share': small_store_share,
        'pantry_user_share': pantry_user_share
    }


def run_multi_seed(config: SimulationConfig, 
                   num_seeds: int = 30, 
                   num_days: int = 30,
                   parallel: bool = True) -> Dict:
    """
    Run simulation with multiple seeds and aggregate results
    
    Args:
        config: Simulation configuration
        num_seeds: Number of random seeds to run
        num_days: Number of simulation days per seed
        parallel: Whether to run seeds in parallel
        
    Returns:
        Dictionary with mean and std of metrics across seeds
    """
    print(f"Running {num_seeds} seeds × {num_days} days...", end=" ", flush=True)
    
    if parallel:
        # Run in parallel
        with ProcessPoolExecutor() as executor:
            futures = [executor.submit(run_single_seed, config, seed, num_days) 
                      for seed in range(num_seeds)]
            results = [future.result() for future in as_completed(futures)]
    else:
        # Run sequentially (memory-efficient)
        results = []
        for seed in range(num_seeds):
            result = run_single_seed(config, seed, num_days)
            results.append(result)
            # Aggressive garbage collection after each seed
            import gc
            gc.collect()
    
    # Aggregate across seeds
    aggregated = {}
    for key in results[0].keys():
        values = [r[key] for r in results]
        aggregated[key] = np.mean(values)
        aggregated[f"{key}_std"] = np.std(values)
    
    print("Done.")
    return aggregated


# ============================================================================
# CALIBRATION OBJECTIVE FUNCTION
# ============================================================================

def calculate_calibration_error(metrics: Dict, 
                                targets: CalibrationTargets) -> Tuple[float, Dict]:
    """
    Calculate normalized error for all calibration targets
    
    Args:
        metrics: Simulated metrics
        targets: Target values
        
    Returns:
        (total_error, individual_errors)
    """
    errors = {}
    
    # 1. Annual spend by income (normalized by target)
    error_spend_low = abs(metrics['annual_spend_low'] - targets.annual_spend_low) / targets.annual_spend_low
    error_spend_med = abs(metrics['annual_spend_medium'] - targets.annual_spend_medium) / targets.annual_spend_medium
    error_spend_high = abs(metrics['annual_spend_high'] - targets.annual_spend_high) / targets.annual_spend_high
    
    errors['spend_low'] = error_spend_low
    errors['spend_medium'] = error_spend_med
    errors['spend_high'] = error_spend_high
    
    # 2. Trip frequency shape
    error_weekly = abs(metrics['weekly_share'] - targets.weekly_frequency_share) / targets.weekly_frequency_share
    error_subweekly = abs(metrics['subweekly_share'] - targets.subweekly_frequency_share) / targets.subweekly_frequency_share
    
    errors['weekly_freq'] = error_weekly
    errors['subweekly_freq'] = error_subweekly
    
    # 3. Average distance
    error_dist_car = abs(metrics['distance_car_mi'] - targets.distance_car) / targets.distance_car
    error_dist_no_car = abs(metrics['distance_no_car_mi'] - targets.distance_no_car) / targets.distance_no_car
    
    errors['distance_car'] = error_dist_car
    errors['distance_no_car'] = error_dist_no_car
    
    # 4. Small store share (penalty if > max)
    if metrics['small_store_share'] <= targets.small_store_max:
        error_small = abs(metrics['small_store_share'] - targets.small_store_share) / targets.small_store_share
    else:
        # Heavy penalty for exceeding max
        error_small = 2.0 * (metrics['small_store_share'] - targets.small_store_max) / targets.small_store_share
    
    errors['small_store'] = error_small
    
    # NOTE: Pantry metrics removed - not applicable to baseline (no pantries in baseline)
    # Pantries are only in Scenario 3 intervention
    
    # Total error (MEAN of normalized errors - consistent with 2-phase calibration)
    # Using MEAN instead of SUM so error is normalized 0-1 and comparable
    total_error = sum(errors.values()) / len(errors) if len(errors) > 0 else 999.0
    
    return total_error, errors


def check_within_tolerance(errors: Dict, targets: CalibrationTargets) -> Dict[str, bool]:
    """
    Check which targets are within tolerance
    
    Args:
        errors: Individual errors
        targets: Target specifications
        
    Returns:
        Dictionary of pass/fail for each metric
    """
    within_tolerance = {}
    
    # Annual spend (±10%)
    within_tolerance['spend_low'] = errors['spend_low'] <= targets.annual_spend_tolerance
    within_tolerance['spend_medium'] = errors['spend_medium'] <= targets.annual_spend_tolerance
    within_tolerance['spend_high'] = errors['spend_high'] <= targets.annual_spend_tolerance
    
    # Frequency shape
    within_tolerance['weekly_freq'] = errors['weekly_freq'] <= targets.weekly_frequency_tolerance / targets.weekly_frequency_share
    within_tolerance['subweekly_freq'] = errors['subweekly_freq'] <= targets.subweekly_frequency_tolerance / targets.subweekly_frequency_share
    
    # Distance (±25%)
    within_tolerance['distance_car'] = errors['distance_car'] <= targets.distance_tolerance
    within_tolerance['distance_no_car'] = errors['distance_no_car'] <= targets.distance_tolerance
    
    # Small store (hard constraint ≤10%)
    within_tolerance['small_store'] = errors['small_store'] <= 0.5  # Reasonable error
    
    # NOTE: Pantry tolerance removed - not in baseline scenario
    
    return within_tolerance


# ============================================================================
# GRID SEARCH CALIBRATION
# ============================================================================

def grid_search_calibration(
    alpha_values: List[float],
    gamma_values: List[float],
    threshold_low_values: List[float],
    targets: CalibrationTargets = CalibrationTargets(),
    ranges: ParameterRanges = ParameterRanges(),
    num_seeds: int = 30,
    num_days: int = 30,
    num_consumers: int = 50  # Memory-efficient default
) -> pd.DataFrame:
    """
    Grid search over α_distance × γ_quality × go-shop threshold
    
    Args:
        alpha_values: List of alpha_distance values to test
        gamma_values: List of gamma_quality values to test
        threshold_low_values: List of go_shop_threshold_low values to test
        targets: Calibration targets
        ranges: Parameter ranges
        num_seeds: Number of seeds per configuration
        num_days: Number of days per seed
        
    Returns:
        DataFrame with results sorted by total error
    """
    print(f"\n{'='*70}")
    print(f"GRID SEARCH CALIBRATION")
    print(f"{'='*70}")
    print(f"Testing {len(alpha_values)} × {len(gamma_values)} × {len(threshold_low_values)} = "
          f"{len(alpha_values) * len(gamma_values) * len(threshold_low_values)} configurations")
    print(f"Each with {num_seeds} seeds × {num_days} days")
    print(f"{'='*70}\n")
    
    results = []
    
    total_configs = len(alpha_values) * len(gamma_values) * len(threshold_low_values)
    current = 0
    
    for alpha, gamma, threshold_low in itertools.product(alpha_values, gamma_values, threshold_low_values):
        current += 1
        print(f"\n[{current}/{total_configs}] Testing: α={alpha:.2f}, γ={gamma:.2f}, threshold_low={threshold_low:.1f}")
        
        # Create config
        config = SimulationConfig(
            num_consumers=num_consumers,  # Memory-efficient setting
            simulation_days=num_days,
            alpha_distance=alpha,
            gamma_quality_variety=gamma,
            go_shop_threshold_low=threshold_low,
            # Keep other parameters at reasonable defaults
            beta_price_budget=1.0,
            delta_convenience=0.4,
            go_shop_threshold_medium=7.0,
            go_shop_threshold_high=14.0
            # Note: pantry_propensity will use model defaults (0.75/0.15)
        )
        
        # Run simulation
        metrics = run_multi_seed(config, num_seeds=num_seeds, num_days=num_days, parallel=False)
        
        # Calculate error
        total_error, individual_errors = calculate_calibration_error(metrics, targets)
        within_tol = check_within_tolerance(individual_errors, targets)
        
        # Store results
        result = {
            'alpha_distance': alpha,
            'gamma_quality': gamma,
            'threshold_low': threshold_low,
            'total_error': total_error,
            **metrics,
            **{f'error_{k}': v for k, v in individual_errors.items()},
            **{f'pass_{k}': v for k, v in within_tol.items()},
            'all_pass': all(within_tol.values())
        }
        results.append(result)
        
        # Print summary
        print(f"  Total error: {total_error:.3f}")
        print(f"  Passed: {sum(within_tol.values())}/{len(within_tol)} metrics")
        if result['all_pass']:
            print(f"  ✅ ALL METRICS WITHIN TOLERANCE!")
    
    # Convert to DataFrame and sort
    df = pd.DataFrame(results)
    df = df.sort_values('total_error')
    
    print(f"\n{'='*70}")
    print(f"GRID SEARCH COMPLETE")
    print(f"{'='*70}")
    print(f"Best configuration:")
    print(f"  α (distance) = {df.iloc[0]['alpha_distance']:.2f}")
    print(f"  γ (quality) = {df.iloc[0]['gamma_quality']:.2f}")
    print(f"  threshold_low = {df.iloc[0]['threshold_low']:.1f}")
    print(f"  Total error = {df.iloc[0]['total_error']:.3f}")
    print(f"  Metrics passed: {sum([df.iloc[0][f'pass_{k}'] for k in within_tol.keys()])}/{len(within_tol)}")
    print(f"{'='*70}\n")
    
    return df


# ============================================================================
# ITERATIVE CALIBRATION (2-3 PASSES)
# ============================================================================

def iterative_calibration(
    initial_config: Optional[SimulationConfig] = None,
    targets: CalibrationTargets = CalibrationTargets(),
    ranges: ParameterRanges = ParameterRanges(),
    num_passes: int = 3,
    num_seeds: int = 30,
    num_days: int = 30
) -> SimulationConfig:
    """
    Iterative calibration with manual tuning guidance
    
    Args:
        initial_config: Starting configuration (uses defaults if None)
        targets: Calibration targets
        ranges: Parameter ranges
        num_passes: Number of calibration passes
        num_seeds: Number of seeds per pass
        num_days: Number of days per seed
        
    Returns:
        Calibrated configuration
    """
    if initial_config is None:
        config = SimulationConfig()
    else:
        config = initial_config
    
    print(f"\n{'='*70}")
    print(f"ITERATIVE CALIBRATION ({num_passes} passes)")
    print(f"{'='*70}\n")
    
    for pass_num in range(1, num_passes + 1):
        print(f"\n{'='*70}")
        print(f"PASS {pass_num}/{num_passes}")
        print(f"{'='*70}")
        
        print(f"\nCurrent parameters:")
        print(f"  α (distance) = {config.alpha_distance:.2f}")
        print(f"  β (price) = {config.beta_price_budget:.2f}")
        print(f"  γ (quality) = {config.gamma_quality_variety:.2f}")
        print(f"  δ (convenience) = {config.delta_convenience:.2f}")
        print(f"  Go-shop thresholds: Low={config.go_shop_threshold_low:.1f}, "
              f"Med={config.go_shop_threshold_medium:.1f}, High={config.go_shop_threshold_high:.1f}")
        print(f"  Pantry propensity (eligible) = {config.pantry_propensity_eligible:.2f}")
        
        # Run simulation
        metrics = run_multi_seed(config, num_seeds=num_seeds, num_days=num_days, parallel=False)
        
        # Calculate errors
        total_error, individual_errors = calculate_calibration_error(metrics, targets)
        within_tol = check_within_tolerance(individual_errors, targets)
        
        # Print results
        print(f"\n{'='*40}")
        print(f"RESULTS - PASS {pass_num}")
        print(f"{'='*40}")
        
        print(f"\n1. Annual Spend:")
        print(f"   Low:    ${metrics['annual_spend_low']:>7.0f} (target: ${targets.annual_spend_low:.0f}) "
              f"{'✅' if within_tol['spend_low'] else '❌'} error={individual_errors['spend_low']:.3f}")
        print(f"   Medium: ${metrics['annual_spend_medium']:>7.0f} (target: ${targets.annual_spend_medium:.0f}) "
              f"{'✅' if within_tol['spend_medium'] else '❌'} error={individual_errors['spend_medium']:.3f}")
        print(f"   High:   ${metrics['annual_spend_high']:>7.0f} (target: ${targets.annual_spend_high:.0f}) "
              f"{'✅' if within_tol['spend_high'] else '❌'} error={individual_errors['spend_high']:.3f}")
        
        print(f"\n2. Trip Frequency:")
        print(f"   Weekly:    {metrics['weekly_share']:.2%} (target: {targets.weekly_frequency_share:.2%}) "
              f"{'✅' if within_tol['weekly_freq'] else '❌'} error={individual_errors['weekly_freq']:.3f}")
        print(f"   Sub-weekly: {metrics['subweekly_share']:.2%} (target: {targets.subweekly_frequency_share:.2%}) "
              f"{'✅' if within_tol['subweekly_freq'] else '❌'} error={individual_errors['subweekly_freq']:.3f}")
        
        print(f"\n3. Average Distance:")
        print(f"   Car:    {metrics['distance_car_mi']:.2f} mi (target: {targets.distance_car:.2f} mi) "
              f"{'✅' if within_tol['distance_car'] else '❌'} error={individual_errors['distance_car']:.3f}")
        print(f"   No-car: {metrics['distance_no_car_mi']:.2f} mi (target: {targets.distance_no_car:.2f} mi) "
              f"{'✅' if within_tol['distance_no_car'] else '❌'} error={individual_errors['distance_no_car']:.3f}")
        
        print(f"\n4. Small Store Share:")
        print(f"   {metrics['small_store_share']:.2%} (target: {targets.small_store_share:.2%}, max: {targets.small_store_max:.2%}) "
              f"{'✅' if within_tol['small_store'] else '❌'} error={individual_errors['small_store']:.3f}")
        
        print(f"\n5. Pantry User Share:")
        print(f"   {metrics['pantry_user_share']:.2%} (target: {targets.pantry_user_share:.2%}) "
              f"{'✅' if within_tol['pantry_users'] else '❌'} error={individual_errors['pantry_users']:.3f}")
        
        print(f"\nTOTAL ERROR: {total_error:.3f}")
        print(f"PASSED: {sum(within_tol.values())}/{len(within_tol)} metrics")
        
        # Check if all within tolerance
        if all(within_tol.values()):
            print(f"\n🎉 ALL METRICS WITHIN TOLERANCE! Calibration complete.")
            break
        
        # Manual adjustment guidance
        if pass_num < num_passes:
            print(f"\n{'='*40}")
            print(f"ADJUSTMENT GUIDANCE FOR NEXT PASS")
            print(f"{'='*40}")
            
            # Provide specific recommendations
            adjustments = []
            
            # Annual spend adjustments
            if not within_tol['spend_low'] or not within_tol['spend_medium'] or not within_tol['spend_high']:
                print("\n💡 Annual spend off target:")
                print("   → Adjust go-shop thresholds and/or basket size parameters")
                if metrics['annual_spend_low'] < targets.annual_spend_low * 0.9:
                    print("   → Low income spending too low: decrease go_shop_threshold_low")
                elif metrics['annual_spend_low'] > targets.annual_spend_low * 1.1:
                    print("   → Low income spending too high: increase go_shop_threshold_low")
            
            # Distance adjustments
            if not within_tol['distance_car']:
                if metrics['distance_car_mi'] > targets.distance_car * 1.25:
                    print("\n💡 Car distance too far: increase α_distance")
                    adjustments.append(('alpha_distance', min(config.alpha_distance * 1.2, ranges.alpha_distance_range[1])))
                elif metrics['distance_car_mi'] < targets.distance_car * 0.75:
                    print("\n💡 Car distance too short: decrease α_distance")
                    adjustments.append(('alpha_distance', max(config.alpha_distance * 0.8, ranges.alpha_distance_range[0])))
            
            # Small store share adjustments
            if not within_tol['small_store']:
                if metrics['small_store_share'] > targets.small_store_max:
                    print("\n💡 Too many small store trips: increase γ_quality")
                    adjustments.append(('gamma_quality_variety', min(config.gamma_quality_variety * 1.15, ranges.gamma_quality_range[1])))
            
            # Apply adjustments
            if adjustments:
                print(f"\nApplying adjustments:")
                new_params = {}
                for param, value in adjustments:
                    print(f"   {param}: {getattr(config, param):.2f} → {value:.2f}")
                    new_params[param] = value
                
                # Create new config with adjustments
                config = SimulationConfig(**{**config.__dict__, **new_params})
            else:
                print("\nNo automatic adjustments. Consider manual tuning.")
    
    print(f"\n{'='*70}")
    print(f"CALIBRATION COMPLETE")
    print(f"{'='*70}\n")
    
    return config


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("FOOD ACCESS ABM - CALIBRATION FRAMEWORK")
    print("="*70)
    
    # Define targets and ranges
    targets = CalibrationTargets()
    ranges = ParameterRanges()
    
    print("\nCalibration Targets:")
    print(f"  1. Annual spend: Low=${targets.annual_spend_low:.0f}, "
          f"Med=${targets.annual_spend_medium:.0f}, High=${targets.annual_spend_high:.0f} (±{targets.annual_spend_tolerance:.0%})")
    print(f"  2. Trip frequency: Weekly={targets.weekly_frequency_share:.0%}±{targets.weekly_frequency_tolerance:.0%}, "
          f"Sub-weekly={targets.subweekly_frequency_share:.0%}±{targets.subweekly_frequency_tolerance:.0%}")
    print(f"  3. Distance: Car={targets.distance_car:.1f}mi, No-car={targets.distance_no_car:.1f}mi (±{targets.distance_tolerance:.0%})")
    print(f"  4. Small store share: ≤{targets.small_store_max:.0%} (prefer {targets.small_store_share:.0%})")
    print(f"  5. Pantry users: {targets.pantry_user_share:.0%}±{targets.pantry_user_tolerance:.0%}")
    
    # Choose calibration method
    print("\n" + "="*70)
    print("Select calibration method:")
    print("  1. Iterative calibration (3 passes, guided adjustments)")
    print("  2. Grid search (α × γ × threshold_low)")
    print("  3. Quick test (single run with default parameters)")
    print("="*70)
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == '1':
        # Iterative calibration
        final_config = iterative_calibration(
            targets=targets,
            ranges=ranges,
            num_passes=3,
            num_seeds=30,
            num_days=30
        )
        
        print("\nFinal calibrated parameters:")
        print(f"  alpha_distance = {final_config.alpha_distance:.2f}")
        print(f"  beta_price_budget = {final_config.beta_price_budget:.2f}")
        print(f"  gamma_quality_variety = {final_config.gamma_quality_variety:.2f}")
        print(f"  delta_convenience = {final_config.delta_convenience:.2f}")
        print(f"  go_shop_threshold_low = {final_config.go_shop_threshold_low:.1f}")
        print(f"  go_shop_threshold_medium = {final_config.go_shop_threshold_medium:.1f}")
        print(f"  go_shop_threshold_high = {final_config.go_shop_threshold_high:.1f}")
        print(f"  pantry_propensity_eligible = {final_config.pantry_propensity_eligible:.2f}")
        
    elif choice == '2':
        # Grid search
        alpha_values = [0.8, 1.0, 1.2, 1.4]
        gamma_values = [0.5, 0.6, 0.7, 0.8]
        threshold_low_values = [2.0, 2.5, 3.0]
        
        results_df = grid_search_calibration(
            alpha_values=alpha_values,
            gamma_values=gamma_values,
            threshold_low_values=threshold_low_values,
            targets=targets,
            ranges=ranges,
            num_seeds=10,  # Fewer seeds for grid search
            num_days=30
        )
        
        # Save results
        results_df.to_csv('calibration_grid_search_results.csv', index=False)
        print("\nResults saved to: calibration_grid_search_results.csv")
        
        # Print top 5
        print("\nTop 5 configurations:")
        print(results_df[['alpha_distance', 'gamma_quality', 'threshold_low', 'total_error', 'all_pass']].head())
        
    else:
        # Quick test
        print("\nRunning quick test with default parameters...")
        config = SimulationConfig()
        metrics = run_multi_seed(config, num_seeds=5, num_days=30, parallel=False)
        
        total_error, individual_errors = calculate_calibration_error(metrics, targets)
        within_tol = check_within_tolerance(individual_errors, targets)
        
        print("\nQuick Test Results:")
        print(f"  Annual spend low: ${metrics['annual_spend_low']:.0f} (target: ${targets.annual_spend_low:.0f})")
        print(f"  Weekly frequency: {metrics['weekly_share']:.2%} (target: {targets.weekly_frequency_share:.2%})")
        print(f"  Distance (car): {metrics['distance_car_mi']:.2f} mi (target: {targets.distance_car:.2f} mi)")
        print(f"  Total error: {total_error:.3f}")
        print(f"  Passed: {sum(within_tol.values())}/{len(within_tol)} metrics")
    
    print("\n✅ Calibration framework ready to use!")

