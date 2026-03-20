"""
Live Enhanced Mesa-Geo Food Access Dashboard
===========================================

Interactive web dashboard with adaptive parameter section:
- Before: Full parameter configuration
- After: Compact summary focused on simulation monitoring

This dashboard integrates with the separate scenario files:
- enhanced_scenario_1.py (Grocery Store)
- enhanced_scenario_2.py (Food Hub + Corner Stores)
- enhanced_scenario_comparison.py (Comparison Analysis)
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context, ALL
from dash.exceptions import PreventUpdate
import dash_leaflet as dl
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import threading
import time
import json
import glob
import os
from datetime import datetime

# Import enhanced Mesa-Geo modules
from baseline_scenario import create_baseline_scenario, BaselineScenarioModel
from enhanced_scenario_1 import create_enhanced_scenario_1, EnhancedScenario1Model
from enhanced_scenario_2 import create_enhanced_scenario_2, EnhancedScenario2Model
from enhanced_scenario_3 import create_enhanced_scenario_3, EnhancedScenario3Model
from enhanced_scenario_4 import create_enhanced_scenario_4
from enhanced_mesa_geo_model import SimulationConfig, IncomeLevel, ProviderType

# Import dashboard parameters layout
from dashboard_parameters import (
    create_dynamic_parameter_layout, 
    get_all_parameter_input_ids,
    get_scenario_parameter_input_ids,
    get_sections_for_scenario,
    render_section_for_scenario
)
from dashboard_config_builder import build_config_from_inputs
from sensitivity_analysis_sobol import (
    load_calibration_center,
    build_sa_problem,
    run_sa_sweep,
    load_latest_sa_results,
    compute_budget_table,
    build_heatmap_figure,
    build_bar_figure,
    build_scatter_figure,
    build_convergence_figure
)

# Load Health Zone 1 polygon for map display
import geopandas as gpd
from shapely.geometry import Point

# Initialize Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Modeling food access: an agent-based model for evaluating interventions for Health Zone 1, Jacksonville, FL"

# Add enhanced custom CSS styling
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
            
            body {
                font-family: 'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }
            
            /* Main container overlay */
            .main-container {
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                margin: 20px;
                overflow: hidden;
            }
            
            /* Navigation tabs styling */
            .nav-tabs {
                list-style: none;
                display: flex;
                padding: 0;
                margin: 0;
                background: linear-gradient(135deg, #667eea, #764ba2);
                position: relative;
                overflow: hidden;
            }
            
            .nav-tabs::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: linear-gradient(45deg, rgba(255,255,255,0.1) 0%, transparent 100%);
                pointer-events: none;
            }
            
            .nav-item {
                flex: 1;
                position: relative;
            }
            
            .nav-link {
                display: block;
                padding: 20px 24px;
                text-decoration: none;
                color: rgba(255, 255, 255, 0.8);
                font-weight: 600;
                font-size: 16px;
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                text-align: center;
                background: transparent;
                border: none;
                position: relative;
                overflow: hidden;
            }
            
            .nav-link::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
                transition: left 0.6s ease;
            }
            
            .nav-link:hover::before {
                left: 100%;
            }
            
            .nav-link:hover {
                color: white;
                background: rgba(255, 255, 255, 0.1);
                transform: translateY(-2px);
            }
            
            .nav-link.active {
                color: white;
                background: rgba(255, 255, 255, 0.2);
                box-shadow: inset 0 -4px 0 #fff;
            }
            
            /* Enhanced card styling */
            .card {
                background: linear-gradient(145deg, #ffffff, #f8f9fa);
                border-radius: 20px;
                box-shadow: 
                    0 10px 30px rgba(0,0,0,0.1),
                    0 1px 8px rgba(0,0,0,0.05),
                    inset 0 1px 0 rgba(255,255,255,0.8);
                padding: 30px;
                margin: 20px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                position: relative;
                overflow: hidden;
            }
            
            .card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
                background: linear-gradient(90deg, #667eea, #764ba2, #667eea);
                background-size: 200% 100%;
                animation: gradient-shift 3s ease infinite;
            }
            
            @keyframes gradient-shift {
                0%, 100% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
            }
            
            .card:hover {
                transform: translateY(-8px) scale(1.02);
                box-shadow: 
                    0 20px 60px rgba(0,0,0,0.15),
                    0 8px 20px rgba(0,0,0,0.1),
                    inset 0 1px 0 rgba(255,255,255,0.9);
            }
            
            /* Enhanced input styling */
            input[type="number"] {
                width: 100% !important;
                padding: 14px 16px;
                border: 2px solid #e1e8ed;
                border-radius: 12px;
                font-size: 15px;
                font-weight: 500;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                background: linear-gradient(145deg, #ffffff, #f8f9fa);
                box-shadow: inset 0 2px 4px rgba(0,0,0,0.04);
            }
            
            input[type="number"]:focus {
                border-color: #667eea;
                outline: none;
                box-shadow: 
                    0 0 0 4px rgba(102, 126, 234, 0.1),
                    inset 0 2px 4px rgba(0,0,0,0.04);
                background: #ffffff;
                transform: translateY(-2px);
            }
            
            /* Enhanced label styling */
            label {
                font-weight: 600;
                color: #2d3748;
                margin-bottom: 8px;
                display: block;
                font-size: 14px;
                letter-spacing: 0.5px;
                text-transform: uppercase;
            }
            
            /* Enhanced button styling */
            button {
                cursor: pointer;
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                font-weight: 600;
                border: none;
                border-radius: 12px;
                padding: 14px 28px;
                font-size: 15px;
                position: relative;
                overflow: hidden;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            button::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
                transition: left 0.6s ease;
            }
            
            button:hover::before {
                left: 100%;
            }
            
            button:hover {
                transform: translateY(-3px) scale(1.05);
                box-shadow: 0 8px 25px rgba(0,0,0,0.2);
            }
            
            button:active {
                transform: translateY(-1px) scale(1.02);
            }
            
            /* Enhanced metrics card styling */
            .metric-card {
                background: linear-gradient(145deg, #ffffff, #f8f9fa) !important;
                border: 2px solid rgba(102, 126, 234, 0.1) !important;
                border-radius: 14px !important;
                padding: 14px 12px !important;
                text-align: center !important;
                margin: 6px 0 !important;
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
                box-shadow: 
                    0 5px 16px rgba(0,0,0,0.06),
                    0 2px 8px rgba(0,0,0,0.04) !important;
                position: relative !important;
                overflow: hidden !important;
                min-height: 75px !important;
                max-height: 95px !important;
                display: flex !important;
                flex-direction: column !important;
                justify-content: center !important;
            }
            
            .metric-card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: linear-gradient(45deg, #667eea, #764ba2);
                opacity: 0;
                transition: opacity 0.4s ease;
                z-index: 1;
            }
            
            .metric-card:hover::before {
                opacity: 0.05;
            }
            
            .metric-card:hover {
                transform: translateY(-8px) rotate(1deg);
                box-shadow: 
                    0 20px 40px rgba(0,0,0,0.15),
                    0 8px 20px rgba(0,0,0,0.08);
                border-color: #667eea;
            }
            
            .metric-value {
                font-size: 2.0em !important;
                font-weight: 700 !important;
                margin: 0 !important;
                background: linear-gradient(135deg, #667eea, #764ba2) !important;
                -webkit-background-clip: text !important;
                -webkit-text-fill-color: transparent !important;
                background-clip: text !important;
                position: relative !important;
                z-index: 2 !important;
                line-height: 1.0 !important;
            }
            
            .metric-label {
                font-size: 0.75em !important;
                color: #4a5568 !important;
                margin: 6px 0 0 0 !important;
                font-weight: 600 !important;
                text-transform: uppercase !important;
                letter-spacing: 0.8px !important;
                position: relative !important;
                z-index: 2 !important;
                line-height: 1.1 !important;
            }
            
            /* Enhanced status display styling */
            .status-display {
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                border-radius: 12px;
                padding: 16px 24px;
                margin: 16px 0;
                font-weight: 600;
                text-align: center;
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
                position: relative;
                overflow: hidden;
            }
            
            .status-display::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
                animation: loading-shimmer 2s infinite;
            }
            
            @keyframes loading-shimmer {
                0% { left: -100%; }
                100% { left: 100%; }
            }
            
            /* Enhanced two column layout */
            .two-col-layout {
                display: flex;
                gap: 30px;
                align-items: flex-start;
            }
            
            .two-col-layout > div {
                flex: 1;
                min-width: 0;
            }
            
            /* Enhanced responsive design */
            @media (max-width: 768px) {
                .two-col-layout {
                    flex-direction: column;
                    gap: 20px;
                }
                
                .nav-tabs {
                    flex-direction: column;
                }
                
                .card {
                    margin: 10px;
                    padding: 20px;
                }
                
                .main-container {
                    margin: 10px;
                }
            }
            
            /* Enhanced map styling */
            .leaflet-container {
                border-radius: 16px;
                box-shadow: 
                    0 15px 35px rgba(0,0,0,0.1),
                    0 5px 15px rgba(0,0,0,0.05);
                border: 3px solid rgba(255, 255, 255, 0.3);
                overflow: hidden;
            }
            
            /* Real-time update indicator */
            .live-indicator {
                display: inline-block;
                width: 8px;
                height: 8px;
                background: #27ae60;
                border-radius: 50%;
                animation: blink 1.5s infinite;
                margin-left: 8px;
            }
            
            @keyframes blink {
                0%, 50% { opacity: 1; }
                51%, 100% { opacity: 0.3; }
            }
            
            /* Enhanced charts styling */
            .chart-container {
                background: white;
                border-radius: 16px;
                padding: 20px;
                margin: 12px 0;
                box-shadow: 0 8px 25px rgba(0,0,0,0.08);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            
            /* Parameter summary styling */
            .param-summary {
                background: linear-gradient(145deg, #f8f9fa, #ffffff);
                border-radius: 16px;
                padding: 20px;
                margin: 15px 0;
                box-shadow: 0 5px 15px rgba(0,0,0,0.05);
                border-left: 4px solid #667eea;
            }
            
            .param-summary h6 {
                color: #2d3748;
                font-weight: 700;
                margin: 0 0 15px 0;
                font-size: 16px;
            }
            
            .param-summary p {
                margin: 8px 0;
                color: #4a5568;
                font-size: 14px;
                font-weight: 500;
            }
            
            /* Compact metrics styling for sidebar */
            .compact-metric {
                background: linear-gradient(145deg, #ffffff, #f8f9fa);
                border-radius: 12px;
                padding: 15px;
                margin: 10px 0;
                text-align: center;
                box-shadow: 0 4px 15px rgba(0,0,0,0.05);
                border: 1px solid rgba(102, 126, 234, 0.1);
            }
            
            .compact-metric h4 {
                font-size: 1.8em;
                font-weight: 700;
                margin: 0;
                background: linear-gradient(135deg, #667eea, #764ba2);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            
            .compact-metric p {
                font-size: 0.85em;
                color: #6c757d;
                margin: 5px 0 0 0;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            /* CircleMarker colors handled dynamically via component props */
            
            /* Force browser refresh for button spacing */
            #static-buttons-container {
                display: flex !important;
                gap: 30px !important;
                margin-top: auto !important;
                padding: 25px 20px 20px 20px !important;
                justify-content: space-evenly !important;
                align-items: stretch !important;
            }
            
            /* Cache busting - version 2.3 - Optimized metrics sizing */
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Global simulation state with thread-safe access
import threading
simulation_lock = threading.Lock()

class SimulationState:
    def __init__(self):
        self.current_model = None
        self.sim_running = False
        self.simulation_thread = None
        self.simulation_data = []
        self.current_scenario = "scenario1"
        self.comparison_results = None
        self.current_day = 0
        self.max_days = 30
        self.status_message = "Ready to start simulation"
        self.current_params = {}
        # Persist final outputs from each scenario run for cross-run comparison
        self.scenario_snapshots = {}
        # Map/UI cache
        self.cached_map = None
        self.last_map_day = -1
        self.last_model_id = None
        self.prev_running = False
        
    def reset(self):
        with simulation_lock:
            self.current_model = None
            self.sim_running = False
            self.simulation_data = []
            # Keep scenario_snapshots/comparison_results across runs so comparison can use prior outputs
            self.current_day = 0
            self.status_message = "Reset complete"
            self.cached_map = None
            self.last_map_day = -1
            self.last_model_id = None
            self.prev_running = False
    
    def update_data(self, new_data):
        with simulation_lock:
            self.simulation_data.append(new_data)
    
    def get_data(self):
        with simulation_lock:
            return self.simulation_data.copy()

sim_state = SimulationState()

# Sensitivity Analysis state
sa_cancel_event = threading.Event()


class SAProgressState:
    def __init__(self):
        self._lock = threading.Lock()
        self._data = {"completed": 0, "total": 0, "done": False}

    def update(self, completed, total, done=False, result_path=None):
        with self._lock:
            self._data = {"completed": completed, "total": total,
                          "done": done, "result_path": result_path}

    def get(self):
        with self._lock:
            return self._data.copy()


sa_progress_state = SAProgressState()


def update_sa_progress(completed, total, done=False, result_path=None):
    """Called by run_sa_sweep() to update dashboard progress"""
    sa_progress_state.update(completed, total, done, result_path)


# Load Health Zone 1 polygon
def load_health_zone():
    """Load Health Zone 1 polygon for map display"""
    try:
        gdf = gpd.read_file("/Users/goshtasbshahriari/Desktop/Code/Data/HealthZones1and4/Health_Zones_1_and_4.shp")
        gdf = gdf.to_crs(epsg=4326)
        hz1 = gdf[gdf["HealthZ"] == 1]
        if not hz1.empty:
            # Convert to GeoJSON for Dash Leaflet
            geojson = json.loads(hz1.to_json())
            return geojson
    except Exception as e:
        print(f"Warning: Could not load Health Zone polygon: {e}")
    
    # Fallback polygon
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-81.8, 30.2], [-81.5, 30.2], 
                    [-81.5, 30.5], [-81.8, 30.5], 
                    [-81.8, 30.2]
                ]]
            },
            "properties": {"name": "Health Zone 1"}
        }]
    }

health_zone_geojson = load_health_zone()


def _extract_geojson_bounds(geojson_obj):
    """Return [[south, west], [north, east]] bounds from GeoJSON."""
    lons = []
    lats = []

    def _walk(coords):
        if isinstance(coords, (list, tuple)):
            if len(coords) >= 2 and isinstance(coords[0], (int, float)) and isinstance(coords[1], (int, float)):
                lons.append(float(coords[0]))
                lats.append(float(coords[1]))
            else:
                for item in coords:
                    _walk(item)

    for feature in geojson_obj.get("features", []):
        geometry = feature.get("geometry", {})
        _walk(geometry.get("coordinates", []))

    if not lons or not lats:
        return [[30.2, -81.8], [30.5, -81.5]]
    return [[min(lats), min(lons)], [max(lats), max(lons)]]


HZ1_BOUNDS = _extract_geojson_bounds(health_zone_geojson)

# Enhanced layout with adaptive parameter section
app.layout = html.Div([
    html.Div([
        # Header
        html.Div([
            html.H2("🗺️ Modeling food access: an agent-based model for evaluating interventions for Health Zone 1, Jacksonville, FL", style={'margin': '0'}),
            # html.P([
            #     "Health Zone 1, Jacksonville, FL | Adaptive Parameter Interface",
            #     html.Span(className="live-indicator")
            # ], style={'margin': '8px 0 0 0', 'opacity': '0.9'})
        ], style={
            'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            'color': 'white',
            'padding': '40px 30px',
            'textAlign': 'center',
            'position': 'relative',
            'overflow': 'hidden'
        }),
        
        # Navigation tabs
        html.Div([
            html.Ul([
                html.Li(html.A("📊 Baseline (Current)", href="#", id="tab-baseline", className="nav-link active"), className="nav-item"),
                html.Li(html.A("🏪 Scenario 1: New Grocery Store", href="#", id="tab-scenario1", className="nav-link"), className="nav-item"),
                html.Li(html.A("🏬 Scenario 2: Food Hub + Corner Stores", href="#", id="tab-scenario2", className="nav-link"), className="nav-item"),
                html.Li(html.A("🚚 Scenario 3: Mobile Pantries", href="#", id="tab-scenario3", className="nav-link"), className="nav-item"),
                html.Li(html.A("📦 Scenario 4: Subsidized Delivery", href="#", id="tab-scenario4", className="nav-link"), className="nav-item"),
                html.Li(html.A("⚖️ Compare All Scenarios", href="#", id="tab-comparison", className="nav-link"), className="nav-item"),
                html.Li(html.A("🔬 Sensitivity Analysis", href="#", id="tab-sensitivity", className="nav-link"), className="nav-item"),
            ], className="nav-tabs"),
        ]),
        
        # Store current scenario (default to baseline)
        dcc.Store(id="selected-scenario", data="baseline"),
        # Global picked locations store (always present in layout)
        dcc.Store(id="picked-pantry-locations", data=[]),
        dcc.Store(id="current-form-values", data={}),
        # Store for FINAL metrics - persists in browser even after page refresh!
        dcc.Store(id="final-metrics-store", data=None, storage_type='session'),
        dcc.Store(id="sa-results-store", data=None),
        dcc.Store(id="sa-running-store", data=False),
        html.Div(id="dummy-output-for-sliders", style={"display": "none"}),
        
        # Two-column layout with static inputs (always present)
        html.Div([
            # Left column - Static inputs with adaptive visibility
            html.Div([
                html.Div([
                    # Parameter content area that expands
                    html.Div([
                    html.Div(id="adaptive-parameter-section"),
                        html.Div(id="static-inputs-container"),
                        # Hidden div to store collected parameters
                        html.Div(id="collected-parameters", style={"display": "none"}),
                    ], style={"flex": "1", "overflowY": "auto", "paddingBottom": "10px"}),
                    
                    # All buttons - ALWAYS present at bottom, one row
                    html.Div([
                        html.Button("🚀 Start Simulation", id="start-btn", n_clicks=0,
                                   style={"background": "linear-gradient(135deg, #27ae60, #2ecc71)", "color": "white", "border": "none", "padding": "10px 20px", "borderRadius": "6px", "cursor": "pointer", "fontWeight": "500", "flex": "1"}),
                        html.Button("⏸️ Stop Simulation", id="stop-btn", n_clicks=0,
                                   style={"background": "linear-gradient(135deg, #e74c3c, #c0392b)", "color": "white", "border": "none", "padding": "10px 20px", "borderRadius": "6px", "cursor": "pointer", "fontWeight": "500", "flex": "1"}),
                        html.Button("🔄 Reset", id="reset-btn", n_clicks=0,
                                   style={"background": "linear-gradient(135deg, #f39c12, #e67e22)", "color": "white", "border": "none", "padding": "10px 20px", "borderRadius": "6px", "cursor": "pointer", "fontWeight": "500", "flex": "1"})
                    ], id="static-buttons-container", style={"display": "flex", "gap": "30px", "marginTop": "auto", "paddingTop": "25px", "paddingBottom": "20px", "alignItems": "stretch", "justifyContent": "space-evenly", "padding": "25px 20px 20px 20px"}),
                    
                ], className="card", style={"height": "600px", "display": "flex", "flexDirection": "column"}),
            ], style={"width": "50%", "paddingRight": "10px"}),
            
            # Right column - Enhanced Live Metrics with Two-Level Navigation
                        html.Div([
                        html.Div([
                    html.H4("📊 Live Metrics & Status", style={"margin": "0 0 15px 0", "color": "#2d3748", "fontWeight": "700", "fontSize": "1.5em"}),
                    
                    # Store for current selections
                    dcc.Store(id="selected-main-metric", data="primary"),
                    dcc.Store(id="selected-sub-metric", data="primary-main"),
                    
                    # Top-level navigation (right to left clickable tabs)
                        html.Div([
                        html.Div("Primary Metrics", id={"type": "metrics-main-tab", "index": "primary"}, 
                                className="metrics-main-tab", 
                                style={"padding": "8px 16px", "cursor": "pointer", "borderRadius": "6px", 
                                      "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", 
                                      "color": "white", "fontWeight": "500", "textAlign": "center", "fontSize": "13px"}),
                        html.Div("Live Charts", id={"type": "metrics-main-tab", "index": "charts"}, 
                                className="metrics-main-tab",
                                style={"padding": "8px 16px", "cursor": "pointer", "borderRadius": "6px", 
                                      "background": "#f7fafc", "color": "#4a5568", "fontWeight": "500", 
                                      "textAlign": "center", "border": "1px solid #e2e8f0", "fontSize": "13px"}),
                        html.Div("Live Results", id={"type": "metrics-main-tab", "index": "results"}, 
                                className="metrics-main-tab",
                                style={"padding": "8px 16px", "cursor": "pointer", "borderRadius": "6px", 
                                      "background": "#f7fafc", "color": "#4a5568", "fontWeight": "500", 
                                      "textAlign": "center", "border": "1px solid #e2e8f0", "fontSize": "13px"})
                    ], style={"display": "flex", "gap": "8px", "marginBottom": "15px", "justifyContent": "flex-end"}),
                    
                    # Content area with left navigation and main content
                        html.Div([
                        # Left sub-navigation (35% width)
                        html.Div([
                            html.Div("SECTIONS", style={"fontSize": "11px", "fontWeight": "600", "color": "#9ca3af", "marginBottom": "8px", "textTransform": "uppercase", "letterSpacing": "0.5px"}),
                            html.Div(id="metrics-sub-nav", children=[
                                # Default primary metrics sub-nav
                                html.Div("Primary Metrics", id={"type": "metrics-sub-item", "index": "primary-main"}, 
                                        style={"padding": "6px 10px", "cursor": "pointer", "borderRadius": "4px", 
                                              "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", 
                                              "color": "white", "fontSize": "12px", "marginBottom": "4px"}),
                                html.Div("Progress", id={"type": "metrics-sub-item", "index": "progress"}, 
                                        style={"padding": "6px 10px", "cursor": "pointer", "borderRadius": "4px", 
                                              "background": "#f9f9f9", "color": "#4a5568", "fontSize": "12px", "marginBottom": "4px"}),
                                html.Div("Real-time Counts", id={"type": "metrics-sub-item", "index": "counts"}, 
                                        style={"padding": "6px 10px", "cursor": "pointer", "borderRadius": "4px", 
                                              "background": "#f9f9f9", "color": "#4a5568", "fontSize": "12px", "marginBottom": "4px"}),
                                html.Div("Performance", id={"type": "metrics-sub-item", "index": "performance"}, 
                                        style={"padding": "6px 10px", "cursor": "pointer", "borderRadius": "4px", 
                                              "background": "#f9f9f9", "color": "#4a5568", "fontSize": "12px", "marginBottom": "4px"})
                            ])
                        ], style={"width": "35%", "paddingRight": "12px", "borderRight": "1px solid #e2e8f0"}),
                        
                        # Main content area (65% width)
                    html.Div([
                            # Status Display (always visible at top)
                            html.Div(id="status-display", className="status-display", style={"marginBottom": "10px"}),
                            
                            # Dynamic content area
                            html.Div(id="metrics-content", children=[
                                # Default: Primary Metrics content
                                html.Div(id="live-metrics", style={"height": "250px", "overflowY": "auto"})
                            ])
                        ], style={"width": "65%", "paddingLeft": "12px", "flex": "1"})
                    ], style={"display": "flex", "flex": "1", "minHeight": "0"})
                    
                ], className="card", style={"height": "600px", "display": "flex", "flexDirection": "column"}),
            ], style={"width": "50%", "paddingLeft": "10px"}),
        ], id="main-content-row", style={"display": "flex", "gap": "20px", "margin": "20px", "justifyContent": "space-between"}),
        
        # Sensitivity Analysis tab content (hidden when not selected)
        html.Div(id="sa-tab-content", style={"display": "none"}, children=[]),
        
        # Map (full width) - Fixed container to prevent jumping
        html.Div([
            html.H4("🗺️ Live Agent Visualization", style={"textAlign": "center", "color": "#2d3748", "margin": "0 0 20px 0", "fontWeight": "700", "fontSize": "1.5em"}),
            html.Div(
                id="map-container",
                style={
                    'width': '100%', 
                    'height': '700px', 
                    'borderRadius': '16px',
                    'position': 'relative',
                    'overflow': 'hidden',
                    'border': '2px solid #e2e8f0'
                },
                children=[
            dl.Map(
                id="live-map",
                        center=[30.3575, -81.6892],
                        zoom=12,
                        bounds=HZ1_BOUNDS,
                        preferCanvas=False,
                children=[dl.TileLayer()],
                        style={'width': '100%', 'height': '100%', 'borderRadius': '16px'}
                    )
                ]
            ),
            
            # Map legend
            html.Div([
                html.Div([
                    html.Span("🟢", style={"fontSize": "18px", "marginRight": "8px"}),
                    html.Span("Satisfied Consumers", style={"marginRight": "25px", "fontWeight": "500"}),
                    html.Span("🔴", style={"fontSize": "18px", "marginRight": "8px"}),
                    html.Span("Unsatisfied Consumers", style={"marginRight": "25px", "fontWeight": "500"}),
                    html.Span("🏪", style={"fontSize": "18px", "marginRight": "8px"}),
                    html.Span("Food Providers", style={"fontWeight": "500"})
                ], style={"textAlign": "center", "marginTop": "16px", "color": "#6c757d", "fontSize": "15px"})
            ])
        ], className="card"),
        
    ], className="main-container"),
    
    # Auto-update interval for REAL-TIME updates (optimized for performance)
    dcc.Interval(
        id='interval-component',
        interval=1000,  # 1 second - much more reasonable for UI performance
        n_intervals=0,
        disabled=False
    ),
])

# Ensure Dash knows about dynamic components used in callbacks (prevents "nonexistent" errors)
app.validation_layout = html.Div([
    app.layout,
    dcc.Store(id="picked-pantry-locations", data=[]),
    dcc.Store(id="current-form-values", data={})
])

# Tab selection callbacks
@app.callback(
    Output("selected-scenario", "data"),
    [Input("tab-baseline", "n_clicks"),
     Input("tab-scenario1", "n_clicks"), 
     Input("tab-scenario2", "n_clicks"), 
     Input("tab-scenario3", "n_clicks"),
     Input("tab-scenario4", "n_clicks"),
     Input("tab-comparison", "n_clicks"),
     Input("tab-sensitivity", "n_clicks")],
    State("selected-scenario", "data")
)
def select_scenario(n0, n1, n2, n3, n4, n5, n6, current):
    ctx = callback_context
    if not ctx.triggered:
        return current
    
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if triggered_id == "tab-baseline":
        return "baseline"
    elif triggered_id == "tab-scenario1":
        return "scenario1"
    elif triggered_id == "tab-scenario2":
        return "scenario2"
    elif triggered_id == "tab-scenario3":
        return "scenario3"
    elif triggered_id == "tab-scenario4":
        return "scenario4"
    elif triggered_id == "tab-comparison":
        return "comparison"
    elif triggered_id == "tab-sensitivity":
        return "sensitivity"
    return current

# Toggle SA tab visibility vs normal content
@app.callback(
    [Output("sa-tab-content", "style"),
     Output("map-container", "style"),
     Output("main-content-row", "style")],
    Input("selected-scenario", "data")
)
def toggle_sa_visibility(selected):
    map_style = {
        'width': '100%',
        'height': '700px',
        'borderRadius': '16px',
        'position': 'relative',
        'overflow': 'hidden',
        'border': '2px solid #e2e8f0'
    }
    row_style = {"display": "flex", "gap": "20px", "margin": "20px", "justifyContent": "space-between"}
    if selected == "sensitivity":
        sa_style = {"display": "block", "margin": "20px"}
        map_style["display"] = "none"
        row_style["display"] = "none"
    else:
        sa_style = {"display": "none"}
    return sa_style, map_style, row_style


# Tab highlighting
@app.callback(
    [Output("tab-baseline", "className"),
     Output("tab-scenario1", "className"), 
     Output("tab-scenario2", "className"),
     Output("tab-scenario3", "className"),
     Output("tab-scenario4", "className"),
     Output("tab-comparison", "className"),
     Output("tab-sensitivity", "className")],
    Input("selected-scenario", "data")
)
def update_tab_classes(selected):
    return [
        "nav-link active" if selected == "baseline" else "nav-link",
        "nav-link active" if selected == "scenario1" else "nav-link",
        "nav-link active" if selected == "scenario2" else "nav-link",
        "nav-link active" if selected == "scenario3" else "nav-link",
        "nav-link active" if selected == "scenario4" else "nav-link",
        "nav-link active" if selected == "comparison" else "nav-link",
        "nav-link active" if selected == "sensitivity" else "nav-link"
    ]

# ADAPTIVE PARAMETER SECTION - Changes based on simulation state
@app.callback(
    Output("adaptive-parameter-section", "children"),
    [Input("selected-scenario", "data"),
     Input("interval-component", "n_intervals")]
)
def update_adaptive_parameter_section(scenario, n_intervals):
    """Update parameter section - full parameters when not running, compact summary when running"""
    
    with simulation_lock:
        is_running = sim_state.sim_running
        params = sim_state.current_params
        current_day = sim_state.current_day
        max_days = sim_state.max_days
        snapshots = dict(sim_state.scenario_snapshots)
    
    if is_running:
        # RUNNING STATE: Show compact summary and focused controls
        scenario_names = {
            "baseline": "📊 Baseline (Current Situation)",
            "scenario1": "🏪 Grocery Store Scenario",
            "scenario2": "🏬 Food Hub Network Scenario", 
            "scenario3": "🚚 Mobile Pantries Scenario",
            "scenario4": "📦 Subsidized Delivery Scenario",
            "comparison": "⚖️ Compare All Scenarios"
        }
        
        # Extract config from params
        config_dict = params.get('config', {}) if params else {}
        
        return html.Div([
            html.H4("🎛️ Simulation Control", style={"margin": "0 0 25px 0", "color": "#2d3748", "fontWeight": "700", "fontSize": "1.5em"}),
            
            # Configuration Summary - Parameters Only (No Metrics)
            html.Div([
                html.H6(f"{scenario_names.get(scenario, 'Unknown')} Configuration", style={"color": "#4a5568", "fontWeight": "600", "marginBottom": "15px"}),
                html.P(f"👥 Consumers: {config_dict.get('num_consumers', 'N/A')}", style={"margin": "8px 0", "fontSize": "14px"}),
                html.P(f"⏰ Duration: {config_dict.get('simulation_days', 'N/A')} days", style={"margin": "8px 0", "fontSize": "14px"}),
                
                # Scenario-specific parameters
                *([
                    html.P(f"🏪 Grocery Store Capacity: {config_dict.get('grocery_store_capacity', 'N/A')}", style={"margin": "8px 0", "fontSize": "14px"}),
                ] if scenario == "scenario1" else [
                    html.P(f"🏬 Corner Stores: {config_dict.get('num_corner_stores', 'N/A')}", style={"margin": "8px 0", "fontSize": "14px"}),
                    html.P(f"🏪 Corner Store Capacity: {config_dict.get('corner_store_capacity', 'N/A')}", style={"margin": "8px 0", "fontSize": "14px"}),
                    html.P(f"🏭 Food Hub Capacity: {config_dict.get('food_hub_capacity', 'N/A')}", style={"margin": "8px 0", "fontSize": "14px"}),
                    html.P(f"📦 Food Hubs: {config_dict.get('num_food_hubs', 'N/A')}", style={"margin": "8px 0", "fontSize": "14px"}),
                ] if scenario == "scenario2" else [
                    html.P(f"🚚 Mobile Pantries: {config_dict.get('num_mobile_pantries', 'N/A')}", style={"margin": "8px 0", "fontSize": "14px"}),
                    html.P(f"📦 Pantry Capacity: {config_dict.get('mobile_pantry_capacity', 'N/A')}", style={"margin": "8px 0", "fontSize": "14px"}),
                    html.P(f"📅 Strategy: {config_dict.get('mobile_pantry_strategy', 'N/A')}", style={"margin": "8px 0", "fontSize": "14px"}),
                ] if scenario == "scenario3" else [
                    html.P(f"📦 Delivery Service: Active", style={"margin": "8px 0", "fontSize": "14px", "color": "#2d7a3e", "fontWeight": "600"}),
                    html.P(f"🚚 Delivery Area: 20 km radius", style={"margin": "8px 0", "fontSize": "14px"}),
                    html.P(f"📊 Capacity: 500 deliveries/day", style={"margin": "8px 0", "fontSize": "14px"}),
                    html.P(f"💰 Subsidy: Low=$0, Med=$2.98, High=$5.95", style={"margin": "8px 0", "fontSize": "14px"}),
                ] if scenario == "scenario4" else []),
                
                html.P(f"📅 Progress: Day {current_day}/{max_days} ({(current_day/max_days*100):.0f}%)" if max_days > 0 else f"📅 Progress: Day {current_day}", style={"margin": "8px 0", "fontSize": "14px", "fontWeight": "600", "color": "#805ad5"}),
            ], style={"background": "#f7fafc", "padding": "15px", "borderRadius": "8px", "border": "1px solid #e2e8f0"})
        ])
    
    else:
        if scenario == "comparison":
            available = [k for k in ["baseline", "scenario1", "scenario2", "scenario3", "scenario4"] if k in snapshots]
            return html.Div([
                html.H4("⚖️ Comparison Overview", style={"margin": "0 0 16px 0", "color": "#2d3748", "fontWeight": "700", "fontSize": "1.5em"}),
                html.P("This tab compares previously completed runs. No new simulation is launched here.", style={"margin": "0 0 10px 0", "color": "#4a5568"}),
                html.P(f"Saved runs: {len(available)}/5", style={"margin": "0", "fontWeight": "600", "color": "#2d3748"})
            ])
        # SETUP STATE: Show title for parameters
        return html.Div([
            html.H4("🎛️ Simulation Parameters", style={"margin": "0 0 25px 0", "color": "#2d3748", "fontWeight": "700", "fontSize": "1.5em"}),
        ])

# Update parameter layout based on scenario and simulation state
@app.callback(
    Output("static-inputs-container", "children"),
    [Input("selected-scenario", "data"),
     Input("interval-component", "n_intervals")],
    [State("static-inputs-container", "children")],
    prevent_initial_call=False
)
def update_parameter_layout(scenario, n_intervals, existing_children):
    """Update the parameter inputs based on selected scenario and simulation state"""
    from dash import callback_context
    from dash.exceptions import PreventUpdate
    
    with simulation_lock:
        is_running = sim_state.sim_running
        last_running_state = getattr(sim_state, 'last_parameter_running_state', None)
    
    # Get what triggered this callback
    ctx = callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
    
    # If simulation is running, hide inputs
    if is_running:
        with simulation_lock:
            sim_state.last_parameter_running_state = True
        return html.Div()

    if scenario == "comparison":
        with simulation_lock:
            snapshots = dict(sim_state.scenario_snapshots)
        rows = []
        label_map = {
            "baseline": "Baseline",
            "scenario1": "Scenario 1",
            "scenario2": "Scenario 2",
            "scenario3": "Scenario 3",
            "scenario4": "Scenario 4",
        }
        for key in ["baseline", "scenario1", "scenario2", "scenario3", "scenario4"]:
            snap = snapshots.get(key)
            if snap and snap.get("final_metrics"):
                fm = snap["final_metrics"]
                rows.append(html.Tr([
                    html.Td(label_map[key], style={"padding": "8px"}),
                    html.Td(f"{float(fm.get('satisfaction_rate', 0.0)):.1%}", style={"padding": "8px", "textAlign": "right"}),
                    html.Td(f"{float(fm.get('food_insecurity_rate', 0.0)):.1%}", style={"padding": "8px", "textAlign": "right"}),
                    html.Td(f"{float(fm.get('avg_travel_distance', 0.0)):.2f}", style={"padding": "8px", "textAlign": "right"}),
                ]))
            else:
                rows.append(html.Tr([
                    html.Td(label_map[key], style={"padding": "8px"}),
                    html.Td("Not run yet", style={"padding": "8px", "color": "#a0aec0"}),
                    html.Td("-", style={"padding": "8px", "textAlign": "right", "color": "#a0aec0"}),
                    html.Td("-", style={"padding": "8px", "textAlign": "right", "color": "#a0aec0"}),
                ]))
        return html.Div([
            html.H5("📊 Saved Scenario Runs", style={"marginBottom": "12px", "color": "#2d3748"}),
            html.Table([
                html.Thead(html.Tr([
                    html.Th("Scenario", style={"padding": "8px", "textAlign": "left"}),
                    html.Th("Satisfaction", style={"padding": "8px", "textAlign": "right"}),
                    html.Th("Insecurity", style={"padding": "8px", "textAlign": "right"}),
                    html.Th("Avg Dist (km)", style={"padding": "8px", "textAlign": "right"}),
                ], style={"background": "#edf2f7"})),
                html.Tbody(rows)
            ], style={"width": "100%", "borderCollapse": "collapse", "fontSize": "13px"}),
            html.P("Run Baseline and Scenarios 1-4 first, then open Results in this tab for comparison charts.",
                   style={"marginTop": "10px", "color": "#4a5568", "fontSize": "12px"})
        ], style={"background": "#f7fafc", "padding": "12px", "borderRadius": "8px", "border": "1px solid #e2e8f0"})

    # Check if simulation just stopped (running state changed from True to False)
    simulation_just_stopped = (last_running_state is True and not is_running)
    
    # Show inputs when simulation is not running
    # Only prevent updates on interval if simulation hasn't changed state and we have inputs
    if (triggered_id == "interval-component" and 
        not simulation_just_stopped and 
        existing_children and 
        not is_running):
        # Don't update on interval if we already have inputs showing
        raise PreventUpdate
    
    # Update running state tracking
    with simulation_lock:
        sim_state.last_parameter_running_state = False
    
    # Always show sectioned inputs when simulation is not running
    # Render ALL sections so all param inputs exist in DOM for parameter collection
    sections = get_sections_for_scenario(scenario or "scenario1")
    default_value = sections[0][0] if sections else None
    scen = scenario or "scenario1"
    content = html.Div([
        html.Div(
            id={"type": "param-block", "index": section_key},
            children=render_section_for_scenario(scen, section_key),
            style={"display": "block" if section_key == default_value else "none"}
        )
        for section_key, _ in sections
    ]) if sections else html.Div()
    
    return html.Div([
        # Left side - clickable list of sections (match metrics styling)
        html.Div([
            html.Div("PARAMETER SECTIONS", style={"fontSize": "11px", "fontWeight": "600", "color": "#9ca3af", "marginBottom": "8px", "textTransform": "uppercase", "letterSpacing": "0.5px"}),
            html.Div([
                html.Div(
                    label,
                    id={"type": "param-section-item", "index": key},
                    style={
                        "padding": "6px 10px",
                        "cursor": "pointer",
                        "borderRadius": "4px",
                        "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)" if key == default_value else "#f9f9f9",
                        "color": "white" if key == default_value else "#4a5568",
                        "fontSize": "12px",
                        "marginBottom": "4px",
                        "transition": "all 0.3s ease"
                    },
                    className="param-section-item"
                ) for key, label in sections  # Fixed: use sections directly, not options
            ]),
            # Hidden component to store selected value
            dcc.Store(id="param-section-nav", data=default_value)
        ], style={"width": "35%", "paddingRight": "15px"}),
        
        # Right side - parameter content
        html.Div([
            html.Div(
                id="param-section-container", 
                children=content
            )
        ], style={"width": "65%"})
    ], style={"display": "flex", "gap": "10px"})

# DISABLED: Simplified callback - not needed for basic inputs
# app.clientside_callback(
#     """
#     function(trigger) {
#         return "{}";
#     }
#     """,
#     Output("current-form-values", "data"),
#     [Input({"type": "param-section-item", "index": ALL}, "n_clicks")],
#     prevent_initial_call=True
# )

