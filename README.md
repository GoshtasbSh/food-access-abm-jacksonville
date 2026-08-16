# GeoMesa Food Access ABM

Agent-based model (ABM) for evaluating food access interventions in Health Zone 1, Jacksonville, FL. Developed for PhD dissertation research.

## Overview

This project simulates household food shopping behavior using a discrete choice model, calibrated to match real-world survey data. It evaluates four policy interventions:

- **Baseline** — Current state (existing stores, market-rate delivery)
- **Scenario 1** — New grocery store (North location)
- **Scenario 2** — Food hub network + corner stores
- **Scenario 3** — Mobile pantries
- **Scenario 4** — Subsidized delivery program

The model uses Mesa-Geo for spatial agent-based modeling, real census demographics, and curated supermarket locations.

## Requirements

- Python 3.9+
- Conda or pip

## Installation

```bash
# Clone the repository
git clone https://github.com/GoshtasbSh/food-access-abm-jacksonville.git
cd food-access-abm-jacksonville

# Create and activate environment (conda)
conda create -n abm310 python=3.10
conda activate abm310

# Install dependencies
pip install -r requirements.txt
```

## Data Requirements

The model expects the following data:

| File | Location | Description |
|------|----------|-------------|
| `supermarkets_with_coords_CURATED.csv` | Project root | Curated store list (included) |
| `hz1_household_data_CORRECTED.csv` | Project root | Census-derived household data (included) |
| `health_zone_1_census_tracts.txt` | Project root | Census tract IDs (included) |
| `Health_Zones_1_and_4.shp` | External | Health Zone shapefile for map display |
| Census data (optional) | `census_data/` or env | Raw census files for HZ1CensusDataLoader |

### Configuring Data Paths

By default, the Health Zone shapefile is expected at:
```
<parent_of_project>/Data/HealthZones1and4/Health_Zones_1_and_4.shp
```
For example, if the project is in `~/Desktop/Code/GeoMesa_Food_Access`, the default path is `~/Desktop/Code/Data/HealthZones1and4/Health_Zones_1_and_4.shp`.

Override paths via environment variables:

```bash
# Base directory for external data (shapefiles)
export GEOMESA_DATA_DIR="/path/to/your/Data"

# Or set the shapefile path directly
export GEOMESA_HEALTH_ZONE_SHP="/path/to/Health_Zones_1_and_4.shp"

# Census data (for HZ1CensusDataLoader - duval_household_attributes.csv, ACS*.csv)
export GEOMESA_CENSUS_DATA_DIR="/path/to/census/data"
```

If the shapefile is missing, the map will use a fallback polygon (Jacksonville area).

## Running the Dashboards

### Live Interactive Dashboard

Run simulations in real time, change parameters, and compare scenarios:

```bash
python live_enhanced_mesa_dash.py
```

Open **http://localhost:8050** in your browser.

### Dissertation Results Dashboard

View pre-computed results (500 households × 365 days, 50 seeds):

```bash
python abm_dashboard_dissertation.py
```

Open **http://localhost:8065** in your browser.

Results are loaded from `results/journal_results_50seeds_recal/` — the recalibrated
(γ = 2.6) 50-seed build, which is the calibration-valid model behind the paper and
supersedes the earlier 6-seed γ = 0.6 runs. The dashboard auto-detects files by
pattern (e.g. `baseline_500hh_365d_seed102_*.json`). Sobol sensitivity indices for
the same build are read from `sobol_indices.json`.

## Running Scenarios

To generate new scenario results:

```bash
# Baseline (no intervention)
python baseline_scenario.py

# Scenario 1: North grocery store
python enhanced_scenario_1.py

# Scenario 2: Food hub + corner stores
python enhanced_scenario_2.py

# Scenario 3: Mobile pantries
python enhanced_scenario_3.py

# Scenario 4: Delivery program
python enhanced_scenario_4.py
```

Outputs are written to `scenarios_results/` as JSON. Use the dissertation dashboard to visualize them.

## Project Structure

```
GeoMesa_Food_Access/
├── config.py                    # Data path configuration
├── requirements.txt
├── README.md
│
├── enhanced_mesa_geo_model.py   # Core ABM engine
├── baseline_scenario.py         # Baseline scenario
├── enhanced_scenario_1.py       # S1: North grocery
├── enhanced_scenario_2.py       # S2: Food hub + corner stores
├── enhanced_scenario_3.py       # S3: Mobile pantries
├── enhanced_scenario_4.py       # S4: Delivery program
├── enhanced_scenario_comparison.py
│
├── live_enhanced_mesa_dash.py   # Live interactive dashboard
├── abm_dashboard_dissertation.py # Dissertation results dashboard
├── dashboard_parameters.py
├── dashboard_config_builder.py
│
├── hz1_census_data_loader.py     # Census demographics
├── census_tract_loader.py
├── real_supermarket_loader.py   # Store data
│
├── sensitivity_analysis_sobol.py # Sobol sensitivity analysis
│
├── supermarkets_with_coords_CURATED.csv
├── hz1_household_data_CORRECTED.csv
├── health_zone_1_census_tracts.txt
├── FINAL_CALIBRATED_PARAMS_*.json
│
├── scenarios_results/           # Scenario run outputs
├── sa_results/                  # Sensitivity analysis outputs
└── extra_Files/                 # Calibration, past versions, tests
```

## Calibration

The model uses calibrated parameters from `FINAL_CALIBRATED_PARAMS_*.json`. These are loaded automatically. Calibration scripts and framework are in `extra_Files/`.

## Sensitivity Analysis

Sobol sensitivity analysis (optional, requires `SALib`):

```bash
pip install SALib
# Run via the live dashboard: Sensitivity Analysis tab
```

## Citation

If you use this code in research, please cite the software and/or the associated journal paper (when published). A `CITATION.cff` file is included for automated citation. Update `CITATION.cff` with your name, email, and GitHub URL before publication.

## License

MIT License. See [LICENSE](LICENSE).
