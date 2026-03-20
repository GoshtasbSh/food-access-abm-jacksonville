# GeoMesa Food Access ABM – Comprehensive Model Analysis Report

**Date:** February 18, 2025  
**Scope:** Full codebase review, dashboard connectivity, calibration, and validation

---

## Executive Summary

Your GeoMesa Food Access ABM is structurally sound: baseline and four intervention scenarios are implemented, the core model logic is coherent, and calibration has produced validated parameters. However, there are critical gaps in dashboard–model connectivity: **interactive dashboard inputs are largely not used by the main model**. Most user-edited parameters do not reach the simulation. The calibration framework is well designed; the best results come from Phase 1 + Phase 2 validation. Validation exists but could be systematized.

---

## 1. Model Architecture – How It Works Step by Step

### 1.1 High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  live_enhanced_mesa_dash.py (Dashboard)                                      │
│  User selects scenario, edits parameters, clicks Start                       │
└──────────────────────────────────────────┬──────────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  dashboard_config_builder.build_config_from_inputs(input_dict)              │
│  Builds SimulationConfig from collected parameters                           │
└──────────────────────────────────────────┬──────────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Scenario factory (create_baseline_scenario, create_enhanced_scenario_1..4)  │
│  Creates model with config, adds households, providers                        │
└──────────────────────────────────────────┬──────────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  model.step() – run daily (1..N days)                                       │
│  Each day: households decide to shop, choose store, travel, spend           │
└──────────────────────────────────────────┬──────────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Metrics: satisfaction, food insecurity, travel distance, spending           │
│  Stored in model.metrics_history, displayed in dashboard                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Model Step Logic (Per Day)

1. **Household needs check**
   - Each household has a “go-shop” threshold (days since last trip).
   - If `days_since_last_shop >= threshold`, household decides to shop.

2. **Store choice (discrete choice model)**
   - Household evaluates all reachable providers (grocery, corner, food hub, pantry, delivery).
   - Utility:  
     `U = α×distance + β×price/budget + γ×quality + δ×convenience`
   - Chooses provider with highest utility (or probabilistic choice).

3. **Trip execution**
   - Travel to store (or delivery).
   - Basket size from income × household size (income multipliers).
   - Corner stores: $25 cap, 1.16× price premium.
   - Full-shop vs top-up logic based on budget and need.

4. **Metrics aggregation**
   - Satisfaction, food insecurity, travel distance, spending by income, store-type shares, etc.

---

## 2. Scenarios and Their Parameters

| Scenario | Description | Key Parameters |
|----------|-------------|----------------|
| **Baseline** | Current HZ1: real stores, FNEFL pantries, market-rate delivery | Real data; num_consumers, simulation_days, α, β, γ, δ, delivery propensities |
| **Scenario 1** | New grocery store | `grocery_store_capacity` (default 600) |
| **Scenario 2** | Food hub + corner network | `food_hub_capacity`, `num_corner_stores`, `corner_store_capacity` |
| **Scenario 3** | Additional mobile pantries | `num_mobile_pantries`, `mobile_pantry_capacity`, `mobile_pantry_strategy` |
| **Scenario 4** | Subsidized delivery | `delivery_capacity`, `base_service_fee`, `distance_fee_per_km`, `delivery_area_km` (function args) |

### Scenario Parameter Sources

- **Scenarios 1–3** read from `SimulationConfig` (e.g. `config.grocery_store_capacity`, `config.num_corner_stores`).
- **Scenario 4** uses function arguments in `create_enhanced_scenario_4()` (not config fields):  
  `delivery_capacity=500`, `base_service_fee=2.00`, `distance_fee_per_km=0.75`, `delivery_area_km=20.0`.

---

## 3. Dashboard Connection – Gap Analysis

### 3.1 Current Parameter Collection (Critical Bug)

The dashboard uses a **clientside callback** to fill `collected-parameters`:

```javascript
// live_enhanced_mesa_dash.py lines 1126–1155
document.getElementById('num-consumers')   // WRONG: actual ID is param-num-consumers
document.getElementById('simulation-days')  // WRONG: actual ID is param-simulation-days
```