# Combined callback to handle both clicking on parameter section items and scenario changes
@app.callback(
    [Output("param-section-nav", "data"), 
     Output("param-section-container", "children")],
    [Input({"type": "param-section-item", "index": ALL}, "n_clicks"), 
     Input("selected-scenario", "data")],
    [State("param-section-nav", "data"),
     State("current-form-values", "data")],
    prevent_initial_call=True
)
def handle_section_and_scenario_changes(n_clicks_list, scenario, current_section, form_values):
    """Handle both clicking on parameter section items and scenario changes"""
    from dash.exceptions import PreventUpdate
    from dash import callback_context
    import json
    
    if not scenario:
        raise PreventUpdate
    
    # Parse current form values - form_values is already a dict from Store component
    current_values = {}
    if form_values and isinstance(form_values, dict):
        current_values = form_values
    elif form_values:
        try:
            current_values = json.loads(form_values) if isinstance(form_values, str) else {}
        except:
            current_values = {}
    
    # Get sections for current scenario
    sections = get_sections_for_scenario(scenario)
    if not sections:
        raise PreventUpdate
    
    # Find what triggered this callback
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    # Determine selected section
    selected_section = current_section
    
    # If a section item was clicked, only update selection highlight.
    # Do NOT re-render parameter components, otherwise Dash recreates inputs
    # and values can snap back to defaults.
    if "param-section-item" in trigger_id and any(n_clicks_list):
        selected_section = json.loads(trigger_id)["index"]
        return selected_section, dash.no_update
    
    # If scenario changed, use current section or default to first section
    elif "selected-scenario" in trigger_id:
        section_keys = [key for key, _ in sections]
        selected_section = current_section if current_section in section_keys else section_keys[0]
    
    # Scenario changed: render all sections but display only the selected section.
    # Keeping components mounted preserves values while switching sections.
    all_sections = get_sections_for_scenario(scenario)
    content = html.Div([
        html.Div(
            id={"type": "param-block", "index": section_key},
            children=render_section_for_scenario(scenario, section_key),
            style={"display": "block" if section_key == selected_section else "none"}
        )
        for section_key, _ in all_sections
    ])
    
    return selected_section, content

