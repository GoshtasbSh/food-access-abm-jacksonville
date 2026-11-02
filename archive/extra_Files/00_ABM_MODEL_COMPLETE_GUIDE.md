# 🏛️ Agent-Based Model for Food Access Analysis

**Complete Guide to the GeoMesa Food Access ABM**

**Version:** 3.0  
**Date:** October 28, 2025  
**Model Type:** Household-Based Agent-Based Model with Geospatial Components

---

## Table of Contents

1. [Model Overview](#1-model-overview)
2. [Model Architecture](#2-model-architecture)
3. [Input Data & Parameters](#3-input-data--parameters)
4. [Agents & Their Behavior](#4-agents--their-behavior)
5. [Scenarios](#5-scenarios)
6. [Calibration](#6-calibration)
7. [Validation](#7-validation)
8. [How to Run the Model](#8-how-to-run-the-model)
9. [Output & Analysis](#9-output--analysis)
10. [File Structure](#10-file-structure)

---

## 1. Model Overview

### Purpose

This Agent-Based Model (ABM) simulates food access dynamics in Jacksonville's Health Zone 1, focusing on:
- Household shopping behavior
- Food provider operations
- Transportation barriers
- Intervention effectiveness (new stores, delivery subsidies, food hubs, mobile pantries)

### Key Features

- **Household agents** with realistic demographics from census data
- **Multiple food provider types** (grocery stores, corner stores, delivery services, food hubs, mobile pantries)
- **Geospatial analysis** using actual Jacksonville locations
- **Discrete choice model** for household decision-making
- **Scenario comparison** to evaluate interventions

### Research Questions

1. How does current food access vary by income and car ownership?
2. Which interventions most effectively improve food security?
3. What is the cost-effectiveness of delivery subsidies vs. physical infrastructure?
4. How do transportation barriers affect food access equity?

---

## 2. Model Architecture

### Framework

- **Mesa 3.0**: Agent-based modeling framework
- **Mesa-Geo**: Geospatial extension for Mesa
- **GeoPandas/Shapely**: Spatial data handling
- **Plotly/Dash**: Interactive visualization

### Model Components

```
┌─────────────────────────────────────────────────────────────┐
│ EnhancedMesaGeoModel (Main Model)                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐        ┌──────────────────┐          │
│  │ Household Agents │◄──────►│  Food Providers  │          │
│  │ (300-500)        │        │  (7-15)          │          │
│  └──────────────────┘        └──────────────────┘          │
│          │                           │                      │
│          │                           │                      │
│          ▼                           ▼                      │
│  ┌──────────────────────────────────────────────┐          │
│  │   GeoSpace (Jacksonville Health Zone 1)      │          │
│  │   - KDTree spatial index                     │          │
│  │   - Distance calculations                    │          │
│  │   - Provider-household matching              │          │
│  └──────────────────────────────────────────────┘          │
│                                                             │
│  ┌──────────────────────────────────────────────┐          │
│  │   Discrete Choice Model                      │          │
│  │   U = α(-distance) + β(-price) +             │          │
│  │       γ(quality) + δ(convenience)            │          │
│  └──────────────────────────────────────────────┘          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Input Data & Parameters

### 3.1 Census Data (Fixed Inputs)

**Source:** U.S. Census Bureau, American Community Survey (2023)

| Data Type | Values | Used For |
|-----------|--------|----------|
| **Income distribution** | Low: 45%, Med: 35%, High: 20% | Household income assignment |
| **Household size** | 1-2: 60%, 3-4: 30%, 5+: 10% | Household composition |
| **Vehicle availability** | Car: 60%, No car: 40% | Transportation access |
| **SNAP eligibility** | ~40% of low-income | Food assistance programs |
| **Race/ethnicity** | White: 35%, Black: 55%, Hispanic: 5%, Asian: 3%, Other: 2% | Demographics |

**Income Cutoffs (2023):**
- Low: < $28,262
- Medium: $28,262 - $90,239
- High: > $90,239

### 3.2 Economic Parameters (Fixed - From USDA Data)

**Source:** USDA Food Plans 2023

| Parameter | Low Income | Medium Income | High Income | Source |
|-----------|------------|---------------|-------------|--------|
| **Weekly food budget** | $101 | $173 | $327 | USDA Thrifty/Low-Cost/Moderate Plans |
| **Budget distribution** | Lognormal σ=0.25 | | | Literature standard |

**Basket Size by Household Size (mean):**
- 1 person: $131
- 2 people: $143
- 3-4 people: $204
- 5+ people: $262
- **Distribution:** Lognormal σ=0.30

**Source:** USDA + Consumer Expenditure Survey

### 3.3 Travel Parameters (Fixed - From Research)

**Source:** Ver Ploeg et al. (2015) - USDA ERS

| Parameter | Value | Source |
|-----------|-------|--------|
| **Max distance (car)** | 5.5 km (3.4 mi) | USDA ERS food access research |
| **Max distance (no car)** | 0.8 km (0.5 mi) | USDA ERS food access research |
| **Distance noise** | ±10% uniform | Individual preferences |

### 3.4 Delivery Parameters (Fixed Structure)

**Source:** Industry data (Instacart, Walmart+, Amazon Fresh)

| Parameter | Value | Source |
|-----------|-------|--------|
| **Base service fee** | $2.00 | Industry standard 2023 |
| **Distance fee** | $0.75/km | Delivery service benchmarks |
| **Delivery area** | 20 km | Urban service typical |
| **Capacity** | 500 orders/day | Mid-sized service |
| **Hard blockers** | 50% | Pew Research (2021) - Digital divide |

**Subsidy Structure (Scenario 4):**
- Low income: FREE ($0)
- Medium income: 50% off
- High income: Full price

### 3.5 Food Provider Locations (Fixed - Real Data)

**Source:** Actual Jacksonville locations

**Grocery Stores:**
- Walmart Neighborhood Market: (-81.6892, 30.3575), capacity 800
- Save-A-Lot: (-81.7012, 30.3425), capacity 400

**Corner Stores (5 locations):**
- Various locations in Health Zone 1, capacity 50-60 each

---

## 4. Agents & Their Behavior

### 4.1 Household Agents (`EnhancedHouseholdAgent`)

#### Attributes (Fixed per Household)

| Attribute | Type | Source |
|-----------|------|--------|
| `income` | IncomeLevel (LOW/MED/HIGH) | Census data |
| `household_size` | int (1-6) | Census data |
| `vehicle_available` | bool | Census data |
| `snap_eligible` | bool | Census data + income |
| `race` | str | Census data |
| `annual_income` | float | Census data |
| `weekly_budget` | float | USDA + lognormal |
| `mean_basket_size` | float | USDA + household size |
| `max_travel_distance` | float | USDA ERS + noise |
| `can_use_delivery` | bool | 50% (digital divide) |

#### State Variables (Change During Simulation)

| Variable | Initial | Changes When |
|----------|---------|--------------|
| `food_supply` | 1-5 days worth | Daily consumption, shopping |
| `days_since_last_shop` | 0 | Increments daily, resets on shop |
| `weekly_spent` | 0 | Accumulates spending |
| `satisfied_today` | False | Based on food_supply threshold |
| `shopping_history` | [] | Records each shopping event |

#### Daily Behavior Logic

```
FOR EACH DAY:
  1. Consume food (household_size units/day)
  2. Increment days_since_last_shop
  3. Check if need to shop:
     IF days_since_last_shop >= go_shop_threshold:
        needs_to_shop = True
     
  4. IF needs_to_shop:
     A. Find best PHYSICAL store (using utility model)
     B. IF can_use_delivery AND consider_delivery_today():
        - Find best GROCERY STORE (for delivery pickup)
        - Calculate delivery fee (store → household distance)
        - Compare delivery vs. physical
        - Choose based on cost, distance, subsidies
     
     C. Attempt to shop at chosen provider
     D. IF success:
        - Restock food_supply
        - Pay (basket + delivery_fee if applicable)
        - Reset days_since_last_shop = 0
        - Record event in shopping_history
  
  5. Update satisfaction:
     satisfied_today = (food_supply >= household_size × 2)
```

#### Discrete Choice Model

Households choose providers using utility maximization:

```
U(provider, distance) = 
    α × (-normalized_distance) +         [α = 1.0, range 0.6-1.6]
    β × (-price_burden) +                 [β = 0.8, range 0.6-1.4]
    γ × quality_score +                   [γ = 0.6, range 0.4-1.0]
    δ × convenience_score +               [δ = 0.4, range 0.2-0.8]
    store_type_bias(income, store_type)

Provider with HIGHEST utility is chosen.
```

**Calibration Note:** α, β, γ, δ are THE PRIMARY PARAMETERS TO CALIBRATE.

### 4.2 Food Provider Agents

#### Types

1. **Grocery Stores** (`EnhancedGroceryStore`)
   - Large inventory (400-800/day)
   - High quality score (0.8)
   - Full variety
   
2. **Corner Stores** (`EnhancedCornerStore`)
   - Small inventory (50-60/day)
   - Lower quality (0.6)
   - Limited variety
   
3. **Delivery Services** (`EnhancedDeliveryService`)
   - Virtual provider (no physical visit)
   - Picks up from grocery stores
   - Distance-based fees
   - Can be subsidized
   
4. **Food Hubs** (`EnhancedFoodHub`) - Scenario 2
   - High quality (0.9)
   - Large capacity (300/day)
   
5. **Mobile Pantries** (`EnhancedMobilePantry`) - Scenario 3
   - Free food
   - Lower quality (0.7)
   - Limited capacity (120/day)

#### Daily Behavior

```
FOR EACH DAY:
  1. Reset daily counters:
     - current_inventory = capacity
     - customers_served_today = 0
     - daily_revenue = 0
  
  2. Serve customers as they arrive:
     - Decrement inventory
     - Increment customers served
     - Track revenue
  
  3. Record metrics for analysis
```

---

## 5. Scenarios

### Baseline (Market-Rate Delivery)

**Purpose:** Control condition representing current state

**Providers:**
- 2 grocery stores (Walmart, Save-A-Lot)
- 5 corner stores
- 1 **UNSUBSIDIZED** delivery service (everyone pays full price)

**Expected Outcomes:**
- Satisfaction: 60-70%
- Delivery adoption: 5-10% overall (2-4% low, 8-12% med, 15-20% high)
- Travel distance: 2.5-3.0 km average

**File:** `baseline_scenario.py`

### Scenario 1: New Grocery Store

**Intervention:** Add new full-service grocery store in food desert area

**Expected Outcomes:**
- Improved access in underserved area
- Reduced travel distance for nearby households
- Increased satisfaction: +5-10%

**File:** `enhanced_scenario_1.py`

### Scenario 2: Food Hub Network

**Intervention:** Add 2-3 community food hubs with high-quality affordable food

**Expected Outcomes:**
- Better quality/variety options
- Improved access for low-income households
- Increased satisfaction: +8-12%

**File:** `enhanced_scenario_2.py`

### Scenario 3: Mobile Pantry

**Intervention:** Add mobile pantries serving different areas on rotation

**Expected Outcomes:**
- Free food option for eligible households
- Improved food security for most vulnerable
- Increased satisfaction: +10-15%

**File:** `enhanced_scenario_3.py`

### Scenario 4: Subsidized Delivery

**Intervention:** Subsidize online grocery delivery with tiered pricing

**Subsidy Structure:**
- Low income: **FREE** ($0)
- Medium income: **50% off**
- High income: **Full price**

**Expected Outcomes:**
- Delivery adoption: 10-15% overall (15-20% low, 12-16% med, 15-20% high)
- Reduced travel burden (delivery = 0 km for household)
- Increased satisfaction: +5-10%
- **Equity impact:** Largest benefit for low-income households

**File:** `enhanced_scenario_4.py`

---

## 6. Calibration

### 6.1 What to Calibrate

#### PRIMARY Parameters (Main Calibration Targets)

| Parameter | Starting Value | Range | What to Match |
|-----------|---------------|-------|---------------|
| `alpha_distance` | 1.0 | [0.6, 1.6] | Observed travel distances |
| `beta_price` | 0.8 | [0.6, 1.4] | Store choice by income |
| `gamma_quality` | 0.6 | [0.4, 1.0] | Avoid >10% corner as primary |
| `delta_convenience` | 0.4 | [0.2, 0.8] | Shopping frequency patterns |

#### SECONDARY Parameters

| Parameter | Starting Value | Range | What to Match |
|-----------|---------------|-------|---------------|
| `go_shop_threshold_low` | 2.5 days | [2.0, 3.5] | Low-income shopping frequency |
| `go_shop_threshold_medium` | 6.5 days | [6.0, 8.0] | Medium-income shopping frequency |
| `go_shop_threshold_high` | 14.0 days | [10.0, 18.0] | High-income shopping frequency |
| `pantry_propensity_eligible` | 0.15 | [0.10, 0.25] | Pantry utilization (10-15%) |

#### DELIVERY Parameters (Scenario 4 Specific)

| Parameter | Starting Value | Range | What to Match |
|-----------|---------------|-------|---------------|
| `delivery_baseline_low` | 0.02 | [0.0, 0.05] | Low-income baseline delivery (2-4%) |
| `delivery_baseline_medium` | 0.08 | [0.05, 0.15] | Medium-income baseline delivery (8-12%) |
| `delivery_baseline_high` | 0.15 | [0.10, 0.25] | High-income baseline delivery (15-20%) |
| `delivery_subsidy_uplift` | 2.0 | [1.5, 3.0] | Subsidy impact multiplier |
| `delivery_choice_free_prob` | 0.4 | [0.2, 0.6] | FREE delivery choice probability |
| `delivery_choice_nocar_far_prob` | 0.3 | [0.1, 0.5] | No-car delivery choice |
| `delivery_choice_accessible_prob` | 0.1 | [0.0, 0.2] | Accessible physical choice |

**TOTAL: 15 calibration parameters**

### 6.2 Calibration Targets

#### Target 1: Annual Household Spending by Income

**Data Source:** BLS Consumer Expenditure Survey 2023

| Income | Target | Tolerance |
|--------|--------|-----------|
| Low | $5,300 | ±10% |
| Medium | $9,000 | ±10% |
| High | $17,000 | ±10% |

**How to Measure:**
```python
annual_spend = sum([event['basket'] + event.get('delivery_fee', 0) 
                    for event in household.shopping_history]) × 52 / num_days
```

**How to Calibrate:**
- Primarily: `go_shop_threshold` values
- Ensure: `weekly_spend ≈ trips_per_week × mean_basket`

---

#### Target 2: Shopping Frequency Distribution

**Data Source:** Food Marketing Institute (FMI 2022), USDA FoodAPS

| Pattern | Target | Tolerance |
|---------|--------|-----------|
| Weekly shoppers (5-7 days) | 40% | ±10% |
| Frequent (<weekly, >2 days) | 22% | ±8% |
| Bulk (>7 days) | 38% | ±10% |

**Directional Check:**
- Low-income: MORE frequent (smaller budgets)
- High-income: LESS frequent (bulk shopping)

**How to Calibrate:**
- Primary: `go_shop_threshold` values
- Secondary: `delta_convenience` (penalizes frequent trips if low)

---

#### Target 3: Average Travel Distance

**Data Source:** Ver Ploeg et al. (2015) - USDA ERS

| Household Type | Target | Tolerance |
|----------------|--------|-----------|
| Car owners | 3-4 miles (4.8-6.4 km) | +25% |
| No car | ≤0.5 miles (≤0.8 km) | +25% |

**How to Calibrate:**
- Primary: `alpha_distance`
- Fixed: `max_distance_car` and `max_distance_no_car` (do NOT tune)

---

#### Target 4: Primary Store Type

**Data Source:** Food Marketing Institute (FMI 2022)

| Store Type | Target |
|------------|--------|
| Grocery/supercenter as primary | ≥90% |
| Corner/convenience as primary | ≤10% (prefer ≈5%) |

**Why:** Corner stores should be supplemental, not primary

**How to Calibrate:**
- Primary: `gamma_quality` (higher = penalizes low-quality stores)
- Secondary: Store-type biases

---

#### Target 5: Pantry Utilization

**Data Source:** Feeding America 2023, local food bank data

| Metric | Target | Tolerance |
|--------|--------|-----------|
| Share of eligible HH with ≥1 pantry visit | 10-15% | ±3% |

**How to Calibrate:**
- Adjust: `pantry_propensity_eligible`

---

#### Target 6: Delivery Adoption (Baseline)

**Data Source:** USDA FoodAPS, Nielsen, pre-subsidy SNAP pilot

| Income | Target | Tolerance |
|--------|--------|-----------|
| Low | 2-4% | ±1% |
| Medium | 8-12% | ±2% |
| High | 15-20% | ±3% |

**How to Calibrate:**
- Adjust: `delivery_baseline_low/medium/high`

---

#### Target 7: Delivery Adoption (Scenario 4 - Subsidized)

**Data Source:** USDA Online SNAP Pilot (2019-2021)

| Income | Target | Expected Uplift |
|--------|--------|-----------------|
| Low (FREE) | 15-20% | 5-8× baseline |
| Medium (50% off) | 12-16% | 1.5-2× baseline |
| High (full price) | 15-20% | ~1× baseline |

**How to Calibrate:**
- Adjust: `delivery_subsidy_uplift`
- Adjust: `delivery_choice_free_prob`
- Validate: `uplift = adoption_s4 / adoption_baseline`

---

### 6.3 Calibration Workflow

#### Step 1: Calibrate Baseline (WITHOUT Delivery Scenarios)

**Goal:** Match targets 1-5 first

```
1. Run baseline 30 times (30 seeds × 30 days each)
2. Measure all 5 targets
3. Calculate error for each target
4. Adjust parameters:
   - Start with alpha_distance (biggest impact on travel)
   - Then gamma_quality (impacts store choice)
   - Then go_shop_thresholds (impacts frequency/spending)
   - Finally pantry_propensity
5. Repeat until all 5 targets within tolerance
```

**Objective Function:**
```python
total_error = sum([
    |actual_spending_low - 5300| / 5300,
    |actual_spending_med - 9000| / 9000,
    |actual_spending_high - 17000| / 17000,
    |actual_weekly_shoppers - 0.40| / 0.40,
    |actual_car_distance - 5.0| / 5.0,
    |actual_nocar_distance - 0.8| / 0.8,
    |actual_corner_primary - 0.05| / 0.05,
    |actual_pantry_rate - 0.125| / 0.125
])
```

**Stop When:** `total_error < 0.5` (50% average error) AND each individual target within tolerance

#### Step 2: Calibrate Baseline Delivery

**Goal:** Match target 6 (baseline delivery adoption)

```
1. Use calibrated parameters from Step 1
2. Run baseline WITH delivery (market-rate)
3. Measure delivery adoption by income
4. Adjust delivery_baseline_low/medium/high
5. Repeat until target 6 within tolerance
```

#### Step 3: Calibrate Scenario 4 (Subsidized Delivery)

**Goal:** Match target 7 (subsidized delivery adoption)

```
1. Use ALL calibrated parameters from Steps 1-2
2. Run Scenario 4 (subsidized delivery)
3. Measure delivery adoption by income
4. Adjust:
   - delivery_subsidy_uplift
   - delivery_choice_free_prob
5. Validate uplift: adoption_s4 / adoption_baseline ≈ subsidy_uplift
6. Repeat until target 7 within tolerance
```

#### Step 4: Validate All Scenarios

Run Scenarios 1, 2, 3 with calibrated parameters and check results make sense.

---

### 6.4 Calibration Implementation

**NOT Automatic** - Manual iterative process

**Files Needed:**
- `baseline_scenario.py` - For Steps 1-2
- `enhanced_scenario_4.py` - For Step 3
- Custom analysis scripts to measure targets

**Example Calibration Script:**

```python
from baseline_scenario import create_baseline_scenario
from enhanced_mesa_geo_model import SimulationConfig
import numpy as np

# Step 1: Run baseline multiple times
results = []
for seed in range(30):
    config = SimulationConfig(
        num_consumers=300,
        simulation_days=30,
        alpha_distance=1.0,  # TRY DIFFERENT VALUES
        gamma_quality=0.6,
        # ... other parameters
    )
    
    model = create_baseline_scenario(config)
    for day in range(30):
        model.step()
    
    # Measure targets
    # ... calculate spending, frequency, distance, etc.
    results.append(metrics)

# Calculate average error
# Adjust parameters
# Repeat
```

**Expected Time:** 2-4 hours for full calibration (3-8 iterations)

---

## 7. Validation

### 7.1 Face Validity

**Question:** Do model behaviors make intuitive sense?

✅ **Check:**
- Low-income shops more frequently (smaller trips)
- No-car households travel shorter distances
- Delivery adoption higher for high-income (can afford)
- FREE delivery increases low-income adoption
- Households prefer grocery stores over corner stores

### 7.2 Internal Validation

**Question:** Is model output stable and consistent?

#### Stochasticity Test

```python
# Run 100 times with different seeds
results = []
for seed in range(100):
    model = create_baseline_scenario()
    # ... run
    results.append(satisfaction_rate)

mean = np.mean(results)
std = np.std(results)
cv = std / mean  # Coefficient of variation

# Check: CV should be < 0.15 (15%)
assert cv < 0.15, f"Too stochastic: CV = {cv:.2%}"
```

**Expected:**
- Satisfaction: 65% ± 5% (CV ≈ 7%)
- Travel distance: 2.5 km ± 0.3 km (CV ≈ 12%)

#### Sensitivity Analysis

Test how outcomes change with parameter variations:

```python
# Vary alpha_distance by ±20%
for alpha in [0.8, 1.0, 1.2]:
    # Run model
    # Check if avg_distance changes monotonically
```

**Expected:** Higher α → Lower distance (more penalty)

### 7.3 External Validation

**Question:** Does model match independent real-world data?

#### Data Sources for Validation

1. **USDA FoodAPS (2012-2013):** Food shopping diaries
2. **USDA Online SNAP Pilot (2019-2021):** Delivery adoption with subsidies
3. **Feeding America reports:** Pantry utilization
4. **Local food bank data (Jacksonville):** Ground truth for study area
5. **Nielsen Homescan:** Consumer panel data (if accessible)

#### Validation Metrics

| Metric | Model Output | Real Data | MAPE |
|--------|--------------|-----------|------|
| Annual spending (low) | ? | $5,300 | <15% |
| Trip frequency | ? | 40% weekly | <15% |
| Travel distance (car) | ? | 3-4 mi | <25% |
| Delivery adoption (baseline) | ? | 2-4% low | <20% |
| Delivery adoption (subsidized) | ? | 15-20% low | <20% |

**Good:** MAPE < 15%  
**Acceptable:** MAPE < 25%  
**Poor:** MAPE > 25%

### 7.4 Comparative Validation

**Question:** Do scenario comparisons show expected patterns?

✅ **Check:**
- Scenario 4 vs. Baseline: Higher delivery adoption ✅
- Scenario 4 vs. Baseline: Lower travel distance ✅
- Scenario 4 vs. Baseline: Similar or slightly higher satisfaction ✅
- Subsidy uplift: adoption_s4 / adoption_baseline ≈ 5-8× for low-income ✅

---

## 8. How to Run the Model

### 8.1 Setup

```bash
# Create conda environment
conda create -n abm310 python=3.10
conda activate abm310

# Install dependencies
pip install -r requirements.txt
```

### 8.2 Run Baseline

```python
from baseline_scenario import create_baseline_scenario
from enhanced_mesa_geo_model import SimulationConfig

# Configure
config = SimulationConfig(
    num_consumers=300,
    simulation_days=30
)

# Create model
baseline = create_baseline_scenario(config)

# Run simulation
for day in range(30):
    baseline.step()
    if (day + 1) % 10 == 0:
        print(f"Day {day+1}/30 complete")

# Analyze results
results = baseline.analyze_baseline_outcomes()
print(f"Satisfaction: {results['overall_metrics']['avg_satisfaction_rate']:.1%}")
print(f"Delivery adoption: {results['baseline_analysis']['delivery_metrics']['overall_adoption']:.1%}")
```

### 8.3 Run Scenario 4

```python
from enhanced_scenario_4 import create_enhanced_scenario_4

# Create scenario (uses same config)
scenario4 = create_enhanced_scenario_4(config)

# Run
for day in range(30):
    scenario4.step()

# Compare to baseline
# ...
```

### 8.4 Run Dashboard (Interactive)

```bash
python live_enhanced_mesa_dash.py
```

Then open browser to `http://localhost:8050`

- Select scenario (Baseline, Scenario 1-4)
- Set number of households (300 recommended)
- Set simulation days (30 recommended)
- Click "Start Simulation"
- Watch real-time visualization

---

## 9. Output & Analysis

### 9.1 Model Outputs

| Output | Type | Description |
|--------|------|-------------|
| `metrics_history` | List[Dict] | Daily metrics (satisfaction, travel, etc.) |
| `shopping_history` | Per household | All shopping events |
| `food_providers` | List | Provider utilization data |
| `spatial_data` | GeoDataFrame | Geospatial analysis |

### 9.2 Key Metrics

**Household-Level:**
- Satisfaction rate (% with adequate food)
- Food insecurity rate (% food insecure)
- Shopping frequency (trips/week)
- Travel distance (km/trip)
- Delivery adoption (% trips via delivery)
- Weekly spending ($)

**Provider-Level:**
- Customers served
- Utilization rate (customers / capacity)
- Revenue (if tracked)
- Catchment area

**Equity Metrics:**
- Satisfaction gap (car vs. no-car)
- Satisfaction gap (low vs. high income)
- Spatial equity index
- Access disparity by census tract

### 9.3 Scenario Comparison

```python
# Compare satisfaction
baseline_satisfaction = 65%
scenario4_satisfaction = 72%
improvement = +7%  # Subsidy impact

# Compare delivery adoption
baseline_delivery = 5%
scenario4_delivery = 15%
uplift = 3×  # Subsidy effectiveness

# Compare equity
baseline_gap = 15% (car vs no-car satisfaction)
scenario4_gap = 8%  # Reduced gap (delivery helps no-car HH)
```

---

## 10. File Structure

### Core Model Files

| File | Purpose | Lines | Documented In |
|------|---------|-------|---------------|
| `enhanced_mesa_geo_model.py` | Main ABM engine, agent classes, model logic | 1906 | `01_CORE_MODEL_CODE.md` |
| `census_tract_loader.py` | Load census data, generate household demographics | ~300 | `02_CENSUS_LOADER_CODE.md` |

### Scenario Files

| File | Purpose | Documented In |
|------|---------|---------------|
| `baseline_scenario.py` | Baseline with market-rate delivery | `03_BASELINE_CODE.md` |
| `enhanced_scenario_1.py` | New grocery store | `04_SCENARIO_1_CODE.md` |
| `enhanced_scenario_2.py` | Food hub network | `05_SCENARIO_2_CODE.md` |
| `enhanced_scenario_3.py` | Mobile pantry | `06_SCENARIO_3_CODE.md` |
| `enhanced_scenario_4.py` | Subsidized delivery | `07_SCENARIO_4_CODE.md` |

### Dashboard Files

| File | Purpose | Documented In |
|------|---------|---------------|
| `live_enhanced_mesa_dash.py` | Interactive dashboard | `08_DASHBOARD_CODE.md` |
| `dashboard_parameters.py` | Dashboard parameter layouts | (Included in 08) |
| `dashboard_config_builder.py` | Config builder from dashboard | (Included in 08) |

### Analysis Files

| File | Purpose |
|------|---------|
| `enhanced_scenario_comparison.py` | Compare scenarios |
| `calibration_framework.py` | Calibration utilities |

---

## Summary

### What Makes This Model Unique

1. **Household-based** (not individual-based) with realistic demographics
2. **Geospatial** using actual Jacksonville locations
3. **Delivery service** with distance-based fees and subsidies
4. **Discrete choice model** for realistic decision-making
5. **Multiple interventions** (physical infrastructure + delivery)
6. **Calibrated to real data** (USDA, Census, industry data)
7. **Interactive dashboard** for exploration

### Key Findings (Expected)

- **Baseline:** 60-70% satisfaction, 5-10% delivery adoption
- **Scenario 4 (subsidized delivery):** 65-75% satisfaction, 10-15% delivery adoption
- **Equity impact:** Largest benefits for low-income, no-car households
- **Cost-effectiveness:** Delivery subsidy may be more cost-effective than building new stores

### Next Steps

1. ✅ Model is implemented
2. ⚠️ **Calibrate to match real-world targets** (2-4 hours)
3. ⚠️ **Validate against independent data**
4. ⚠️ **Run all scenarios and compare**
5. ⚠️ **Analyze policy implications**
6. ⚠️ **Write up results for publication**

---

**For detailed line-by-line code documentation, see:**
- `01_CORE_MODEL_CODE.md` - Main model code
- `02_CENSUS_LOADER_CODE.md` - Census data loading
- `03-07_SCENARIO_CODE.md` - Scenario implementations
- `08_DASHBOARD_CODE.md` - Dashboard code

**Model Status:** ✅ Ready for calibration and use