- **IDs mismatch:** Inputs use `param-num-consumers` and `param-simulation-days`, but the JS looks for `num-consumers` and `simulation-days`. Elements are never found.
- **Result:** Collection always falls back to defaults: `num-consumers: 300`, `simulation-days: 30`.

### 3.2 `build_config_from_inputs()` vs. Expected Parameters

| Dashboard Input ID | In `build_config_from_inputs`? | Used in Model? |
|-------------------|-------------------------------|----------------|
| `param-num-consumers` | ✓ Yes (as `param-num-consumers`) | Yes |
| `param-simulation-days` | ✓ Yes | Yes |
| `param-alpha`, `param-beta`, `param-gamma`, `param-delta` | ✓ Yes | Yes |
| `param-delivery-low/medium/high` | ✓ Yes | Yes |
| `param-grocery-capacity` | ❌ No | Scenario 1 uses `config.grocery_store_capacity` |
| `param-food-hub-capacity` | ❌ No | Scenario 2 |
| `param-num-corner-stores` | ❌ No | Scenario 2 |
| `param-corner-capacity` | ❌ No | Scenario 2 |
| `param-num-mobile-pantries` | ❌ No | Scenario 3 |
| `param-mobile-pantry-capacity` | ❌ No | Scenario 3 |
| `param-pantry-strategy` | ❌ No | Scenario 3 |
| `param-delivery-capacity` | ❌ No | Scenario 4 (function arg) |
| `param-base-fee` | ❌ No | Scenario 4 |
| `param-distance-fee` | ❌ No | Scenario 4 |
| `param-delivery-area` | ❌ No | Scenario 4 |

### 3.3 Additional Problem: Key Mismatch

Even if the DOM lookup were fixed, the clientside callback returns:

```json
{"num-consumers": 300, "simulation-days": 30}
```

But `build_config_from_inputs` expects:

```python
'param-num-consumers'  # NOT 'num-consumers'
'param-simulation-days'  # NOT 'simulation-days'
```

So current keys would not match, and config would still fall back to defaults for these two fields.

### 3.4 Conclusion: Dashboard–Model Connection

**Interactive inputs are largely not used.** The model effectively runs with:

1. Hard-coded defaults for basic parameters (due to collection/key bugs).
2. Choice and delivery parameters never populated from the UI.
3. No scenario-specific parameters (grocery capacity, food hub, corner stores, pantries, subsidized delivery) passed from the dashboard.

---

## 4. Calibration System – What Exists and What Works Best

### 4.1 Calibration Files Overview

| File | Role | Recommended Use |
|------|------|-----------------|
| `calibration_framework.py` | Core: targets, `run_single_seed`, `run_multi_seed`, `calculate_calibration_error`, grid search | Use as the main calibration engine |
| `run_MEMORY_OPTIMIZED_calibration.py` | Phase 1: 108 configs, 50 HH, 90 days, 1 seed | First pass to find candidate parameter sets |
| `run_PHASE2_VALIDATION.py` | Phase 2: top 5 configs, 200 HH, 365 days, 5 seeds | Robustness check and final selection |
| `run_FINAL_calibration_with_pantries.py` | Pantries + delivery included | Useful if calibrating with pantries |
| `calibrate_choice_model.py` | Simple α/β/γ/δ/threshold tuning | Auxiliary |
| `calculate_optimal_multipliers.py` | Basket size multipliers | Auxiliary |

### 4.2 Best Calibration Result

**File:** `FINAL_CALIBRATED_PARAMS_20251124_003047.json`  
**Calibration error:** 0.238 (≈23.8% average deviation)

**Parameters:**

```json
{
  "alpha_distance": 2.5,
  "beta_price_budget": 0.7,
  "gamma_quality_variety": 1.0,
  "delta_convenience": 0.4,
  "go_shop_threshold_low": 4,
  "go_shop_threshold_medium": 7,
  "go_shop_threshold_high": 14
}
```

