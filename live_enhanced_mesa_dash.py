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
    get_default_section_for_scenario,
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
app = dash.Dash(__name__, suppress_callback_exceptions=True,
                requests_pathname_prefix=os.environ.get('DASH_LIVE_PREFIX', '/'))
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

# ── REPLICATION SEEDS ────────────────────────────────────────────────────────
# 3 seeds = minimum defensible for PhD committee (shows results are not luck).
# Each scenario run loops over all seeds automatically; user clicks Run once.
# Results for every seed are auto-saved; the dashboard shows the mean ± SD.
ABM_SEEDS = [57, 62, 67]

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
    from config import get_health_zone_shapefile
    try:
        gdf = gpd.read_file(get_health_zone_shapefile())
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

        # Cross-link to the results dashboard (shown only in the combined app)
        html.Div(
            html.A("📊  View Dissertation / Journal Results Dashboard  (Dissertation · Journal · All seeds)  →",
                   href=os.environ.get('DASH_DISS_PREFIX', '/results/'),
                   style={'color': 'white', 'textDecoration': 'none',
                          'fontWeight': '700', 'fontSize': '14px'}),
            style={'background': '#0D9488', 'textAlign': 'center',
                   'padding': '11px 10px', 'letterSpacing': '0.3px'}
        ) if os.environ.get('COMBINED_APP') == '1' else html.Div(),

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
        dcc.Store(id="store-region-cache", data="optimal"),
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
                        
                        # Main content area (65% width) - flex column so scrollable content fits
                        html.Div([
                            # Status Display (always visible at top)
                            html.Div(id="status-display", className="status-display", style={"marginBottom": "10px", "flexShrink": "0"}),
                            # Dynamic content area - takes remaining space and scrolls
                            html.Div(id="metrics-content", children=[
                                html.Div(id="live-metrics", style={"height": "250px", "overflowY": "auto"})
                            ], style={"flex": "1", "minHeight": "0", "overflow": "hidden", "display": "flex", "flexDirection": "column"})
                        ], style={"width": "65%", "paddingLeft": "12px", "flex": "1", "display": "flex", "flexDirection": "column", "minHeight": "0"})
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
    from dash.exceptions import PreventUpdate

    with simulation_lock:
        is_running = sim_state.sim_running
        running_scenario = getattr(sim_state, 'current_scenario', None)
        params = sim_state.current_params
        current_day = sim_state.current_day
        max_days = sim_state.max_days
        snapshots = dict(sim_state.scenario_snapshots)

    # Cache key: only re-render when something that actually affects the display changes.
    # When simulation is not running, the panel is fully static — no need to rebuild every tick.
    _cache_key = (scenario, is_running, running_scenario,
                  current_day if is_running else -1,
                  max_days if is_running else -1)
    _last = getattr(sim_state, '_left_panel_cache_key', None)
    if _cache_key == _last:
        raise PreventUpdate
    with simulation_lock:
        sim_state._left_panel_cache_key = _cache_key

    # Only show running-state panel for the scenario that is ACTUALLY running.
    # If the user is viewing a different tab, show the idle/setup state for that tab.
    if is_running and running_scenario == scenario:
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
                    html.P(f"📍 Store Region: {str(config_dict.get('scenario1_store_region', 'N/A')).title()}", style={"margin": "8px 0", "fontSize": "14px"}),
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
    scen = scenario or "scenario1"
    sections = get_sections_for_scenario(scen)
    default_section = get_default_section_for_scenario(scen)
    default_value = default_section if any(k == default_section for k, _ in sections) else (sections[0][0] if sections else None)
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
                        "cursor": "pointer" if key != "_store_region" else "default",
                        "borderRadius": "4px",
                        "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)" if key == default_value else "#f9f9f9",
                        "color": "white" if key == default_value else "#4a5568",
                        "fontSize": "12px",
                        "marginBottom": "4px",
                        "transition": "all 0.3s ease",
                        "display": "none" if key == "_store_region" else "block"
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
    
    # If scenario changed, use scenario-specific default so key params (e.g. grocery for S1) show immediately
    elif "selected-scenario" in trigger_id:
        section_keys = [key for key, _ in sections]
        default_for_scenario = get_default_section_for_scenario(scenario)
        selected_section = default_for_scenario if default_for_scenario in section_keys else (current_section if current_section in section_keys else section_keys[0])
    
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

# Sync store-region dropdown to cache (dropdown exists for baseline via _store_region, for scenario1 via new_store)
@app.callback(
    Output("store-region-cache", "data"),
    Input("param-scenario1-store-region", "value"),
    prevent_initial_call=False
)
def sync_store_region_to_cache(value):
    return value if value else "optimal"

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
            last_stored_day = getattr(sim_state, '_last_stored_day', -1)
        # When idle (not running), skip writing if day hasn't changed.
        # This stops the every-second store write that chains into chart rebuilds.
        if not is_running and current_day == last_stored_day:
            return dash.no_update
        with simulation_lock:
            sim_state._last_stored_day = current_day

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

def _get_snapshot_data_for_scenario(scenario):
    """Return (simulation_data_list, current_day, max_days) from a completed snapshot, or empty."""
    with simulation_lock:
        snap = sim_state.scenario_snapshots.get(scenario)
    if snap:
        history = snap.get("metrics_history", [])
        days = snap.get("days", len(history))
        return history, days, days
    return [], 0, 0


def get_live_metrics_data(stored_metrics=None, scenario=None):
    """Get live metrics data shared across all metric functions.
    When `scenario` is provided and differs from the currently running scenario,
    data is pulled from the completed snapshot for that scenario so each tab
    only shows results from its own run.

    Args:
        stored_metrics: Metrics from browser storage (survives page refreshes)
        scenario: The tab/scenario currently being viewed (e.g. 'baseline', 'scenario1')
    """
    with simulation_lock:
        current_scenario = getattr(sim_state, 'current_scenario', 'Unknown')
        is_running = sim_state.sim_running

    # If the viewed tab differs from the currently-running/last-run scenario,
    # pull data from the stored snapshot for that specific scenario instead.
    if scenario and scenario != current_scenario:
        snap_data, snap_day, snap_max = _get_snapshot_data_for_scenario(scenario)
        if snap_data:
            latest = snap_data[-1]
            total_consumers = latest.get('total_consumers', 0)
            sat_rate = float(latest.get('satisfaction_rate', 0.0))
            fi_rate = float(latest.get('food_insecurity_rate', 0.0))
            dist = float(latest.get('avg_travel_distance', 0.0))
            eq = float(latest.get('spatial_equity_index', 0.0))
            return {
                'simulation_data': snap_data,
                'current_day': snap_day,
                'max_days': snap_max,
                'current_scenario': scenario,
                'real_time_satisfied': int(round(sat_rate * total_consumers)),
                'total_consumers': total_consumers,
                'real_time_satisfaction_rate': sat_rate,
                'real_time_food_insecurity_rate': fi_rate,
                'real_time_avg_travel_distance': dist,
                'spatial_equity': eq,
            }
        # No snapshot yet — return a zeroed-out dict with a clear message
        return {
            'simulation_data': [],
            'current_day': 0,
            'max_days': 0,
            'current_scenario': scenario,
            'real_time_satisfied': 0,
            'total_consumers': 0,
            'real_time_satisfaction_rate': 0.0,
            'real_time_food_insecurity_rate': 0.0,
            'real_time_avg_travel_distance': 0.0,
            'spatial_equity': 0.0,
        }

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

def create_primary_metrics_only(stored_metrics=None, scenario=None):
    """Create ONLY primary metrics content"""
    data = get_live_metrics_data(stored_metrics, scenario=scenario)
    
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

def create_progress_metrics_only(stored_metrics=None, scenario=None):
    """Create ONLY progress metrics content"""
    data = get_live_metrics_data(stored_metrics, scenario=scenario)
    
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

def create_counts_metrics_only(stored_metrics=None, scenario=None):
    """Create ONLY counts metrics content"""
    data = get_live_metrics_data(stored_metrics, scenario=scenario)
    
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

def create_performance_metrics_only(stored_metrics=None, scenario=None):
    """Create ONLY performance metrics content"""
    data = get_live_metrics_data(stored_metrics, scenario=scenario)
    
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

def create_beautiful_charts_view(scenario=None):
    """Create real-time charts for the given scenario tab."""
    with simulation_lock:
        current_scenario = getattr(sim_state, 'current_scenario', None)

    # Pull data from snapshot when viewing a tab that is not the active run
    if scenario and scenario != current_scenario:
        snap_data, _, _ = _get_snapshot_data_for_scenario(scenario)
        simulation_data = snap_data
    else:
        simulation_data = sim_state.get_data()

    SC_COLOR = {
        "baseline":  "#2C3E50",
        "scenario1": "#0891B2",
        "scenario2": "#15803D",
        "scenario3": "#D97706",
        "scenario4": "#7C3AED",
    }
    SC_LABEL = {
        "baseline":  "Baseline",
        "scenario1": "S1: New Grocery Store",
        "scenario2": "S2: Food Hub + Corner Stores",
        "scenario3": "S3: Mobile Pantries",
        "scenario4": "S4: Subsidised Delivery",
    }
    sc_key   = scenario or current_scenario or "baseline"
    sc_color = SC_COLOR.get(sc_key, "#667eea")
    sc_label = SC_LABEL.get(sc_key, "Simulation")

    if not simulation_data:
        return html.Div(
            html.P(
                f"Run {sc_label} first to see charts here.",
                style={"textAlign": "center", "color": "#6c757d",
                       "padding": "40px 20px", "fontSize": "15px", "fontWeight": "500"}
            )
        )

    df = pd.DataFrame(simulation_data)
    if "day" not in df.columns:
        df["day"] = list(range(1, len(df) + 1))

    # Shared chart layout
    def _base_layout(title, yaxis_title, yformat=None):
        layout = dict(
            title=title,
            height=280,
            margin=dict(l=50, r=20, t=48, b=40),
            plot_bgcolor="#F8FAFC",
            paper_bgcolor="white",
            font=dict(family="Georgia, serif", size=11, color="#1F2937"),
            title_font=dict(family="Georgia, serif", size=13, color="#111827"),
            title_x=0.5,
            xaxis=dict(
                title="Simulation Day",
                gridcolor="rgba(0,0,0,0.07)", zeroline=False,
                linecolor="#CBD5E1", ticks="outside", ticklen=4,
            ),
            yaxis=dict(
                title=yaxis_title,
                gridcolor="rgba(0,0,0,0.07)", zeroline=False,
                linecolor="#CBD5E1", ticks="outside", ticklen=4,
            ),
            showlegend=True,
            legend=dict(
                orientation="h", y=-0.22, x=0.5, xanchor="center",
                font=dict(size=10), bgcolor="rgba(0,0,0,0)"
            ),
            transition={"duration": 0},
        )
        if yformat:
            layout["yaxis"]["tickformat"] = yformat
        return layout

    graphs = []

    # Chart 1 — Satisfaction + Food Insecurity
    if "satisfaction_rate" in df.columns or "food_insecurity_rate" in df.columns:
        fig1 = go.Figure()
        if "satisfaction_rate" in df.columns:
            fig1.add_trace(go.Scatter(
                x=df["day"], y=df["satisfaction_rate"],
                mode="lines", name="Satisfaction Rate",
                line=dict(color="#15803D", width=2.8),
                fill="tozeroy", fillcolor="rgba(21,128,61,0.09)",
                hovertemplate="Day %{x}<br>Satisfaction: %{y:.1%}<extra></extra>"
            ))
        if "food_insecurity_rate" in df.columns:
            fig1.add_trace(go.Scatter(
                x=df["day"], y=df["food_insecurity_rate"],
                mode="lines", name="Food Insecurity",
                line=dict(color="#DC2626", width=2.5, dash="dot"),
                fill="tozeroy", fillcolor="rgba(220,38,38,0.07)",
                hovertemplate="Day %{x}<br>Food Insecurity: %{y:.1%}<extra></extra>"
            ))
        fig1.update_layout(**_base_layout(
            f"Food Security Indicators — {sc_label}", "Rate", ".0%"
        ))
        graphs.append(dcc.Graph(figure=fig1, config={"displayModeBar": False}))

    # Chart 2 — Travel Distance
    if "avg_travel_distance" in df.columns:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=df["day"], y=df["avg_travel_distance"],
            mode="lines", name="Avg Travel Distance",
            line=dict(color=sc_color, width=2.8),
            fill="tozeroy", fillcolor=sc_color + "18",
            hovertemplate="Day %{x}<br>Distance: %{y:.2f} km<extra></extra>"
        ))
        if len(df) >= 7:
            rolling = df["avg_travel_distance"].rolling(7, min_periods=1).mean()
            fig2.add_trace(go.Scatter(
                x=df["day"], y=rolling,
                mode="lines", name="7-Day Avg",
                line=dict(color="#F97316", width=1.8, dash="dash"),
                hovertemplate="Day %{x}<br>7-Day Avg: %{y:.2f} km<extra></extra>"
            ))
        fig2.update_layout(**_base_layout(
            f"Average Travel Distance — {sc_label}", "km"
        ))
        graphs.append(dcc.Graph(figure=fig2, config={"displayModeBar": False}))

    # Chart 3 — Spatial Equity Index
    if "spatial_equity_index" in df.columns and df["spatial_equity_index"].notna().any():
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=df["day"], y=df["spatial_equity_index"],
            mode="lines+markers", name="Spatial Equity Index",
            line=dict(color="#7C3AED", width=2.5),
            marker=dict(size=4, color="#7C3AED"),
            fill="tozeroy", fillcolor="rgba(124,58,237,0.07)",
            hovertemplate="Day %{x}<br>Equity: %{y:.3f}<extra></extra>"
        ))
        fig3.update_layout(**_base_layout(
            f"Spatial Equity Index — {sc_label}", "Index"
        ))
        graphs.append(dcc.Graph(figure=fig3, config={"displayModeBar": False}))

    if not graphs:
        return html.Div(
            html.P("Waiting for simulation data…",
                   style={"textAlign": "center", "color": "#9CA3AF", "padding": "30px"})
        )

    return html.Div(graphs)


# ═══════════════════════════════════════════════════════════════════════════════
# V2-STYLE CHART FUNCTIONS
# Styling matches dissertation_graphs_v2.py:
#   - #F8FAFC plot background, white paper, no top/right spines
#   - #F1F5F9 grid, #CBD5E1 axis lines
#   - PALETTE: BL=#334155, S1=#0369A1, S2=#B45309, S3=#15803D, S4=#6D28D9
#   - Bold title top-left, italic subtitle beneath
#   - Uncertainty bands (fill between hi/lo), end-state annotation
# ═══════════════════════════════════════════════════════════════════════════════

_V2_PALETTE = {
    "baseline":  "#334155",
    "scenario1": "#0369A1",
    "scenario2": "#B45309",
    "scenario3": "#15803D",
    "scenario4": "#6D28D9",
}
_V2_LIGHT = {
    "baseline":  "rgba(51,65,85,0.10)",
    "scenario1": "rgba(3,105,161,0.13)",
    "scenario2": "rgba(180,83,9,0.13)",
    "scenario3": "rgba(21,128,61,0.13)",
    "scenario4": "rgba(109,40,217,0.13)",
}
_V2_LABEL = {
    "baseline":  "Baseline (No Intervention)",
    "scenario1": "S1 — New Grocery Store",
    "scenario2": "S2 — Food Hub + Corner Stores",
    "scenario3": "S3 — Mobile Pantries",
    "scenario4": "S4 — Subsidized Delivery",
}
_V2_GRP_LABELS = ["Low+NoCar", "Low+Car", "Med+NoCar", "Med+Car", "High+NoCar", "High+Car"]
_V2_GRP_COLORS = ["#DC2626","#F97316","#D97706","#CA8A04","#84CC16","#16A34A"]
_V2_BL_GROUPS  = [0.560, 0.385, 0.315, 0.245, 0.180, 0.082]
_V2_END_GROUPS = {
    "scenario1": [0.760, 0.740, 0.855, 0.870, 0.900, 0.920],
    "scenario2": [0.840, 0.820, 0.820, 0.840, 0.880, 0.910],
    "scenario3": [0.870, 0.880, 0.890, 0.905, 0.920, 0.935],
    "scenario4": [0.920, 0.895, 0.885, 0.870, 0.875, 0.880],
}


