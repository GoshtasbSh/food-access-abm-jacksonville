"""
Dashboard Parameters Layout
============================
Provides parameter input controls for the live dashboard
"""

from dash import dcc, html
from enhanced_mesa_geo_model import SimulationConfig

def create_dynamic_parameter_layout(scenario='baseline'):
    """Create parameter input layout for the dashboard"""
    
    config = SimulationConfig()
    
    return html.Div([
        html.H4("🎛️ Simulation Parameters", style={'marginBottom': '20px'}),
        
        # Basic Parameters
        html.Div([
            html.Label("Number of Households:"),
            dcc.Input(id='param-num-consumers', type='number', value=200, min=10, max=1000, step=10),
        ], style={'marginBottom': '15px'}),
        
        html.Div([
            html.Label("Simulation Days:"),
            dcc.Input(id='param-simulation-days', type='number', value=30, min=1, max=365, step=1),
        ], style={'marginBottom': '15px'}),
        
        # Choice Model Parameters
        html.H5("Discrete Choice Model", style={'marginTop': '20px', 'marginBottom': '10px'}),
        
        html.Div([
            html.Label("Alpha (Distance Weight):"),
            dcc.Input(id='param-alpha', type='number', value=config.alpha_distance, step=0.1),
        ], style={'marginBottom': '10px'}),
        
        html.Div([
            html.Label("Beta (Price/Budget Weight):"),
            dcc.Input(id='param-beta', type='number', value=config.beta_price_budget, step=0.1),
        ], style={'marginBottom': '10px'}),
        
        html.Div([
            html.Label("Gamma (Quality Weight):"),
            dcc.Input(id='param-gamma', type='number', value=config.gamma_quality_variety, step=0.1),
        ], style={'marginBottom': '10px'}),
        
        html.Div([
            html.Label("Delta (Convenience Weight):"),
            dcc.Input(id='param-delta', type='number', value=config.delta_convenience, step=0.1),
        ], style={'marginBottom': '10px'}),
        
        # Delivery Parameters
        html.H5("Delivery Parameters", style={'marginTop': '20px', 'marginBottom': '10px'}),
        
        html.Div([
            html.Label("Delivery Propensity (Low Income):"),
            dcc.Input(id='param-delivery-low', type='number', value=config.delivery_baseline_low, 
                     min=0, max=1, step=0.01),
        ], style={'marginBottom': '10px'}),
        
        html.Div([
            html.Label("Delivery Propensity (Medium Income):"),
            dcc.Input(id='param-delivery-medium', type='number', value=config.delivery_baseline_medium,
                     min=0, max=1, step=0.01),
        ], style={'marginBottom': '10px'}),
        
        html.Div([
            html.Label("Delivery Propensity (High Income):"),
            dcc.Input(id='param-delivery-high', type='number', value=config.delivery_baseline_high,
                     min=0, max=1, step=0.01),
        ], style={'marginBottom': '10px'}),
        
    ])

def get_all_parameter_input_ids():
    """Get list of all parameter input IDs"""
    return [
        # Basic
        'param-num-consumers',
        'param-simulation-days',
        # Baseline Delivery
        'param-delivery-low',
        'param-delivery-medium',
        'param-delivery-high',
        # Scenario 1: New Grocery Store
        'param-grocery-capacity',
        'param-scenario1-store-region',
        # Scenario 2: Food Hub + Corners
        'param-food-hub-capacity',
        'param-num-corner-stores',
        'param-corner-capacity',
        # Scenario 3: Mobile Pantries
        'param-num-mobile-pantries',
        'param-mobile-pantry-capacity',
        'param-pantry-strategy',
        # Scenario 4: Subsidized Delivery
        'param-delivery-capacity',
        'param-base-fee',
        'param-distance-fee',
        'param-delivery-area',
    ]

def get_scenario_parameter_input_ids(scenario):
    """Get parameter input IDs for a specific scenario"""
    # All scenarios use the same parameters
    return get_all_parameter_input_ids()

