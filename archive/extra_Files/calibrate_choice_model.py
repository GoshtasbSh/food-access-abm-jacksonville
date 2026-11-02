"""
Calibration helper for discrete choice model weights

This script helps you calibrate α, β, γ, δ by:
1. Running simulations with different parameter values
2. Comparing results to target metrics
3. Finding best-fit parameters
"""

import os
import sys
import numpy as np
from typing import Dict, List, Tuple
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enhanced_mesa_geo_model import SimulationConfig, IncomeLevel
from baseline_scenario import BaselineScenarioModel


def run_simulation_with_config(config: SimulationConfig, num_days: int = 90) -> Dict:
    """
    Run simulation with given config and return metrics
    
    Args:
        config: SimulationConfig with parameters to test
        num_days: Number of simulation days
        
    Returns:
        Dictionary of metrics
    """
    model = BaselineScenarioModel(config=config)
    
    # Run simulation
    for i in range(num_days):
        model.step()
    
    # Calculate metrics
    all_consumers = model.consumers
    
    # Average travel distance (when shopping)
    distances = [c.travel_distance for c in all_consumers 
                 if hasattr(c, 'travel_distance') and c.travel_distance > 0]
    avg_distance = np.mean(distances) if distances else 0
    
    # Shopping frequency (from history)
    shopping_frequencies = []
    for c in all_consumers:
        if hasattr(c, 'shopping_history') and len(c.shopping_history) > 1:
            # Calculate days between trips
            days = [c.shopping_history[i]['day'] - c.shopping_history[i-1]['day'] 
                   for i in range(1, len(c.shopping_history))]
            if days:
                shopping_frequencies.append(np.mean(days))
    avg_frequency = np.mean(shopping_frequencies) if shopping_frequencies else 0
    
    # Store type distribution
    store_choices = {}
    for c in all_consumers:
        if hasattr(c, 'shopping_history'):
            for trip in c.shopping_history:
                store_type = trip.get('provider_type', 'unknown')
                store_choices[store_type] = store_choices.get(store_type, 0) + 1
    
    # Satisfaction rate
    total_needed = sum(1 for c in all_consumers if hasattr(c, 'needed_to_shop_today') and c.needed_to_shop_today)
    total_satisfied = sum(1 for c in all_consumers if hasattr(c, 'satisfied_today') and c.satisfied_today)
    satisfaction_rate = total_satisfied / total_needed if total_needed > 0 else 0
    
    return {
        'avg_distance': avg_distance,
        'avg_frequency': avg_frequency,
        'store_choices': store_choices,
        'satisfaction_rate': satisfaction_rate,
        'total_trips': len(distances)
    }


def calibrate_alpha(target_distance: float, 
                   alpha_range: Tuple[float, float] = (0.5, 2.0),
                   num_tests: int = 5) -> List[Dict]:
    """
    Calibrate alpha_distance to match target average travel distance
    
    Args:
        target_distance: Target average distance in km
        alpha_range: (min, max) range for alpha
        num_tests: Number of values to test
        
    Returns:
        List of results sorted by closeness to target
    """
    print(f"\n{'='*70}")
    print(f"CALIBRATING ALPHA (Distance Weight)")
    print(f"{'='*70}")
    print(f"Target average distance: {target_distance:.2f} km")
    print(f"Testing alpha range: {alpha_range[0]:.2f} to {alpha_range[1]:.2f}")
    print(f"Number of tests: {num_tests}\n")
    
    results = []
    alpha_values = np.linspace(alpha_range[0], alpha_range[1], num_tests)
    
    for i, alpha in enumerate(alpha_values):
        print(f"Test {i+1}/{num_tests}: alpha = {alpha:.2f}...", end=" ")
        
        config = SimulationConfig(alpha_distance=alpha)
        metrics = run_simulation_with_config(config, num_days=90)
        
        error = abs(metrics['avg_distance'] - target_distance)
        
        results.append({
            'alpha': alpha,
            'avg_distance': metrics['avg_distance'],
            'error': error,
            'metrics': metrics
        })
        
        print(f"Distance: {metrics['avg_distance']:.2f} km (error: {error:.2f})")
    
    # Sort by error
    results.sort(key=lambda x: x['error'])
    
    print(f"\n{'='*70}")
    print(f"BEST FIT:")
    print(f"  alpha = {results[0]['alpha']:.2f}")
    print(f"  Simulated distance: {results[0]['avg_distance']:.2f} km")
    print(f"  Target distance: {target_distance:.2f} km")
    print(f"  Error: {results[0]['error']:.2f} km")
    print(f"{'='*70}\n")
    
    return results