# DISABLED: Form value restore - not needed, values persist naturally in Dash
# app.clientside_callback(
#     """
#     function(children, form_values) {
#         return window.dash_clientside.no_update;
#     }
#     """,
#     Output("param-section-container", "style"),
#     [Input("param-section-container", "children"),
#      Input("current-form-values", "data")],
#     prevent_initial_call=False
# )

# Note: current-form-values.data is managed by the clientside callback above

# Separate callback to handle styling - this ensures the correct number of styles
@app.callback(
    Output({"type": "param-section-item", "index": ALL}, "style"),
    [Input("param-section-nav", "data")],
    [State("selected-scenario", "data")],
    prevent_initial_call=False
)
def update_param_section_styles(selected_section, scenario):
    """Update the styles for parameter section items"""
    from dash.exceptions import PreventUpdate
    
    if not scenario or not selected_section:
        raise PreventUpdate
    
    # Get sections for current scenario 
    sections = get_sections_for_scenario(scenario)
    if not sections:
        raise PreventUpdate
    
    # Generate dynamic styles for all sections (match metrics styling)
    styles = []
    for key, _ in sections:
        if key == selected_section:
            # Selected style with theme gradient (match metrics)
            style = {
                "padding": "6px 10px",
                "cursor": "pointer",
                "borderRadius": "4px",
                "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                "color": "white",
                "fontSize": "12px",
                "marginBottom": "4px",
                "transition": "all 0.3s ease"
            }
        else:
            # Unselected style (match metrics)
            style = {
                "padding": "6px 10px",
                "cursor": "pointer",
                "borderRadius": "4px",
                "background": "#f9f9f9",
                "color": "#4a5568",
                "fontSize": "12px",
                "marginBottom": "4px",
                "transition": "all 0.3s ease"
            }
        styles.append(style)
    
    return styles

# Toggle parameter section visibility (single visible section, values preserved)
@app.callback(
    Output({"type": "param-block", "index": ALL}, "style"),
    [Input("param-section-nav", "data")],
    [State("selected-scenario", "data")],
    prevent_initial_call=False
)
def update_param_block_visibility(selected_section, scenario):
    from dash.exceptions import PreventUpdate
    if not scenario or not selected_section:
        raise PreventUpdate
    sections = get_sections_for_scenario(scenario)
    if not sections:
        raise PreventUpdate
    return [
        {"display": "block"} if key == selected_section else {"display": "none"}
        for key, _ in sections
    ]

# Parameter collection: runs on interval to keep collected-parameters updated.
# Uses correct param-* IDs and keys to match build_config_from_inputs.
# Build param IDs - must match dashboard_config_builder expectations
_param_ids = [
    'param-num-consumers', 'param-simulation-days',
    'param-delivery-low', 'param-delivery-medium', 'param-delivery-high',
    'param-grocery-capacity', 'param-scenario1-store-region', 'param-food-hub-capacity', 'param-num-corner-stores',
    'param-corner-capacity', 'param-num-mobile-pantries', 'param-mobile-pantry-capacity',
    'param-pantry-strategy', 'param-delivery-capacity', 'param-base-fee',
    'param-distance-fee', 'param-delivery-area'
]
_param_defaults = {
    'param-num-consumers': 300, 'param-simulation-days': 30,
    'param-delivery-low': 0.08, 'param-delivery-medium': 0.20, 'param-delivery-high': 0.35,
    'param-grocery-capacity': 600, 'param-scenario1-store-region': 'optimal', 'param-food-hub-capacity': 300,
    'param-num-corner-stores': 6, 'param-corner-capacity': 60,
    'param-num-mobile-pantries': 2, 'param-mobile-pantry-capacity': 120,
    'param-pantry-strategy': 'fixed',
    'param-delivery-capacity': 500, 'param-base-fee': 2.0, 'param-distance-fee': 0.75,
    'param-delivery-area': 20.0
}

app.clientside_callback(
    """
    function(scenario, n, startClicks) {
        var params = {};
        var defaults = """ + json.dumps(_param_defaults) + """;
        var ids = """ + json.dumps(_param_ids) + """;
        for (var i = 0; i < ids.length; i++) {
            var id = ids[i];
            var el = document.getElementById(id);
            if (el) {
                // dcc.Input may render as the input element itself (with matching id),
                // while dcc.Dropdown renders a wrapper div containing an input.
                var inp = null;
                if (el.matches && el.matches('input, select, textarea')) {
                    inp = el;
                } else {
                    inp = el.querySelector('input, select, textarea');
                }

                // Prefer explicit value property when available.
                var rawValue = (inp && inp.value !== undefined) ? inp.value :
                               (el.value !== undefined ? el.value : undefined);

                if (rawValue !== '' && rawValue !== undefined && rawValue !== null) {
                    var v = rawValue;
                    // Keep known categorical params as strings.
                    if (id.includes('strategy') || id.includes('store-region')) {
                        params[id] = String(v);
                    } else {
                        params[id] = isNaN(Number(v)) ? v : Number(v);
                    }
                } else if (defaults[id] !== undefined) {
                    params[id] = defaults[id];
                }
            } else if (defaults[id] !== undefined) {
                params[id] = defaults[id];
            }
        }
        return JSON.stringify(params);
    }
    """,
    Output("collected-parameters", "children"),
    [Input("selected-scenario", "data"), Input("interval-component", "n_intervals"), Input("start-btn", "n_clicks")],
    prevent_initial_call=False
)

# Control visibility of buttons based on simulation state
@app.callback(
    Output("static-buttons-container", "style"),
    Input("interval-component", "n_intervals")
)
def control_ui_visibility(n_intervals):
    """Control visibility of buttons based on simulation state"""
    
    with simulation_lock:
        is_running = sim_state.sim_running
    
    if is_running:
        # RUNNING STATE: Show buttons
        buttons_style = {"textAlign": "center", "marginTop": "25px", "display": "block"}
    else:
        # SETUP STATE: Show buttons
        buttons_style = {"textAlign": "center", "display": "block"}
    
    return buttons_style



# INTERVAL CONTROL: Always enable interval to ensure UI updates reliably
@app.callback(
    Output("interval-component", "disabled"),
    [Input("start-btn", "n_clicks"),
     Input("stop-btn", "n_clicks"),
     Input("reset-btn", "n_clicks"),
     Input("selected-scenario", "data")],
    prevent_initial_call=False
)
def control_interval_updates(start_clicks, stop_clicks, reset_clicks, scenario):
    """Keep interval enabled; avoid self-disabling deadlock that prevents UI updates."""
    return False