Validation settings: 200 households, 365 days, 5 seeds.

These values are already set as defaults in `SimulationConfig` (enhanced_mesa_geo_model.py lines 244–258).

### 4.3 Calibration Targets (from calibration_framework.py)

| Metric | Target | Source |
|--------|--------|--------|
| Annual spend (low income) | $5,270 | Your table |
| Annual spend (medium) | $8,989 | Your table |
| Annual spend (high) | $16,996 | Your table |
| Weekly frequency share | ~40% | Your table |
| Sub-weekly frequency share | ~22% | Your table |
| Distance (car) | 3.48 mi | 5.6 km |
| Distance (no car) | 0.50 mi | 0.8 km |
| Primary “other” (corner/small) stores | ≤10% | Your table |

### 4.4 What the Calibration Does

1. **Phase 1 (Memory-Optimized):**
   - Grid search over α, γ, threshold (108 combinations).
   - Each config: 50 HH, 90 days, 1 seed.
   - For each run: annual spend by income, trip frequency, distances, small-store share.
   - Normalized error computed (mean of component errors).

2. **Phase 2 (Validation):**
   - Top 5 configs from Phase 1.
   - 200 HH, 365 days, 5 seeds per config.
   - Final best = Config #73 (error 0.238).

---

## 5. Validation – What Exists

| File | Purpose |
|------|---------|
| `run_PHASE2_VALIDATION.py` | Validates best calibration configs with full population and year |
| `COMPREHENSIVE_MODEL_VERIFICATION.py` | Structural checks: income classification, quality scores, corner constraints, full-shop logic, frequency, spending, end-to-end |
| `COMPREHENSIVE_FINAL_TEST_dashboard_and_all_scenarios.py` | Integration: dashboard logic + all scenarios |
| `FINAL_VERIFICATION_mobile_pantries_and_delivery.py` | Mobile pantries and delivery |
| `test_*.py`, `verify_*.py` | Unit-style tests (budget, delivery, census, pantries) |

---

## 6. Summary of Gaps

| Gap | Severity | Location |
|-----|----------|----------|
| Clientside callback uses wrong DOM IDs | **Critical** | `live_enhanced_mesa_dash.py` 1136–1148 |
| Key mismatch: `num-consumers` vs `param-num-consumers` | **Critical** | Clientside callback vs `dashboard_config_builder.py` |
| Scenario-specific params not in `build_config_from_inputs` | **High** | `dashboard_config_builder.py` |
| Scenario 4 params (delivery) passed as function args, not via config | **Medium** | `live_enhanced_mesa_dash.py` 2181, `enhanced_scenario_4.py` |
| No collection of α, β, γ, δ, delivery from DOM | **High** | Clientside callback only collects 2 params |

---

## 7. Recommended Fixes for Dashboard–Model Connection

### Fix 1: Use a Server-Side Callback for Parameter Collection

Replace the clientside callback with a server-side callback that:

1. Uses `Input("start-btn", "n_clicks")` plus `State` for all parameter inputs.
2. Reads from the actual Dash inputs:  
   `State("param-num-consumers", "value")`, `State("param-simulation-days", "value")`,  
   `State("param-alpha", "value")`, etc.
3. Builds `input_dict` with keys that match what `build_config_from_inputs` expects (e.g. `param-num-consumers`, `param-alpha`).
4. Passes this to `build_config_from_inputs` when Start is clicked.

### Fix 2: Extend `build_config_from_inputs`

Add mappings for scenario parameters:

```python
# Scenario 1
if 'param-grocery-capacity' in input_values:
    config.grocery_store_capacity = int(input_values['param-grocery-capacity'])

# Scenario 2
if 'param-food-hub-capacity' in input_values:
    config.food_hub_capacity = int(input_values['param-food-hub-capacity'])
if 'param-num-corner-stores' in input_values:
    config.num_corner_stores = int(input_values['param-num-corner-stores'])
if 'param-corner-capacity' in input_values:
    config.corner_store_capacity = int(input_values['param-corner-capacity'])

# Scenario 3
if 'param-num-mobile-pantries' in input_values:
    config.num_mobile_pantries = int(input_values['param-num-mobile-pantries'])
if 'param-mobile-pantry-capacity' in input_values:
    config.mobile_pantry_capacity = int(input_values['param-mobile-pantry-capacity'])
if 'param-pantry-strategy' in input_values:
    config.mobile_pantry_strategy = input_values['param-pantry-strategy']

# Scenario 4: store in config or pass to create_enhanced_scenario_4
```

