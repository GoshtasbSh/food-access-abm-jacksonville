"""
Dashboard Config Builder
=========================
Builds SimulationConfig from dashboard inputs
"""

from enhanced_mesa_geo_model import SimulationConfig

def build_config_from_inputs(input_values):
    """
    Build a SimulationConfig object from dashboard input values
    
    Args:
        input_values: Dictionary of parameter names to values
        
    Returns:
        SimulationConfig object
    """
    
    # Create base config
    config = SimulationConfig()
    
    # Update with input values if provided
    if input_values:
        # Basic parameters
        if 'param-num-consumers' in input_values and input_values['param-num-consumers']:
            config.num_consumers = int(input_values['param-num-consumers'])
        
        if 'param-simulation-days' in input_values and input_values['param-simulation-days']:
            config.simulation_days = int(input_values['param-simulation-days'])
        
        # Choice model parameters are intentionally fixed to calibrated values
        # from SimulationConfig and are not editable from dashboard runtime UI.
        
        # Go-shop thresholds (calibration parameters; use defaults if not in dashboard)
        if 'param-go-shop-low' in input_values and input_values['param-go-shop-low'] is not None:
            config.go_shop_threshold_low = float(input_values['param-go-shop-low'])
        if 'param-go-shop-med' in input_values and input_values['param-go-shop-med'] is not None:
            config.go_shop_threshold_medium = float(input_values['param-go-shop-med'])
        if 'param-go-shop-high' in input_values and input_values['param-go-shop-high'] is not None:
            config.go_shop_threshold_high = float(input_values['param-go-shop-high'])
        
        # Delivery parameters
        if 'param-delivery-low' in input_values and input_values['param-delivery-low'] is not None:
            config.delivery_baseline_low = float(input_values['param-delivery-low'])
        
        if 'param-delivery-medium' in input_values and input_values['param-delivery-medium'] is not None:
            config.delivery_baseline_medium = float(input_values['param-delivery-medium'])
        
        if 'param-delivery-high' in input_values and input_values['param-delivery-high'] is not None:
            config.delivery_baseline_high = float(input_values['param-delivery-high'])
        
        # Scenario 1: New Grocery Store
        if 'param-grocery-capacity' in input_values and input_values['param-grocery-capacity'] is not None:
            config.grocery_store_capacity = int(input_values['param-grocery-capacity'])
        if 'param-scenario1-store-region' in input_values and input_values['param-scenario1-store-region']:
            config.scenario1_store_region = str(input_values['param-scenario1-store-region'])
        
        # Scenario 2: Food Hub + Corner Stores
        if 'param-food-hub-capacity' in input_values and input_values['param-food-hub-capacity'] is not None:
            config.food_hub_capacity = int(input_values['param-food-hub-capacity'])
        if 'param-num-corner-stores' in input_values and input_values['param-num-corner-stores'] is not None:
            config.num_corner_stores = int(input_values['param-num-corner-stores'])
        if 'param-corner-capacity' in input_values and input_values['param-corner-capacity'] is not None:
            config.corner_store_capacity = int(input_values['param-corner-capacity'])
        
        # Scenario 3: Mobile Pantries
        if 'param-num-mobile-pantries' in input_values and input_values['param-num-mobile-pantries'] is not None:
            config.num_mobile_pantries = int(input_values['param-num-mobile-pantries'])
        if 'param-mobile-pantry-capacity' in input_values and input_values['param-mobile-pantry-capacity'] is not None:
            config.mobile_pantry_capacity = int(input_values['param-mobile-pantry-capacity'])
        if 'param-pantry-strategy' in input_values and input_values['param-pantry-strategy']:
            config.mobile_pantry_strategy = str(input_values['param-pantry-strategy'])
    
    return config

def get_config_summary(config):
    """
    Get a summary of the current configuration
    
    Args:
        config: SimulationConfig object
        
    Returns:
        Dictionary with configuration summary
    """
    return {
        'num_consumers': config.num_consumers,
        'simulation_days': config.simulation_days,
        'alpha_distance': config.alpha_distance,
        'beta_price_budget': config.beta_price_budget,
        'gamma_quality_variety': config.gamma_quality_variety,
        'delta_convenience': config.delta_convenience,
        'delivery_baseline_low': config.delivery_baseline_low,
        'delivery_baseline_medium': config.delivery_baseline_medium,
        'delivery_baseline_high': config.delivery_baseline_high,
    }