# PERSIST METRICS TO BROWSER STORAGE: Updates every interval to preserve final metrics
@app.callback(
    Output("final-metrics-store", "data"),
    [Input("interval-component", "n_intervals"),
     Input("reset-btn", "n_clicks")],
    prevent_initial_call=False
)
def persist_metrics_to_store(n_intervals, reset_clicks):
    """Store latest metrics in browser storage so they survive page refreshes"""
    from dash import callback_context
    
    ctx = callback_context
    if ctx.triggered:
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        # Clear store on reset
        if trigger_id == 'reset-btn':
            print("🔄 Clearing final-metrics-store due to reset")
            return None
    
    # Get current simulation data
    simulation_data = sim_state.get_data() or []
    if not simulation_data:
        # No data yet, return None or existing store value will be kept
        return dash.no_update
    
    # Get the latest metrics
    latest = simulation_data[-1]
    
    # Only store if we have valid metrics
    if latest and all(k in latest for k in ('satisfaction_rate', 'food_insecurity_rate', 'avg_travel_distance')):
        with simulation_lock:
            is_running = sim_state.sim_running
            current_day = sim_state.current_day
            max_days = sim_state.max_days
            current_scenario = getattr(sim_state, 'current_scenario', 'Unknown')
            total_consumers = len(sim_state.current_model.consumers) if sim_state.current_model and hasattr(sim_state.current_model, 'consumers') else 0
        
        stored_metrics = {
            'satisfaction_rate': float(latest['satisfaction_rate']),
            'food_insecurity_rate': float(latest['food_insecurity_rate']),
            'avg_travel_distance': float(latest['avg_travel_distance']),
            'spatial_equity': float(latest.get('spatial_equity_index', 0.0)),
            'current_day': current_day,
            'max_days': max_days,
            'current_scenario': current_scenario,
            'total_consumers': total_consumers,
            'is_running': is_running,
            'timestamp': n_intervals  # For debugging
        }
        
        if not is_running:
            pass
        
        return stored_metrics
    
    return dash.no_update

# REAL-TIME UPDATES: All elements update together
@app.callback(
    [Output("live-map", "children"),
     Output("status-display", "children")],
    [Input("interval-component", "n_intervals")]
)
def update_all_live_elements(n_intervals):
    """Update ALL elements in real-time"""
    
    # Get current simulation status
    with simulation_lock:
        current_model = sim_state.current_model
        running = sim_state.sim_running
        day = sim_state.current_day
        status_msg = sim_state.status_message
        last_day = getattr(sim_state, 'last_map_day', -1)
        prev_running = getattr(sim_state, 'prev_running', None)
    
    # Update map logic: 
    # - Always update while running (ensures visible changes every step)
    # - Also update once after model creation (day == 0)
    # - Force one final update right after simulation stops
    # - Cache when not running to prevent unnecessary work
    model_id = id(current_model) if current_model else None
    last_model_id = getattr(sim_state, 'last_model_id', None)
    
    just_stopped = (prev_running is True and running is False)
    # Update map every interval while running OR when the day changes OR state changed
    should_update = (
        running or
        day != last_day or
        just_stopped or
        model_id != last_model_id or 
        not hasattr(sim_state, 'cached_map') or 
        sim_state.cached_map is None
    )
    
    if should_update:
        # Build fresh map layer when needed with error handling
        try:
            map_children = create_enhanced_map_view(current_model, running, day)
            
            with simulation_lock:
                sim_state.cached_map = map_children
                sim_state.last_map_day = day
                sim_state.last_model_id = model_id
        except Exception as e:
            print(f"⚠️ Error creating map view: {e}")
            # Fallback to basic map
            map_children = [
                dl.TileLayer(),
                dl.GeoJSON(
                    data=health_zone_geojson,
                    options={"interactive": False},
                    style={"fillColor": "#667eea", "weight": 3, "color": "#764ba2", "fillOpacity": 0.15, "pointerEvents": "none"}
                )
            ]
    else:
        with simulation_lock:
            map_children = sim_state.cached_map if hasattr(sim_state, 'cached_map') else None

    
    # Ensure map children is a valid list of layers (fallback to base tile and health zone)
    if not isinstance(map_children, list) or len(map_children) == 0:
        map_children = [
            dl.TileLayer(),
            dl.GeoJSON(
                data=health_zone_geojson,
                options={"interactive": False},
                style={"fillColor": "#667eea", "weight": 3, "color": "#764ba2", "fillOpacity": 0.15, "pointerEvents": "none"}
            )
        ]
    
    # Update status
    status_content = status_msg
    
    # Remember running state to detect transitions
    with simulation_lock:
        sim_state.prev_running = running
    return map_children, status_content

def create_enhanced_map_view(current_model, running, day):
    """Create enhanced map view with detailed agent popups"""
    
    # Always start with base layers
    map_children = [
        dl.TileLayer(),
        # Add health zone
        dl.GeoJSON(
            data=health_zone_geojson,
            options={"interactive": False},
            style={"fillColor": "#667eea", "weight": 3, "color": "#764ba2", "fillOpacity": 0.15, "pointerEvents": "none"}
        )
    ]
    
    # Add simulation elements if model exists
    if current_model and hasattr(current_model, 'consumers'):
        try:
            # PERFORMANCE FIX: Only render a sample of consumers to avoid freezing the UI
            # With 300+ agents, rendering all markers with popups takes 5-10 seconds per frame
            max_consumers_to_show = 100
            total_consumers = len(current_model.consumers)
            
            # CONSISTENT SAMPLING: Show the SAME households every step (not random each time)
            # Use deterministic selection based on household ID so they stay visible across days
            if total_consumers > 0 and total_consumers <= max_consumers_to_show:
                # Show all consumers if total is under limit
                consumers_to_render = current_model.consumers
            else:
                # Select first N consumers for consistent display
                # Sort by unique_id to ensure deterministic selection
                sorted_consumers = sorted(current_model.consumers, key=lambda c: c.unique_id)
                consumers_to_render = sorted_consumers[:max_consumers_to_show]
            
            # Add a label showing sampling info
            if total_consumers > max_consumers_to_show:
                sample_label = dl.Marker(
                    position=[30.35, -81.70],
                    icon={
                        "iconUrl": "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-grey.png",
                        "iconSize": [20, 33],
                        "iconAnchor": [10, 33]
                    },
                    children=[dl.Tooltip(f"📊 Showing {len(consumers_to_render)} of {total_consumers} households")]
                )
                map_children.append(sample_label)
            
            # Add sampled consumers with minimal logging for performance
            for i, consumer in enumerate(consumers_to_render):
                lat, lon = consumer.geometry.y, consumer.geometry.x
                satisfied = getattr(consumer, 'satisfied_today', False)
                
                # Use CircleMarker with DYNAMIC colors that change based on satisfaction
                if satisfied:
                    fill_color = "#28a745"  # Bootstrap success green
                    border_color = "#1e7e34"  # Darker green border
                    color_name = "SATISFIED"
                    emoji = "🟢"
                else:
                    fill_color = "#dc3545"  # Bootstrap danger red  
                    border_color = "#bd2130"  # Darker red border
                    color_name = "UNSATISFIED"
                    emoji = "🔴"
                
                # CircleMarker with FORCED update using unique key based on satisfaction state
                # This ensures Dash Leaflet recreates the marker when satisfaction changes
                marker_key = f"consumer-{consumer.unique_id}-{day}-{satisfied}"
                # Build rich popup content for the HOUSEHOLD
                last_event = consumer.shopping_history[-1] if getattr(consumer, 'shopping_history', []) else None
                last_event_text = (
                    f"Day {last_event.get('day')}, {last_event.get('provider_type')} (id {last_event.get('provider_id')}), {last_event.get('distance', 0):.2f} km"
                ) if last_event else "None"
                
                # Get NEW household characteristics
                income_value = getattr(getattr(consumer, 'income', None), 'value', 'N/A')
                household_size = getattr(consumer, 'household_size', 'N/A')
                vehicle_available = getattr(consumer, 'vehicle_available', False)
                race = getattr(consumer, 'race', 'N/A')
                snap_eligible = getattr(consumer, 'snap_eligible', False)
                annual_income = getattr(consumer, 'annual_income', 0)
                census_tract = getattr(consumer, 'census_tract', 'N/A')
                
                # Economic parameters
                weekly_budget = getattr(consumer, 'weekly_budget', 0)
                mean_basket = getattr(consumer, 'mean_basket_size', 0)
                
                # Choice model parameters
                days_since_last = getattr(consumer, 'days_since_last_shop', 0)
                go_shop_threshold = getattr(consumer, 'go_shop_threshold', 0)
                
                # Simplified popup for performance
                consumer_popup = dl.Popup(html.Div([
                    html.B(f"🏠 HH {consumer.unique_id} ({income_value})"), html.Br(),
                    html.Span(f"👥 {household_size} | 🚗 {'Car' if vehicle_available else 'No car'}"), html.Br(),
                    html.Span(f"💰 ${annual_income:,.0f}/yr | ${weekly_budget:.0f}/wk"), html.Br(),
                    html.Span(f"🛒 ${mean_basket:.0f} | ~{go_shop_threshold:.0f}d"), html.Br(),
                    html.Span(f"{'✅ Satisfied' if satisfied else '❌ Unsatisfied'} | {getattr(consumer, 'food_supply', 0)}d supply"), html.Br(),
                    html.Span(f"Travel: {getattr(consumer, 'travel_distance', 0):.1f} km"),
                ], style={"fontSize": "12px", "maxWidth": "250px"}))
                
                # Use DivMarker to render a small circle with full Popup support
                marker = dl.DivMarker(
                    id=marker_key,
                    position=[lat, lon],
                    iconOptions={
                        "className": "",
                        "html": f'<div style="width:12px;height:12px;border-radius:50%;background:{fill_color};border:2px solid {border_color};"></div>'
                    },
                    children=[
                        dl.Tooltip(f"{emoji} Consumer {consumer.unique_id} - {color_name}"),
                        consumer_popup
                    ]
                )
                map_children.append(marker)
        except Exception as e:
            print(f"⚠️ Error rendering consumers: {e}")
            # Continue without consumer markers
        
    
    # Add providers with distinct symbols and popups
    if current_model and hasattr(current_model, 'food_providers') and current_model.food_providers:
        # Check if this is an intervention scenario (has new stores)
        has_new_store = hasattr(current_model, 'new_store') and current_model.new_store is not None
        new_store_id = current_model.new_store.unique_id if has_new_store else None
        
        has_new_hub = hasattr(current_model, 'new_food_hub') and current_model.new_food_hub is not None
        new_hub_id = current_model.new_food_hub.unique_id if has_new_hub else None
        
        new_corner_store_ids = set()
        if hasattr(current_model, 'new_corner_stores'):
            new_corner_store_ids = set(s.unique_id for s in current_model.new_corner_stores)
        
        new_pantry_ids = set()
        if hasattr(current_model, 'mobile_pantries'):
            new_pantry_ids = set(p.unique_id for p in current_model.mobile_pantries)
        
        for provider in current_model.food_providers:
            ptype = getattr(provider, 'provider_type', None)
            ptype_val = getattr(ptype, 'value', None) if ptype is not None else None
            if not ptype_val:
                ptype_val = getattr(provider, 'store_type', 'provider')
            ptype_val = str(ptype_val).lower()
            
            # Check if this is a NEW provider (intervention)
            is_new = (provider.unique_id == new_store_id or 
                     provider.unique_id == new_hub_id or
                     provider.unique_id in new_corner_store_ids or
                     provider.unique_id in new_pantry_ids)
            
            # Choose icon by provider type
            if ptype_val in ("food_hub", "foodhub", "hub"):
                label = "🆕 NEW Food Hub" if is_new else "Food Hub"
                icon_bg = "#6f42c1"
                icon_emoji = "🏬"
            elif ptype_val in ("corner_store", "corner", "cornerstore"):
                label = "🆕 NEW Corner Store" if is_new else "Corner Store"
                icon_bg = "#fd7e14"
                icon_emoji = "🏪"
            elif ptype_val in ("mobile_pantry", "mobile", "pantry"):
                label = "🆕 NEW Mobile Pantry" if is_new else "Mobile Pantry"
                icon_bg = "#20c997"
                icon_emoji = "🥫"
            elif ptype_val in ("delivery_service", "delivery"):
                label = "Delivery Service"
                icon_bg = "#0d6efd"
                icon_emoji = "🚚"
            else:
                label = "🆕 NEW Grocery Store" if is_new else "Grocery Store (Existing)"
                icon_bg = "#dc3545" if is_new else "#198754"
                icon_emoji = "🛒"

            is_pantry = ptype_val in ("mobile_pantry", "mobile", "pantry")
            revenue_line = "Daily revenue: N/A (free pantry service)" if is_pantry else f"Daily revenue: ${getattr(provider, 'daily_revenue', 0):.2f}"
            
            provider_popup = dl.Popup([
                html.B(label), html.Br(),
                html.Ul([
                    html.Li(f"Capacity: {getattr(provider, 'capacity', 'N/A')}") ,
                    html.Li(f"Current inventory: {getattr(provider, 'current_inventory', 'N/A')}") ,
                    html.Li(f"Operating hours: {getattr(provider, 'operating_hours', ('N/A','N/A'))}") ,
                    html.Li(f"Service radius: {getattr(provider, 'service_area_radius', 'N/A')} km"),
                    html.Li(f"Customers served today: {getattr(provider, 'customers_served_today', 'N/A')}") ,
                    html.Li(f"Active today: {getattr(provider, 'active_today', 'N/A') if hasattr(provider, 'active_today') else 'N/A'}"),
                    html.Li(revenue_line)
                ], style={"margin": "6px 0"})
            ])
            
            store_marker = dl.DivMarker(
                position=[provider.geometry.y, provider.geometry.x],
                iconOptions={
                    "className": "",
                    "html": (
                        f'<div style="width:24px;height:24px;border-radius:50%;'
                        f'background:{icon_bg};border:2px solid white;display:flex;'
                        f'align-items:center;justify-content:center;font-size:13px;'
                        f'box-shadow:0 1px 4px rgba(0,0,0,0.35);">{icon_emoji}</div>'
                    )
                },
                children=[dl.Tooltip(f"{icon_emoji} {label}"), provider_popup]
            )
            map_children.append(store_marker)
    
    return map_children

