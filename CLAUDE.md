# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Agent-based model (ABM) simulating household food shopping behavior in Health Zone 1, Jacksonville, FL. Built for PhD dissertation research using Mesa-Geo. Evaluates four food access policy interventions (new grocery store, food hub network, mobile pantries, subsidized delivery) against a baseline using a discrete choice model calibrated to real census/survey data.

## Environment Setup

```bash
conda create -n abm310 python=3.10
conda activate abm310
pip install -r requirements.txt
```

Python 3.9+ required. Key dependencies: mesa, mesa-geo, geopandas, dash, plotly, scipy, SALib.

## Running the Application

```bash
# Live interactive dashboard (localhost:8050) — runs simulations in real-time
python live_enhanced_mesa_dash.py

# Dissertation results dashboard (localhost:8065) — displays pre-computed results from scenarios_results/
python abm_dashboard_dissertation.py

# Individual scenario runs (outputs JSON to scenarios_results/)
python baseline_scenario.py
python enhanced_scenario_1.py   # North grocery store
python enhanced_scenario_2.py   # Food hub + corner stores
python enhanced_scenario_3.py   # Mobile pantries
python enhanced_scenario_4.py   # Subsidized delivery
```

## Architecture

### Core Model (`enhanced_mesa_geo_model.py`)
The central module (~2000+ lines). Contains:
- **SimulationConfig** dataclass: All simulation parameters (budgets, frequencies, choice model weights, store capacities). On `__post_init__`, auto-loads calibrated parameters from `FINAL_CALIBRATED_PARAMS_*.json` files.
- **Discrete choice model**: Household store selection based on utility weights (alpha_distance, beta_price_budget, gamma_quality_variety, delta_convenience) — these are calibrated and should not be changed without re-calibration.
- **Agent types**: Households (HouseholdAgent via mesa-geo GeoAgent), food providers (various ProviderType enum values).
- **IncomeClassifier**: Jacksonville 2023 income thresholds (low < $28,262, medium < $90,239, high).
- **CensusTractData**: Census demographic structure (income, household size, vehicle access, race distributions).

### Data Flow
1. `config.py` resolves all data paths (shapefile, CSV, census) via env vars or defaults
2. `real_supermarket_loader.py` loads store locations from `supermarkets_with_coords_CURATED.csv`
3. `hz1_census_data_loader.py` + `census_tract_loader.py` load household demographics
4. Scenario files (baseline + enhanced_scenario_1-4) create model variants by adding/modifying providers
5. Dashboards consume model output or pre-computed JSON from `scenarios_results/`

### Dashboard Layer
- `live_enhanced_mesa_dash.py`: Dash app importing all scenario modules, runs simulations with user-tunable parameters. Uses `dashboard_parameters.py` for UI layout and `dashboard_config_builder.py` to translate UI inputs into SimulationConfig.
- `abm_dashboard_dissertation.py`: Standalone Dash app loading JSON results. Pattern-matches files like `baseline_500hh_365d_seed42_*.json`. Supports multi-seed analysis with bootstrap CIs.
- `sensitivity_analysis_sobol.py`: Sobol sensitivity analysis integrated into the live dashboard.

### Calibration
Calibrated parameters live in `FINAL_CALIBRATED_PARAMS_*.json` (project root or `extra_Files/`). The model auto-discovers the highest-priority file at startup. Calibration scripts and historical results are archived in `extra_Files/`.

## External Data

The Health Zone shapefile is expected at `../Data/HealthZones1and4/Health_Zones_1_and_4.shp` relative to the project. Override via:
- `GEOMESA_DATA_DIR` — base directory for shapefiles
- `GEOMESA_HEALTH_ZONE_SHP` — direct shapefile path
- `GEOMESA_CENSUS_DATA_DIR` — census data directory

If the shapefile is missing, the map uses a fallback polygon.

## Key Conventions

- All scenario files follow the pattern: a `create_*` factory function + a `*Model` class inheriting from the base model
- Parameters marked "CALIBRATED" in SimulationConfig are loaded from JSON and must not be manually overridden without re-running calibration
- `extra_Files/` is an archive of past calibration runs, diagnostics, and test scripts — not part of the active codebase
- Scenario results are JSON files written to `scenarios_results/` with naming convention `{scenario}_{hh}hh_{days}d_seed{n}_{timestamp}.json`