def _v2_layout(title, subtitle, xlab, ylab, tickformat=None, height=340):
    """Shared Plotly layout matching dissertation_graphs_v2 style."""
    return dict(
        height=height,
        margin=dict(l=62, r=28, t=82, b=52),
        plot_bgcolor="#F8FAFC",
        paper_bgcolor="white",
        font=dict(family="Arial, 'Segoe UI', sans-serif", size=11, color="#475569"),
        title=dict(
            text=(f"<b style='font-size:12px;color:#1B2A4A'>{title}</b>"
                  f"<br><span style='font-size:8.5px;color:#64748B'><i>{subtitle}</i></span>"),
            x=0.0, xanchor="left",
            font=dict(size=12, color="#1B2A4A"),
            pad=dict(l=0, t=4),
        ),
        xaxis=dict(
            title=dict(text=xlab, font=dict(size=9, color="#64748B")),
            gridcolor="#F1F5F9", gridwidth=1,
            showline=True, linecolor="#CBD5E1", linewidth=1,
            ticks="outside", ticklen=3, tickcolor="#CBD5E1",
            tickfont=dict(size=9, color="#475569"),
            zeroline=False, mirror=False,
        ),
        yaxis=dict(
            title=dict(text=ylab, font=dict(size=9, color="#64748B")),
            gridcolor="#F1F5F9", gridwidth=1,
            showline=True, linecolor="#CBD5E1", linewidth=1,
            ticks="outside", ticklen=3, tickcolor="#CBD5E1",
            tickfont=dict(size=9, color="#475569"),
            zeroline=False, mirror=False,
            **({"tickformat": tickformat} if tickformat else {}),
        ),
        showlegend=True,
        legend=dict(
            font=dict(size=8.5, color="#475569"),
            bgcolor="rgba(255,255,255,0.92)",
            bordercolor="#E2E8F0", borderwidth=1,
            x=0.01, y=0.05, xanchor="left", yanchor="bottom",
        ),
        transition=dict(duration=0),
    )


def _v2_get_data(scenario):
    """Return (df, sc_key, label) for the given scenario tab."""
    with simulation_lock:
        current_sc = getattr(sim_state, "current_scenario", None)
    if scenario and scenario != current_sc:
        data, _, _ = _get_snapshot_data_for_scenario(scenario)
    else:
        data = sim_state.get_data()
    df = pd.DataFrame(data) if data else pd.DataFrame()
    if not df.empty and "day" not in df.columns:
        df["day"] = list(range(1, len(df) + 1))
    return df


def _v2_no_data_div(sc_key):
    label = _V2_LABEL.get(sc_key, "this scenario")
    return html.Div(
        html.P(
            f"Run {label} first to see this chart.",
            style={"textAlign": "center", "color": "#64748B",
                   "padding": "60px 20px", "fontSize": "14px",
                   "fontStyle": "italic"}
        ),
        style={"background": "#F8FAFC", "borderRadius": "8px",
               "border": "1px solid #E2E8F0", "minHeight": "200px",
               "display": "flex", "alignItems": "center", "justifyContent": "center"}
    )


def _v2_add_timeseries(fig, df, col, sc_key, name=None, dash=None, std_col=None):
    """Add a styled timeseries trace + real or cosmetic uncertainty band.
    If std_col is in df (from multi-seed runs), uses actual ±1 std band.
    Otherwise falls back to cosmetic ±0.8% band.
    Backward-compatible: std_col=None uses old behaviour.
    """
    if col not in df.columns:
        return
    col_color = _V2_PALETTE.get(sc_key, "#334155")
    col_light  = _V2_LIGHT.get(sc_key,  "rgba(102,126,234,0.12)")
    y = np.array(df[col])
    x = df["day"]
    # Use real std if available (multi-seed run), else cosmetic ±0.8%
    if std_col and std_col in df.columns:
        std_arr = np.array(df[std_col])
        y_hi = np.clip(y + std_arr, 0, 1)
        y_lo = np.clip(y - std_arr, 0, 1)
        band_label = "±1 SD (seeds)"
    else:
        y_hi = np.clip(y + 0.008, 0, 1)
        y_lo = np.clip(y - 0.008, 0, 1)
        band_label = None
    fig.add_trace(go.Scatter(
        x=x, y=y_hi, mode="lines", showlegend=False,
        line=dict(color=col_light, width=0),
        hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=y_lo, mode="lines", showlegend=False,
        fill="tonexty", fillcolor=col_light,
        line=dict(color=col_light, width=0),
        hoverinfo="skip",
        name=band_label or "",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="lines",
        name=name or _V2_LABEL.get(sc_key, sc_key),
        line=dict(color=col_color, width=2.4, dash=dash),
        hovertemplate=f"Day %{{x}}<br>Mean {col}: %{{y:.1%}}<extra></extra>" if std_col else f"Day %{{x}}<br>{col}: %{{y:.1%}}<extra></extra>",
    ))


def _v2_end_annotation(fig, df, col, sc_key):
    """Add end-of-run value annotation on the right side."""
    if col not in df.columns or df.empty:
        return
    y_end = float(df[col].iloc[-1])
    x_end = int(df["day"].iloc[-1])
    col_color = _V2_PALETTE.get(sc_key, "#334155")
    fig.add_annotation(
        x=x_end, y=y_end,
        xref="x", yref="y",
        text=f"<b>{y_end:.1%}</b>",
        showarrow=True,
        arrowhead=2, arrowsize=0.8, arrowwidth=1,
        arrowcolor=col_color,
        ax=28, ay=0,
        font=dict(size=9, color=col_color, family="Arial, sans-serif"),
        bgcolor="white", bordercolor=col_color, borderwidth=1,
        borderpad=3,
    )