def get_live_metrics_data(stored_metrics=None):
    """Get live metrics data shared across all metric functions.
    Prefer model-produced daily metrics when available to avoid partial-day bias.
    Fallback to stored metrics from browser storage if in-memory data is lost.
    Final fallback to real-time computation scoped to 'needed to shop' households.
    
    Args:
        stored_metrics: Metrics from browser storage (survives page refreshes)
    """
    simulation_data = sim_state.get_data() or []
    latest = simulation_data[-1] if simulation_data else {}

    # Get additional state information
    with simulation_lock:
        current_day = sim_state.current_day
        max_days = sim_state.max_days
        current_scenario = getattr(sim_state, 'current_scenario', 'Unknown')
        current_model = sim_state.current_model
        is_running = sim_state.sim_running

    # PRIORITY 1: If simulation is complete and we have stored metrics from browser storage, use them
    # This SURVIVES page refreshes and dashboard restarts!
    if not is_running and not latest and stored_metrics and all(k in stored_metrics for k in ('satisfaction_rate', 'food_insecurity_rate', 'avg_travel_distance')):
        return {
            'simulation_data': simulation_data,
            'current_day': stored_metrics.get('current_day', current_day),
            'max_days': stored_metrics.get('max_days', max_days),
            'current_scenario': stored_metrics.get('current_scenario', current_scenario),
            'real_time_satisfied': int(round(stored_metrics['satisfaction_rate'] * stored_metrics.get('total_consumers', 0))),
            'total_consumers': stored_metrics.get('total_consumers', 0),
            'real_time_satisfaction_rate': stored_metrics['satisfaction_rate'],
            'real_time_food_insecurity_rate': stored_metrics['food_insecurity_rate'],
            'real_time_avg_travel_distance': stored_metrics['avg_travel_distance'],
            'spatial_equity': stored_metrics.get('spatial_equity', 0.0),
        }

    # PRIORITY 2: If simulation is complete (not running) and we have in-memory data, use it
    # This is the normal case when simulation just finished
    if not is_running and latest and all(k in latest for k in ('satisfaction_rate', 'food_insecurity_rate', 'avg_travel_distance')):
        satisfaction_rate = float(latest['satisfaction_rate'])
        food_insecurity_rate = float(latest['food_insecurity_rate'])
        avg_travel_distance = float(latest['avg_travel_distance'])
        spatial_equity = float(latest.get('spatial_equity_index', 0.0))
        total_consumers = len(getattr(current_model, 'consumers', [])) if current_model else 0
        real_time_satisfied = int(round(satisfaction_rate * total_consumers)) if total_consumers else 0
        return {
            'simulation_data': simulation_data,
            'current_day': current_day,
            'max_days': max_days,
            'current_scenario': current_scenario,
            'real_time_satisfied': real_time_satisfied,
            'total_consumers': total_consumers,
            'real_time_satisfaction_rate': satisfaction_rate,
            'real_time_food_insecurity_rate': food_insecurity_rate,
            'real_time_avg_travel_distance': avg_travel_distance,
            'spatial_equity': spatial_equity,
        }
    
    # If we already have model-collected daily metrics for current day (while running), use them
    if is_running and latest and all(k in latest for k in ('satisfaction_rate', 'food_insecurity_rate', 'avg_travel_distance')):
        satisfaction_rate = float(latest['satisfaction_rate'])
        food_insecurity_rate = float(latest['food_insecurity_rate'])
        avg_travel_distance = float(latest['avg_travel_distance'])
        spatial_equity = float(latest.get('spatial_equity_index', 0.0))
        total_consumers = len(getattr(current_model, 'consumers', [])) if current_model else 0
        real_time_satisfied = int(round(satisfaction_rate * total_consumers)) if total_consumers else 0
        return {
            'simulation_data': simulation_data,
            'current_day': current_day,
            'max_days': max_days,
            'current_scenario': current_scenario,
            'real_time_satisfied': real_time_satisfied,
            'total_consumers': total_consumers,
            'real_time_satisfaction_rate': satisfaction_rate,
            'real_time_food_insecurity_rate': food_insecurity_rate,
            'real_time_avg_travel_distance': avg_travel_distance,
            'spatial_equity': spatial_equity,
        }

    # Fallback: compute real-time metrics from current model state
    satisfied_needed = 0
    needed_count = 0
    total_consumers = 0
    total_travel_distance = 0.0

    if current_model and hasattr(current_model, 'consumers'):
        total_consumers = len(current_model.consumers)
        for consumer in current_model.consumers:
            needed = getattr(consumer, 'needed_to_shop_today', False)
            if needed:
                needed_count += 1
                if getattr(consumer, 'satisfied_today', False):
                    satisfied_needed += 1
            total_travel_distance += float(getattr(consumer, 'travel_distance', 0.0))

    # Rates scoped to those who needed to shop today to avoid rising cumulative bias
    real_time_satisfaction_rate = (satisfied_needed / needed_count) if needed_count > 0 else 0.0
    real_time_food_insecurity_rate = ((needed_count - satisfied_needed) / needed_count) if needed_count > 0 else 0.0
    # Average travel distance across all consumers who traveled today
    real_time_avg_travel_distance = 0.0
    if current_model and getattr(current_model, 'consumers', None):
        travelers = [c for c in current_model.consumers if getattr(c, 'travel_distance', 0.0) > 0]
        if travelers:
            real_time_avg_travel_distance = sum(c.travel_distance for c in travelers) / len(travelers)
    spatial_equity = latest.get('spatial_equity_index', real_time_satisfaction_rate) if latest else real_time_satisfaction_rate

    return {
        'simulation_data': simulation_data,
        'current_day': current_day,
        'max_days': max_days,
        'current_scenario': current_scenario,
        'real_time_satisfied': satisfied_needed,
        'total_consumers': total_consumers,
        'real_time_satisfaction_rate': real_time_satisfaction_rate,
        'real_time_food_insecurity_rate': real_time_food_insecurity_rate,
        'real_time_avg_travel_distance': real_time_avg_travel_distance,
        'spatial_equity': spatial_equity
    }

def create_primary_metrics_only(stored_metrics=None):
    """Create ONLY primary metrics content"""
    data = get_live_metrics_data(stored_metrics)
    
    return html.Div([
        html.H5("📊 Primary Metrics", style={"color": "#2d3748", "fontWeight": "700", "marginBottom": "15px", "fontSize": "1.2em"}),
                html.Div([
                    html.Div([
                html.H3(f"{data['real_time_satisfaction_rate']:.1%}", className="metric-value", style={"color": "#28a745"}),
                html.P("🟢 Real-Time Satisfaction", className="metric-label")
            ], className="metric-card"),
                    
                    html.Div([
                html.H3(f"{data['real_time_food_insecurity_rate']:.1%}", className="metric-value", style={"color": "#dc3545"}),
                html.P("🔴 Food Insecurity Rate", className="metric-label")
            ], className="metric-card"),
                    
                    html.Div([
                html.H3(f"{data['real_time_avg_travel_distance']:.2f} km", className="metric-value", style={"color": "#007bff"}),
                html.P("🚗 Avg Travel Distance", className="metric-label")
            ], className="metric-card"),
                    
                    html.Div([
                html.H3(f"{data['spatial_equity']:.3f}", className="metric-value", style={"color": "#6f42c1"}),
                html.P("⚖️ Spatial Equity Index", className="metric-label")
            ], className="metric-card"),
        ], style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "12px", "marginBottom": "20px"}),
        
        # Additional Key Statistics
        html.H6("📈 Key Statistics", style={"color": "#2d3748", "fontWeight": "600", "marginBottom": "10px", "fontSize": "1.1em"}),
                    html.Div([
            html.Div([
                html.P(f"Total Population: {data['total_consumers']}", style={"margin": "0", "color": "#4a5568", "fontSize": "14px"}),
                html.P(f"Satisfied Today: {data['real_time_satisfied']}", style={"margin": "0", "color": "#28a745", "fontSize": "14px"}),
                html.P(f"Unsatisfied Today: {data['total_consumers'] - data['real_time_satisfied']}", style={"margin": "0", "color": "#dc3545", "fontSize": "14px"}),
            ], style={"background": "#f8f9fa", "padding": "10px", "borderRadius": "6px", "border": "1px solid #e9ecef"}),
        ], style={"marginBottom": "20px"}),
        
        # Current Status
        html.H6("🎯 Current Status", style={"color": "#2d3748", "fontWeight": "600", "marginBottom": "10px", "fontSize": "1.1em"}),
                    html.Div([
            html.P(f"Scenario: {data['current_scenario']}", style={"margin": "0 0 5px 0", "color": "#4a5568", "fontSize": "14px"}),
            html.P(f"Day: {data['current_day']} of {data['max_days']}", style={"margin": "0 0 5px 0", "color": "#4a5568", "fontSize": "14px"}),
            html.P(f"Data Points Collected: {len(data['simulation_data'])}", style={"margin": "0", "color": "#4a5568", "fontSize": "14px"}),
        ], style={"background": "#f8f9fa", "padding": "10px", "borderRadius": "6px", "border": "1px solid #e9ecef"})
    ])

def create_progress_metrics_only(stored_metrics=None):
    """Create ONLY progress metrics content"""
    data = get_live_metrics_data(stored_metrics)
    
    return html.Div([
        html.H5("⏱️ Simulation Progress", style={"color": "#2d3748", "fontWeight": "700", "marginBottom": "15px", "fontSize": "1.2em"}),
        html.Div([
            html.Div([
                html.H3(f"Day {data['current_day']}", className="metric-value", style={"color": "#fd7e14"}),
                html.P("📅 Current Day", className="metric-label")
            ], className="metric-card"),
            
                html.Div([
                html.H3(f"{data['max_days']}", className="metric-value", style={"color": "#6c757d"}),
                html.P("🏁 Total Days", className="metric-label")
            ], className="metric-card"),
                
                html.Div([
                html.H3(f"{(data['current_day']/data['max_days']*100):.0f}%" if data['max_days'] > 0 else "0%", className="metric-value", style={"color": "#20c997"}),
                html.P("📈 Progress", className="metric-label")
            ], className="metric-card"),
            
                    html.Div([
                html.H3(f"{data['current_scenario'].title()}", className="metric-value", style={"color": "#e83e8c", "fontSize": "1.2em"}),
                html.P("🎯 Scenario", className="metric-label")
            ], className="metric-card"),
        ], style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "12px", "marginBottom": "20px"}),
        
        # Timeline Information
        html.H6("📆 Timeline Details", style={"color": "#2d3748", "fontWeight": "600", "marginBottom": "10px", "fontSize": "1.1em"}),
                    html.Div([
            html.P(f"Days Completed: {data['current_day']}", style={"margin": "0 0 5px 0", "color": "#4a5568", "fontSize": "14px"}),
            html.P(f"Days Remaining: {max(0, data['max_days'] - data['current_day'])}", style={"margin": "0 0 5px 0", "color": "#4a5568", "fontSize": "14px"}),
            html.P(f"Completion Rate: {(data['current_day']/data['max_days']*100):.1f}%" if data['max_days'] > 0 else "0%", style={"margin": "0 0 5px 0", "color": "#4a5568", "fontSize": "14px"}),
            html.P(f"Total Data Points: {len(data['simulation_data'])}", style={"margin": "0", "color": "#4a5568", "fontSize": "14px"}),
        ], style={"background": "#f8f9fa", "padding": "10px", "borderRadius": "6px", "border": "1px solid #e9ecef", "marginBottom": "20px"}),
        
        # Progress Bar Visualization
        html.H6("📊 Progress Visualization", style={"color": "#2d3748", "fontWeight": "600", "marginBottom": "10px", "fontSize": "1.1em"}),
                    html.Div([
            html.Div([
                html.Div(
                    style={
                        "width": f"{(data['current_day']/data['max_days']*100):.1f}%" if data['max_days'] > 0 else "0%",
                        "height": "20px",
                        "background": "linear-gradient(90deg, #28a745 0%, #20c997 100%)",
                        "borderRadius": "10px",
                        "transition": "width 0.5s ease"
                    }
                )
            ], style={
                "width": "100%",
                "height": "20px",
                "background": "#e9ecef",
                "borderRadius": "10px",
                "marginBottom": "10px"
            }),
            html.P(f"Progress: {(data['current_day']/data['max_days']*100):.1f}% Complete" if data['max_days'] > 0 else "0% Complete", 
                  style={"margin": "0", "textAlign": "center", "color": "#4a5568", "fontSize": "14px"})
        ], style={"background": "#f8f9fa", "padding": "15px", "borderRadius": "6px", "border": "1px solid #e9ecef"})
    ])

def create_counts_metrics_only(stored_metrics=None):
    """Create ONLY counts metrics content"""
    data = get_live_metrics_data(stored_metrics)
    
    return html.Div([
        html.H5("👥 Real-Time Counts", style={"color": "#2d3748", "fontWeight": "700", "marginBottom": "15px", "fontSize": "1.2em"}),
                    html.Div([
            html.Div([
                html.H3(f"{data['real_time_satisfied']}", className="metric-value", style={"color": "#28a745"}),
                html.P("😊 Satisfied Consumers", className="metric-label")
            ], className="metric-card"),
                    
                    html.Div([
                html.H3(f"{data['total_consumers'] - data['real_time_satisfied']}", className="metric-value", style={"color": "#dc3545"}),
                html.P("😞 Unsatisfied Consumers", className="metric-label")
            ], className="metric-card"),
            
            html.Div([
                html.H3(f"{data['total_consumers']}", className="metric-value", style={"color": "#17a2b8"}),
                html.P("👥 Total Consumers", className="metric-label")
            ], className="metric-card"),
            
            html.Div([
                html.H3(f"{len(data['simulation_data'])}", className="metric-value", style={"color": "#ffc107"}),
                html.P("📊 Data Points", className="metric-label")
            ], className="metric-card"),
        ], style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "12px"})
    ])

def create_performance_metrics_only(stored_metrics=None):
    """Create ONLY performance metrics content"""
    data = get_live_metrics_data(stored_metrics)
    
    return html.Div([
        html.H5("⚡ Performance Statistics", style={"color": "#2d3748", "fontWeight": "700", "marginBottom": "15px", "fontSize": "1.2em"}),
        html.Div([
            html.Div([
                html.H3("Fast", className="metric-value", style={"color": "#28a745"}),
                html.P("💾 System Performance", className="metric-label")
            ], className="metric-card"),
            
            html.Div([
                html.H3("Stable", className="metric-value", style={"color": "#007bff"}),
                html.P("🔄 Memory Usage", className="metric-label")
            ], className="metric-card"),
            
            html.Div([
                html.H3("Optimized", className="metric-value", style={"color": "#6f42c1"}),
                html.P("⚡ Processing Speed", className="metric-label")
            ], className="metric-card"),
            
            html.Div([
                html.H3("Efficient", className="metric-value", style={"color": "#ffc107"}),
                html.P("📊 Data Flow", className="metric-label")
            ], className="metric-card"),
        ], style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "12px"})
    ])

def create_beautiful_metrics_cards():
    """Create comprehensive metrics cards with ALL simulation metrics"""
    
    # Historical data may be empty at the beginning; do NOT early-return.
    # We compute real-time metrics directly from the current model state below.
    simulation_data = sim_state.get_data() or []
    
    latest = simulation_data[-1] if simulation_data else {}
    
    # Get additional state information
    with simulation_lock:
        current_day = sim_state.current_day
        max_days = sim_state.max_days
        current_scenario = getattr(sim_state, 'current_scenario', 'Unknown')
        current_model = sim_state.current_model
    
    # Calculate ALL metrics in real-time from current model
    real_time_satisfied = 0
    total_consumers = 0
    total_travel_distance = 0
    food_insecure_count = 0
    
    if current_model and hasattr(current_model, 'consumers'):
        total_consumers = len(current_model.consumers)
        
        for consumer in current_model.consumers:
            # Real-time satisfaction
            satisfied = getattr(consumer, 'satisfied_today', False)
            if satisfied:
                real_time_satisfied += 1
            
            # Real-time food insecurity (opposite of satisfaction)
            if not satisfied:
                food_insecure_count += 1
            
            # Real-time travel distance (if available)
            travel_distance = getattr(consumer, 'last_travel_distance', 0)
            total_travel_distance += travel_distance
    
    # Calculate real-time rates
    real_time_satisfaction_rate = real_time_satisfied / total_consumers if total_consumers > 0 else 0
    real_time_food_insecurity_rate = food_insecure_count / total_consumers if total_consumers > 0 else 0
    real_time_avg_travel_distance = total_travel_distance / total_consumers if total_consumers > 0 else 0
    
    # Spatial equity index - use from simulation data if available, otherwise calculate basic metric
    spatial_equity = latest.get('spatial_equity_index', real_time_satisfaction_rate) if latest else real_time_satisfaction_rate
    
    return html.Div([
        # Primary Metrics (Top Row)
        html.H5("📊 Primary Metrics", style={"color": "#2d3748", "fontWeight": "700", "marginBottom": "15px", "fontSize": "1.2em"}),
        html.Div([
            html.Div([
                html.H3(f"{real_time_satisfaction_rate:.1%}", className="metric-value", style={"color": "#28a745"}),
                html.P("🟢 Real-Time Satisfaction", className="metric-label")
            ], className="metric-card"),
            
            html.Div([
                html.H3(f"{real_time_food_insecurity_rate:.1%}", className="metric-value", style={"color": "#dc3545"}),
                html.P("🔴 Food Insecurity Rate", className="metric-label")
            ], className="metric-card"),
            
            html.Div([
                html.H3(f"{real_time_avg_travel_distance:.2f} km", className="metric-value", style={"color": "#007bff"}),
                html.P("🚗 Avg Travel Distance", className="metric-label")
            ], className="metric-card"),
            
            html.Div([
                html.H3(f"{spatial_equity:.3f}", className="metric-value", style={"color": "#6f42c1"}),
                html.P("⚖️ Spatial Equity Index", className="metric-label")
            ], className="metric-card"),
        ], style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "12px", "marginBottom": "25px"}),
        
        # Simulation Progress (Second Row)
        html.H5("⏱️ Simulation Progress", style={"color": "#2d3748", "fontWeight": "700", "marginBottom": "15px", "fontSize": "1.2em"}),
                    html.Div([
            html.Div([
                html.H3(f"Day {current_day}", className="metric-value", style={"color": "#fd7e14"}),
                html.P("📅 Current Day", className="metric-label")
            ], className="metric-card"),
            
            html.Div([
                html.H3(f"{max_days}", className="metric-value", style={"color": "#6c757d"}),
                html.P("🏁 Total Days", className="metric-label")
            ], className="metric-card"),
            
            html.Div([
                html.H3(f"{(current_day/max_days*100):.0f}%" if max_days > 0 else "0%", className="metric-value", style={"color": "#20c997"}),
                html.P("📈 Progress", className="metric-label")
            ], className="metric-card"),
            
            html.Div([
                html.H3(f"{current_scenario.title()}", className="metric-value", style={"color": "#e83e8c", "fontSize": "1.2em"}),
                html.P("🎯 Scenario", className="metric-label")
            ], className="metric-card"),
        ], style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "12px", "marginBottom": "25px"}),
        
        # Real-Time Counts (Third Row)
        html.H5("👥 Real-Time Counts", style={"color": "#2d3748", "fontWeight": "700", "marginBottom": "15px", "fontSize": "1.2em"}),
        html.Div([
            html.Div([
                html.H3(f"{real_time_satisfied}", className="metric-value", style={"color": "#28a745"}),
                html.P("😊 Satisfied Consumers", className="metric-label")
            ], className="metric-card"),
            
            html.Div([
                html.H3(f"{total_consumers - real_time_satisfied}", className="metric-value", style={"color": "#dc3545"}),
                html.P("😞 Unsatisfied Consumers", className="metric-label")
            ], className="metric-card"),
            
            html.Div([
                html.H3(f"{total_consumers}", className="metric-value", style={"color": "#17a2b8"}),
                html.P("👥 Total Consumers", className="metric-label")
            ], className="metric-card"),
            
            html.Div([
                html.H3(f"{len(simulation_data)}", className="metric-value", style={"color": "#ffc107"}),
                html.P("📊 Data Points", className="metric-label")
            ], className="metric-card"),
        ], style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "12px"})
    ])