def calibrate_beta(target_discount_share: float,
                  beta_range: Tuple[float, float] = (0.3, 1.2),
                  num_tests: int = 5) -> List[Dict]:
    """
    Calibrate beta_price_budget to match target share of trips to discount stores
    
    Args:
        target_discount_share: Target % of trips to discount stores (0-1)
        beta_range: (min, max) range for beta
        num_tests: Number of values to test
        
    Returns:
        List of results sorted by closeness to target
    """
    print(f"\n{'='*70}")
    print(f"CALIBRATING BETA (Price/Budget Weight)")
    print(f"{'='*70}")
    print(f"Target discount store share: {target_discount_share:.1%}")
    print(f"Testing beta range: {beta_range[0]:.2f} to {beta_range[1]:.2f}")
    print(f"Number of tests: {num_tests}\n")
    
    results = []
    beta_values = np.linspace(beta_range[0], beta_range[1], num_tests)
    
    for i, beta in enumerate(beta_values):
        print(f"Test {i+1}/{num_tests}: beta = {beta:.2f}...", end=" ")
        
        config = SimulationConfig(beta_price_budget=beta)
        metrics = run_simulation_with_config(config, num_days=90)
        
        # Calculate discount store share
        store_choices = metrics['store_choices']
        discount_trips = store_choices.get('discount', 0) + store_choices.get('supercenter', 0)
        total_trips = sum(store_choices.values())
        discount_share = discount_trips / total_trips if total_trips > 0 else 0
        
        error = abs(discount_share - target_discount_share)
        
        results.append({
            'beta': beta,
            'discount_share': discount_share,
            'error': error,
            'metrics': metrics
        })
        
        print(f"Discount share: {discount_share:.1%} (error: {error:.3f})")
    
    # Sort by error
    results.sort(key=lambda x: x['error'])
    
    print(f"\n{'='*70}")
    print(f"BEST FIT:")
    print(f"  beta = {results[0]['beta']:.2f}")
    print(f"  Simulated discount share: {results[0]['discount_share']:.1%}")
    print(f"  Target discount share: {target_discount_share:.1%}")
    print(f"  Error: {results[0]['error']:.3f}")
    print(f"{'='*70}\n")
    
    return results


def calibrate_go_shop_threshold(target_frequency: float,
                                income_level: str = 'low',
                                threshold_range: Tuple[float, float] = (2.0, 5.0),
                                num_tests: int = 5) -> List[Dict]:
    """
    Calibrate go-shop threshold to match target shopping frequency
    
    Args:
        target_frequency: Target days between trips
        income_level: 'low', 'medium', or 'high'
        threshold_range: (min, max) range for threshold
        num_tests: Number of values to test
        
    Returns:
        List of results sorted by closeness to target
    """
    print(f"\n{'='*70}")
    print(f"CALIBRATING GO-SHOP THRESHOLD ({income_level.upper()} income)")
    print(f"{'='*70}")
    print(f"Target shopping frequency: Every {target_frequency:.1f} days")
    print(f"Testing threshold range: {threshold_range[0]:.1f} to {threshold_range[1]:.1f}")
    print(f"Number of tests: {num_tests}\n")
    
    results = []
    threshold_values = np.linspace(threshold_range[0], threshold_range[1], num_tests)
    
    for i, threshold in enumerate(threshold_values):
        print(f"Test {i+1}/{num_tests}: threshold = {threshold:.1f}...", end=" ")
        
        # Set threshold based on income level
        if income_level == 'low':
            config = SimulationConfig(go_shop_threshold_low=threshold)
        elif income_level == 'medium':
            config = SimulationConfig(go_shop_threshold_medium=threshold)
        else:  # high
            config = SimulationConfig(go_shop_threshold_high=threshold)
        
        metrics = run_simulation_with_config(config, num_days=90)
        
        error = abs(metrics['avg_frequency'] - target_frequency)
        
        results.append({
            'threshold': threshold,
            'avg_frequency': metrics['avg_frequency'],
            'error': error,
            'metrics': metrics
        })
        
        print(f"Frequency: Every {metrics['avg_frequency']:.1f} days (error: {error:.2f})")
    
    # Sort by error
    results.sort(key=lambda x: x['error'])
    
    print(f"\n{'='*70}")
    print(f"BEST FIT:")
    print(f"  threshold = {results[0]['threshold']:.1f}")
    print(f"  Simulated frequency: Every {results[0]['avg_frequency']:.1f} days")
    print(f"  Target frequency: Every {target_frequency:.1f} days")
    print(f"  Error: {results[0]['error']:.2f} days")
    print(f"{'='*70}\n")
    
    return results