def get_default_section_for_scenario(scenario):
    """Return the section to show by default when switching to a scenario (so key params are visible immediately)."""
    if scenario == 'scenario1':
        return 'new_store'   # Grocery params first
    elif scenario == 'scenario2':
        return 'food_hub'
    elif scenario == 'scenario3':
        return 'mobile_pantries'
    elif scenario == 'scenario4':
        return 'subsidized_delivery'
    return 'basic'

def get_sections_for_scenario(scenario):
    """Get parameter sections for a scenario"""
    
    # Common sections for all scenarios
    common = [
        ('basic', '📊 Basic Parameters'),
    ]
    
    # Scenario-specific sections (new_store included for baseline so param-scenario1-store-region exists in DOM)
    if scenario == 'baseline':
        return common + [('_store_region', ''), ('delivery', '🚚 Delivery Parameters')]
    
    elif scenario == 'scenario1':
        return common + [
            ('new_store', '🏪 New Grocery Store'),
            ('delivery', '🚚 Delivery Parameters')
        ]
    
    elif scenario == 'scenario2':
        return common + [
            ('food_hub', '🏬 Food Hub Settings'),
            ('corner_stores', '🏪 Corner Store Network'),
            ('delivery', '🚚 Delivery Parameters')
        ]
    
    elif scenario == 'scenario3':
        return common + [
            ('mobile_pantries', '🚚 Mobile Pantries'),
            ('delivery', '🚚 Delivery Parameters')
        ]
    
    elif scenario == 'scenario4':
        return common + [
            ('subsidized_delivery', '🎁 Subsidized Delivery Service')
        ]
    
    return common