def create_beautiful_charts_view():
    """Create stunning real-time charts"""
    
    simulation_data = sim_state.get_data()
    
    if not simulation_data:
        return html.Div([
            html.P("📈 Start simulation to see real-time charts", 
                  style={'textAlign': 'center', 'color': '#6c757d', 'padding': '30px', 'fontSize': '18px', 'fontWeight': '500'})
        ])
    
    df = pd.DataFrame(simulation_data)
    
    # Stunning satisfaction chart
    satisfaction_fig = px.line(df, x='day', y='satisfaction_rate', 
                              title='📊 Satisfaction Rate Over Time (Real-time)',
                              color_discrete_sequence=['#27ae60'])
    satisfaction_fig.update_layout(
        height=280, 
        margin=dict(l=30, r=30, t=50, b=30),
        plot_bgcolor='rgba(255,255,255,0.95)',
        paper_bgcolor='rgba(255,255,255,0.95)',
        font=dict(family="Inter, sans-serif", size=12),
        title_font_size=16,
        title_font_color='#2d3748',
        title_x=0.5,
        transition={'duration': 0}  # Disable animation
    )
    satisfaction_fig.update_traces(line=dict(width=4))
    satisfaction_fig.update_xaxes(gridcolor='rgba(0,0,0,0.1)')
    satisfaction_fig.update_yaxes(gridcolor='rgba(0,0,0,0.1)')
    
    # Stunning distance chart
    distance_fig = px.line(df, x='day', y='avg_travel_distance', 
                          title='🛣️ Average Travel Distance (Real-time)',
                          color_discrete_sequence=['#667eea'])
    distance_fig.update_layout(
        height=280, 
        margin=dict(l=30, r=30, t=50, b=30),
        plot_bgcolor='rgba(255,255,255,0.95)',
        paper_bgcolor='rgba(255,255,255,0.95)',
        font=dict(family="Inter, sans-serif", size=12),
        title_font_size=16,
        title_font_color='#2d3748',
        title_x=0.5,
        transition={'duration': 0}  # Disable animation
    )
    distance_fig.update_traces(line=dict(width=4))
    distance_fig.update_xaxes(gridcolor='rgba(0,0,0,0.1)')
    distance_fig.update_yaxes(gridcolor='rgba(0,0,0,0.1)')
    
    # Food insecurity chart
    if 'food_insecurity_rate' in df.columns:
        insecurity_fig = px.line(df, x='day', y='food_insecurity_rate', 
                                title='🍽️ Food Insecurity Rate (Real-time)',
                                color_discrete_sequence=['#e74c3c'])
        insecurity_fig.update_layout(
            height=280, 
            margin=dict(l=30, r=30, t=50, b=30),
            plot_bgcolor='rgba(255,255,255,0.95)',
            paper_bgcolor='rgba(255,255,255,0.95)',
            font=dict(family="Inter, sans-serif", size=12),
            title_font_size=16,
            title_font_color='#2d3748',
            title_x=0.5,
            transition={'duration': 0}  # Disable animation
        )
        insecurity_fig.update_traces(line=dict(width=4))
        insecurity_fig.update_xaxes(gridcolor='rgba(0,0,0,0.1)')
        insecurity_fig.update_yaxes(gridcolor='rgba(0,0,0,0.1)')
    else:
        insecurity_fig = None
    
    return html.Div([
        dcc.Graph(figure=satisfaction_fig),
        dcc.Graph(figure=distance_fig),
        dcc.Graph(figure=insecurity_fig) if insecurity_fig else html.Div()
    ])

def _store_scenario_snapshot(scenario_name):
    """Persist final metrics for a scenario run for later comparison."""
    with simulation_lock:
        if not sim_state.simulation_data:
            return
        latest = sim_state.simulation_data[-1]
        sim_state.scenario_snapshots[scenario_name] = {
            "scenario": scenario_name,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "days": sim_state.current_day,
            "metrics_history": list(sim_state.simulation_data),
            "final_metrics": dict(latest) if isinstance(latest, dict) else {}
        }


def _build_comparison_rows_from_snapshots(snapshot_dict):
    name_map = {
        "baseline": "Baseline",
        "scenario1": "Scenario 1",
        "scenario2": "Scenario 2",
        "scenario3": "Scenario 3",
        "scenario4": "Scenario 4",
    }
    rows = []
    for key in ["baseline", "scenario1", "scenario2", "scenario3", "scenario4"]:
        snap = snapshot_dict.get(key)
        if not snap:
            continue
        final = snap.get("final_metrics", {})
        rows.append({
            "scenario": name_map[key],
            "satisfaction_rate": float(final.get("satisfaction_rate", 0.0)),
            "food_insecurity_rate": float(final.get("food_insecurity_rate", 0.0)),
            "avg_travel_distance": float(final.get("avg_travel_distance", 0.0)),
            "spatial_equity_index": float(final.get("spatial_equity_index", 0.0)),
            "days": int(snap.get("days", 0)),
            "timestamp": snap.get("timestamp", "")
        })
    return rows


def create_results_view(selected_scenario=None):
    """Create results analysis; comparison tab uses stored scenario snapshots."""
    
    with simulation_lock:
        comparison_results = sim_state.comparison_results
        current_model = sim_state.current_model
        running = sim_state.sim_running
        simulation_data = sim_state.simulation_data
        scenario_snapshots = dict(sim_state.scenario_snapshots)
    
    if selected_scenario == "comparison":
        if (not comparison_results) or (not isinstance(comparison_results, dict)):
            comparison_results = {"rows": _build_comparison_rows_from_snapshots(scenario_snapshots)}

        comp_df = pd.DataFrame(comparison_results.get("rows", []))
        if not comp_df.empty:
            rank_df = comp_df.sort_values(
                by=["satisfaction_rate", "food_insecurity_rate", "avg_travel_distance"],
                ascending=[False, True, True]
            ).reset_index(drop=True)
            rank_df["rank"] = rank_df.index + 1

            sat_fig = px.bar(
                rank_df, x="scenario", y="satisfaction_rate", color="scenario",
                title="😊 Satisfaction by Scenario", text_auto=".1%"
            )
            sat_fig.update_layout(height=280, showlegend=False, margin=dict(l=20, r=20, t=45, b=30))

            fi_fig = px.bar(
                rank_df, x="scenario", y="food_insecurity_rate", color="scenario",
                title="🍽️ Food Insecurity by Scenario (Lower is Better)", text_auto=".1%"
            )
            fi_fig.update_layout(height=280, showlegend=False, margin=dict(l=20, r=20, t=45, b=30))

            dist_fig = px.bar(
                rank_df, x="scenario", y="avg_travel_distance", color="scenario",
                title="🛣️ Avg Travel Distance by Scenario (km)", text_auto=".2f"
            )
            dist_fig.update_layout(height=280, showlegend=False, margin=dict(l=20, r=20, t=45, b=30))

            best_row = rank_df.iloc[0]
            ranking_text = " > ".join(rank_df["scenario"].tolist())

            return html.Div([
                html.H5("⚖️ Cross-Run Scenario Comparison", style={'color': '#27ae60', 'fontSize': '20px', 'fontWeight': '700'}),
                html.P(
                    f"Best overall: {best_row['scenario']} | Ranking: {ranking_text}",
                    style={'margin': '8px 0 12px 0', 'color': '#4a5568', 'fontSize': '14px'}
                ),
                dcc.Graph(figure=sat_fig),
                dcc.Graph(figure=fi_fig),
                dcc.Graph(figure=dist_fig)
            ])

        missing = []
        for key, label in [("baseline", "Baseline"), ("scenario1", "Scenario 1"), ("scenario2", "Scenario 2"), ("scenario3", "Scenario 3"), ("scenario4", "Scenario 4")]:
            if key not in scenario_snapshots:
                missing.append(label)
        return html.Div([
            html.H5("⚖️ Cross-Run Scenario Comparison", style={'color': '#2d3748', 'fontSize': '20px', 'fontWeight': '700'}),
            html.P("Run each scenario at least once to populate comparison.", style={'color': '#6c757d'}),
            html.P(f"Missing runs: {', '.join(missing)}", style={'color': '#b7791f', 'fontWeight': '600'})
        ])

    elif current_model:
        # Calculate real-time summary stats
        latest_data = simulation_data[-1] if simulation_data else {}
        
        return html.Div([
            html.H5("📊 Real-time Simulation Results", style={'color': '#667eea', 'marginBottom': '20px', 'fontSize': '18px', 'fontWeight': '700'}),
            
            html.Div([
                html.Div([
                    html.H6("🎯 Current Status", style={'color': '#2d3748', 'marginBottom': '12px', 'fontWeight': '600'}),
                    html.P(f"👥 Total Consumers: {len(current_model.consumers)}", style={'margin': '6px 0', 'fontSize': '15px'}),
                    html.P(f"🏪 Food Providers: {len(current_model.food_providers)}", style={'margin': '6px 0', 'fontSize': '15px'}),
                    html.P(f"📅 Current Day: {sim_state.current_day}/{sim_state.max_days}", style={'margin': '6px 0', 'fontSize': '15px'}),
                    html.P(f"⏰ Status: {'🟢 Running' if running else '⏸️ Stopped'}", style={'margin': '6px 0', 'fontSize': '15px', 'fontWeight': '600'})
                ], style={'flex': '1', 'marginRight': '20px'}),
                
                html.Div([
                    html.H6("📈 Latest Metrics", style={'color': '#2d3748', 'marginBottom': '12px', 'fontWeight': '600'}),
                    html.P(f"😊 Satisfaction: {latest_data.get('satisfaction_rate', 0):.1%}", style={'margin': '6px 0', 'fontSize': '15px'}),
                    html.P(f"🚗 Avg Distance: {latest_data.get('avg_travel_distance', 0):.2f} km", style={'margin': '6px 0', 'fontSize': '15px'}),
                    html.P(f"🍽️ Food Insecurity: {latest_data.get('food_insecurity_rate', 0):.1%}", style={'margin': '6px 0', 'fontSize': '15px'}),
                    html.P(f"⚖️ Spatial Equity: {latest_data.get('spatial_equity_index', 0):.3f}", style={'margin': '6px 0', 'fontSize': '15px'})
                ], style={'flex': '1'})
            ], style={'display': 'flex', 'gap': '20px'})
        ])
    else:
        return html.Div([
            html.P("🔄 Start simulation to see real-time results", 
                  style={'color': '#6c757d', 'textAlign': 'center', 'fontSize': '18px', 'padding': '30px', 'fontWeight': '500'})
        ])

# Simulation control callback
@app.callback(
    [Output("start-btn", "disabled")],
    [Input("start-btn", "n_clicks"),
     Input("stop-btn", "n_clicks"),
     Input("reset-btn", "n_clicks"),
     Input("selected-scenario", "data")],
    [State("selected-scenario", "data"),
     State("collected-parameters", "children")]
)
def control_simulation(start_clicks, stop_clicks, reset_clicks, selected_tab, scenario, collected_params):
    """Control simulation with comprehensive parameter handling"""
    ctx = callback_context
    if not ctx.triggered:
        return [scenario == 'comparison']
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'start-btn' and not sim_state.sim_running:
        # Build configuration from collected parameters
        try:
            import json
            input_dict = json.loads(collected_params) if collected_params else {}
            config = build_config_from_inputs(input_dict)
            
            # Clean parameter summary
            print("\n" + "="*60)
            print(f"SIMULATION CONFIGURATION - {scenario.upper()}")
            print("="*60)
            print(f"Scenario: {scenario}")
            print(f"Consumers: {config.num_consumers}")
            print(f"Simulation Days: {config.simulation_days}")
            print(f"Max Car Distance: {config.max_distance_car} km")
            print(f"Max Walk Distance (no car): {config.max_distance_no_car} km")
            
            if scenario == 'scenario1':
                print(f"Grocery Store Capacity: {config.grocery_store_capacity}")
                print(f"Grocery Hours: {config.operating_hours.get('grocery_store', 'N/A')}")
                print(f"Service Rate: {config.service_areas.get('grocery_store', 'N/A')}")
            elif scenario == 'scenario2':
                print(f"Corner Stores: {config.num_corner_stores}")
                print(f"Food Hub Capacity: {config.food_hub_capacity}")
                print(f"Hub Hours: {config.operating_hours.get('food_hub', 'N/A')}")
                print(f"Corner Hours: {config.operating_hours.get('corner_store', 'N/A')}")
                print(f"Market Days: {config.food_hub_market_days}")
            elif scenario == 'scenario3':
                print(f"Mobile Pantries: {config.num_mobile_pantries}")
                print(f"Pantry Capacity: {config.mobile_pantry_capacity}")

                print(f"Strategy: {config.mobile_pantry_strategy}")
            
            print(f"Income Modifiers: {config.income_modifiers}")
            print("="*60)
        except Exception as e:
            print(f"Configuration building error: {e}")
            with simulation_lock:
                sim_state.status_message = f"❌ Invalid parameters: {str(e)}"
            return [scenario == 'comparison']

        # Comparison tab is display-only: do not launch simulations here.
        if scenario == 'comparison':
            with simulation_lock:
                rows = _build_comparison_rows_from_snapshots(sim_state.scenario_snapshots)
                sim_state.comparison_results = {"rows": rows}
                sim_state.status_message = (
                    "⚖️ Comparison updated from saved scenario runs."
                    if rows else
                    "⚠️ No saved runs yet. Run Baseline and Scenarios 1-4 first."
                )
            return [True]

        # Initialize and start the simulation
        with simulation_lock:
            sim_state.current_params = {
                'scenario': scenario,
                'config': config.__dict__
            }
            sim_state.current_scenario = scenario
            sim_state.max_days = config.simulation_days
        sim_state.reset()
        sim_state.sim_running = True
        
        # Start single scenario
        try:
            if scenario == 'baseline':
                model = create_baseline_scenario(config, use_real_data=True)
                print(f"✅ Created baseline model with {len(model.food_providers)} providers")
            elif scenario == 'scenario1':
                model = create_enhanced_scenario_1(config, include_baseline=True, use_real_data=True)
                print(f"✅ Created Scenario 1 model with {len(model.food_providers)} providers")
            elif scenario == 'scenario2':
                model = create_enhanced_scenario_2(config, include_baseline=True, use_real_data=True)
                print(f"✅ Created Scenario 2 model with {len(model.food_providers)} providers")
            elif scenario == 'scenario3':
                model = create_enhanced_scenario_3(config, include_baseline=True, use_real_data=True)
                print(f"✅ Created Scenario 3 model with {len(model.food_providers)} providers")
            elif scenario == 'scenario4':
                delivery_cap = int(input_dict.get('param-delivery-capacity', 500))
                base_fee = float(input_dict.get('param-base-fee', 2.00))
                dist_fee = float(input_dict.get('param-distance-fee', 0.75))
                area_km = float(input_dict.get('param-delivery-area', 20.0))
                model = create_enhanced_scenario_4(
                    config, use_real_data=True,
                    delivery_capacity=delivery_cap,
                    base_service_fee=base_fee,
                    distance_fee_per_km=dist_fee,
                    delivery_area_km=area_km
                )
                print(f"✅ Created Scenario 4 model with {len(model.food_providers)} providers (includes delivery service)")
            
            with simulation_lock:
                sim_state.current_model = model
            
            def run_simulation():
                try:
                    with simulation_lock:
                        sim_state.status_message = f"🚀 Running {scenario} simulation..."
                    for day in range(sim_state.max_days):
                        with simulation_lock:
                            should_continue = sim_state.sim_running
                        if not should_continue:
                            print(f"🛑 Simulation stopped at day {day + 1}")
                            break
                        model.step()
                        with simulation_lock:
                            sim_state.current_day = day + 1
                            if getattr(model, 'metrics_history', None):
                                latest_metrics = model.metrics_history[-1]
                                sim_state.simulation_data.append(latest_metrics)
                                pass
                            progress = ((day + 1) / sim_state.max_days) * 100
                            sim_state.status_message = f"🚀 Running {scenario} - Day {day + 1}/{sim_state.max_days} ({progress:.0f}%) ⚡"
                        # Slow down to allow UI interval updates to render each day
                        time.sleep(1.0)
                    with simulation_lock:
                        sim_state.status_message = f"✅ {scenario} simulation complete! 🎉"
                    _store_scenario_snapshot(scenario)
                except Exception as e:
                    print(f"Simulation error: {e}")
                    with simulation_lock:
                        sim_state.status_message = f"❌ Simulation failed: {str(e)}"
                finally:
                    with simulation_lock:
                        sim_state.sim_running = False
            sim_state.simulation_thread = threading.Thread(target=run_simulation)
            sim_state.simulation_thread.start()
        except Exception as e:
            print(f"Model creation error: {e}")
            with simulation_lock:
                sim_state.status_message = f"❌ Failed to create model: {str(e)}"
    
    elif button_id == 'stop-btn':
        with simulation_lock:
            sim_state.sim_running = False
            sim_state.status_message = "🛑 Simulation stopped by user"
    
    elif button_id == 'reset-btn':
        sim_state.reset()
    
    return [scenario == 'comparison']