def compare_configs(configs: List[Tuple[str, SimulationConfig]], 
                   num_days: int = 90) -> None:
    """
    Compare multiple configurations side-by-side
    
    Args:
        configs: List of (name, config) tuples
        num_days: Number of simulation days
    """
    print(f"\n{'='*70}")
    print(f"COMPARING CONFIGURATIONS")
    print(f"{'='*70}\n")
    
    results = {}
    for name, config in configs:
        print(f"Running: {name}...")
        metrics = run_simulation_with_config(config, num_days)
        results[name] = metrics
    
    print(f"\n{'='*70}")
    print(f"COMPARISON RESULTS")
    print(f"{'='*70}\n")
    
    # Print comparison table
    print(f"{'Configuration':<20} {'Avg Distance':<15} {'Avg Frequency':<15} {'Satisfaction':<15}")
    print("-" * 70)
    for name, metrics in results.items():
        print(f"{name:<20} {metrics['avg_distance']:>8.2f} km    "
              f"{metrics['avg_frequency']:>8.1f} days   "
              f"{metrics['satisfaction_rate']:>8.1%}")
    print("=" * 70 + "\n")


# Example usage
if __name__ == '__main__':
    print("\n" + "="*70)
    print("CHOICE MODEL CALIBRATION TOOL")
    print("="*70)
    
    # Example 1: Calibrate alpha to match average distance
    print("\nExample 1: Finding alpha that produces 3.2 km average travel distance")
    alpha_results = calibrate_alpha(target_distance=3.2, num_tests=5)
    
    # Example 2: Calibrate beta to match discount store usage
    print("\nExample 2: Finding beta that produces 30% discount store usage")
    beta_results = calibrate_beta(target_discount_share=0.30, num_tests=5)
    
    # Example 3: Calibrate go-shop threshold
    print("\nExample 3: Finding threshold that produces 6.5 day shopping frequency")
    threshold_results = calibrate_go_shop_threshold(
        target_frequency=6.5,
        income_level='medium',
        num_tests=5
    )
    
    # Example 4: Compare configurations
    print("\nExample 4: Comparing default vs. calibrated parameters")
    configs = [
        ("Default", SimulationConfig()),
        ("High α (distance matters more)", SimulationConfig(alpha_distance=1.5)),
        ("High β (price matters more)", SimulationConfig(beta_price_budget=1.0)),
        ("Low α (distance matters less)", SimulationConfig(alpha_distance=0.7))
    ]
    compare_configs(configs, num_days=90)
    
    print("\n✅ Calibration examples complete!")
    print("\nTo use custom values, create config:")
    print("""
config = SimulationConfig(
    alpha_distance=1.3,      # From calibration
    beta_price_budget=0.85,  # From calibration
    go_shop_threshold_medium=6.5
)
model = BaselineScenarioModel(config=config)
""")

