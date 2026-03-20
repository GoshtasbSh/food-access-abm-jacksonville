# GeoMesa Food Access Agent-Based Model — Comprehensive Guide

**Modeling food access: An agent-based model for evaluating interventions for Health Zone 1, Jacksonville, FL**

This document describes the full architecture, data flow, calibration, and usage of the GeoMesa Food Access ABM. It is intended for researchers, reviewers, and collaborators who need to understand and run the model.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Model Architecture Overview](#2-model-architecture-overview)
3. [File Structure and Dependencies](#3-file-structure-and-dependencies)
4. [Core Components](#4-core-components)
5. [Parameter System and Alignment](#5-parameter-system-and-alignment)
6. [Calibration Workflow](#6-calibration-workflow)
7. [How to Run the Model](#7-how-to-run-the-model)
8. [Data Flow Diagram](#8-data-flow-diagram)
9. [Validation and Verification](#9-validation-and-verification)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Executive Summary

The GeoMesa Food Access ABM simulates household food-shopping behavior in Health Zone 1 (Jacksonville, FL) under different policy and infrastructure scenarios. Households (agents) make daily decisions about when and where to shop based on a discrete choice model that weighs distance, price, quality, and convenience. The model is calibrated to targets (annual spending by income, corner store share, travel distances) and used to evaluate interventions such as new grocery stores, food hubs, mobile pantries, and subsidized delivery.

**Key outputs:**
- Annual spending by income level (low, medium, high)
- Corner store share of trips
- Average travel distance (car vs. no car)
- Total trips, satisfaction rates, and spatial equity metrics

---

## 2. Model Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        LIVE DASHBOARD (live_enhanced_mesa_dash.py)      │
│  • Interactive UI: Baseline, Scenario 1–4, Comparison, Sensitivity      │
│  • Parameter inputs → build_config_from_inputs → SimulationConfig       │
│  • Runs simulations in background thread; real-time metrics             │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             │ SimulationConfig
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     SCENARIO MODELS (baseline_scenario, enhanced_*)      │
│  • create_baseline_scenario(config)                                     │
│  • create_enhanced_scenario_1/2/3/4(config)                             │
│  • Setup: households (census), providers (real data), mobile pantries    │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             │ BaselineScenarioModel / EnhancedScenario*Model
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  CORE MODEL (enhanced_mesa_geo_model.py)                 │
│  • EnhancedMesaGeoModel extends mesa.Model                              │
│  • Households: EnhancedHouseholdAgent (discrete choice, shopping)       │
│  • Providers: Grocery, Corner, Food Hub, Mobile Pantry, Delivery         │
│  • Runs step-by-step; collects metrics                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. File Structure and Dependencies

### 3.1 Main Python Files

| File | Purpose | Imports From |
|------|---------|--------------|
| `enhanced_mesa_geo_model.py` | Core ABM: agents, discrete choice, SimulationConfig | mesa, mesa_geo, numpy, pandas, geopandas |
| `baseline_scenario.py` | Baseline: current HZ1 food environment | enhanced_mesa_geo_model, census_tract_loader, real_supermarket_loader, hz1_census_data_loader |
| `enhanced_scenario_1.py` | Scenario 1: New grocery store | baseline_scenario, enhanced_mesa_geo_model, hz1_census_data_loader |
| `enhanced_scenario_2.py` | Scenario 2: Food hub + corner stores | baseline_scenario, enhanced_mesa_geo_model |
| `enhanced_scenario_3.py` | Scenario 3: Mobile pantries | baseline_scenario, enhanced_mesa_geo_model |
| `enhanced_scenario_4.py` | Scenario 4: Subsidized delivery | baseline_scenario, enhanced_mesa_geo_model |
| `enhanced_scenario_comparison.py` | Compare Scenario 1 vs 2 only | enhanced_scenario_1, enhanced_scenario_2 |
| `live_enhanced_mesa_dash.py` | Interactive dashboard | All scenario modules, dashboard_config_builder, dashboard_parameters, sensitivity_analysis_sobol |
| `dashboard_config_builder.py` | Build SimulationConfig from UI inputs | enhanced_mesa_geo_model |
| `dashboard_parameters.py` | Parameter layout for dashboard | enhanced_mesa_geo_model |
| `sensitivity_analysis_sobol.py` | Sobol sensitivity analysis | enhanced_mesa_geo_model, baseline_scenario, SALib |
| `hz1_census_data_loader.py` | Real census demographics for HZ1 | enhanced_mesa_geo_model |
| `real_supermarket_loader.py` | Load real store locations from CSV | — |
| `census_tract_loader.py` | Census tract spatial data | — |

### 3.2 Calibration Files

| File | Purpose | Output |
|------|---------|--------|
| `extra_Files/run_MEMORY_OPTIMIZED_calibration.py` | Phase 1: Grid search (108 configs) | `MEMORY_OPTIMIZED_RESULTS_*.csv`, `BEST_MEMORY_OPTIMIZED_PARAMS_*.json` |
| `run_PHASE2_VALIDATION.py` | Phase 2: Validate top 5 with full settings | `FINAL_CALIBRATED_PARAMS_*.json` |
| `calibration_framework.py` | Reusable calibration utilities | — |

### 3.3 Data Files (Expected Paths)

- **Health Zone polygon:** `.../Data/HealthZones1and4/Health_Zones_1_and_4.shp`
- **Roads:** `.../Data/Roads/All Jacksonville Roads.shp`
- **Supermarkets:** `GeoMesa_Food_Access/supermarkets_with_coords_CURATED.csv`
- **Census:** `.../Data/duval_household_attributes.csv`, etc. (see `hz1_census_data_loader.py`)
- **Methodology note (pantries):** Food pantry locations were sourced from a verified HZ1 pantry database. Coordinates were obtained via street-level geocoding with one GPS-confirmed anchor point (`Johnson Family YMCA`; BusinessYab 2024). Coordinate accuracy is estimated at ±200m, sufficient for the spatial resolution of the ABM.

---

## 4. Core Components

### 4.1 SimulationConfig (enhanced_mesa_geo_model.py)

Single source of truth for model parameters. Key calibration-related fields:

| Parameter | Default | Description | Used By |
|-----------|---------|-------------|---------|
| `alpha_distance` | 2.5 | Distance disutility weight | Discrete choice model |
| `beta_price_budget` | 0.7 | Price/budget consciousness | Discrete choice model |
| `gamma_quality_variety` | 1.0 | Quality/variety preference | Discrete choice model |
| `delta_convenience` | 0.4 | Convenience factor | Discrete choice model |
| `go_shop_threshold_low` | 4.0 | Days until low-income HH shops | Shopping trigger |
| `go_shop_threshold_medium` | 7.0 | Days until medium-income HH shops | Shopping trigger |
| `go_shop_threshold_high` | 14.0 | Days until high-income HH shops | Shopping trigger |
| `num_consumers` | 500 | Number of households | All scenarios |
| `simulation_days` | 30 | Simulation length | All scenarios |

### 4.2 Household Agent (EnhancedHouseholdAgent)

Each household has:
- **Income level:** LOW / MEDIUM / HIGH (2023 cutoffs)
- **Vehicle availability:** Boolean
- **Household size:** 1–5+
- **SNAP eligibility, race:** From census
- **Shopping parameters:** Weekly budget, basket size, frequency, max travel distance

**Discrete choice model (store selection):**
```
Utility = α×distance_term + β×price_term + γ×quality_term + δ×convenience_term + store_bias
```
- **distance_term:** -α × (distance / max_travel_distance)
- **price_term:** β × price_score × budget_weight
- **quality_term:** γ × provider.quality_score
- **convenience_term:** δ × availability_score
- **store_bias:** Income-specific (e.g., low-income prefers discount stores)

**Shopping trigger:**
- Shop when `days_since_last_shop >= go_shop_threshold` OR `food_supply <= shopping_threshold`
- `go_shop_threshold` depends on income (from config)

### 4.3 Food Providers

| Type | Example | Capacity (default) |
|------|---------|--------------------|
| Grocery/Supermarket | Publix, Walmart | 600 |
| Corner Store | Convenience | 60 |
| Food Hub | Fresh produce market | 300 |
| Mobile Pantry | FNEFL distributions | 120 |
| Delivery Service | Instacart-style | 500 |

### 4.4 Output Metrics (Calibration Targets)

| Metric | Target | Source |
|--------|--------|--------|
| avg_spend_low | $5,300/yr | Low-income annual spending |
| avg_spend_med | $9,000/yr | Medium-income |
| avg_spend_high | $17,000/yr | High-income |
| corner_share | 10% | Share of trips to corner stores |
| avg_dist_car | 5.6 km | Car-using households |
| avg_dist_nocar | 0.8 km | No-car households |

---

## 5. Parameter System and Alignment

### 5.1 Dashboard → SimulationConfig Mapping

`dashboard_config_builder.build_config_from_inputs(input_values)` maps UI IDs to config:

| Dashboard Input ID | SimulationConfig Field |
|--------------------|------------------------|
| param-num-consumers | num_consumers |
| param-simulation-days | simulation_days |
| param-alpha | alpha_distance |
| param-beta | beta_price_budget |
| param-gamma | gamma_quality_variety |
| param-delta | delta_convenience |
| param-go-shop-low | go_shop_threshold_low |
| param-go-shop-med | go_shop_threshold_medium |
| param-go-shop-high | go_shop_threshold_high |
| param-delivery-low/medium/high | delivery_baseline_* |
| param-grocery-capacity | grocery_store_capacity |
| param-num-corner-stores | num_corner_stores |
| ... | (see dashboard_config_builder.py) |

**Note:** Go-shop thresholds are not yet exposed in the dashboard UI; SimulationConfig defaults (4, 7, 14) are used, which match calibration.

### 5.2 Calibration JSON Structure

**BEST_MEMORY_OPTIMIZED_PARAMS_*.json:**
```json
{
  "best_parameters": {
    "alpha_distance": 2.5,
    "beta_price_budget": 1.3,
    "gamma_quality_variety": 1,
    "delta_convenience": 0.4,
    "go_shop_threshold_low": 4,
    "go_shop_threshold_medium": 7,
    "go_shop_threshold_high": 14
  },
  "calibration_error": 0.274,
  "metrics": { ... },
  "timestamp": "20251123_235231"
}
```

**FINAL_CALIBRATED_PARAMS_*.json (Phase 2):** Uses `final_parameters` with same keys; includes seed-level results.

### 5.3 Sensitivity Analysis Parameters

`sensitivity_analysis_sobol.py` uses the same 7 parameters:
- alpha_distance, beta_price_budget, gamma_quality_variety, delta_convenience
- go_shop_threshold_low, go_shop_threshold_medium, go_shop_threshold_high

Loads from `BEST_MEMORY_OPTIMIZED_PARAMS_*.json` (searches `.` and `extra_Files/`).

---

## 6. Calibration Workflow

### 6.1 Phase 1: Memory-Optimized Grid Search

**Command:**
```bash
cd /Users/goshtasbshahriari/Desktop/Code/GeoMesa_Food_Access
python extra_Files/run_MEMORY_OPTIMIZED_calibration.py
```

**Settings:**
- 50 households, 90 days, 1 seed per config
- Grid: α, β, γ, δ, threshold_low, threshold_med, threshold_high
- ~108 configurations
- Output: `MEMORY_OPTIMIZED_RESULTS_YYYYMMDD_HHMMSS.csv`, `BEST_MEMORY_OPTIMIZED_PARAMS_YYYYMMDD_HHMMSS.json` (saved in project root, i.e. current working directory when you run the command)

**Duration:** ~1–2 hours (depends on hardware)

### 6.2 Phase 2: Full Validation

**Command:**
```bash
cd /Users/goshtasbshahriari/Desktop/Code/GeoMesa_Food_Access
python run_PHASE2_VALIDATION.py
```

**What it does:**
- Reads latest `MEMORY_OPTIMIZED_RESULTS_*.csv` (or `extra_Files/` if not in root)
- Selects top 5 configs by error
- Runs each with 200 households, 365 days, 5 seeds
- Output: `FINAL_CALIBRATED_PARAMS_YYYYMMDD_HHMMSS.json`

**Duration:** ~20–40 minutes

### 6.3 Does Calibration Work Correctly?

Yes. The scripts:
- Import from `enhanced_mesa_geo_model` and `baseline_scenario`
- Build `SimulationConfig` with the 7 calibrated parameters
- Use `create_baseline_scenario(config)` to run the model
- Extract metrics using the same logic as `run_PHASE2_VALIDATION.py` (spending by income, corner share, travel distances)
- Compute error against targets and save best parameters

**Calibration targets** (in `calculate_error`):
- avg_spend_low: 5300, avg_spend_med: 9000, avg_spend_high: 17000
- corner_share: 0.10, avg_dist_car: 5.6, avg_dist_nocar: 0.8

---

## 7. How to Run the Model

### 7.1 Interactive Dashboard (Recommended)

```bash
cd /Users/goshtasbshahriari/Desktop/Code/GeoMesa_Food_Access
python live_enhanced_mesa_dash.py
```

Open: **http://localhost:8050**

**Tabs:**
- **Baseline:** Current HZ1 food environment
- **Scenario 1:** Add new grocery store
- **Scenario 2:** Food hub + corner store network
- **Scenario 3:** Mobile pantries
- **Scenario 4:** Subsidized delivery
- **Compare Scenario 1 vs 2:** Run Scenario 1 and Scenario 2, then compare their metrics
- **Sensitivity Analysis:** Sobol indices (requires `pip install SALib` and `BEST_MEMORY_OPTIMIZED_PARAMS_*.json`)

**Workflow:**
1. Select scenario
2. Adjust parameters (households, days, choice model, scenario-specific)
3. Click "Start Simulation"
4. View live metrics and map
5. Use "Stop" or "Reset" as needed

### 7.2 Run Calibration (Two-Phase)

```bash
cd /Users/goshtasbshahriari/Desktop/Code/GeoMesa_Food_Access

# Phase 1
python extra_Files/run_MEMORY_OPTIMIZED_calibration.py

# Phase 2 (after Phase 1 completes)
python run_PHASE2_VALIDATION.py
```

### 7.3 Run All Scenarios (Batch, Calibrated Params)

```bash
cd /Users/goshtasbshahriari/Desktop/Code/GeoMesa_Food_Access
python run_ALL_SCENARIOS_calibrated.py
```

Uses calibrated parameters from JSON; outputs comparison JSON.

### 7.4 Sensitivity Analysis (from Dashboard)

1. Open dashboard, go to "Sensitivity Analysis" tab
2. Ensure `BEST_MEMORY_OPTIMIZED_PARAMS_*.json` exists in project root or `extra_Files/`
3. Set N (sample size) and bounds %
4. Click "Run Sensitivity Analysis"
5. Wait (long runs; progress shown)

**Or run standalone:** `sensitivity_analysis_sobol` is imported by the dashboard; there is no standalone CLI.

---

## 8. Data Flow Diagram

```
User Input (Dashboard)
       │
       ▼
collected-parameters (JSON) ──► build_config_from_inputs() ──► SimulationConfig
       │                                                                   │
       │                                                                   ▼
       │                                              create_baseline_scenario(config)
       │                                              create_enhanced_scenario_*(config)
       │                                                           │
       │                                                           ▼
       │                                              BaselineScenarioModel / EnhancedScenario*Model
       │                                                           │
       │                                                           ▼
       │                                              EnhancedMesaGeoModel
       │                                              • Households (HZ1 census)
       │                                              • Providers (real stores, pantries, delivery)
       │                                              • step() loop
       │                                                           │
       │                                                           ▼
       │                                              Metrics: spend, corner_share, distances
       │                                                           │
       └──────────────────────────────────────────────────────────┘
                                       │
       ┌───────────────────────────────┼───────────────────────────────┐
       │                               │                               │
       ▼                               ▼                               ▼
Live Metrics Display            Map (agent locations)          Final Results Store
```

---

## 9. Validation and Verification

| Script | Purpose |
|--------|---------|
| `extra_Files/COMPREHENSIVE_MODEL_VERIFICATION.py` | Structural checks: income classification, quality scores, full-shop logic, etc. |
| `extra_Files/FINAL_VERIFICATION_mobile_pantries_and_delivery.py` | Verifies pantries and delivery across scenarios |
| `extra_Files/verify_calibration_error.py` | Validates error calculation |

---

## 10. Troubleshooting

### Dashboard: "Nothing happens when I click Start"
- Check browser console (F12) for JavaScript errors
- Check terminal where dashboard runs for Python tracebacks
- Ensure `collected-parameters` is populated (parameter collection callback)

### Sensitivity Analysis: "Nothing shows"
- Install: `pip install SALib`
- Ensure `BEST_MEMORY_OPTIMIZED_PARAMS_*.json` in project root or `extra_Files/`
- Check terminal for exceptions
- Try smaller N (e.g., 50) for faster test

### Calibration: "ModuleNotFoundError: mesa"
- Install: `pip install mesa mesa-geo`
- See project requirements for full dependency list

### Data paths not found
- Update paths in `enhanced_mesa_geo_model.py`, `baseline_scenario.py`, `hz1_census_data_loader.py` to match your system
- Health zone shapefile, census CSVs, and supermarket CSV paths are hardcoded

### Parameter mismatch between dashboard and calibration
- Dashboard uses `build_config_from_inputs`; alpha, beta, gamma, delta map correctly
- Go-shop thresholds use SimulationConfig defaults (4, 7, 14) unless added to UI
- Calibration JSON keys: `alpha_distance`, `beta_price_budget`, etc. — all match SimulationConfig

---

## Appendix A: Dependency Summary

- **mesa**, **mesa-geo** — ABM framework
- **dash**, **dash-leaflet** — Dashboard
- **geopandas**, **shapely**, **geopy** — Spatial
- **pandas**, **numpy** — Data
- **plotly** — Charts
- **SALib** — Sensitivity analysis (optional)

---

## Appendix B: Changelog / Version

- Model uses 2023 income cutoffs, real HZ1 census and store data
- Calibration: Two-phase (Phase 1 grid, Phase 2 validation)
- Dashboard: Baseline + 4 scenarios + comparison + sensitivity tab
- Sensitivity analysis: Sobol method, 7 parameters, ThreadPoolExecutor

---

*Document generated for GeoMesa Food Access ABM. For questions, see source code comments and CALIBRATION_AND_VALIDATION_SUMMARY.md.*