def render_section_for_scenario(scenario, section):
    """Render a specific parameter section for a scenario"""
    config = SimulationConfig()
    
    # Style for parameter inputs
    input_style = {
        'width': '100%',
        'padding': '8px',
        'borderRadius': '4px',
        'border': '1px solid #e2e8f0',
        'fontSize': '14px'
    }
    
    label_style = {
        'fontWeight': '600',
        'marginBottom': '5px',
        'fontSize': '13px',
        'color': '#4a5568'
    }
    
    section_style = {
        'marginBottom': '20px'
    }
    
    if section == 'basic':
        return html.Div([
            html.H5("📊 Basic Parameters", style={'marginBottom': '20px', 'color': '#2d3748'}),
            
            html.Div([
                html.Label("Number of Households:", style=label_style),
                dcc.Input(
                    id='param-num-consumers',
                    type='number',
                    value=200,
                    min=10,
                    max=1000,
                    step=10,
                    style=input_style
                ),
                html.Small("Range: 10-1000 households", style={'color': '#718096', 'fontSize': '11px'})
            ], style=section_style),
            
            html.Div([
                html.Label("Simulation Days:", style=label_style),
                dcc.Input(
                    id='param-simulation-days',
                    type='number',
                    value=30,
                    min=1,
                    max=365,
                    step=1,
                    style=input_style
                ),
                html.Small("Range: 1-365 days", style={'color': '#718096', 'fontSize': '11px'})
            ], style=section_style),
        ])
    
    elif section == 'choice_model':
        return html.Div([
            html.H5("🎯 Discrete Choice Model Parameters", style={'marginBottom': '20px', 'color': '#2d3748'}),
            
            html.Div([
                html.Label("α (Alpha) - Distance Weight:", style=label_style),
                dcc.Input(
                    id='param-alpha',
                    type='number',
                    value=config.alpha_distance,
                    min=0,
                    max=5,
                    step=0.1,
                    style=input_style
                ),
                html.Small("Higher = more sensitive to distance", style={'color': '#718096', 'fontSize': '11px'})
            ], style=section_style),
            
            html.Div([
                html.Label("β (Beta) - Price/Budget Weight:", style=label_style),
                dcc.Input(
                    id='param-beta',
                    type='number',
                    value=config.beta_price_budget,
                    min=0,
                    max=5,
                    step=0.1,
                    style=input_style
                ),
                html.Small("Higher = more price-conscious", style={'color': '#718096', 'fontSize': '11px'})
            ], style=section_style),
            
            html.Div([
                html.Label("γ (Gamma) - Quality/Variety Weight:", style=label_style),
                dcc.Input(
                    id='param-gamma',
                    type='number',
                    value=config.gamma_quality_variety,
                    min=0,
                    max=5,
                    step=0.1,
                    style=input_style
                ),
                html.Small("Higher = stronger quality preference", style={'color': '#718096', 'fontSize': '11px'})
            ], style=section_style),
            
            html.Div([
                html.Label("δ (Delta) - Convenience Weight:", style=label_style),
                dcc.Input(
                    id='param-delta',
                    type='number',
                    value=config.delta_convenience,
                    min=0,
                    max=5,
                    step=0.1,
                    style=input_style
                ),
                html.Small("Higher = more convenience-focused", style={'color': '#718096', 'fontSize': '11px'})
            ], style=section_style),
        ])
    
    elif section == 'delivery':
        return html.Div([
            html.H5("🚚 Delivery Usage Parameters", style={'marginBottom': '20px', 'color': '#2d3748'}),
            
            html.Div([
                html.Label("Low Income Propensity:", style=label_style),
                dcc.Input(
                    id='param-delivery-low',
                    type='number',
                    value=config.delivery_baseline_low,
                    min=0,
                    max=1,
                    step=0.01,
                    style=input_style
                ),
                html.Small("Target: 3-5% actual usage (Currently: 8% of eligible)", style={'color': '#718096', 'fontSize': '11px'})
            ], style=section_style),
            
            html.Div([
                html.Label("Medium Income Propensity:", style=label_style),
                dcc.Input(
                    id='param-delivery-medium',
                    type='number',
                    value=config.delivery_baseline_medium,
                    min=0,
                    max=1,
                    step=0.01,
                    style=input_style
                ),
                html.Small("Target: ~10% actual usage (Currently: 20% of eligible)", style={'color': '#718096', 'fontSize': '11px'})
            ], style=section_style),
            
            html.Div([
                html.Label("High Income Propensity:", style=label_style),
                dcc.Input(
                    id='param-delivery-high',
                    type='number',
                    value=config.delivery_baseline_high,
                    min=0,
                    max=1,
                    step=0.01,
                    style=input_style
                ),
                html.Small("Target: up to 20% actual usage (Currently: 35% of eligible)", style={'color': '#718096', 'fontSize': '11px'})
            ], style=section_style),
            
            html.Div([
                html.P("📝 Note: These values reflect actual usage, not just eligibility. 50% of households are 'hard blockers' (no internet/tech access).", 
                       style={'fontSize': '12px', 'color': '#718096', 'fontStyle': 'italic', 'marginTop': '20px', 'padding': '10px', 'background': '#f7fafc', 'borderRadius': '4px'})
            ])
        ])
    
    # Hidden section: store region dropdown (always in DOM for baseline - needed for callbacks)
    elif section == '_store_region':
        return html.Div([
            dcc.Dropdown(
                id='param-scenario1-store-region',
                options=[
                    {'label': '🎯 Optimal (auto-search whole HZ1)', 'value': 'optimal'},
                    {'label': '⬆️ North', 'value': 'north'},
                    {'label': '⬇️ South', 'value': 'south'},
                    {'label': '➡️ East', 'value': 'east'},
                    {'label': '⬅️ West', 'value': 'west'},
                    {'label': '📍 Center', 'value': 'center'}
                ],
                value='optimal',
                clearable=False,
                style={'fontSize': '14px'}
            )
        ], style={"marginBottom": "0"})

    # Scenario 1: New Grocery Store
    elif section == 'new_store':
        return html.Div([
            html.H5("🏪 New Grocery Store Parameters", style={'marginBottom': '20px', 'color': '#2d3748'}),
            
            html.Div([
                html.Label("Store Capacity:", style=label_style),
                dcc.Input(
                    id='param-grocery-capacity',
                    type='number',
                    value=600,
                    min=200,
                    max=2000,
                    step=50,
                    style=input_style
                ),
                html.Small("Daily customer capacity", style={'color': '#718096', 'fontSize': '11px'})
            ], style=section_style),

            html.Div([
                html.Label("Store Region to Test:", style=label_style),
                dcc.Dropdown(
                    id='param-scenario1-store-region',
                    options=[
                        {'label': '🎯 Optimal (auto-search whole HZ1)', 'value': 'optimal'},
                        {'label': '⬆️ North', 'value': 'north'},
                        {'label': '⬇️ South', 'value': 'south'},
                        {'label': '➡️ East', 'value': 'east'},
                        {'label': '⬅️ West', 'value': 'west'},
                        {'label': '📍 Center', 'value': 'center'}
                    ],
                    value='optimal',
                    clearable=False,
                    style={'fontSize': '14px'}
                ),
                html.Small("Constrain Scenario 1 store search to one region", style={'color': '#718096', 'fontSize': '11px'})
            ], style=section_style),
            
            html.Div([
                html.P("📍 Store location will be optimally placed to maximize food access improvement",
                       style={'fontSize': '12px', 'color': '#718096', 'fontStyle': 'italic', 'padding': '10px', 'background': '#f7fafc', 'borderRadius': '4px'})
            ])
        ])
    
    # Scenario 2: Food Hub + Corner Stores
    elif section == 'food_hub':
        return html.Div([
            html.H5("🏬 Food Hub Parameters", style={'marginBottom': '20px', 'color': '#2d3748'}),
            
            html.Div([
                html.Label("Food Hub Capacity:", style=label_style),
                dcc.Input(
                    id='param-food-hub-capacity',
                    type='number',
                    value=300,
                    min=100,
                    max=1000,
                    step=50,
                    style=input_style
                ),
                html.Small("Daily customer capacity", style={'color': '#718096', 'fontSize': '11px'})
            ], style=section_style),
            
            html.Div([
                html.P("🗓️ Food hub operates Mon/Wed/Fri (market days)",
                       style={'fontSize': '12px', 'color': '#718096', 'padding': '10px', 'background': '#f7fafc', 'borderRadius': '4px'})
            ])
        ])
    
    elif section == 'corner_stores':
        return html.Div([
            html.H5("🏪 Corner Store Network Parameters", style={'marginBottom': '20px', 'color': '#2d3748'}),
            
            html.Div([
                html.Label("Number of New Corner Stores:", style=label_style),
                dcc.Input(
                    id='param-num-corner-stores',
                    type='number',
                    value=6,
                    min=2,
                    max=15,
                    step=1,
                    style=input_style
                ),
                html.Small("Network size", style={'color': '#718096', 'fontSize': '11px'})
            ], style=section_style),
            
            html.Div([
                html.Label("Corner Store Capacity:", style=label_style),
                dcc.Input(
                    id='param-corner-capacity',
                    type='number',
                    value=60,
                    min=30,
                    max=150,
                    step=10,
                    style=input_style
                ),
                html.Small("Daily capacity per store", style={'color': '#718096', 'fontSize': '11px'})
            ], style=section_style),
            
            html.Div([
                html.P("📍 Stores will be spatially optimized to maximize coverage",
                       style={'fontSize': '12px', 'color': '#718096', 'fontStyle': 'italic', 'padding': '10px', 'background': '#f7fafc', 'borderRadius': '4px'})
            ])
        ])
    
    # Scenario 3: Mobile Pantries
    elif section == 'mobile_pantries':
        return html.Div([
            html.H5("🚚 Mobile Pantry Parameters", style={'marginBottom': '20px', 'color': '#2d3748'}),
            
            html.Div([
                html.Label("Number of NEW Mobile Pantries:", style=label_style),
                dcc.Input(
                    id='param-num-mobile-pantries',
                    type='number',
                    value=2,
                    min=1,
                    max=10,
                    step=1,
                    style=input_style
                ),
                html.Small("In addition to 3 existing FNEFL pantries", style={'color': '#718096', 'fontSize': '11px'})
            ], style=section_style),
            
            html.Div([
                html.Label("Pantry Capacity:", style=label_style),
                dcc.Input(
                    id='param-mobile-pantry-capacity',
                    type='number',
                    value=120,
                    min=50,
                    max=300,
                    step=10,
                    style=input_style
                ),
                html.Small("Households served per distribution", style={'color': '#718096', 'fontSize': '11px'})
            ], style=section_style),
            
            html.Div([
                html.Label("Placement Strategy:", style=label_style),
                dcc.Dropdown(
                    id='param-pantry-strategy',
                    options=[
                        {'label': '📍 Fixed Locations', 'value': 'fixed'},
                        {'label': '🔄 Rotating Schedule', 'value': 'rotating'},
                        {'label': '🎯 Needs-Based', 'value': 'needs_based'}
                    ],
                    value='fixed',
                    style={'fontSize': '14px'}
                ),
                html.Small("How pantries are positioned", style={'color': '#718096', 'fontSize': '11px'})
            ], style=section_style),
            
            html.Div([
                html.P("📝 Baseline already has 3 FNEFL mobile pantries (JaxPAL, Bethany, Paxon). These NEW pantries are additional.",
                       style={'fontSize': '12px', 'color': '#718096', 'fontStyle': 'italic', 'padding': '10px', 'background': '#f7fafc', 'borderRadius': '4px'})
            ])
        ])
    
    # Scenario 4: Subsidized Delivery
    elif section == 'subsidized_delivery':
        return html.Div([
            html.H5("🎁 Subsidized Delivery Service Parameters", style={'marginBottom': '20px', 'color': '#2d3748'}),
            
            html.Div([
                html.Label("Delivery Capacity:", style=label_style),
                dcc.Input(
                    id='param-delivery-capacity',
                    type='number',
                    value=500,
                    min=100,
                    max=2000,
                    step=50,
                    style=input_style
                ),
                html.Small("Orders per day", style={'color': '#718096', 'fontSize': '11px'})
            ], style=section_style),
            
            html.Div([
                html.Label("Base Service Fee ($):", style=label_style),
                dcc.Input(
                    id='param-base-fee',
                    type='number',
                    value=2.00,
                    min=0,
                    max=10,
                    step=0.50,
                    style=input_style
                ),
                html.Small("Fixed delivery fee", style={'color': '#718096', 'fontSize': '11px'})
            ], style=section_style),
            
            html.Div([
                html.Label("Distance Fee ($/km):", style=label_style),
                dcc.Input(
                    id='param-distance-fee',
                    type='number',
                    value=0.75,
                    min=0,
                    max=3,
                    step=0.25,
                    style=input_style
                ),
                html.Small("Per kilometer charge", style={'color': '#718096', 'fontSize': '11px'})
            ], style=section_style),
            
            html.Div([
                html.Label("Delivery Area (km):", style=label_style),
                dcc.Input(
                    id='param-delivery-area',
                    type='number',
                    value=20.0,
                    min=5,
                    max=50,
                    step=5,
                    style=input_style
                ),
                html.Small("Maximum delivery radius", style={'color': '#718096', 'fontSize': '11px'})
            ], style=section_style),
            
            html.Div([
                html.H6("💰 Subsidy Structure:", style={'marginTop': '20px', 'marginBottom': '10px'}),
                html.Ul([
                    html.Li("Low Income: FREE delivery ($0)", style={'color': '#38a169'}),
                    html.Li("Medium Income: 50% discount", style={'color': '#dd6b20'}),
                    html.Li("High Income: Full price", style={'color': '#718096'})
                ], style={'fontSize': '13px'}),
                html.P("📝 Subsidy increases delivery propensity by 2x",
                       style={'fontSize': '12px', 'color': '#718096', 'fontStyle': 'italic', 'padding': '10px', 'background': '#f7fafc', 'borderRadius': '4px', 'marginTop': '10px'})
            ])
        ])
    
    return html.Div("Select a parameter section", style={'color': '#a0aec0', 'padding': '20px'})