### Fix 3: Scenario 4 Integration

Either:

- Add delivery fields to `SimulationConfig` and use them in `create_enhanced_scenario_4`, or
- Keep function args and pass them from the dashboard:

```python
model = create_enhanced_scenario_4(
    config, use_real_data=True,
    delivery_capacity=input_dict.get('param-delivery-capacity', 500),
    base_service_fee=input_dict.get('param-base-fee', 2.00),
    distance_fee_per_km=input_dict.get('param-distance-fee', 0.75),
    delivery_area_km=input_dict.get('param-delivery-area', 20.0)
)
```

### Fix 4: `collected-parameters` Flow

- Remove or bypass the broken clientside callback.
- Use the server-side callback described above so parameters are collected only when Start is clicked and passed to `build_config_from_inputs`.

---

## 8. Calibration Improvements

1. **Structured pipeline:**  
   Keep Phase 1 (exploration) → Phase 2 (validation) as the main workflow.

2. **Parameter expansion:**  
   Include delivery and pantry parameters in calibration if they affect baseline behavior (e.g. baseline delivery usage).

3. **Sensitivity analysis:**  
   After calibration, run sensitivity tests on key parameters (α, β, γ, thresholds).

4. **External validation:**  
   Compare model outputs to independent datasets (e.g. USDA, local surveys, trip data) if available.

5. **Automated reporting:**  
   Add a script that:
   - Loads FINAL_CALIBRATED_PARAMS
   - Runs N seeds
   - Produces a short report of mean ± std for spend, frequency, distances, small-store share.

---

## 9. Checklist – What Works vs. Gaps

| Component | Status | Notes |
|-----------|--------|-------|
| Core ABM (enhanced_mesa_geo_model.py) | ✅ Working | Logic, discrete choice, spatial logic |
| Baseline scenario | ✅ Working | Real stores, pantries, delivery |
| Scenario 1 (new grocery) | ✅ Working | Uses config |
| Scenario 2 (food hub + corners) | ✅ Working | Uses config |
| Scenario 3 (mobile pantries) | ✅ Working | Uses config |
| Scenario 4 (subsidized delivery) | ✅ Working | Uses defaults only (no UI override) |
| Data loaders (census, stores) | ✅ Working | HZ1 data loaded correctly |
| Calibration framework | ✅ Working | Targets, error, grid search |
| Best calibration | ✅ Applied | FINAL_CALIBRATED_PARAMS 20251124 |
| Phase 2 validation | ✅ Working | 200 HH, 365 d, 5 seeds |
| Dashboard UI | ✅ Working | Map, metrics, scenario selection |
| Dashboard → model params | ❌ Broken | Most inputs not used |
| Scenario-specific UI params | ❌ Not wired | Need `build_config_from_inputs` updates |

---

## 10. Quick Reference – Model Entry Points

| Task | Command / File |
|------|----------------|
| Run dashboard | `python live_enhanced_mesa_dash.py` |
| Run all scenarios (calibrated) | `python run_ALL_SCENARIOS_calibrated.py` |
| Run Phase 1 calibration | `python run_MEMORY_OPTIMIZED_calibration.py` |
| Run Phase 2 validation | `python run_PHASE2_VALIDATION.py` |
| Comprehensive model check | `python COMPREHENSIVE_MODEL_VERIFICATION.py` |
| Best calibration params | `FINAL_CALIBRATED_PARAMS_20251124_003047.json` |

---

*Report generated from full codebase analysis. For implementation of the recommended fixes, see Section 7.*