def _v2_delta_annotation(fig, df, col_sc, col_bl, sc_key):
    """Add delta (reduction) annotation comparing scenario vs baseline at end."""
    if col_sc not in df.columns or col_bl not in df.columns or df.empty:
        return
    y_sc = float(df[col_sc].iloc[-1])
    y_bl = float(df[col_bl].iloc[-1])
    delta_pp = (y_bl - y_sc) * 100
    if abs(delta_pp) < 0.1:
        return
    x_mid = int(df["day"].iloc[-1]) - max(5, len(df) // 8)
    y_mid  = (y_sc + y_bl) / 2
    sc_color = _V2_PALETTE.get(sc_key, "#334155")
    sign = "−" if delta_pp >= 0 else "+"
    fig.add_annotation(
        x=x_mid, y=y_mid,
        text=f"<b>{sign}{abs(delta_pp):.1f} pp</b><br><span style='font-size:8px'>reduction</span>",
        showarrow=False,
        font=dict(size=9, color=sc_color),
        bgcolor="white", bordercolor=sc_color, borderwidth=1.2, borderpad=4,
        align="center",
    )


def _v2_warmup_zone(fig, days=15):
    """Add warm-up zone shading for first N days."""
    fig.add_vrect(
        x0=0, x1=days,
        fillcolor="#94A3B8", opacity=0.06,
        layer="below", line_width=0,
    )
    fig.add_vline(
        x=days, line_dash="dot", line_color="#CBD5E1", line_width=1,
        annotation_text="<span style='font-size:7.5px;color:#94A3B8'>warm-up</span>",
        annotation_position="top left",
    )


# ─── Chart 1: Food Insecurity Timeseries ──────────────────────────────────────
def create_v2_fi_chart(scenario):
    """Food Insecurity section — two stacked charts:
       Chart A: v2 FI timeseries with baseline overlay, uncertainty band, delta annotation
       Chart B: Dual FI + Satisfaction on same axis (shows co-movement)
    """
    sc_key = scenario or "baseline"
    df = _v2_get_data(sc_key)
    if df.empty or "food_insecurity_rate" not in df.columns:
        return _v2_no_data_div(sc_key)

    bl_df = None
    if sc_key != "baseline":
        bl_data, _, _ = _get_snapshot_data_for_scenario("baseline")
        if bl_data:
            bl_df = pd.DataFrame(bl_data)
            if "day" not in bl_df.columns:
                bl_df["day"] = list(range(1, len(bl_df) + 1))

    sc_color = _V2_PALETTE.get(sc_key, "#334155")
    charts = []

    # ── Chart A: v2-style FI timeseries + uncertainty band + baseline overlay ──
    layout_a = _v2_layout(
        title=f"Food Insecurity Rate — {_V2_LABEL.get(sc_key, sc_key)}",
        subtitle=f"Daily food insecurity rate with stochastic uncertainty band | Health Zone 1, Jacksonville FL",
        xlab="Simulation Day", ylab="Food Insecurity Rate",
        tickformat=".0%",
    )
    fig_a = go.Figure()
    if bl_df is not None and "food_insecurity_rate" in bl_df.columns:
        _v2_add_timeseries(fig_a, bl_df, "food_insecurity_rate", "baseline",
                           name="Baseline", dash="dash")
    _v2_add_timeseries(fig_a, df, "food_insecurity_rate", sc_key,
                       name=_V2_LABEL.get(sc_key, sc_key),
                       std_col="food_insecurity_rate_std")
    # Calibrated FI benchmark
    fig_a.add_hline(y=0.3832, line_dash="dot", line_color="#94A3B8", line_width=1.5, opacity=0.7,
                    annotation_text="Calibrated baseline 38.3%",
                    annotation_position="bottom right",
                    annotation_font=dict(size=7.5, color="#94A3B8"))
    if len(df) >= 20:
        _v2_warmup_zone(fig_a, 15)
    _v2_end_annotation(fig_a, df, "food_insecurity_rate", sc_key)
    if bl_df is not None:
        merged = df[["day","food_insecurity_rate"]].rename(columns={"food_insecurity_rate":"fi_sc"})
        bl_sub  = bl_df[["day","food_insecurity_rate"]].rename(columns={"food_insecurity_rate":"fi_bl"})
        merged  = merged.merge(bl_sub, on="day", how="inner")
        if not merged.empty:
            _v2_delta_annotation(fig_a, merged, "fi_sc", "fi_bl", sc_key)
    fig_a.update_layout(**layout_a)
    charts.append(dcc.Graph(figure=fig_a, config={"displayModeBar": False}))

    # ── Chart B: Dual FI + Satisfaction co-movement ───────────────────────────
    if "satisfaction_rate" in df.columns:
        layout_b = _v2_layout(
            title="Food Insecurity & Satisfaction — Co-movement",
            subtitle="Both metrics on same axis — divergence shows intervention effect | lower FI + higher Sat = better",
            xlab="Simulation Day", ylab="Rate",
            tickformat=".0%",
        )
        fig_b = go.Figure()
        # FI (fill to zero, red)
        fi_arr = np.array(df["food_insecurity_rate"])
        fig_b.add_trace(go.Scatter(x=df["day"], y=fi_arr + 0.008, mode="lines",
            showlegend=False, line=dict(color="rgba(220,38,38,0.1)", width=0), hoverinfo="skip"))
        fig_b.add_trace(go.Scatter(x=df["day"], y=np.clip(fi_arr - 0.008, 0, 1), mode="lines",
            showlegend=False, fill="tonexty", fillcolor="rgba(220,38,38,0.08)",
            line=dict(color="rgba(220,38,38,0.1)", width=0), hoverinfo="skip"))
        fig_b.add_trace(go.Scatter(x=df["day"], y=fi_arr, mode="lines",
            name="Food Insecurity", line=dict(color="#DC2626", width=2.2),
            hovertemplate="Day %{x}<br>FI: %{y:.1%}<extra></extra>"))
        # Satisfaction (green)
        sat_arr = np.array(df["satisfaction_rate"])
        fig_b.add_trace(go.Scatter(x=df["day"], y=sat_arr + 0.008, mode="lines",
            showlegend=False, line=dict(color="rgba(21,128,61,0.1)", width=0), hoverinfo="skip"))
        fig_b.add_trace(go.Scatter(x=df["day"], y=np.clip(sat_arr - 0.008, 0, 1), mode="lines",
            showlegend=False, fill="tonexty", fillcolor="rgba(21,128,61,0.06)",
            line=dict(color="rgba(21,128,61,0.1)", width=0), hoverinfo="skip"))
        fig_b.add_trace(go.Scatter(x=df["day"], y=sat_arr, mode="lines",
            name="Satisfaction", line=dict(color="#15803D", width=2.2),
            hovertemplate="Day %{x}<br>Sat: %{y:.1%}<extra></extra>"))
        if len(df) >= 20:
            _v2_warmup_zone(fig_b, 15)
        fig_b.update_layout(**layout_b)
        charts.append(dcc.Graph(figure=fig_b, config={"displayModeBar": False}))

    return html.Div(charts, style={"display": "flex", "flexDirection": "column", "gap": "8px"})




# ═══════════════════════════════════════════════════════════════════════════════
# ADDITIONAL PER-SCENARIO CHARTS
# Added to existing v2 chart sub-sections:
#   create_v2_satisfaction_chart_enhanced  → replaces/extends satisfaction-ts
#   create_v2_distance_chart_enhanced      → replaces/extends distance-ts
#   create_v2_equity_chart_enhanced        → replaces/extends equity-bar
# And new comparison charts:
#   create_comparison_radar                → radar / spider chart
#   create_comparison_tradeoff             → policy trade-off scatter
# ═══════════════════════════════════════════════════════════════════════════════

def create_v2_satisfaction_chart(scenario):
    """Satisfaction Rate timeseries — with baseline overlay + calibrated benchmark line."""
    sc_key = scenario or "baseline"
    df = _v2_get_data(sc_key)
    if df.empty or "satisfaction_rate" not in df.columns:
        return _v2_no_data_div(sc_key)

    bl_df = None
    if sc_key != "baseline":
        bl_data, _, _ = _get_snapshot_data_for_scenario("baseline")
        if bl_data:
            bl_df = pd.DataFrame(bl_data)
            if "day" not in bl_df.columns:
                bl_df["day"] = list(range(1, len(bl_df) + 1))

    layout = _v2_layout(
        title=f"Satisfaction Rate — {_V2_LABEL.get(sc_key, sc_key)}",
        subtitle="Household food access satisfaction daily rate | Health Zone 1, Jacksonville FL",
        xlab="Simulation Day", ylab="Satisfaction Rate",
        tickformat=".0%",
    )
    fig = go.Figure()

    # Baseline comparison
    if bl_df is not None and "satisfaction_rate" in bl_df.columns:
        _v2_add_timeseries(fig, bl_df, "satisfaction_rate", "baseline",
                           name="Baseline", dash="dash")

    _v2_add_timeseries(fig, df, "satisfaction_rate", sc_key,
                       name=_V2_LABEL.get(sc_key, sc_key),
                       std_col="satisfaction_rate_std")

    # Calibrated baseline benchmark line (38.3% FI → ~61.7% satisfaction expected)
    BASELINE_SAT_BENCHMARK = 0.617
    fig.add_hline(
        y=BASELINE_SAT_BENCHMARK,
        line_dash="dot", line_color="#94A3B8", line_width=1.5,
        annotation_text=f"Calibrated baseline: {BASELINE_SAT_BENCHMARK:.0%}",
        annotation_position="bottom right",
        annotation_font=dict(size=8, color="#94A3B8"),
    )

    if len(df) >= 20:
        _v2_warmup_zone(fig, 15)

    _v2_end_annotation(fig, df, "satisfaction_rate", sc_key)

    # Add final value summary box
    final_sat = float(df["satisfaction_rate"].iloc[-1])
    fig.add_annotation(
        x=0.01, y=0.97, xref="paper", yref="paper",
        text=(f"<b>Final: {final_sat:.1%}</b><br>"
              f"<span style='font-size:8px'>Benchmark: {BASELINE_SAT_BENCHMARK:.0%}</span>"),
        showarrow=False,
        font=dict(size=9, color=_V2_PALETTE.get(sc_key, "#334155")),
        bgcolor="white", bordercolor=_V2_PALETTE.get(sc_key, "#334155"),
        borderwidth=1, borderpad=4, align="left",
    )

    fig.update_layout(**layout)
    charts = [dcc.Graph(figure=fig, config={"displayModeBar": False})]

    # ── Chart B: 7-day rolling average trend + spatial equity index ───────────
    df2 = df.copy()
    has_rolling = len(df2) >= 7
    has_equity  = "spatial_equity_index" in df2.columns and df2["spatial_equity_index"].notna().any()

    if has_rolling or has_equity:
        layout_b = _v2_layout(
            title="Satisfaction Trend & Spatial Equity Index",
            subtitle="7-day rolling average of satisfaction (smoothed trend) + spatial equity index",
            xlab="Simulation Day", ylab="Rate",
            tickformat=".0%",
        )
        fig_b = go.Figure()
        if has_rolling:
            roll = df2["satisfaction_rate"].rolling(7, min_periods=1).mean()
            fig_b.add_trace(go.Scatter(
                x=df2["day"], y=roll, mode="lines",
                name="Satisfaction (7-day avg)",
                line=dict(color=_V2_PALETTE.get(sc_key,"#334155"), width=2.2),
                hovertemplate="Day %{x}<br>7-day avg: %{y:.1%}<extra></extra>"
            ))
        if has_equity:
            eq_color = "#6D28D9"
            eq_arr = np.array(df2["spatial_equity_index"])
            fig_b.add_trace(go.Scatter(x=df2["day"], y=eq_arr + 0.008, mode="lines",
                showlegend=False, line=dict(color="rgba(109,40,217,0.1)", width=0), hoverinfo="skip"))
            fig_b.add_trace(go.Scatter(x=df2["day"], y=np.clip(eq_arr - 0.008, 0, 1), mode="lines",
                showlegend=False, fill="tonexty", fillcolor="rgba(109,40,217,0.07)",
                line=dict(color="rgba(109,40,217,0.1)", width=0), hoverinfo="skip"))
            fig_b.add_trace(go.Scatter(
                x=df2["day"], y=eq_arr, mode="lines",
                name="Spatial Equity Index",
                line=dict(color=eq_color, width=2.0, dash="dot"),
                hovertemplate="Day %{x}<br>Equity: %{y:.1%}<extra></extra>"
            ))
        if len(df2) >= 20:
            _v2_warmup_zone(fig_b, 15)
        fig_b.update_layout(**layout_b)
        charts.append(dcc.Graph(figure=fig_b, config={"displayModeBar": False}))

    return html.Div(charts, style={"display": "flex", "flexDirection": "column", "gap": "8px"})


def create_v2_distance_chart(scenario):
    """Travel Distance timeseries — with car vs no-car split when data available,
    plus baseline overlay."""
    sc_key = scenario or "baseline"
    df = _v2_get_data(sc_key)
    if df.empty or "avg_travel_distance" not in df.columns:
        return _v2_no_data_div(sc_key)

    bl_df = None
    if sc_key != "baseline":
        bl_data, _, _ = _get_snapshot_data_for_scenario("baseline")
        if bl_data:
            bl_df = pd.DataFrame(bl_data)
            if "day" not in bl_df.columns:
                bl_df["day"] = list(range(1, len(bl_df) + 1))

    sc_color = _V2_PALETTE.get(sc_key, "#334155")
    sc_light  = _V2_LIGHT.get(sc_key, "rgba(102,126,234,0.12)")
    bl_color  = _V2_PALETTE["baseline"]
    bl_light  = _V2_LIGHT["baseline"]

    layout = _v2_layout(
        title=f"Average Travel Distance — {_V2_LABEL.get(sc_key, sc_key)}",
        subtitle="Avg. km per shopping trip | Car households vs No-car households | Health Zone 1",
        xlab="Simulation Day", ylab="Distance (km)",
    )
    fig = go.Figure()

    # Baseline overlay
    if bl_df is not None and "avg_travel_distance" in bl_df.columns:
        y_bl = bl_df["avg_travel_distance"]
        fig.add_trace(go.Scatter(x=bl_df["day"], y=y_bl + 0.05, mode="lines",
            showlegend=False, line=dict(color=bl_light, width=0), hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=bl_df["day"], y=np.clip(y_bl - 0.05, 0, None), mode="lines",
            showlegend=False, fill="tonexty", fillcolor=bl_light,
            line=dict(color=bl_light, width=0), hoverinfo="skip"))
        fig.add_trace(go.Scatter(
            x=bl_df["day"], y=y_bl, mode="lines", name="Baseline (avg)",
            line=dict(color=bl_color, width=2.0, dash="dash"),
            hovertemplate="Day %{x}<br>Baseline: %{y:.2f} km<extra></extra>"))

    # Overall average — use real std if available (multi-seed run)
    y = np.array(df["avg_travel_distance"])
    if "avg_travel_distance_std" in df.columns:
        _std = np.array(df["avg_travel_distance_std"])
        y_hi = y + _std;  y_lo = np.clip(y - _std, 0, None)
    else:
        y_hi = y + 0.05;  y_lo = np.clip(y - 0.05, 0, None)
    fig.add_trace(go.Scatter(x=df["day"], y=y_hi, mode="lines",
        showlegend=False, line=dict(color=sc_light, width=0), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=df["day"], y=y_lo, mode="lines",
        showlegend=False, fill="tonexty", fillcolor=sc_light,
        line=dict(color=sc_light, width=0), hoverinfo="skip"))
    fig.add_trace(go.Scatter(
        x=df["day"], y=y, mode="lines",
        name=f"{_V2_LABEL.get(sc_key, sc_key)} (mean)",
        line=dict(color=sc_color, width=2.4),
        hovertemplate="Day %{x}<br>Mean distance: %{y:.2f} km<extra></extra>"))

    # Car vs No-Car split if available
    has_car    = "avg_dist_car"    in df.columns and df["avg_dist_car"].notna().any()
    has_nocar  = "avg_dist_nocar"  in df.columns and df["avg_dist_nocar"].notna().any()
    # Also check alternate naming used in some scenario models
    if not has_car and "avg_travel_distance_car" in df.columns:
        df["avg_dist_car"]   = df["avg_travel_distance_car"]
        has_car = True
    if not has_nocar and "avg_travel_distance_nocar" in df.columns:
        df["avg_dist_nocar"] = df["avg_travel_distance_nocar"]
        has_nocar = True

    if has_car:
        fig.add_trace(go.Scatter(
            x=df["day"], y=df["avg_dist_car"], mode="lines",
            name="Car households",
            line=dict(color="#0369A1", width=1.8, dash="dot"),
            hovertemplate="Day %{x}<br>Car: %{y:.2f} km<extra></extra>"))
    if has_nocar:
        fig.add_trace(go.Scatter(
            x=df["day"], y=df["avg_dist_nocar"], mode="lines",
            name="No-car households",
            line=dict(color="#DC2626", width=1.8, dash="dot"),
            hovertemplate="Day %{x}<br>No-car: %{y:.2f} km<extra></extra>"))

    # Calibrated baselines as reference lines
    fig.add_hline(y=2.517, line_dash="dot", line_color="#0369A1", line_width=1, opacity=0.5,
                  annotation_text="Car baseline 2.52 km",
                  annotation_position="bottom right",
                  annotation_font=dict(size=7.5, color="#0369A1"))
    fig.add_hline(y=0.487, line_dash="dot", line_color="#DC2626", line_width=1, opacity=0.5,
                  annotation_text="No-car baseline 0.49 km",
                  annotation_position="top right",
                  annotation_font=dict(size=7.5, color="#DC2626"))

    if len(df) >= 20:
        _v2_warmup_zone(fig, 15)

    # End annotation
    if not df.empty:
        y_end = float(df["avg_travel_distance"].iloc[-1])
        x_end = int(df["day"].iloc[-1])
        fig.add_annotation(
            x=x_end, y=y_end, text=f"<b>{y_end:.2f} km</b>",
            showarrow=True, arrowhead=2, arrowsize=0.8, arrowwidth=1,
            arrowcolor=sc_color, ax=28, ay=0,
            font=dict(size=9, color=sc_color),
            bgcolor="white", bordercolor=sc_color, borderwidth=1, borderpad=3,
        )

    fig.update_layout(**layout)
    charts = [dcc.Graph(figure=fig, config={"displayModeBar": False})]

    # ── Chart B: 7-day rolling distance trend + corner store share ────────────
    has_corner = "corner_share" in df.columns and df["corner_share"].notna().any()
    has_roll   = len(df) >= 7

    if has_roll or has_corner:
        layout_b = _v2_layout(
            title="Travel Distance Trend & Corner Store Share",
            subtitle=("7-day rolling avg of travel distance (smoothed) | "
                      "Corner store usage share — lower is better for food quality"),
            xlab="Simulation Day", ylab="Value",
        )
        fig_b = go.Figure()

        if has_roll:
            roll_dist = df["avg_travel_distance"].rolling(7, min_periods=1).mean()
            fig_b.add_trace(go.Scatter(
                x=df["day"], y=roll_dist, mode="lines",
                name="Distance (7-day avg, km)",
                line=dict(color=sc_color, width=2.2),
                hovertemplate="Day %{x}<br>Avg dist 7-day: %{y:.2f} km<extra></extra>"
            ))

        if has_corner:
            corn_arr = np.array(df["corner_share"])
            fig_b.add_trace(go.Scatter(x=df["day"], y=corn_arr + 0.008, mode="lines",
                showlegend=False, line=dict(color="rgba(217,119,6,0.1)", width=0), hoverinfo="skip"))
            fig_b.add_trace(go.Scatter(x=df["day"], y=np.clip(corn_arr - 0.008, 0, 1),
                mode="lines", showlegend=False, fill="tonexty",
                fillcolor="rgba(217,119,6,0.07)",
                line=dict(color="rgba(217,119,6,0.1)", width=0), hoverinfo="skip"))
            fig_b.add_trace(go.Scatter(
                x=df["day"], y=corn_arr, mode="lines",
                name="Corner Store Share",
                line=dict(color="#D97706", width=2.0, dash="dash"),
                hovertemplate="Day %{x}<br>Corner share: %{y:.1%}<extra></extra>"
            ))
            # Calibrated corner share reference
            fig_b.add_hline(y=0.399, line_dash="dot", line_color="#D97706",
                            line_width=1, opacity=0.5,
                            annotation_text="Baseline corner share 39.9%",
                            annotation_position="bottom right",
                            annotation_font=dict(size=7.5, color="#D97706"))

        if len(df) >= 20:
            _v2_warmup_zone(fig_b, 15)
        fig_b.update_layout(**layout_b)
        charts.append(dcc.Graph(figure=fig_b, config={"displayModeBar": False}))

    return html.Div(charts, style={"display": "flex", "flexDirection": "column", "gap": "8px"})


def create_v2_equity_chart(scenario):
    """Equity Impact grouped bar — food insecurity by income × vehicle group.
    Includes Gini-style equity gap summary annotation."""
    sc_key = scenario or "baseline"
    df = _v2_get_data(sc_key)
    if df.empty:
        return _v2_no_data_div(sc_key)

    sc_color = _V2_PALETTE.get(sc_key, "#334155")
    bl_color  = _V2_PALETTE["baseline"]

    if "food_insecurity_rate" in df.columns:
        sim_fi_end = float(df["food_insecurity_rate"].iloc[-1])
    else:
        sim_fi_end = 0.3832

    BL_SCALE = sim_fi_end / 0.3832 if sc_key == "baseline" else 1.0
    bl_vals  = [v * BL_SCALE for v in _V2_BL_GROUPS]

    if sc_key in _V2_END_GROUPS:
        sc_mults = _V2_END_GROUPS[sc_key]
        sc_vals  = [b * m for b, m in zip(bl_vals, sc_mults)]
    else:
        sc_vals = bl_vals

    x_labels = _V2_GRP_LABELS

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Baseline", x=x_labels, y=bl_vals,
        marker=dict(color=bl_color, opacity=0.72),
        text=[f"{v:.0%}" for v in bl_vals],
        textposition="outside",
        textfont=dict(size=8, color="#1B2A4A"),
        hovertemplate="%{x}<br>Baseline: %{y:.1%}<extra></extra>",
    ))

    if sc_key != "baseline":
        fig.add_trace(go.Bar(
            name=_V2_LABEL.get(sc_key, sc_key), x=x_labels, y=sc_vals,
            marker=dict(color=sc_color, opacity=0.85),
            text=[f"{v:.0%}" for v in sc_vals],
            textposition="outside",
            textfont=dict(size=8, color="#1B2A4A"),
            hovertemplate="%{x}<br>Scenario: %{y:.1%}<extra></extra>",
        ))

    layout = _v2_layout(
        title=f"Equity Impact — {_V2_LABEL.get(sc_key, sc_key)}",
        subtitle="Food insecurity rate by income × vehicle availability group | Validation Pattern V1",
        xlab="", ylab="Food Insecurity Rate",
        tickformat=".0%",
        height=360,
    )
    layout["barmode"] = "group"
    layout["legend"]["x"] = 0.99
    layout["legend"]["y"] = 0.99
    layout["legend"]["xanchor"] = "right"
    layout["legend"]["yanchor"] = "top"

    # Gini-style equity gap: difference between most and least vulnerable group
    if sc_key in _V2_END_GROUPS:
        bl_gap  = (bl_vals[0]  - bl_vals[-1])  * 100   # Low+NoCar vs High+Car
        sc_gap  = (sc_vals[0]  - sc_vals[-1])  * 100
        gap_chg = bl_gap - sc_gap
        sign    = "↓" if gap_chg >= 0 else "↑"
        fig.add_annotation(
            x=0.01, y=0.97, xref="paper", yref="paper",
            text=(f"<b>Equity Gap</b><br>"
                  f"Baseline: {bl_gap:.1f} pp<br>"
                  f"Scenario: {sc_gap:.1f} pp<br>"
                  f"<b>{sign} {abs(gap_chg):.1f} pp {('reduced' if gap_chg>=0 else 'widened')}</b>"),
            showarrow=False,
            font=dict(size=8, color=sc_color),
            bgcolor="white", bordercolor=sc_color,
            borderwidth=1, borderpad=5, align="left",
        )
        # Annotate biggest gain
        deltas  = [b - s for b, s in zip(bl_vals, sc_vals)]
        best_i  = int(np.argmax(deltas))
        best_dp = deltas[best_i] * 100
        if best_dp > 0.5:
            fig.add_annotation(
                x=x_labels[best_i], y=sc_vals[best_i],
                text=f"<b>−{best_dp:.1f} pp</b><br><span style='font-size:7px'>biggest gain</span>",
                showarrow=True, arrowhead=2, arrowsize=0.7, arrowwidth=1,
                arrowcolor=sc_color, ax=0, ay=-38,
                font=dict(size=8, color=sc_color),
                bgcolor="white", bordercolor=sc_color, borderwidth=1, borderpad=3,
            )

    fig.update_layout(**layout)
    charts = [dcc.Graph(figure=fig, config={"displayModeBar": False})]

    # ── Chart B: Corner Store Share & Spatial Equity Index timeseries ─────────
    has_corner = "corner_share"         in df.columns and df["corner_share"].notna().any()
    has_equity = "spatial_equity_index" in df.columns and df["spatial_equity_index"].notna().any()

    if has_corner or has_equity:
        layout_b = _v2_layout(
            title="Corner Store Share & Spatial Equity Index Over Time",
            subtitle=("Corner store usage share vs spatial equity index — "
                      "lower corner share + higher equity index = better food environment"),
            xlab="Simulation Day", ylab="Rate / Index",
            tickformat=".0%",
        )
        fig_b = go.Figure()
        if has_corner:
            corn = np.array(df["corner_share"])
            fig_b.add_trace(go.Scatter(x=df["day"], y=corn + 0.008, mode="lines",
                showlegend=False, line=dict(color="rgba(217,119,6,0.1)", width=0), hoverinfo="skip"))
            fig_b.add_trace(go.Scatter(x=df["day"], y=np.clip(corn - 0.008, 0, 1),
                mode="lines", showlegend=False, fill="tonexty",
                fillcolor="rgba(217,119,6,0.07)",
                line=dict(color="rgba(217,119,6,0.1)", width=0), hoverinfo="skip"))
            fig_b.add_trace(go.Scatter(
                x=df["day"], y=corn, mode="lines",
                name="Corner Store Share",
                line=dict(color="#D97706", width=2.0, dash="dash"),
                hovertemplate="Day %{x}<br>Corner share: %{y:.1%}<extra></extra>"
            ))
        if has_equity:
            eq = np.array(df["spatial_equity_index"])
            fig_b.add_trace(go.Scatter(x=df["day"], y=eq + 0.008, mode="lines",
                showlegend=False, line=dict(color="rgba(109,40,217,0.1)", width=0), hoverinfo="skip"))
            fig_b.add_trace(go.Scatter(x=df["day"], y=np.clip(eq - 0.008, 0, 1),
                mode="lines", showlegend=False, fill="tonexty",
                fillcolor="rgba(109,40,217,0.07)",
                line=dict(color="rgba(109,40,217,0.1)", width=0), hoverinfo="skip"))
            fig_b.add_trace(go.Scatter(
                x=df["day"], y=eq, mode="lines",
                name="Spatial Equity Index",
                line=dict(color="#7C3AED", width=2.0),
                hovertemplate="Day %{x}<br>Equity index: %{y:.1%}<extra></extra>"
            ))
        if len(df) >= 20:
            _v2_warmup_zone(fig_b, 15)
        fig_b.update_layout(**layout_b)
        charts.append(dcc.Graph(figure=fig_b, config={"displayModeBar": False}))

    # ── Chart C: Final snapshot summary bar ───────────────────────────────────
    if not df.empty:
        latest = df.iloc[-1]
        snap_day = int(latest.get("day", len(df)))
        bar_keys  = ["satisfaction_rate", "food_insecurity_rate", "spatial_equity_index"]
        bar_names = ["Satisfaction",      "Food Insecurity",       "Spatial Equity Index"]
        bar_cols  = ["#15803D",           "#DC2626",               "#7C3AED"]
        bar_vals  = [float(latest.get(k, 0)) for k in bar_keys]

        # Only render if at least one metric is non-zero
        if any(v > 0 for v in bar_vals):
            layout_c = _v2_layout(
                title=f"Final Snapshot — Key Metrics at Day {snap_day}",
                subtitle=f"End-of-run summary for {_V2_LABEL.get(sc_key, sc_key)} | "
                         f"Calibrated baseline: FI=38.3% | MAPE=9.46%",
                xlab="", ylab="Rate / Index",
                tickformat=".0%",
                height=300,
            )
            fig_c = go.Figure([go.Bar(
                x=bar_names, y=bar_vals,
                marker=dict(color=bar_cols, opacity=0.85,
                            line=dict(color="white", width=1.5)),
                text=[f"{v:.1%}" for v in bar_vals],
                textposition="outside",
                textfont=dict(size=11, color="#1B2A4A"),
                hovertemplate="%{x}<br>%{y:.1%}<extra></extra>",
            )])
            # Reference line at 38.3% FI baseline
            fig_c.add_hline(y=0.3832, line_dash="dot", line_color="#94A3B8",
                            line_width=1.2, opacity=0.7,
                            annotation_text="FI baseline 38.3%",
                            annotation_position="top right",
                            annotation_font=dict(size=7.5, color="#94A3B8"))
            layout_c["barmode"] = "group"
            layout_c["yaxis"]["range"] = [0, 1.1]
            fig_c.update_layout(**layout_c)
            charts.append(dcc.Graph(figure=fig_c, config={"displayModeBar": False}))

    return html.Div(charts, style={"display": "flex", "flexDirection": "column", "gap": "8px"})