# Scenario 3: Capture clicks to pick fixed mobile pantry locations
@app.callback(
    Output("picked-pantry-locations", "data"),
    [Input("live-map", "click_lat_lng"), Input("selected-scenario", "data")],
    [State("picked-pantry-locations", "data")],
    prevent_initial_call=True
)
def pick_pantry_locations(click_lat_lng, scenario, picked):
    picked = picked or []
    if scenario != "scenario3":
        return picked
    if not click_lat_lng:
        return picked
    lat, lon = click_lat_lng
    picked.append({"lat": lat, "lon": lon})
    return picked

# Display picked locations text in parameters section
@app.callback(
    Output("picked-pantry-locations-display", "children"),
    [Input("picked-pantry-locations", "data"), Input("mobile-pantry-pick-mode", "value")]
)
def show_picked_locations(data, mode):
    if mode != "map":
        return "Using street list input."
    data = data or []
    if not data:
        return "Click on the map to add locations."
    lines = [f"{i+1}. ({round(d['lat'],5)}, {round(d['lon'],5)})" for i, d in enumerate(data)]
    return html.Pre("\n".join(lines), style={"margin": 0})

# Callbacks for Two-Level Metrics Navigation
@app.callback(
    [Output({"type": "metrics-main-tab", "index": ALL}, "style"),
     Output("selected-main-metric", "data")],
    [Input({"type": "metrics-main-tab", "index": ALL}, "n_clicks")],
    [State("selected-main-metric", "data")]
)
def handle_main_metrics_tab_click(n_clicks_list, current_main):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    # Determine which tab was clicked
    clicked_tab = None
    for i, n_clicks in enumerate(n_clicks_list):
        if n_clicks:
            clicked_tab = ctx.triggered[0]['prop_id'].split('"index":"')[1].split('"')[0]
            break
    
    if not clicked_tab:
        clicked_tab = current_main or "primary"
    
    # Generate styles for main tabs
    main_tab_styles = []
    for i, tab_type in enumerate(["primary", "charts", "results"]):
        if tab_type == clicked_tab:
            style = {"padding": "8px 16px", "cursor": "pointer", "borderRadius": "6px", 
                    "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", 
                    "color": "white", "fontWeight": "500", "textAlign": "center", "fontSize": "13px"}
        else:
            style = {"padding": "8px 16px", "cursor": "pointer", "borderRadius": "6px", 
                    "background": "#f7fafc", "color": "#4a5568", "fontWeight": "500", 
                    "textAlign": "center", "border": "1px solid #e2e8f0", "fontSize": "13px"}
        main_tab_styles.append(style)
    

    
    return main_tab_styles, clicked_tab

@app.callback(
    [Output("selected-sub-metric", "data"),
     Output("metrics-content", "children"),
     Output({"type": "metrics-sub-item", "index": ALL}, "style")],  # Add style output for highlighting
    [Input({"type": "metrics-sub-item", "index": ALL}, "n_clicks"),
     Input("selected-main-metric", "data"),
     Input("selected-scenario", "data"),
     Input("interval-component", "n_intervals"),  # Add interval to update metrics automatically
     Input("final-metrics-store", "data")],  # Add stored metrics as input
    [State("selected-sub-metric", "data"),
     State({"type": "metrics-sub-item", "index": ALL}, "id")],
    prevent_initial_call=False
)
def handle_sub_metrics_click(n_clicks_list, main_metric, selected_scenario, n_intervals, stored_metrics, current_sub, sub_item_ids):
    ctx = callback_context
    
    # Determine what triggered this callback
    triggered_prop_id = ctx.triggered[0]['prop_id'] if ctx.triggered else ""
    
    # Check what triggered this callback
    if 'selected-main-metric' in triggered_prop_id:
        # Main metric changed, set default sub-metric
        if main_metric == "primary":
            clicked_sub = "primary-main"
        elif main_metric == "charts":
            clicked_sub = "satisfaction-chart"
        else:
            clicked_sub = "summary-report"
    elif 'interval-component' in triggered_prop_id:
        # Interval triggered - use current sub-selection to update content
        clicked_sub = current_sub or "primary-main"

    else:
        # Sub-item was clicked, determine which one
        clicked_sub = None
        if ctx.triggered:
            try:
                clicked_sub = ctx.triggered[0]['prop_id'].split('"index":"')[1].split('"')[0]
            except (IndexError, AttributeError):
                pass
        
        if not clicked_sub:
            # Set default based on main metric
            if main_metric == "primary":
                clicked_sub = current_sub or "primary-main"
            elif main_metric == "charts":
                clicked_sub = current_sub or "satisfaction-chart"
            else:
                clicked_sub = current_sub or "summary-report"
    

    
    # Generate content based on selection
    if main_metric == "primary":
        if clicked_sub == "primary-main":
            # Show ONLY primary metrics content

            try:
                primary_content = create_primary_metrics_only(stored_metrics)
                content = [html.Div([
                    primary_content
                ], style={"height": "400px", "overflowY": "auto", "padding": "10px"})]
            except Exception as e:
                print(f"⚠️ Error creating primary metrics in callback: {e}")
                content = [html.Div([
                    html.H6("Primary Metrics", style={"margin": "0 0 10px 0", "color": "#2d3748"}),
                    html.P("Primary metrics will appear here when data is available.",
                          style={"color": "#4a5568", "fontSize": "14px"})
                ], style={"height": "250px", "overflowY": "auto"})]
        elif clicked_sub == "progress":

            content = [html.Div([
                create_progress_metrics_only(stored_metrics)
            ], style={"height": "400px", "overflowY": "auto", "padding": "10px"})]
        elif clicked_sub == "counts":

            content = [html.Div([
                create_counts_metrics_only(stored_metrics)
            ], style={"height": "400px", "overflowY": "auto", "padding": "10px"})]
        elif clicked_sub == "performance":

            content = [html.Div([
                create_performance_metrics_only(stored_metrics)
            ], style={"height": "400px", "overflowY": "auto", "padding": "10px"})]
        else:

            content = [html.Div([
                html.H6("Default Metrics", style={"margin": "0 0 10px 0", "color": "#2d3748"}),
                html.P("Select a specific metrics category from the left to view detailed information.",
                      style={"color": "#4a5568", "fontSize": "14px"})
            ], style={"height": "250px", "overflowY": "auto"})]
    elif main_metric == "charts":
        all_charts = create_beautiful_charts_view()
        # Keep chart tab responsive by rendering one chart panel at a time.
        if clicked_sub == "daily-trends" and isinstance(all_charts, html.Div) and len(all_charts.children) >= 2:
            chart_child = all_charts.children[1]
        elif clicked_sub == "provider-usage" and isinstance(all_charts, html.Div) and len(all_charts.children) >= 3:
            chart_child = all_charts.children[2]
        elif isinstance(all_charts, html.Div) and all_charts.children:
            chart_child = all_charts.children[0]
        else:
            chart_child = all_charts
        content = [html.Div([
            chart_child
        ], style={"height": "400px", "overflowY": "auto", "padding": "10px"})]
    else:  # results
        content = [html.Div([
            create_results_view(selected_scenario)
        ], style={"height": "400px", "overflowY": "auto", "padding": "10px"})]
    
    # Generate styles for exactly the rendered sub-items (prevents ALL-pattern length mismatch)
    rendered_items = [
        d.get("index") for d in (sub_item_ids or [])
        if isinstance(d, dict) and d.get("index")
    ]
    if not rendered_items:
        if main_metric == "primary":
            rendered_items = ["primary-main", "progress", "counts", "performance"]
        elif main_metric == "charts":
            rendered_items = ["satisfaction-chart", "daily-trends", "provider-usage"]
        else:  # results
            rendered_items = ["summary-report", "detailed-stats", "export-data"]
    
    # Generate styles for highlighting
    sub_item_styles = []
    for item in rendered_items:
        if item == clicked_sub:
            # Selected item - highlight with gradient
            style = {
                "padding": "6px 10px", 
                "cursor": "pointer", 
                "borderRadius": "4px",
                "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", 
                "color": "white", 
                "fontSize": "12px", 
                "marginBottom": "4px",
                "transition": "all 0.3s ease"
            }
        else:
            # Unselected item - neutral background
            style = {
                "padding": "6px 10px", 
                "cursor": "pointer", 
                "borderRadius": "4px",
                "background": "#f9f9f9", 
                "color": "#4a5568", 
                "fontSize": "12px", 
                "marginBottom": "4px",
                "transition": "all 0.3s ease"
            }
        sub_item_styles.append(style)
    
    return clicked_sub, content, sub_item_styles

# Initialize metrics sub-navigation on page load
@app.callback(
    Output("metrics-sub-nav", "children"),
    [Input("selected-main-metric", "data")],
    prevent_initial_call=False
)
def initialize_metrics_navigation(main_metric):
    """Initialize the metrics navigation and content"""
    main_metric = main_metric or "primary"
    
    # Default sub-navigation
    if main_metric == "primary":
        sub_nav = [
            html.Div("Primary Metrics", id={"type": "metrics-sub-item", "index": "primary-main"}, 
                    style={"padding": "6px 10px", "cursor": "pointer", "borderRadius": "4px", 
                          "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", 
                          "color": "white", "fontSize": "12px", "marginBottom": "4px"}),
            html.Div("Progress", id={"type": "metrics-sub-item", "index": "progress"}, 
                    style={"padding": "6px 10px", "cursor": "pointer", "borderRadius": "4px", 
                          "background": "#f9f9f9", "color": "#4a5568", "fontSize": "12px", "marginBottom": "4px"}),
            html.Div("Real-time Counts", id={"type": "metrics-sub-item", "index": "counts"}, 
                    style={"padding": "6px 10px", "cursor": "pointer", "borderRadius": "4px", 
                          "background": "#f9f9f9", "color": "#4a5568", "fontSize": "12px", "marginBottom": "4px"}),
            html.Div("Performance", id={"type": "metrics-sub-item", "index": "performance"}, 
                    style={"padding": "6px 10px", "cursor": "pointer", "borderRadius": "4px", 
                          "background": "#f9f9f9", "color": "#4a5568", "fontSize": "12px", "marginBottom": "4px"})
        ]
    elif main_metric == "charts":
        sub_nav = [
            html.Div("Satisfaction Chart", id={"type": "metrics-sub-item", "index": "satisfaction-chart"}, 
                    style={"padding": "6px 10px", "cursor": "pointer", "borderRadius": "4px", 
                          "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", 
                          "color": "white", "fontSize": "12px", "marginBottom": "4px"}),
            html.Div("Daily Trends", id={"type": "metrics-sub-item", "index": "daily-trends"}, 
                    style={"padding": "6px 10px", "cursor": "pointer", "borderRadius": "4px", 
                          "background": "#f9f9f9", "color": "#4a5568", "fontSize": "12px", "marginBottom": "4px"}),
            html.Div("Provider Usage", id={"type": "metrics-sub-item", "index": "provider-usage"}, 
                    style={"padding": "6px 10px", "cursor": "pointer", "borderRadius": "4px", 
                          "background": "#f9f9f9", "color": "#4a5568", "fontSize": "12px", "marginBottom": "4px"})
        ]
    else:  # results
        sub_nav = [
            html.Div("Summary Report", id={"type": "metrics-sub-item", "index": "summary-report"}, 
                    style={"padding": "6px 10px", "cursor": "pointer", "borderRadius": "4px", 
                          "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", 
                          "color": "white", "fontSize": "12px", "marginBottom": "4px"}),
            html.Div("Detailed Stats", id={"type": "metrics-sub-item", "index": "detailed-stats"}, 
                    style={"padding": "6px 10px", "cursor": "pointer", "borderRadius": "4px", 
                          "background": "#f9f9f9", "color": "#4a5568", "fontSize": "12px", "marginBottom": "4px"}),
            html.Div("Export Data", id={"type": "metrics-sub-item", "index": "export-data"}, 
                    style={"padding": "6px 10px", "cursor": "pointer", "borderRadius": "4px", 
                          "background": "#f9f9f9", "color": "#4a5568", "fontSize": "12px", "marginBottom": "4px"})
        ]
    
    return sub_nav




# Note: Removed separate live-metrics-display callback since content is generated directly in navigation


# ============== SENSITIVITY ANALYSIS TAB ==============

def _build_sa_figure_tabs():
    """Load pre-generated SA figures from disk and return a dcc.Tabs (or placeholder)."""
    import base64
    sa_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sa_results')
    figures = [
        ("🔵 Pearson Correlations", "fig1_pearson_heatmap.png",
         "Pearson r between each parameter and output metric. "
         "Bounded [-1,1]. *** p<0.001. N=4,096 simulation runs."),
        ("📊 Parameter Rankings", "fig2_ranked_bars.png",
         "Parameters ranked by effect magnitude for key outputs. "
         "Bootstrapped 95% CI shown. Dominant parameter identified per output."),
        ("🔴 Sobol S1 (Spending)", "fig3_sobol_spend_low.png",
         "Sobol first-order index valid for low-income spending only (SumS1=0.975). "
         "Other outputs excluded due to estimator instability at N_base=256."),
        ("🟣 PRCC Analysis", "fig4_prcc_heatmap.png",
         "Partial Rank Correlation controls for all other parameters simultaneously. "
         "Consistent with Pearson results — confirms findings are not artifacts of parameter correlations."),
        ("📈 Convergence", "fig5_convergence.png",
         "Pearson r stabilizes well before N=4,096, demonstrating result stability across sample sizes."),
    ]
    placeholder = html.Div([
        html.Div("📊 No sensitivity results yet.", style={
            "fontWeight": "600", "fontSize": "16px", "color": "#4a5568", "marginBottom": "8px"}),
        html.Div("Run sensitivity analysis first to generate figures.",
                 style={"color": "#9ca3af", "fontSize": "14px"})
    ], style={"padding": "60px", "textAlign": "center"})

    any_found = False
    tabs = []
    for label, filename, caption in figures:
        fpath = os.path.join(sa_dir, filename)
        if os.path.isfile(fpath):
            any_found = True
            with open(fpath, 'rb') as f:
                encoded = base64.b64encode(f.read()).decode('ascii')
            tab_content = html.Div([
                html.Img(src=f"data:image/png;base64,{encoded}",
                         style={"width": "100%", "maxWidth": "1200px", "display": "block",
                                "margin": "12px auto 8px auto", "borderRadius": "6px",
                                "boxShadow": "0 2px 8px rgba(0,0,0,0.08)"}),
                html.P(caption, style={
                    "textAlign": "center", "color": "#4a5568", "fontSize": "12px",
                    "fontStyle": "italic", "maxWidth": "900px", "margin": "4px auto 0 auto"})
            ])
        else:
            tab_content = placeholder
        tabs.append(dcc.Tab(
            label=label, children=[tab_content],
            style={"padding": "10px"},
            selected_style={"padding": "10px", "borderTop": "3px solid #1F4E79"}
        ))
    if not any_found:
        return placeholder
    return dcc.Tabs(tabs, colors={
        "border": "#e2e8f0", "primary": "#1F4E79", "background": "#f8f9fa"})