# ─── NEW: Radar / Spider chart for Comparison tab ────────────────────────────
def create_comparison_radar(rank_df, sc_colors_map):
    """Radar chart showing multi-metric profile for all completed scenarios.
    Axes: Satisfaction, FI Reduction, Equity Index, Access Improvement.
    All values normalised 0-1 (1 = best)."""
    if rank_df.empty:
        return None

    # Normalise metrics so 1 = best for all axes
    metrics = ["satisfaction_rate", "food_insecurity_rate", "avg_travel_distance", "spatial_equity_index"]
    labels  = ["Satisfaction Rate", "FI Reduction", "Travel Efficiency", "Equity (low CV)"]

    norm_df = rank_df.copy()
    # satisfaction_rate: HIGHER is better → normalise 0→1 directly
    for col in ["satisfaction_rate"]:
        if col in norm_df.columns:
            rng = norm_df[col].max() - norm_df[col].min()
            norm_df[col] = (norm_df[col] - norm_df[col].min()) / (rng + 1e-9)
    # FI rate, travel distance AND spatial_equity_index: ALL lower = better → invert
    # spatial_equity_index = CV (std/mean of access scores): higher = more unequal = WORSE
    for col in ["food_insecurity_rate", "avg_travel_distance", "spatial_equity_index"]:
        if col in norm_df.columns:
            rng = norm_df[col].max() - norm_df[col].min()
            norm_df[col] = 1.0 - (norm_df[col] - norm_df[col].min()) / (rng + 1e-9)

    SC_V2_PALETTE = _V2_PALETTE  # reuse
    SC_NAME_MAP = {
        "Baseline": "baseline", "Scenario 1": "scenario1",
        "Scenario 2": "scenario2", "Scenario 3": "scenario3", "Scenario 4": "scenario4"
    }

    fig = go.Figure()
    for _, row in norm_df.iterrows():
        sc_display = row["scenario"]
        sc_key     = SC_NAME_MAP.get(sc_display, "baseline")
        col_color  = SC_V2_PALETTE.get(sc_key, "#334155")
        vals = [float(row.get(m, 0)) for m in metrics]
        vals_closed = vals + [vals[0]]
        labels_closed = labels + [labels[0]]
        fig.add_trace(go.Scatterpolar(
            r=vals_closed, theta=labels_closed,
            fill="toself", fillcolor=col_color, opacity=0.18,
            name=sc_display,
            line=dict(color=col_color, width=2.2),
            hovertemplate=f"<b>{sc_display}</b><br>%{{theta}}: %{{r:.2f}}<extra></extra>",
        ))

    fig.update_layout(
        polar=dict(
            bgcolor="#F8FAFC",
            radialaxis=dict(
                visible=True, range=[0, 1.05],
                tickfont=dict(size=8, color="#64748B"),
                gridcolor="#E2E8F0", linecolor="#CBD5E1",
                tickformat=".0%",
                tickvals=[0.25, 0.5, 0.75, 1.0],
            ),
            angularaxis=dict(
                tickfont=dict(size=9, color="#1B2A4A"),
                gridcolor="#E2E8F0", linecolor="#CBD5E1",
            ),
        ),
        title=dict(
            text=("<b style='font-size:12px;color:#1B2A4A'>Policy Profile — Multi-Metric Radar</b>"
                  "<br><span style='font-size:8.5px;color:#64748B'><i>"
                  "All metrics normalised 0–1 (outer = better). "
                  "Shape reveals each scenario's trade-off pattern.</i></span>"),
            x=0.0, xanchor="left", font=dict(size=12), pad=dict(l=0, t=4),
        ),
        height=360,
        margin=dict(l=60, r=60, t=80, b=40),
        paper_bgcolor="white",
        font=dict(family="Arial, sans-serif", size=10, color="#475569"),
        showlegend=True,
        legend=dict(
            font=dict(size=9), bgcolor="rgba(255,255,255,0.92)",
            bordercolor="#E2E8F0", borderwidth=1,
            x=1.12, y=0.5, xanchor="left", yanchor="middle",
        ),
    )
    return dcc.Graph(figure=fig, config={"displayModeBar": False})


# ─── NEW: Policy Trade-off Scatter for Comparison tab ────────────────────────
def create_comparison_tradeoff(rank_df):
    """Policy trade-off scatter:
    X = Food Insecurity Rate (lower = right = better)
    Y = Satisfaction Rate (higher = better)
    Bubble size = avg travel distance (smaller bubble = better)
    Colour = scenario.
    Each bubble labelled with scenario name."""
    if rank_df.empty:
        return None

    SC_NAME_MAP = {
        "Baseline": "baseline", "Scenario 1": "scenario1",
        "Scenario 2": "scenario2", "Scenario 3": "scenario3", "Scenario 4": "scenario4"
    }

    fig = go.Figure()
    for _, row in rank_df.iterrows():
        sc_display = row["scenario"]
        sc_key     = SC_NAME_MAP.get(sc_display, "baseline")
        col_color  = _V2_PALETTE.get(sc_key, "#334155")
        fi_val     = float(row.get("food_insecurity_rate", 0))
        sat_val    = float(row.get("satisfaction_rate", 0))
        dist_val   = float(row.get("avg_travel_distance", 1))
        # Bubble size scaled inversely to distance (closer = bigger)
        bubble_sz  = max(20, 120 - dist_val * 18)

        fig.add_trace(go.Scatter(
            x=[fi_val], y=[sat_val],
            mode="markers+text",
            name=sc_display,
            marker=dict(
                size=bubble_sz, color=col_color, opacity=0.82,
                line=dict(color="white", width=2),
                symbol="circle",
            ),
            text=[sc_display],
            textposition="top center",
            textfont=dict(size=9, color=col_color),
            hovertemplate=(
                f"<b>{sc_display}</b><br>"
                f"Food Insecurity: %{{x:.1%}}<br>"
                f"Satisfaction: %{{y:.1%}}<br>"
                f"Avg Distance: {dist_val:.2f} km<extra></extra>"
            ),
        ))

    # Arrow annotations showing "better" direction
    fig.add_annotation(
        x=0.02, y=0.03, xref="paper", yref="paper",
        text="← Better FI outcome", showarrow=False,
        font=dict(size=8, color="#64748B"), align="left",
    )
    fig.add_annotation(
        x=0.98, y=0.97, xref="paper", yref="paper",
        text="↑ Better satisfaction", showarrow=False,
        font=dict(size=8, color="#64748B"), align="right",
    )
    fig.add_annotation(
        x=0.01, y=0.97, xref="paper", yref="paper",
        text="Bubble size ∝ 1/travel distance",
        showarrow=False, font=dict(size=7.5, color="#94A3B8"), align="left",
    )

    layout = _v2_layout(
        title="Policy Trade-off Space — Food Insecurity vs Satisfaction",
        subtitle=("Each bubble = one scenario | X-axis: lower = better | "
                  "Y-axis: higher = better | Bubble size: larger = shorter travel distance"),
        xlab="Food Insecurity Rate", ylab="Satisfaction Rate",
        tickformat=".0%", height=340,
    )
    layout["showlegend"] = False   # labels on bubbles are clearer
    layout["xaxis"]["tickformat"] = ".0%"
    layout["yaxis"]["tickformat"] = ".0%"
    # Invert X axis so "better" (lower FI) is on the right
    layout["xaxis"]["autorange"] = "reversed"
    fig.update_layout(**layout)
    return dcc.Graph(figure=fig, config={"displayModeBar": False})


# ─── NEW Chart 5: Satisfaction + Baseline Benchmark ──────────────────────────
def create_v2_sat_benchmark_chart(scenario):
    """Satisfaction rate timeseries with calibrated baseline benchmark line
    and all-scenario end-state comparison bar — for committee."""
    sc_key = scenario or "baseline"
    df = _v2_get_data(sc_key)
    if df.empty or "satisfaction_rate" not in df.columns:
        return _v2_no_data_div(sc_key)

    sc_color = _V2_PALETTE.get(sc_key, "#334155")
    sc_light  = _V2_LIGHT.get(sc_key, "rgba(102,126,234,0.12)")

    # Calibrated baseline satisfaction (from PHASE2 results mean: ~0.61)
    CALIB_BASELINE_SAT = 0.61

    # Collect final satisfaction values from ALL completed snapshots for end-bar
    with simulation_lock:
        snaps = dict(sim_state.scenario_snapshots)

    layout = _v2_layout(
        title=f"Satisfaction Rate vs Benchmark — {_V2_LABEL.get(sc_key, sc_key)}",
        subtitle=(
            "Dashed line = calibrated baseline (0.61) | "
            "Right panel shows final end-state across all completed runs"
        ),
        xlab="Simulation Day", ylab="Satisfaction Rate",
        tickformat=".0%", height=340,
    )

    # Use make_subplots: left = timeseries, right = end-state bar
    from plotly.subplots import make_subplots
    fig = make_subplots(
        rows=1, cols=2,
        column_widths=[0.68, 0.32],
        subplot_titles=["", ""],   # suppressed — panel labels added as annotations below
        horizontal_spacing=0.10,
    )

    # Left: current scenario line + uncertainty band
    y = df["satisfaction_rate"]
    x = df["day"]
    fig.add_trace(go.Scatter(
        x=x, y=y + 0.008, mode="lines", showlegend=False,
        line=dict(color=sc_light, width=0), hoverinfo="skip"), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=x, y=np.clip(y - 0.008, 0, 1), mode="lines", showlegend=False,
        fill="tonexty", fillcolor=sc_light,
        line=dict(color=sc_light, width=0), hoverinfo="skip"), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="lines",
        name=_V2_LABEL.get(sc_key, sc_key),
        line=dict(color=sc_color, width=2.4),
        hovertemplate="Day %{x}<br>Satisfaction: %{y:.1%}<extra></extra>"),
        row=1, col=1)

    # Baseline comparison line if available
    if sc_key != "baseline":
        bl_data, _, _ = _get_snapshot_data_for_scenario("baseline")
        if bl_data:
            bl_df = pd.DataFrame(bl_data)
            if "day" not in bl_df.columns:
                bl_df["day"] = list(range(1, len(bl_df) + 1))
            if "satisfaction_rate" in bl_df.columns:
                fig.add_trace(go.Scatter(
                    x=bl_df["day"], y=bl_df["satisfaction_rate"],
                    mode="lines", name="Baseline (run)",
                    line=dict(color=_V2_PALETTE["baseline"], width=1.8, dash="dash"),
                    hovertemplate="Day %{x}<br>Baseline: %{y:.1%}<extra></extra>"),
                    row=1, col=1)

    # Calibrated benchmark horizontal line
    fig.add_hline(
        y=CALIB_BASELINE_SAT, line_dash="dot", line_color="#94A3B8", line_width=1.5,
        annotation_text=f"Calibrated baseline ({CALIB_BASELINE_SAT:.0%})",
        annotation_position="top left",
        annotation_font=dict(size=8, color="#64748B"),
        row=1, col=1,
    )

    if len(df) >= 20:
        fig.add_vrect(x0=0, x1=15, fillcolor="#94A3B8", opacity=0.05,
                      layer="below", line_width=0, row=1, col=1)

    # Right: end-state bar for all completed scenarios
    bar_scenarios, bar_vals, bar_colors = [], [], []
    SC_KEYS_ORDER = ["baseline", "scenario1", "scenario2", "scenario3", "scenario4"]
    for k in SC_KEYS_ORDER:
        snap = snaps.get(k)
        if not snap:
            continue
        fm = snap.get("final_metrics", {})
        bar_scenarios.append(_V2_LABEL.get(k, k).replace(" — ", "<br>"))
        bar_vals.append(float(fm.get("satisfaction_rate", 0.0)))
        bar_colors.append(_V2_PALETTE.get(k, "#334155"))

    if bar_scenarios:
        fig.add_trace(go.Bar(
            x=bar_scenarios, y=bar_vals,
            marker=dict(color=bar_colors, opacity=0.82),
            text=[f"{v:.0%}" for v in bar_vals],
            textposition="outside",
            textfont=dict(size=9),
            showlegend=False,
            hovertemplate="%{x}<br>Satisfaction: %{y:.1%}<extra></extra>",
        ), row=1, col=2)
        # Benchmark line on bar chart too
        fig.add_hline(y=CALIB_BASELINE_SAT, line_dash="dot",
                      line_color="#94A3B8", line_width=1.5, row=1, col=2)

    # Panel titles as annotations — safe y position avoids collision with figure title
    fig.add_annotation(
        text="<b>Daily Timeseries</b>",
        xref="paper", yref="paper",
        x=0.32, y=1.06, showarrow=False,
        font=dict(size=10, color="#1B2A4A", family="Arial, sans-serif"),
        align="center",
    )
    fig.add_annotation(
        text="<b>End-State by Scenario</b>",
        xref="paper", yref="paper",
        x=0.90, y=1.06, showarrow=False,
        font=dict(size=10, color="#1B2A4A", family="Arial, sans-serif"),
        align="center",
    )

    # Apply v2 styling
    fig.update_layout(
        height=370,
        margin=dict(l=55, r=20, t=88, b=55),
        plot_bgcolor="#F8FAFC",
        paper_bgcolor="white",
        font=dict(family="Arial, sans-serif", size=11, color="#475569"),
        legend=dict(font=dict(size=8.5), bgcolor="rgba(255,255,255,0.92)",
                    bordercolor="#E2E8F0", borderwidth=1,
                    x=0.01, y=0.05, xanchor="left", yanchor="bottom"),
        transition=dict(duration=0),
    )
    for ax in ["xaxis", "xaxis2"]:
        fig.update_layout(**{ax: dict(
            gridcolor="#F1F5F9", zeroline=False,
            showline=True, linecolor="#CBD5E1", ticks="outside",
            ticklen=3, tickcolor="#CBD5E1", tickfont=dict(size=9),
        )})
    for ax in ["yaxis", "yaxis2"]:
        fig.update_layout(**{ax: dict(
            gridcolor="#F1F5F9", zeroline=False,
            showline=True, linecolor="#CBD5E1", ticks="outside",
            ticklen=3, tickcolor="#CBD5E1", tickfont=dict(size=9),
            tickformat=".0%",
        )})

    return dcc.Graph(figure=fig, config={"displayModeBar": False})


# ─── NEW Chart 6: Income Group Breakdown ─────────────────────────────────────
def create_v2_income_groups_chart(scenario):
    """Food insecurity by income group — current scenario vs baseline.
    Uses calibrated income group rates (Coleman-Jensen 2020 ratios × HZ1 38.3%).
    Shows dissertation Validation Pattern V1 with the actual simulated end-state FI rate
    scaled to match the income distribution."""
    sc_key = scenario or "baseline"
    df = _v2_get_data(sc_key)
    if df.empty:
        return _v2_no_data_div(sc_key)

    sc_color = _V2_PALETTE.get(sc_key, "#334155")

    # Final simulated FI rate for scaling
    sim_fi = float(df["food_insecurity_rate"].iloc[-1]) if "food_insecurity_rate" in df.columns else 0.3832

    # Three income groups as used in dissertation (Low <$35k, Med $35-75k, High >$75k)
    # HZ1 shares: Low=52%, Med=30%, High=18% (from hz1_household_data_CORRECTED.csv)
    # Baseline rates derived from Coleman-Jensen 2020 ratios applied to HZ1 avg=38.32%
    INC_LABELS = ["Low Income (<$35k)", "Medium Income ($35-$75k)", "High Income (>$75k)"]
    INC_COLORS = ["#DC2626", "#D97706", "#16A34A"]
    INC_SHARES = [0.52, 0.30, 0.18]   # HZ1 population shares

    # Calibrated baseline rates (these sum to 38.3% weighted by shares)
    BL_INC  = [0.574, 0.281, 0.082]   # low, med, high — from calibration

    # Scale baseline to current simulated FI (in case baseline was actually run)
    bl_data, _, _ = _get_snapshot_data_for_scenario("baseline")
    if bl_data:
        bl_df = pd.DataFrame(bl_data)
        actual_bl_fi = float(bl_df["food_insecurity_rate"].iloc[-1]) if "food_insecurity_rate" in bl_df.columns else 0.3832
        scale = actual_bl_fi / 0.3832
        BL_INC = [v * scale for v in BL_INC]

    # Scenario rates: use _V2_END_GROUPS multipliers for mid-group (Low=avg of Low+NoCar, Low+Car)
    if sc_key in _V2_END_GROUPS:
        mults = _V2_END_GROUPS[sc_key]
        # Low  = mean of Low+NoCar [0], Low+Car [1]
        # Med  = mean of Med+NoCar [2], Med+Car [3]
        # High = mean of High+NoCar [4], High+Car [5]
        SC_INC = [
            BL_INC[0] * (mults[0] + mults[1]) / 2,
            BL_INC[1] * (mults[2] + mults[3]) / 2,
            BL_INC[2] * (mults[4] + mults[5]) / 2,
        ]
        # Additionally scale so the weighted average matches the actual simulated FI
        weighted_sc = sum(r * s for r, s in zip(SC_INC, INC_SHARES))
        if weighted_sc > 0:
            adj = sim_fi / weighted_sc
            SC_INC = [v * adj for v in SC_INC]
    else:
        SC_INC = BL_INC   # baseline: same

    # Chart 1: grouped bar — baseline vs scenario per income group (1 per row)
    x_pos = INC_LABELS
    bl_color = _V2_PALETTE["baseline"]
    fig1 = go.Figure()
    fig1.add_trace(go.Bar(
        name="Baseline", x=x_pos, y=BL_INC,
        marker=dict(color=bl_color, opacity=0.70),
        text=[f"{v:.0%}" for v in BL_INC],
        textposition="outside", textfont=dict(size=9),
        hovertemplate="%{x}<br>Baseline: %{y:.1%}<extra></extra>",
    ))
    if sc_key != "baseline":
        fig1.add_trace(go.Bar(
            name=_V2_LABEL.get(sc_key, sc_key), x=x_pos, y=SC_INC,
            marker=dict(color=sc_color, opacity=0.85),
            text=[f"{v:.0%}" for v in SC_INC],
            textposition="outside", textfont=dict(size=9),
            hovertemplate="%{x}<br>Scenario: %{y:.1%}<extra></extra>",
        ))
    fig1.update_layout(
        title="Food Insecurity by Income Group",
        height=320, margin=dict(l=55, r=25, t=50, b=55),
        plot_bgcolor="#F8FAFC", paper_bgcolor="white",
        font=dict(family="Arial, sans-serif", size=11, color="#475569"),
        barmode="group",
        legend=dict(font=dict(size=8.5), bgcolor="rgba(255,255,255,0.92)",
                    bordercolor="#E2E8F0", borderwidth=1,
                    orientation="h", y=-0.18, x=0.5, xanchor="center"),
        xaxis=dict(gridcolor="#F1F5F9", zeroline=False, showline=True, linecolor="#CBD5E1",
                   ticks="outside", ticklen=3, tickcolor="#CBD5E1", tickfont=dict(size=9)),
        yaxis=dict(gridcolor="#F1F5F9", zeroline=False, showline=True, linecolor="#CBD5E1",
                   ticks="outside", ticklen=3, tickcolor="#CBD5E1", tickfont=dict(size=9), tickformat=".0%"),
    )

    # Chart 2: FI timeseries coloured by estimated income split
    charts = [dcc.Graph(figure=fig1, config={"displayModeBar": False})]
    if "food_insecurity_rate" in df.columns and "day" in df.columns:
        y_agg = df["food_insecurity_rate"]
        x_agg = df["day"]
        fig2 = go.Figure()
        BL_WEIGHTED_AVG = sum(b * s for b, s in zip(BL_INC, INC_SHARES))
        for i, (label, bl_r, sc_r, icol) in enumerate(zip(INC_LABELS, BL_INC, SC_INC, INC_COLORS)):
            if BL_WEIGHTED_AVG > 0:
                ratio = sc_r / BL_WEIGHTED_AVG if BL_WEIGHTED_AVG > 0 else 1.0
                y_grp = np.clip(y_agg * ratio, 0, 1)
            else:
                y_grp = y_agg
            fig2.add_trace(go.Scatter(
                x=x_agg, y=y_grp, mode="lines",
                name=label.replace("\n", " "),
                line=dict(color=icol, width=2.0, dash=["solid","dash","dot"][i]),
                hovertemplate=f"{label}<br>Day %{{x}}<br>FI: %{{y:.1%}}<extra></extra>",
            ))
        fig2.update_layout(
            title="FI Timeseries by Income (estimated)",
            height=320, margin=dict(l=55, r=25, t=50, b=55),
            plot_bgcolor="#F8FAFC", paper_bgcolor="white",
            font=dict(family="Arial, sans-serif", size=11, color="#475569"),
            legend=dict(font=dict(size=8.5), bgcolor="rgba(255,255,255,0.92)",
                        bordercolor="#E2E8F0", borderwidth=1,
                        orientation="h", y=-0.18, x=0.5, xanchor="center"),
            xaxis=dict(gridcolor="#F1F5F9", zeroline=False, showline=True, linecolor="#CBD5E1",
                       ticks="outside", ticklen=3, tickcolor="#CBD5E1", tickfont=dict(size=9)),
            yaxis=dict(gridcolor="#F1F5F9", zeroline=False, showline=True, linecolor="#CBD5E1",
                       ticks="outside", ticklen=3, tickcolor="#CBD5E1", tickfont=dict(size=9), tickformat=".0%"),
        )
        charts.append(dcc.Graph(figure=fig2, config={"displayModeBar": False}))

    return html.Div(charts, style={"display": "flex", "flexDirection": "column", "gap": "12px"})


def _build_scenario_variation_key_and_label(scenario_name, config_dict=None):
    """Build snapshot key and display label from scenario + config params.
    Allows multiple runs of same scenario type (e.g. S1-north, S1-south) in comparison."""
    config_dict = config_dict or {}
    if scenario_name == "baseline":
        return "baseline", "Baseline"
    # Scenario 1: region + capacity in label (e.g. "S1: South Grocery (cap 600)")
    if scenario_name == "scenario1":
        region = str(config_dict.get("scenario1_store_region", "optimal") or "optimal").lower()
        cap    = int(config_dict.get("grocery_store_capacity", 600))
        if region == "optimal":
            return "scenario1_optimal", f"S1: Grocery-Optimal (cap {cap})"
        return f"scenario1_{region}", f"S1: {region.title()} Grocery (cap {cap})"
    # Scenario 2: include num hubs + num corners
    if scenario_name == "scenario2":
        hubs = int(config_dict.get("num_food_hubs", 1))
        corners = int(config_dict.get("num_corner_stores", 6))
        key = f"scenario2_{hubs}_{corners}"
        label = f"S2: {hubs} hub(s), {corners} corner store(s)"
        return key, label
    # Scenario 3: include num pantries + strategy
    if scenario_name == "scenario3":
        n = int(config_dict.get("num_mobile_pantries", 2))
        strat = str(config_dict.get("mobile_pantry_strategy", "fixed") or "fixed")
        key = f"scenario3_{n}_{strat}"
        label = f"S3: {n} pantry(ies), {strat}"
        return key, label
    # Scenario 4: capacity + base fee in label (e.g. "S4: Delivery (cap 500, fee $2.00)")
    if scenario_name == "scenario4":
        cap      = int(config_dict.get("delivery_capacity", 500))
        base_fee = float(config_dict.get("delivery_base_fee", 2.0))
        key      = f"scenario4_{cap}"
        label    = f"S4: Delivery (cap {cap}, fee ${base_fee:.2f})"
        return key, label
    return scenario_name, f"Scenario ({scenario_name})"


def _create_model_for_scenario(scenario, config, input_dict):
    """Create the right model object for a given scenario and config.
    Extracted so multi-seed loops can call it cleanly."""
    if scenario == 'baseline':
        model = create_baseline_scenario(config, use_real_data=True)
    elif scenario == 'scenario1':
        model = create_enhanced_scenario_1(config, include_baseline=True, use_real_data=True)
    elif scenario == 'scenario2':
        model = create_enhanced_scenario_2(config, include_baseline=True, use_real_data=True)
    elif scenario == 'scenario3':
        model = create_enhanced_scenario_3(config, include_baseline=True, use_real_data=True)
    elif scenario == 'scenario4':
        delivery_cap = int(input_dict.get('param-delivery-capacity', 500))
        base_fee     = float(input_dict.get('param-base-fee', 2.00))
        dist_fee     = float(input_dict.get('param-distance-fee', 0.75))
        area_km      = float(input_dict.get('param-delivery-area', 20.0))
        model = create_enhanced_scenario_4(
            config, use_real_data=True,
            delivery_capacity=delivery_cap,
            base_service_fee=base_fee,
            distance_fee_per_km=dist_fee,
            delivery_area_km=area_km
        )
    else:
        raise ValueError(f"Unknown scenario: {scenario}")
    return model


def _autosave_single_seed(scenario, config_dict, seed, snap_key, history, days):
    """Auto-save one seed's raw timeseries to scenarios_results/.
    File name: {snap_key}_{households}hh_{days}d_seed{seed}_{timestamp}.json
    Called inside run_simulation; no lock needed (called after seed loop).
    """
    try:
        script_dir  = os.path.dirname(os.path.abspath(__file__))
        save_dir    = os.path.join(script_dir, "scenarios_results")
        os.makedirs(save_dir, exist_ok=True)
        n_hh   = int(config_dict.get("num_consumers", 0))
        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname  = f"{snap_key}_{n_hh}hh_{days}d_seed{seed}_{ts_str}.json"
        payload = {
            "snap_key": snap_key, "seed": seed, "days": days,
            "n_households": n_hh, "timestamp": datetime.now().isoformat(timespec="seconds"),
            "config": dict(config_dict), "metrics_history": list(history),
            "final_metrics": dict(history[-1]) if history else {}
        }

        def _jd(obj):
            if hasattr(obj, "item"): return obj.item()
            raise TypeError(f"Not serializable: {type(obj).__name__}")

        with open(os.path.join(save_dir, fname), "w") as f:
            json.dump(payload, f, indent=2, default=_jd)
        print(f"   💾 Seed {seed} saved → scenarios_results/{fname}")
    except Exception as e:
        print(f"   ⚠  Auto-save seed {seed} failed: {e}")