def build_sa_layout(center_params, json_path, cal_error, tidy_df, indices_dict=None):
    """Build the full SA tab layout."""
    output_options = [
        'avg_spend_low', 'avg_spend_med', 'avg_spend_high',
        'corner_share', 'food_insecurity_share',
        'avg_dist_car', 'avg_dist_nocar', 'total_trips'
    ]
    param_options = [
        'alpha_distance', 'beta_price_budget', 'gamma_quality_variety',
        'delta_convenience', 'go_shop_threshold_low', 'go_shop_threshold_medium',
        'go_shop_threshold_high'
    ]

    # Parameter bounds table
    param_table = html.Div("No calibration loaded.", style={"fontSize": "13px", "color": "#9ca3af"})
    if center_params:
        pct = 0.30
        rows = [html.Tr([
            html.Th("Parameter", style={"padding": "8px", "textAlign": "left"}),
            html.Th("Center", style={"padding": "8px", "textAlign": "right"}),
            html.Th("±Bounds", style={"padding": "8px", "textAlign": "right"})
        ], style={"background": "linear-gradient(135deg, #667eea, #764ba2)", "color": "white"})]
        for name, v in center_params.items():
            lo, hi = v * (1 - pct), v * (1 + pct)
            rows.append(html.Tr([
                html.Td(name, style={"padding": "6px 8px", "fontSize": "13px"}),
                html.Td(f"{v:.3g}", style={"padding": "6px 8px", "textAlign": "right", "fontSize": "13px"}),
                html.Td(f"[{lo:.3g}, {hi:.3g}]", style={"padding": "6px 8px", "textAlign": "right", "fontSize": "13px"})
            ], style={"background": "#f8f9fa" if len(rows) % 2 == 0 else "white"}))
        param_table = html.Table(rows, style={"width": "100%", "fontSize": "13px", "borderCollapse": "collapse"})

    # Budget table — built from Pearson CSV (primary sensitivity method)
    _output_labels = {
        'avg_spend_low': 'Low-Income Spending', 'avg_spend_med': 'Med-Income Spending',
        'avg_spend_high': 'High-Income Spending', 'corner_share': 'Corner Store Share',
        'food_insecurity_share': 'Food Insecurity', 'avg_dist_car': 'Distance (Car)',
        'avg_dist_nocar': 'Distance (No Car)', 'total_trips': 'Total Trips',
    }
    _param_labels = {
        'alpha_distance': 'α Distance', 'beta_price_budget': 'β Price/Budget',
        'gamma_quality_variety': 'γ Quality', 'delta_convenience': 'δ Convenience',
        'go_shop_threshold_low': 'θ_low Shop Freq.', 'go_shop_threshold_medium': 'θ_med Shop Freq.',
        'go_shop_threshold_high': 'θ_high Shop Freq.',
    }
    budget_content = html.Div("No results yet — run sensitivity analysis above.",
                             style={"padding": "20px", "textAlign": "center", "color": "#9ca3af", "fontSize": "14px"})
    pearson_csv = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'sa_results', 'sensitivity_pearson_results.csv')
    if os.path.isfile(pearson_csv):
        try:
            pdf = pd.read_csv(pearson_csv)
            pdf['abs_r'] = pdf['r'].abs()
            header_style = {"padding": "8px 10px", "textAlign": "left", "fontSize": "12px", "fontWeight": "600"}
            budget_rows = [html.Tr([
                html.Th("Output Metric", style=header_style),
                html.Th("Dominant Parameter", style=header_style),
                html.Th("Pearson r", style={**header_style, "textAlign": "right"}),
                html.Th("95% CI", style={**header_style, "textAlign": "right"}),
                html.Th("Sig.", style={**header_style, "textAlign": "center"}),
            ], style={"background": "linear-gradient(135deg, #1F4E79, #2E75B6)", "color": "white"})]
            for oname in output_options:
                sub = pdf[pdf['output'] == oname]
                if sub.empty:
                    continue
                dom = sub.loc[sub['abs_r'].idxmax()]
                r_val = float(dom['r'])
                ci_lo, ci_hi = float(dom['ci_low']), float(dom['ci_high'])
                pv = float(dom['p_value'])
                sig = "***" if pv < 0.001 else ("**" if pv < 0.01 else ("*" if pv < 0.05 else "ns"))
                r_color = "#C00000" if abs(r_val) > 0.3 else ("#2E75B6" if abs(r_val) > 0.05 else "#6b7280")
                cell = {"padding": "7px 10px", "fontSize": "12px", "borderBottom": "1px solid #e2e8f0"}
                budget_rows.append(html.Tr([
                    html.Td(_output_labels.get(oname, oname), style={**cell, "fontWeight": "500"}),
                    html.Td(_param_labels.get(dom['parameter'], dom['parameter']), style=cell),
                    html.Td(f"{r_val:+.3f}", style={**cell, "textAlign": "right", "fontWeight": "700",
                                                      "color": r_color, "fontFamily": "monospace"}),
                    html.Td(f"[{ci_lo:+.2f}, {ci_hi:+.2f}]", style={**cell, "textAlign": "right",
                                                                       "fontSize": "11px", "color": "#6b7280",
                                                                       "fontFamily": "monospace"}),
                    html.Td(sig, style={**cell, "textAlign": "center", "fontWeight": "600",
                                         "color": "#C00000" if pv < 0.001 else "#6b7280"}),
                ], style={"background": "#f8fafc" if len(budget_rows) % 2 == 0 else "white"}))
            budget_content = html.Table(budget_rows, style={
                "width": "100%", "fontSize": "12px", "borderCollapse": "collapse",
                "borderRadius": "8px", "overflow": "hidden",
                "boxShadow": "0 1px 3px rgba(0,0,0,0.08)"})
        except Exception:
            pass

    subtitle = ""
    if json_path:
        subtitle = f"Calibration: {os.path.basename(json_path)}"
        if cal_error is not None:
            subtitle += f" | Error: {cal_error:.4f}"
    else:
        subtitle = "No calibration file found."

    warning_banner = None
    if not center_params:
        warning_banner = html.Div(
            "⚠️ No FINAL_CALIBRATED_PARAMS or BEST_PHASE1_PARAMS JSON found. Run Phase 2 calibration first.",
            style={"background": "#fef3c7", "color": "#92400e", "padding": "12px 16px", "borderRadius": "8px",
                   "marginBottom": "15px", "fontWeight": "600"}
        )

    return [
        html.Div([
            html.H4("🔬 Sensitivity Analysis — Multi-Method",
                    style={"margin": "0 0 4px 0", "color": "#2d3748", "fontWeight": "700", "fontSize": "1.4em"}),
            html.Div([
                html.Span("Methods: ", style={"fontWeight": "600", "color": "#4a5568"}),
                html.Span("Pearson r (primary) · PRCC (Marino et al. 2008) · Sobol S1 (avg_spend_low only)",
                          style={"color": "#2E75B6", "fontSize": "13px", "fontStyle": "italic"})
            ], style={"marginBottom": "4px"}),
            html.P(subtitle, style={"margin": "0", "color": "#4a5568", "fontSize": "14px"}),
            warning_banner
        ], className="card", style={"marginBottom": "20px"}),

        html.Div([
            html.Div([
                html.H5("Controls", style={"margin": "0 0 15px 0", "color": "#2d3748", "fontWeight": "600"}),
                param_table,
                html.Hr(style={"margin": "20px 0"}),
                html.Label("N (sample size)", style={"fontWeight": "600", "fontSize": "13px"}),
                dcc.Slider(id="sa-n-slider", min=50, max=1024, value=256, step=None,
                           marks={50: "50", 128: "128", 256: "256", 512: "512", 1024: "1024"}),
                html.Hr(style={"margin": "15px 0"}),
                html.Label("Bounds %", style={"fontWeight": "600", "fontSize": "13px"}),
                dcc.Slider(id="sa-bounds-slider", min=10, max=50, step=5, value=30,
                           marks={10: "±10%", 20: "±20%", 30: "±30%", 40: "±40%", 50: "±50%"}),
                html.Hr(style={"margin": "15px 0"}),
                html.Div([
                    html.Button("▶ Run Sensitivity Analysis", id="sa-run-btn", n_clicks=0,
                                style={"background": "linear-gradient(135deg, #27ae60, #2ecc71)", "color": "white",
                                       "border": "none", "padding": "10px 16px", "borderRadius": "8px",
                                       "cursor": "pointer", "fontWeight": "600", "marginRight": "10px"}),
                    html.Button("⏹ Cancel", id="sa-cancel-btn", n_clicks=0,
                                style={"background": "linear-gradient(135deg, #e74c3c, #c0392b)", "color": "white",
                                       "border": "none", "padding": "10px 16px", "borderRadius": "8px",
                                       "cursor": "pointer", "fontWeight": "600"})
                ]),
                html.Div(id="sa-progress-display",
                        style={"marginTop": "15px", "fontSize": "14px", "fontFamily": "monospace"}),
                dcc.Interval(id="sa-interval", interval=2000, n_intervals=0, disabled=True)
            ], className="card", style={"width": "35%", "padding": "25px"}),
            html.Div([
                html.H5("Sensitivity Summary", style={"margin": "0 0 4px 0", "color": "#2d3748", "fontWeight": "600"}),
                html.P("Dominant parameter per output — Pearson r (N = 4,096)",
                       style={"margin": "0 0 12px 0", "color": "#6b7280", "fontSize": "12px", "fontStyle": "italic"}),
                budget_content
            ], className="card", style={"width": "65%", "padding": "25px"})
        ], style={"display": "flex", "gap": "20px", "marginBottom": "20px"}),

        html.Div([
            html.H5("Results — Multi-Method Sensitivity Analysis",
                     style={"margin": "0 0 4px 0", "color": "#2d3748", "fontWeight": "600"}),
            html.P("Pearson r (primary) · PRCC (nonlinearity-robust) · Sobol S1 (avg_spend_low only)",
                   style={"margin": "0 0 12px 0", "color": "#4a5568", "fontSize": "13px", "fontStyle": "italic"}),
            dcc.RadioItems(id="sa-index-toggle", options=[{"label": "S1", "value": "S1"}],
                           value="S1", style={"display": "none"}),
            dcc.Dropdown(id="sa-output-dropdown", options=[{"label": "avg_spend_low", "value": "avg_spend_low"}],
                         value="avg_spend_low", style={"display": "none"}),
            dcc.Dropdown(id="sa-x-param-dropdown", options=[{"label": "alpha_distance", "value": "alpha_distance"}],
                         value="alpha_distance", style={"display": "none"}),
            html.Div(_build_sa_figure_tabs(), id="sa-results-tabs-content", style={"marginTop": "10px"})
        ], className="card", style={"padding": "25px"})
    ]


@app.callback(
    Output("sa-tab-content", "children"),
    Input("selected-scenario", "data")
)
def render_sa_tab(selected):
    try:
        center_params, json_path, cal_error = load_calibration_center()
        raw_df, tidy_df, indices_dict = load_latest_sa_results()
    except Exception as e:
        import traceback
        traceback.print_exc()
        center_params, json_path, cal_error = None, None, None
        tidy_df = None
        indices_dict = {}
    return build_sa_layout(center_params, json_path, cal_error, tidy_df, indices_dict or {})


@app.callback(
    [Output("sa-running-store", "data"),
     Output("sa-progress-display", "children"),
     Output("sa-interval", "disabled")],
    [Input("sa-run-btn", "n_clicks"),
     Input("sa-cancel-btn", "n_clicks")],
    [State("sa-n-slider", "value"),
     State("sa-bounds-slider", "value"),
     State("sa-running-store", "data")],
    prevent_initial_call=True
)
def handle_sa_run(run_clicks, cancel_clicks, N, bounds_pct, is_running):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    triggered = ctx.triggered[0]["prop_id"].split(".")[0]
    if triggered == "sa-cancel-btn":
        sa_cancel_event.set()
        return False, "⏹ Cancelled.", True
    if triggered == "sa-run-btn" and not is_running:
        sa_cancel_event.clear()
        N = N or 256
        bounds_pct = bounds_pct if bounds_pct is not None else 30
        total_runs = N * (2 * 7 + 2)

        def run_in_background():
            try:
                run_sa_sweep(N=N, pct=bounds_pct / 100.0, n_steps=90,
                             progress_callback=update_sa_progress, cancel_event=sa_cancel_event)
            except Exception as e:
                import traceback
                update_sa_progress(0, total_runs, done=True, result_path=None)
                print(f"SA Error: {e}")
                traceback.print_exc()

        threading.Thread(target=run_in_background, daemon=True).start()
        return True, html.Div([
            html.Div("🔄 SENSITIVITY ANALYSIS STARTED", style={"fontWeight": "700", "fontSize": "16px", "color": "#27ae60", "marginBottom": "8px"}),
            html.Div(f"0 / {total_runs} runs  —  first result in ~1-2 min (model setup)", style={"fontSize": "13px", "color": "#4a5568"}),
            html.Div("░░░░░░░░░░░░░░░░░░░░ 0%", style={"fontFamily": "monospace", "marginTop": "4px"})
        ]), False
    raise PreventUpdate


@app.callback(
    [Output("sa-progress-display", "children", allow_duplicate=True),
     Output("sa-results-store", "data"),
     Output("sa-interval", "disabled", allow_duplicate=True)],
    Input("sa-interval", "n_intervals"),
    State("sa-running-store", "data"),
    prevent_initial_call=True
)
def poll_sa_progress(n, is_running):
    progress = sa_progress_state.get()
    if progress.get("done"):
        rp = progress.get("result_path") or ""
        ts = rp.replace("sa_results/sobol_", "") if rp else ""
        save_msg = f" Results saved: sa_results/sobol_raw_{ts}.csv, sobol_tidy_{ts}.csv" if ts else ""
        return (
            f"✅ Complete! {progress.get('total', 0)} runs finished.{save_msg}",
            progress.get("result_path"),
            True
        )
    completed = progress.get("completed", 0)
    total = progress.get("total", 1)
    pct = int(100 * completed / total) if total > 0 else 0
    bar = f"{'█' * (pct // 5)}{'░' * (20 - pct // 5)}"
    return f"🔄 {bar} {pct}% ({completed}/{total} runs)", None, False


@app.callback(
    Output("sa-results-tabs-content", "children"),
    [Input("sa-results-store", "data"),
     Input("sa-index-toggle", "value"),
     Input("sa-output-dropdown", "value"),
     Input("sa-x-param-dropdown", "value")],
    prevent_initial_call=True
)
def update_sa_charts(result_path, index_type, output_name, x_param):
    if not result_path:
        raise PreventUpdate
    return _build_sa_figure_tabs()


if __name__ == '__main__':
    print("Enhanced Mesa-Geo Dashboard Starting...")
    print("Dashboard available at: http://localhost:8050")

    # Suppress Flask HTTP request logs (the POST /_dash-update-component flood)
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.WARNING)

    # Default to stable non-debug mode to avoid watchdog/FSEvents crashes on some macOS setups.
    # Set DASH_DEBUG=1 to enable Dash debug mode when needed.
    debug_mode = os.getenv("DASH_DEBUG", "0") == "1"
    app.run(debug=debug_mode, port=8050, host="0.0.0.0")

# Note: Parameter section rendering is now handled by handle_section_and_scenario_changes callback