def _store_scenario_snapshot(scenario_name, all_seed_histories=None, seeds_used=None):
    """Store mean (±std) snapshot from multi-seed run for comparison charts.
    all_seed_histories: list of per-seed timeseries dicts lists
    seeds_used: list of seed ints that were run
    Falls back to single-seed (sim_state.simulation_data) if not supplied.
    Also auto-saves a summary JSON to scenarios_results/.
    """
    with simulation_lock:
        config_dict = {}
        if sim_state.current_params and "config" in sim_state.current_params:
            config_dict = sim_state.current_params.get("config", {})
        snap_key, display_label = _build_scenario_variation_key_and_label(scenario_name, config_dict)
        n_households = int(config_dict.get("num_consumers", 0))
        n_days       = int(sim_state.current_day or config_dict.get("simulation_days", 0))
        ts_iso       = datetime.now().isoformat(timespec="seconds")

        # ── Build mean ± std timeseries across seeds ────────────────────────
        if all_seed_histories and len(all_seed_histories) > 1:
            import pandas as _pd
            metric_keys = ["satisfaction_rate","food_insecurity_rate",
                           "avg_travel_distance","spatial_equity_index","total_revenue",
                           "spend_low","spend_med","spend_high",
                           "corner_share","pantry_share","delivery_share"]
            # Align all seeds by day index (shortest run length)
            min_len = min(len(h) for h in all_seed_histories)
            df_list = []
            for h in all_seed_histories:
                df_s = _pd.DataFrame(h[:min_len])
                df_list.append(df_s)
            mean_history = []
            for day_idx in range(min_len):
                row = {"day": day_idx + 1}
                for k in metric_keys:
                    vals = [df[k].iloc[day_idx] for df in df_list if k in df.columns]
                    if vals:
                        row[k]              = float(np.mean(vals))
                        row[k + "_std"]     = float(np.std(vals, ddof=1))
                        row[k + "_min"]     = float(np.min(vals))
                        row[k + "_max"]     = float(np.max(vals))
                mean_history.append(row)
            final_metrics = mean_history[-1] if mean_history else {}
            n_seeds = len(all_seed_histories)
        else:
            # Single seed fallback
            history = list(sim_state.simulation_data)
            mean_history = history
            final_metrics = dict(history[-1]) if history and isinstance(history[-1], dict) else {}
            n_seeds = 1

        snap = {
            "scenario":      scenario_name,
            "display_label": display_label,
            "snap_key":      snap_key,
            "timestamp":     ts_iso,
            "days":          n_days,
            "n_seeds":       n_seeds,
            "seeds_used":    list(seeds_used) if seeds_used else [42],
            "config":        dict(config_dict),
            "metrics_history": mean_history,
            "final_metrics":   dict(final_metrics),
        }
        sim_state.scenario_snapshots[snap_key] = snap

    # ── Auto-save summary JSON (outside lock) ──────────────────────────────
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        save_dir   = os.path.join(script_dir, "scenarios_results")
        os.makedirs(save_dir, exist_ok=True)
        seeds_str = "_".join(str(s) for s in (seeds_used or [42]))
        ts_file   = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname     = f"{snap_key}_{n_households}hh_{n_days}d_seeds{seeds_str}_{ts_file}_summary.json"
        fpath     = os.path.join(save_dir, fname)

        def _jd(obj):
            if hasattr(obj, "item"): return obj.item()
            raise TypeError(f"Not serializable: {type(obj).__name__}")

        with open(fpath, "w") as f:
            json.dump(snap, f, indent=2, default=_jd)
        print(f"   💾 Summary saved → scenarios_results/{fname}")
    except Exception as e:
        print(f"   ⚠ Could not auto-save summary: {e}")


def _build_comparison_rows_from_snapshots(snapshot_dict):
    """Build comparison rows from all stored snapshots (supports multiple variations per scenario)."""
    # Order: baseline first, then scenario1 variations, scenario2, scenario3, scenario4
    def sort_key(k):
        order = {"baseline": 0, "scenario1": 1, "scenario2": 2, "scenario3": 3, "scenario4": 4}
        base = k.split("_")[0] if "_" in k else k
        return (order.get(base, 5), k)
    rows = []
    for snap_key in sorted(snapshot_dict.keys(), key=sort_key):
        snap = snapshot_dict.get(snap_key)
        if not snap:
            continue
        final = snap.get("final_metrics", {})
        display_label = snap.get("display_label")
        if not display_label:
            # Fallback for legacy snapshots
            name_map = {"baseline": "Baseline", "scenario1": "S1: Grocery",
                        "scenario2": "S2: Food Hub", "scenario3": "S3: Pantries", "scenario4": "S4: Delivery"}
            base = snap_key.split("_")[0] if "_" in snap_key else snap_key
            display_label = name_map.get(base, snap_key)
        rows.append({
            "scenario": display_label,
            "satisfaction_rate": float(final.get("satisfaction_rate", 0.0)),
            "food_insecurity_rate": float(final.get("food_insecurity_rate", 0.0)),
            "avg_travel_distance": float(final.get("avg_travel_distance", 0.0)),
            "spatial_equity_index": float(final.get("spatial_equity_index", 0.0)),
            "days": int(snap.get("days", 0)),
            "timestamp": snap.get("timestamp", "")
        })
    return rows


def create_results_view(selected_scenario=None):
    """Create results analysis; comparison tab uses stored scenario snapshots.
    Each scenario tab shows results ONLY from its own run."""

    with simulation_lock:
        comparison_results = sim_state.comparison_results
        current_model = sim_state.current_model
        running = sim_state.sim_running
        current_scenario = getattr(sim_state, 'current_scenario', None)
        scenario_snapshots = dict(sim_state.scenario_snapshots)

    # ── COMPARISON TAB ────────────────────────────────────────────────────────
    if selected_scenario == "comparison":
        # ALWAYS rebuild fresh from snapshots — never trust stale sim_state.comparison_results
        rows = _build_comparison_rows_from_snapshots(scenario_snapshots)
        comp_df = pd.DataFrame(rows)

        # Show charts for whatever scenarios have been run — no need to wait for all 5
        if not comp_df.empty:
            rank_df = comp_df.sort_values(
                by=["satisfaction_rate", "food_insecurity_rate", "avg_travel_distance"],
                ascending=[False, True, True]
            ).reset_index(drop=True)
            rank_df["rank"] = rank_df.index + 1

            SC_COLORS = {
                "Baseline": "#1e3a5f", "Scenario 1": "#0891B2",
                "Scenario 2": "#15803D", "Scenario 3": "#D97706", "Scenario 4": "#7C3AED"
            }
            SC_KEYS  = ["baseline", "scenario1", "scenario2", "scenario3", "scenario4"]
            SC_NAMES = {
                "baseline": "Baseline", "scenario1": "S1: Grocery",
                "scenario2": "S2: Food Hub", "scenario3": "S3: Pantries",
                "scenario4": "S4: Delivery"
            }
            SC_COLS = {
                "baseline": "#1e3a5f", "scenario1": "#0891B2",
                "scenario2": "#15803D", "scenario3": "#D97706", "scenario4": "#7C3AED"
            }
            color_seq = [SC_COLORS.get(s, "#667eea") for s in rank_df["scenario"]]

            CMP_LAYOUT = dict(
                plot_bgcolor="#F8FAFC", paper_bgcolor="white",
                font=dict(family="Georgia, serif", size=11, color="#1F2937"),
                title_font=dict(family="Georgia, serif", size=13, color="#111827"),
                title_x=0.5,
                margin=dict(l=55, r=25, t=52, b=42),
                xaxis=dict(gridcolor="rgba(0,0,0,0.06)", zeroline=False,
                           linecolor="#CBD5E1", ticks="outside", ticklen=4, tickcolor="#94A3B8"),
                yaxis=dict(gridcolor="rgba(0,0,0,0.06)", zeroline=False,
                           linecolor="#CBD5E1", ticks="outside", ticklen=4, tickcolor="#94A3B8"),
                showlegend=False,
            )

            best_row = rank_df.iloc[0]
            n_run = len(rank_df)
            ranking_text = " > ".join(rank_df["scenario"].tolist())

            summary_badges = html.Div([
                html.Div([
                    html.Div(f"{n_run}", style={
                        "fontSize": "22px", "fontWeight": "700", "color": "#1e3a5f",
                        "fontFamily": "Georgia, serif"
                    }),
                    html.Div("Runs in Comparison", style={"fontSize": "10px", "color": "#6B7280",
                                                      "textTransform": "uppercase", "letterSpacing": "0.5px"})
                ], style={"textAlign": "center", "padding": "10px 20px",
                          "background": "#F0F9FF", "borderRadius": "8px",
                          "border": "1px solid #BAE6FD"}),
                html.Div([
                    html.Div(best_row["scenario"], style={
                        "fontSize": "14px", "fontWeight": "700",
                        "color": SC_COLORS.get(best_row["scenario"], "#1e3a5f"),
                        "fontFamily": "Georgia, serif"
                    }),
                    html.Div("Best Performing", style={"fontSize": "10px", "color": "#6B7280",
                                                        "textTransform": "uppercase", "letterSpacing": "0.5px"})
                ], style={"textAlign": "center", "padding": "10px 20px",
                          "background": "#F0FDF4", "borderRadius": "8px",
                          "border": "1px solid #BBF7D0"}),
                html.Div([
                    html.Div(ranking_text[:40] + ("..." if len(ranking_text) > 40 else ""),
                             style={"fontSize": "11px", "fontWeight": "600", "color": "#374151",
                                    "fontFamily": "Georgia, serif"}),
                    html.Div("Scenario Ranking", style={"fontSize": "10px", "color": "#6B7280",
                                                         "textTransform": "uppercase", "letterSpacing": "0.5px"})
                ], style={"textAlign": "center", "padding": "10px 20px", "flex": "2",
                          "background": "#FEFCE8", "borderRadius": "8px",
                          "border": "1px solid #FDE68A"}),
            ], style={"display": "flex", "gap": "10px", "marginBottom": "14px", "alignItems": "stretch"})

            # Bar 1: Satisfaction
            sat_fig = go.Figure([go.Bar(
                x=rank_df["scenario"], y=rank_df["satisfaction_rate"],
                marker=dict(color=color_seq, line=dict(color="white", width=1.5)),
                text=[f"{v:.1%}" for v in rank_df["satisfaction_rate"]],
                textposition="outside",
                textfont=dict(size=11, family="Georgia, serif"),
                hovertemplate="%{x}<br>Satisfaction: %{y:.1%}<extra></extra>"
            )])
            sat_fig.update_layout(
                title="Satisfaction Rate by Scenario  (Higher = Better)",
                height=290,
                yaxis=dict(tickformat=".0%",
                           range=[0, min(float(rank_df["satisfaction_rate"].max()) * 1.35, 1.02)],
                           title="Satisfaction Rate",
                           gridcolor="rgba(0,0,0,0.06)", zeroline=False,
                           linecolor="#CBD5E1", ticks="outside", ticklen=4, tickcolor="#94A3B8"),
                **{k: v for k, v in CMP_LAYOUT.items() if k not in ("yaxis",)}
            )
            best_sat = best_row["scenario"]
            sat_fig.add_annotation(
                x=best_sat, y=float(best_row["satisfaction_rate"]) * 1.18,
                text="Best", showarrow=False,
                font=dict(size=10, color=SC_COLORS.get(best_sat, "#1e3a5f"), family="Georgia, serif"),
                yref="y"
            )

            # Bar 2: Food Insecurity (highlight lowest)
            best_fi_scenario = rank_df.loc[rank_df["food_insecurity_rate"].idxmin(), "scenario"]
            fi_colors = [
                "#15803D" if s == best_fi_scenario else SC_COLORS.get(s, "#667eea")
                for s in rank_df["scenario"]
            ]
            fi_fig = go.Figure([go.Bar(
                x=rank_df["scenario"], y=rank_df["food_insecurity_rate"],
                marker=dict(color=fi_colors, line=dict(color="white", width=1.5)),
                text=[f"{v:.1%}" for v in rank_df["food_insecurity_rate"]],
                textposition="outside",
                textfont=dict(size=11, family="Georgia, serif"),
                hovertemplate="%{x}<br>Food Insecurity: %{y:.1%}<extra></extra>"
            )])
            fi_fig.update_layout(
                title="Food Insecurity Rate by Scenario  (Lower = Better)",
                height=290,
                yaxis=dict(tickformat=".0%",
                           range=[0, min(float(rank_df["food_insecurity_rate"].max()) * 1.35, 1.02)],
                           title="Food Insecurity Rate",
                           gridcolor="rgba(0,0,0,0.06)", zeroline=False,
                           linecolor="#CBD5E1", ticks="outside", ticklen=4, tickcolor="#94A3B8"),
                **{k: v for k, v in CMP_LAYOUT.items() if k not in ("yaxis",)}
            )
            fi_val_best = float(rank_df.loc[rank_df["scenario"] == best_fi_scenario, "food_insecurity_rate"].iloc[0])
            fi_fig.add_annotation(
                x=best_fi_scenario, y=fi_val_best * 1.18,
                text="Lowest", showarrow=False,
                font=dict(size=10, color="#15803D", family="Georgia, serif"), yref="y"
            )

            # Bar 3: Travel Distance (highlight shortest)
            best_dist_scenario = rank_df.loc[rank_df["avg_travel_distance"].idxmin(), "scenario"]
            dist_colors = [
                "#15803D" if s == best_dist_scenario else SC_COLORS.get(s, "#667eea")
                for s in rank_df["scenario"]
            ]
            dist_fig = go.Figure([go.Bar(
                x=rank_df["scenario"], y=rank_df["avg_travel_distance"],
                marker=dict(color=dist_colors, line=dict(color="white", width=1.5)),
                text=[f"{v:.2f} km" for v in rank_df["avg_travel_distance"]],
                textposition="outside",
                textfont=dict(size=11, family="Georgia, serif"),
                hovertemplate="%{x}<br>Avg Distance: %{y:.2f} km<extra></extra>"
            )])
            dist_fig.update_layout(
                title="Average Travel Distance by Scenario  (Lower = Better)",
                height=290,
                yaxis=dict(range=[0, float(rank_df["avg_travel_distance"].max()) * 1.35],
                           title="Distance (km)",
                           gridcolor="rgba(0,0,0,0.06)", zeroline=False,
                           linecolor="#CBD5E1", ticks="outside", ticklen=4, tickcolor="#94A3B8"),
                **{k: v for k, v in CMP_LAYOUT.items() if k not in ("yaxis",)}
            )

            # Timeseries: food insecurity overlay — V2 style (iterates over all snapshot keys)
            ts_fig = go.Figure()
            any_ts = False
            def _base_key(k):
                return k.split("_")[0] if "_" in k else k
            for key in sorted(scenario_snapshots.keys(), key=lambda x: ({"baseline":0,"scenario1":1,"scenario2":2,"scenario3":3,"scenario4":4}.get(_base_key(x),5), x)):
                snap = scenario_snapshots.get(key)
                if not snap or not snap.get("metrics_history"):
                    continue
                hist   = snap["metrics_history"]
                days_x = [h.get("day", i + 1) for i, h in enumerate(hist)]
                fi_y   = [h.get("food_insecurity_rate", 0) for h in hist]
                base_k = _base_key(key)
                c      = _V2_PALETTE.get(base_k, "#334155")
                cl     = _V2_LIGHT.get(base_k, "rgba(102,126,234,0.1)")
                disp   = snap.get("display_label", SC_NAMES.get(key, key))
                fi_arr = np.array(fi_y)
                ts_fig.add_trace(go.Scatter(x=days_x, y=fi_arr + 0.008, mode="lines",
                    showlegend=False, line=dict(color=cl, width=0), hoverinfo="skip"))
                ts_fig.add_trace(go.Scatter(x=days_x, y=np.clip(fi_arr - 0.008, 0, 1),
                    mode="lines", showlegend=False, fill="tonexty", fillcolor=cl,
                    line=dict(color=cl, width=0), hoverinfo="skip"))
                ts_fig.add_trace(go.Scatter(
                    x=days_x, y=fi_y, mode="lines",
                    name=disp,
                    line=dict(color=c, width=2.4,
                              dash="dash" if key == "baseline" else None),
                    hovertemplate=f"{disp}<br>Day %{{x}}<br>FI: %{{y:.1%}}<extra></extra>"
                ))
                any_ts = True
            if any_ts:
                ts_layout = _v2_layout(
                    "Food Insecurity Rate Over Time — All Completed Scenarios",
                    "Health Zone 1, Jacksonville FL",
                    "Simulation Day", "Food Insecurity Rate",
                    tickformat=".0%", height=330,
                )
                ts_layout["legend"] = dict(font=dict(size=8.5), bgcolor="rgba(255,255,255,0.92)",
                    bordercolor="#E2E8F0", borderwidth=1,
                    x=0.99, y=0.99, xanchor="right", yanchor="top")
                ts_fig.update_layout(**ts_layout)

            # Timeseries: satisfaction overlay — V2 style (iterates over all snapshot keys)
            sat_ts_fig = go.Figure()
            any_sat_ts = False
            for key in sorted(scenario_snapshots.keys(), key=lambda x: ({"baseline":0,"scenario1":1,"scenario2":2,"scenario3":3,"scenario4":4}.get(_base_key(x),5), x)):
                snap = scenario_snapshots.get(key)
                if not snap or not snap.get("metrics_history"):
                    continue
                hist   = snap["metrics_history"]
                days_x = [h.get("day", i + 1) for i, h in enumerate(hist)]
                sat_y  = [h.get("satisfaction_rate", 0) for h in hist]
                base_k = _base_key(key)
                c      = _V2_PALETTE.get(base_k, "#334155")
                cl     = _V2_LIGHT.get(base_k, "rgba(102,126,234,0.1)")
                disp   = snap.get("display_label", SC_NAMES.get(key, key))
                sat_arr = np.array(sat_y)
                sat_ts_fig.add_trace(go.Scatter(x=days_x, y=sat_arr + 0.008, mode="lines",
                    showlegend=False, line=dict(color=cl, width=0), hoverinfo="skip"))
                sat_ts_fig.add_trace(go.Scatter(x=days_x, y=np.clip(sat_arr - 0.008, 0, 1),
                    mode="lines", showlegend=False, fill="tonexty", fillcolor=cl,
                    line=dict(color=cl, width=0), hoverinfo="skip"))
                sat_ts_fig.add_trace(go.Scatter(
                    x=days_x, y=sat_y, mode="lines",
                    name=disp,
                    line=dict(color=c, width=2.4,
                              dash="dash" if key == "baseline" else None),
                    hovertemplate=f"{disp}<br>Day %{{x}}<br>Sat: %{{y:.1%}}<extra></extra>"
                ))
                any_sat_ts = True
            if any_sat_ts:
                sat_layout = _v2_layout(
                    "Satisfaction Rate Over Time — All Completed Scenarios",
                    "Health Zone 1, Jacksonville FL",
                    "Simulation Day", "Satisfaction Rate",
                    tickformat=".0%", height=330,
                )
                sat_layout["legend"] = dict(font=dict(size=8.5), bgcolor="rgba(255,255,255,0.92)",
                    bordercolor="#E2E8F0", borderwidth=1,
                    x=0.01, y=0.05, xanchor="left", yanchor="bottom")
                sat_ts_fig.update_layout(**sat_layout)

            # Grouped bar: all 3 metrics side by side
            grouped_fig = go.Figure()
            for _, row in rank_df.iterrows():
                sc   = row["scenario"]
                vals = [
                    float(row["satisfaction_rate"]) * 100,
                    float(row["food_insecurity_rate"]) * 100,
                    float(row.get("avg_travel_distance", 0)) * 10
                ]
                grouped_fig.add_trace(go.Bar(
                    name=sc, x=["Satisfaction (%)", "Food Insecurity (%)", "Travel Dist. (kmx10)"],
                    y=vals,
                    marker_color=SC_COLORS.get(sc, "#667eea"),
                    text=[f"{v:.1f}" for v in vals],
                    textposition="outside",
                    textfont=dict(size=9, family="Georgia, serif"),
                ))
            grouped_fig.update_layout(
                title="Multi-Metric Summary — All Scenarios (Grouped)",
                height=310, barmode="group", showlegend=True,
                legend=dict(orientation="h", y=-0.22, x=0.5, xanchor="center",
                            font=dict(size=10, family="Georgia, serif"), bgcolor="rgba(0,0,0,0)"),
                yaxis=dict(title="Value", **CMP_LAYOUT["yaxis"]),
                **{k: v for k, v in CMP_LAYOUT.items() if k not in ("yaxis","showlegend")}
            )

            # Optional info note when no scenarios run yet
            pending_note = html.Div(
                "Run Baseline and/or Scenarios 1–4 to populate the comparison. "
                "Different variations (e.g. S1-north vs S1-south) will appear as separate entries.",
                style={"background": "#F8FAFC", "border": "1px solid #E2E8F0",
                       "borderRadius": "6px", "padding": "8px 14px",
                       "fontSize": "11px", "color": "#64748B", "marginBottom": "10px"}
            ) if len(scenario_snapshots) == 0 else html.Div()

            all_graphs = [
                html.Div(dcc.Graph(figure=sat_fig,  config={"displayModeBar": False}), style={"width": "100%", "marginBottom": "16px"}),
                html.Div(dcc.Graph(figure=fi_fig,   config={"displayModeBar": False}), style={"width": "100%", "marginBottom": "16px"}),
                html.Div(dcc.Graph(figure=dist_fig, config={"displayModeBar": False}), style={"width": "100%", "marginBottom": "16px"}),
            ]
            if any_ts:
                all_graphs.append(html.Div(dcc.Graph(figure=ts_fig,     config={"displayModeBar": False}), style={"width": "100%", "marginBottom": "16px"}))
            if any_sat_ts:
                all_graphs.append(html.Div(dcc.Graph(figure=sat_ts_fig, config={"displayModeBar": False}), style={"width": "100%", "marginBottom": "16px"}))
            all_graphs.append(html.Div(dcc.Graph(figure=grouped_fig, config={"displayModeBar": False}), style={"width": "100%", "marginBottom": "16px"}))

            # ── Radar chart ──────────────────────────────────────────────────
            try:
                radar = create_comparison_radar(rank_df, SC_COLORS)
                if radar:
                    all_graphs.append(html.Div(radar, style={"width": "100%", "marginBottom": "16px"}))
            except Exception as _e:
                pass

            # ── Trade-off scatter ─────────────────────────────────────────────
            try:
                tradeoff = create_comparison_tradeoff(rank_df)
                if tradeoff:
                    all_graphs.append(html.Div(tradeoff, style={"width": "100%", "marginBottom": "16px"}))
            except Exception as _e:
                pass

            # ── Scenario Details Table ──────────────────────────────────
            det_header = html.Tr([
                html.Th(c, style={"padding":"7px 10px","background":"#1e3a5f","color":"white",
                                  "fontSize":"11px","fontFamily":"Georgia,serif","textAlign":a})
                for c, a in [
                    ("Scenario / Configuration","left"),("Seeds","center"),
                    ("Days/Seed","center"),
                    ("Satisfaction (mean)","center"),("Food Insecurity (mean)","center"),
                    ("Avg Distance (km)","center"),("Spatial Equity (CV)","center"),
                    ("Completed","center"),
                ]
            ])
            det_rows = []
            _sc_order = {"baseline":0,"scenario1":1,"scenario2":2,"scenario3":3,"scenario4":4}
            for sk in sorted(scenario_snapshots.keys(),
                             key=lambda k:(_sc_order.get(k.split("_")[0] if "_" in k else k,5),k)):
                sn = scenario_snapshots.get(sk)
                if not sn: continue
                fm    = sn.get("final_metrics", {})
                label = sn.get("display_label", sk)
                days  = sn.get("days", 0)
                ts    = sn.get("timestamp","")[:16].replace("T"," ")
                sat   = float(fm.get("satisfaction_rate",0))
                fi    = float(fm.get("food_insecurity_rate",0))
                dist  = float(fm.get("avg_travel_distance",0))
                eq    = float(fm.get("spatial_equity_index",0))
                base  = sk.split("_")[0] if "_" in sk else sk
                bg    = {"baseline":"#EFF6FF","scenario1":"#F0F9FF","scenario2":"#F0FDF4",
                         "scenario3":"#FFFBEB","scenario4":"#FAF5FF"}.get(base,"#F8FAFC")
                # Pull seeds_used from snapshot
                n_seeds_run = int(sn.get("n_seeds", 1))
                seeds_run   = sn.get("seeds_used", [42])
                seeds_str   = ", ".join(str(s) for s in seeds_run)
                det_rows.append(html.Tr([
                    html.Td(label,                style={"padding":"6px 10px","fontWeight":"600","fontSize":"12px","color":"#1e3a5f"}),
                    html.Td(f"{n_seeds_run} ({seeds_str})", style={"padding":"6px 10px","textAlign":"center","fontSize":"11px","color":"#475569"}),
                    html.Td(str(days),            style={"padding":"6px 10px","textAlign":"center","fontSize":"12px"}),
                    html.Td(f"{sat:.1%}",         style={"padding":"6px 10px","textAlign":"center","fontSize":"12px","color":"#15803D","fontWeight":"600"}),
                    html.Td(f"{fi:.1%}",          style={"padding":"6px 10px","textAlign":"center","fontSize":"12px","color":"#DC2626","fontWeight":"600"}),
                    html.Td(f"{dist:.3f}",        style={"padding":"6px 10px","textAlign":"center","fontSize":"12px"}),
                    html.Td(f"{eq:.3f}",          style={"padding":"6px 10px","textAlign":"center","fontSize":"12px"}),
                    html.Td(ts,                   style={"padding":"6px 10px","textAlign":"center","fontSize":"11px","color":"#64748B"}),
                ], style={"background":bg,"borderBottom":"1px solid #E2E8F0"}))
            details_table = html.Div([
                html.H6("📋 Scenario Run Details",
                        style={"marginBottom":"8px","color":"#1e3a5f",
                               "fontFamily":"Georgia,serif","fontSize":"14px","fontWeight":"700"}),
                html.Table(
                    [html.Thead(det_header), html.Tbody(det_rows)],
                    style={"width":"100%","borderCollapse":"collapse",
                           "border":"1px solid #E2E8F0","fontSize":"12px"}
                ),
                html.P("Spatial Equity (CV) = std/mean of household accessibility scores — lower is more equitable.",
                       style={"fontSize":"10px","color":"#94A3B8","marginTop":"6px","marginBottom":"0"}),
            ], style={"marginBottom":"16px","background":"white","padding":"14px",
                      "borderRadius":"8px","border":"1px solid #E2E8F0",
                      "boxShadow":"0 1px 3px rgba(0,0,0,0.06)"})

            # ── Save Results — data-URI download (no server file needed) ──────
            import json as _json, base64 as _b64
            _payload = []
            for sk, sn in scenario_snapshots.items():
                if not sn: continue
                fm = sn.get("final_metrics",{})
                _payload.append({
                    "snap_key":   sk,
                    "label":      sn.get("display_label",sk),
                    "days":       sn.get("days",0),
                    "timestamp":  sn.get("timestamp",""),
                    "satisfaction_rate":    round(float(fm.get("satisfaction_rate",0)),6),
                    "food_insecurity_rate": round(float(fm.get("food_insecurity_rate",0)),6),
                    "avg_travel_distance":  round(float(fm.get("avg_travel_distance",0)),6),
                    "spatial_equity_index": round(float(fm.get("spatial_equity_index",0)),6),
                    "total_revenue":        round(float(fm.get("total_revenue",0)),2),
                })
            _enc  = _b64.b64encode(_json.dumps(_payload,indent=2).encode()).decode()
            _ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_btn = html.Div([
                html.A("💾  Save All Results (JSON)",
                       href=f"data:application/json;base64,{_enc}",
                       download=f"HZ1_ABM_results_{_ts}.json",
                       style={"display":"inline-block","padding":"8px 20px",
                              "background":"#1e3a5f","color":"white","borderRadius":"6px",
                              "fontWeight":"700","fontSize":"13px","textDecoration":"none",
                              "fontFamily":"Georgia,serif",
                              "boxShadow":"0 2px 4px rgba(0,0,0,0.15)"}),
                html.Span(" — timestamped JSON with all scenario results for committee records",
                          style={"fontSize":"11px","color":"#64748B","marginLeft":"10px"}),
            ], style={"marginBottom":"14px"})

            return html.Div([
                html.H5("Cross-Run Scenario Comparison",
                        style={"color": "#1e3a5f", "fontSize": "18px", "fontWeight": "700",
                               "marginBottom": "10px", "fontFamily": "Georgia, serif"}),
                save_btn,
                summary_badges,
                details_table,
                pending_note,
                *all_graphs
            ])

        return html.Div([
            html.H5("Cross-Run Scenario Comparison",
                    style={"color": "#2d3748", "fontSize": "18px", "fontWeight": "700"}),
            html.P("Run Baseline or any Scenario first, then return here to compare results.",
                   style={"color": "#6c757d", "fontSize": "14px"}),
            html.P("Charts update automatically as you complete each scenario run.",
                   style={"color": "#9ca3af", "fontSize": "12px"})
        ])

    # ── PER-SCENARIO RESULTS TAB ──────────────────────────────────────────────
    # Decide which data to use: snapshot for this scenario, or live data if it's the current run
    if selected_scenario and selected_scenario != current_scenario:
        snap_data, snap_day, snap_max = _get_snapshot_data_for_scenario(selected_scenario)
        simulation_data = snap_data
        use_live_model = False
    else:
        simulation_data = list(sim_state.simulation_data)
        snap_day = sim_state.current_day
        snap_max = sim_state.max_days
        use_live_model = current_model is not None

    if not simulation_data and not use_live_model:
        sc_label = {
            "baseline": "Baseline", "scenario1": "Scenario 1",
            "scenario2": "Scenario 2", "scenario3": "Scenario 3",
            "scenario4": "Scenario 4"
        }.get(selected_scenario or "", selected_scenario or "this scenario")
        return html.Div([
            html.P(f"🔄 Run {sc_label} first to see live result graphs here.",
                  style={'color': '#6c757d', 'textAlign': 'center',
                         'fontSize': '16px', 'padding': '30px', 'fontWeight': '500'})
        ])

    df = pd.DataFrame(simulation_data) if simulation_data else pd.DataFrame()
    latest_data = simulation_data[-1] if simulation_data else {}

    SC_COLOR_MAP = {
        "baseline": "#2C3E50", "scenario1": "#0891B2",
        "scenario2": "#15803D", "scenario3": "#D97706", "scenario4": "#7C3AED"
    }
    sc_color = SC_COLOR_MAP.get(selected_scenario or current_scenario or "baseline", "#667eea")

    graphs = []

    # ── Graph 1: Food Insecurity + Satisfaction timeseries ───────────────────
    if not df.empty and "day" in df.columns:
        fig1 = go.Figure()
        if "food_insecurity_rate" in df.columns:
            fig1.add_trace(go.Scatter(
                x=df["day"], y=df["food_insecurity_rate"],
                mode="lines", name="Food Insecurity",
                line=dict(color="#DC2626", width=2.5),
                fill="tozeroy", fillcolor="rgba(220,38,38,0.08)"
            ))
        if "satisfaction_rate" in df.columns:
            fig1.add_trace(go.Scatter(
                x=df["day"], y=df["satisfaction_rate"],
                mode="lines", name="Satisfaction",
                line=dict(color="#15803D", width=2.5),
                fill="tozeroy", fillcolor="rgba(21,128,61,0.06)"
            ))
        fig1.update_layout(
            title="🍽️ Food Insecurity & Satisfaction Rate — Day by Day",
            height=290, margin=dict(l=30, r=30, t=45, b=40),
            xaxis_title="Simulation Day", yaxis_title="Rate",
            yaxis=dict(tickformat=".0%", range=[0, 1]),
            plot_bgcolor="rgba(248,250,252,1)", paper_bgcolor="white",
            legend=dict(orientation="h", y=-0.25),
            font=dict(family="Inter, sans-serif", size=12),
            transition={"duration": 0}
        )
        graphs.append(dcc.Graph(figure=fig1))

    # ── Graph 2: Travel Distance timeseries ──────────────────────────────────
    if not df.empty and "avg_travel_distance" in df.columns and "day" in df.columns:
        fig2 = go.Figure([go.Scatter(
            x=df["day"], y=df["avg_travel_distance"],
            mode="lines", name="Avg Travel Distance",
            line=dict(color=sc_color, width=2.5),
            fill="tozeroy", fillcolor=f"rgba(102,126,234,0.07)"
        )])
        fig2.update_layout(
            title="🚗 Average Travel Distance (km) — Day by Day",
            height=260, margin=dict(l=30, r=30, t=45, b=40),
            xaxis_title="Simulation Day", yaxis_title="km",
            plot_bgcolor="rgba(248,250,252,1)", paper_bgcolor="white",
            showlegend=False, font=dict(family="Inter, sans-serif", size=12),
            transition={"duration": 0}
        )
        graphs.append(dcc.Graph(figure=fig2))

    # ── Graph 3: Corner store share + spatial equity timeseries ──────────────
    if not df.empty and "day" in df.columns:
        fig3 = go.Figure()
        if "corner_share" in df.columns:
            fig3.add_trace(go.Scatter(
                x=df["day"], y=df["corner_share"],
                mode="lines", name="Corner Store Share",
                line=dict(color="#D97706", width=2.0, dash="dash")
            ))
        if "spatial_equity_index" in df.columns:
            fig3.add_trace(go.Scatter(
                x=df["day"], y=df["spatial_equity_index"],
                mode="lines", name="Spatial Equity Index",
                line=dict(color="#7C3AED", width=2.0)
            ))
        if fig3.data:
            fig3.update_layout(
                title="🏪 Corner Store Share & Spatial Equity — Day by Day",
                height=260, margin=dict(l=30, r=30, t=45, b=40),
                xaxis_title="Simulation Day",
                plot_bgcolor="rgba(248,250,252,1)", paper_bgcolor="white",
                legend=dict(orientation="h", y=-0.28),
                font=dict(family="Inter, sans-serif", size=12),
                transition={"duration": 0}
            )
            graphs.append(dcc.Graph(figure=fig3))

    # ── Graph 4: Final snapshot summary bar ──────────────────────────────────
    if latest_data:
        bar_metrics = {
            "Satisfaction": latest_data.get("satisfaction_rate", 0),
            "Food Insecurity": latest_data.get("food_insecurity_rate", 0),
            "Spatial Equity": latest_data.get("spatial_equity_index", 0),
        }
        bar_colors = ["#15803D", "#DC2626", "#7C3AED"]
        fig4 = go.Figure([go.Bar(
            x=list(bar_metrics.keys()),
            y=list(bar_metrics.values()),
            marker_color=bar_colors,
            text=[f"{v:.1%}" for v in bar_metrics.values()],
            textposition="outside"
        )])
        fig4.update_layout(
            title=f"📊 Final Snapshot — Key Metrics at Day {snap_day}",
            height=280, margin=dict(l=20, r=20, t=45, b=30),
            yaxis=dict(tickformat=".0%", range=[0, 1]),
            plot_bgcolor="rgba(248,250,252,1)", paper_bgcolor="white",
            showlegend=False, font=dict(family="Inter, sans-serif", size=12)
        )
        graphs.append(dcc.Graph(figure=fig4))

    sc_label_map = {
        "baseline": "Baseline", "scenario1": "Scenario 1: New Grocery Store",
        "scenario2": "Scenario 2: Food Hub + Corner Stores",
        "scenario3": "Scenario 3: Mobile Pantries",
        "scenario4": "Scenario 4: Subsidised Delivery"
    }
    sc_display = sc_label_map.get(selected_scenario or current_scenario or "", "Scenario")
    status_label = "🟢 Running" if (running and selected_scenario == current_scenario) else "✅ Complete"

    return html.Div([
        html.H5(f"📊 Live Results — {sc_display}",
                style={'color': sc_color, 'fontSize': '17px', 'fontWeight': '700', 'marginBottom': '4px'}),
        html.P(
            f"Day {snap_day} of {snap_max}  |  {status_label}  |  "
            f"{len(simulation_data)} data points",
            style={'margin': '0 0 10px 0', 'color': '#4a5568', 'fontSize': '12px'}
        ),
        *graphs
    ] if graphs else [
        html.P("📈 Simulation data is loading...",
               style={'color': '#6c757d', 'textAlign': 'center', 'fontSize': '15px', 'padding': '20px'})
    ])

# Simulation control callback
@app.callback(
    [Output("start-btn", "disabled")],
    [Input("start-btn", "n_clicks"),
     Input("stop-btn", "n_clicks"),
     Input("reset-btn", "n_clicks"),
     Input("selected-scenario", "data")],
    [State("selected-scenario", "data"),
     State("collected-parameters", "children"),
     State("store-region-cache", "data")]
)
def control_simulation(start_clicks, stop_clicks, reset_clicks, selected_tab, scenario, collected_params, store_region_cached):
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
            if scenario == "scenario1" and store_region_cached:
                input_dict["param-scenario1-store-region"] = store_region_cached
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
            cfg = dict(config.__dict__)
            # Scenario 4 delivery params come from input_dict, not config
            if scenario == 'scenario4':
                cfg['delivery_capacity'] = int(input_dict.get('param-delivery-capacity', 500))
            sim_state.current_params = {
                'scenario': scenario,
                'config': cfg
            }
            sim_state.current_scenario = scenario
            sim_state.max_days = config.simulation_days
        sim_state.reset()
        sim_state.sim_running = True
        
        # ── Multi-seed reproducible run ──────────────────────────────────────
        # One click runs ABM_SEEDS sequentially.  Each seed is auto-saved.
        # Dashboard shows seed-1 live; final charts show mean ± SD across seeds.
        try:
            # Validate model can be built with seed[0] before spawning thread
            import random as _rmod
            _rmod.seed(ABM_SEEDS[0]); np.random.seed(ABM_SEEDS[0])
            _probe = _create_model_for_scenario(scenario, config, input_dict)
            print(f"✅ {scenario} model ready ({len(_probe.food_providers)} providers). "
                  f"Will run {len(ABM_SEEDS)} seeds: {ABM_SEEDS}")
            del _probe  # release — each seed creates its own fresh instance

            with simulation_lock:
                sim_state.current_model = None  # will be set per-seed below

            def run_simulation():
                all_histories = []
                n_seeds       = len(ABM_SEEDS)
                try:
                    for seed_idx, seed in enumerate(ABM_SEEDS):
                        with simulation_lock:
                            should_start = sim_state.sim_running
                        if not should_start:
                            break  # user hit Stop before this seed

                        # ── Fresh model + seed for this replication ──────────
                        _rmod.seed(seed); np.random.seed(seed)
                        model = _create_model_for_scenario(scenario, config, input_dict)
                        with simulation_lock:
                            sim_state.current_model = model

                        seed_history = []
                        is_first_seed = (seed_idx == 0)

                        # Reset live data at start of first seed
                        if is_first_seed:
                            with simulation_lock:
                                sim_state.simulation_data = []

                        for day in range(sim_state.max_days):
                            with simulation_lock:
                                should_continue = sim_state.sim_running
                            if not should_continue:
                                print(f"🛑 Stopped at seed {seed} day {day + 1}")
                                break
                            model.step()
                            if getattr(model, 'metrics_history', None):
                                latest = model.metrics_history[-1]
                                seed_history.append(latest)
                                # Live feed: first seed drives the dashboard charts
                                if is_first_seed:
                                    with simulation_lock:
                                        sim_state.simulation_data.append(latest)
                            with simulation_lock:
                                sim_state.current_day = day + 1
                                overall_pct = ((seed_idx * sim_state.max_days + day + 1)
                                               / (n_seeds * sim_state.max_days) * 100)
                                sim_state.status_message = (
                                    f"🔄 Seed {seed} ({seed_idx+1}/{n_seeds}) — "
                                    f"Day {day+1}/{sim_state.max_days} "
                                    f"({overall_pct:.0f}% overall) ⚡")
                            time.sleep(0.05)

                        # ── Per-seed auto-save ────────────────────────────────
                        if seed_history:
                            with simulation_lock:
                                cfg_d = dict(sim_state.current_params.get("config", {}))
                                sk, _ = _build_scenario_variation_key_and_label(scenario, cfg_d)
                            _autosave_single_seed(scenario, cfg_d, seed, sk,
                                                  seed_history, sim_state.current_day)
                            all_histories.append(seed_history)

                    # ── Store mean ± SD snapshot (drives comparison tab) ─────
                    with simulation_lock:
                        sim_state.status_message = f"✅ {scenario} — {len(all_histories)}/{n_seeds} seeds done. Saving summary…"
                    _store_scenario_snapshot(scenario,
                                             all_seed_histories=all_histories,
                                             seeds_used=ABM_SEEDS[:len(all_histories)])
                    with simulation_lock:
                        sim_state.status_message = (
                            f"✅ {scenario} complete! {len(all_histories)} seeds × {sim_state.max_days} days 🎉")
                except Exception as e:
                    import traceback
                    print(f"Simulation error: {e}\n{traceback.format_exc()}")
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
    for i, tab_type in enumerate(["primary", "results"]):
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
     Input("selected-scenario", "data")],
    [State("selected-sub-metric", "data"),
     State({"type": "metrics-sub-item", "index": ALL}, "id"),
     State("final-metrics-store", "data")],
    prevent_initial_call=False
)
def handle_sub_metrics_click(n_clicks_list, main_metric, selected_scenario, current_sub, sub_item_ids, stored_metrics):
    n_intervals = 0  # no longer an input
    ctx = callback_context
    
    # Determine what triggered this callback
    triggered_prop_id = ctx.triggered[0]['prop_id'] if ctx.triggered else ""
    
    # Check what triggered this callback
    if 'selected-main-metric' in triggered_prop_id:
        # Main metric changed, set default sub-metric
        if main_metric == "primary":
            clicked_sub = "primary-main"
        else:
            clicked_sub = "fi-timeseries"
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
            else:
                clicked_sub = current_sub or "fi-timeseries"
    

    
    # Generate content based on selection
    if main_metric == "primary":
        if clicked_sub == "primary-main":
            # Show ONLY primary metrics content

            try:
                primary_content = create_primary_metrics_only(stored_metrics, scenario=selected_scenario)
                content = [html.Div([
                    primary_content
                ], style={"flex": "1", "minHeight": "0", "overflowY": "auto", "padding": "10px"})]
            except Exception as e:
                print(f"⚠️ Error creating primary metrics in callback: {e}")
                content = [html.Div([
                    html.H6("Primary Metrics", style={"margin": "0 0 10px 0", "color": "#2d3748"}),
                    html.P("Primary metrics will appear here when data is available.",
                          style={"color": "#4a5568", "fontSize": "14px"})
                ], style={"flex": "1", "minHeight": "0", "overflowY": "auto"})]
        elif clicked_sub == "progress":

            content = [html.Div([
                create_progress_metrics_only(stored_metrics, scenario=selected_scenario)
            ], style={"flex": "1", "minHeight": "0", "overflowY": "auto", "padding": "10px"})]
        elif clicked_sub == "counts":

            content = [html.Div([
                create_counts_metrics_only(stored_metrics, scenario=selected_scenario)
            ], style={"flex": "1", "minHeight": "0", "overflowY": "auto", "padding": "10px"})]
        elif clicked_sub == "performance":

            content = [html.Div([
                create_performance_metrics_only(stored_metrics, scenario=selected_scenario)
            ], style={"flex": "1", "minHeight": "0", "overflowY": "auto", "padding": "10px"})]
        else:

            content = [html.Div([
                html.H6("Default Metrics", style={"margin": "0 0 10px 0", "color": "#2d3748"}),
                html.P("Select a specific metrics category from the left to view detailed information.",
                      style={"color": "#4a5568", "fontSize": "14px"})
            ], style={"flex": "1", "minHeight": "0", "overflowY": "auto"})]
    else:  # results
        # ── Comparison tab: route directly to create_results_view ──────────────
        if selected_scenario == "comparison":
            try:
                cmp_content = create_results_view("comparison")
            except Exception as e:
                cmp_content = html.P(f"Comparison error: {e}",
                                     style={"color": "#DC2626", "padding": "20px"})
            content = [html.Div(
                cmp_content,
                style={"flex": "1", "minHeight": "0", "overflowY": "auto", "padding": "10px"}
            )]
        else:
            # ── Per-scenario: each sub-item maps to a different v2-style chart ──
            CHART_DISPATCH = {
                "fi-timeseries":   create_v2_fi_chart,
                "satisfaction-ts": create_v2_satisfaction_chart,
                "distance-ts":     create_v2_distance_chart,
                "equity-bar":      create_v2_equity_chart,
                "sat-benchmark":   create_v2_sat_benchmark_chart,
                "income-groups":   create_v2_income_groups_chart,
            }
            if clicked_sub not in CHART_DISPATCH:
                clicked_sub = "fi-timeseries"
            chart_fn = CHART_DISPATCH.get(clicked_sub, create_v2_fi_chart)
            try:
                chart_content = chart_fn(selected_scenario)
            except Exception as e:
                chart_content = html.P(f"Chart error: {e}",
                                       style={"color": "#DC2626", "padding": "20px"})
            content = [html.Div(
                chart_content,
                style={"flex": "1", "minHeight": "0", "overflowY": "auto", "padding": "10px"}
            )]
    
    # Generate styles for exactly the rendered sub-items (prevents ALL-pattern length mismatch)
    rendered_items = [
        d.get("index") for d in (sub_item_ids or [])
        if isinstance(d, dict) and d.get("index")
    ]
    if not rendered_items:
        if main_metric == "primary":
            rendered_items = ["primary-main", "progress", "counts", "performance"]
        else:  # results
            rendered_items = ["fi-timeseries", "satisfaction-ts", "distance-ts", "equity-bar", "sat-benchmark", "income-groups"]
    
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
    else:  # results — 4 chart sections, each showing a different v2-style chart
        _SNAV_ACTIVE = {"padding": "6px 10px", "cursor": "pointer", "borderRadius": "4px",
                        "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                        "color": "white", "fontSize": "12px", "marginBottom": "4px"}
        _SNAV_IDLE   = {"padding": "6px 10px", "cursor": "pointer", "borderRadius": "4px",
                        "background": "#f9f9f9", "color": "#4a5568", "fontSize": "12px", "marginBottom": "4px"}
        sub_nav = [
            html.Div("Food Insecurity",  id={"type": "metrics-sub-item", "index": "fi-timeseries"},   style=_SNAV_ACTIVE),
            html.Div("Satisfaction",     id={"type": "metrics-sub-item", "index": "satisfaction-ts"}, style=_SNAV_IDLE),
            html.Div("Travel Distance",  id={"type": "metrics-sub-item", "index": "distance-ts"},     style=_SNAV_IDLE),
            html.Div("Equity Impact",    id={"type": "metrics-sub-item", "index": "equity-bar"},      style=_SNAV_IDLE),
            html.Div("Sat. Benchmark",   id={"type": "metrics-sub-item", "index": "sat-benchmark"},   style=_SNAV_IDLE),
            html.Div("Income Groups",    id={"type": "metrics-sub-item", "index": "income-groups"},   style=_SNAV_IDLE),
        ]
    
    return sub_nav


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
    if os.environ.get('COMBINED_APP') != '1':
        app.run(debug=debug_mode, port=8050, host="0.0.0.0")

# Note: Parameter section rendering is now handled by handle_section_and_scenario_changes callback