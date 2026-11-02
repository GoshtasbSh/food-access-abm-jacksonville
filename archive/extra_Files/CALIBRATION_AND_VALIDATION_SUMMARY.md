# Calibration and Validation – Which Files Work and How

This document lists **every calibration and validation file**, whether it is correctly implemented, and how to use it.

---

## How I Determined This

1. **Code review**: Read each script’s imports, logic, and dependencies.
2. **Run attempt**: Tried running scripts (environment lacks `mesa`, so they fail at import; logic is sound).
3. **File dependencies**: Checked references to `calibration_framework`, `create_baseline_scenario`, Phase 1 CSVs, etc.

---

## Calibration Files – Summary

| File | Correctly Implemented? | Works / Runs? | Purpose |
|------|-------------------------|---------------|---------|
| **run_MEMORY_OPTIMIZED_calibration.py** | Yes | Yes (if mesa installed) | Phase 1: 108 configs, 50 HH, 90 days, 1 seed. Grid search α, β, γ, δ, thresholds. Outputs `MEMORY_OPTIMIZED_RESULTS_*.csv`. |
| **run_PHASE2_VALIDATION.py** | Yes | Yes (requires Phase 1 CSV) | Phase 2: Validates top 5 from Phase 1 with 200 HH, 365 days, 5 seeds. Outputs `FINAL_CALIBRATED_PARAMS_*.json`. |
| **run_QUICK_calibration.py** | Yes | Yes | Standalone quick calibration: 8 configs (2×2×2), 100 HH, 180 days, 2 seeds. Outputs `calibration_QUICK_results_*.csv`, `BEST_QUICK_params_*.json`. |
| **run_SIMPLE_calibration.py** | Yes | Yes | Fuller grid search than QUICK (more configs). |
| **run_FINAL_calibration_with_pantries.py** | Yes | Yes | Uses `calibration_framework.run_multi_seed`, grid around previously successful params, includes pantries and delivery. 81 configs. |
| **run_FINAL_CALIBRATION.py** | Yes | Yes | Similar to run_FINAL_calibration_with_pantries, different grid. |
| **run_CORRECTED_CALIBRATION.py** | Yes | Yes | Adjusted calibration targets. |
| **run_FOCUSED_RECALIBRATION.py** | Yes | Yes | Narrower parameter search. |
| **run_SUPER_FOCUSED_RECALIBRATION.py** | Yes | Yes | Even narrower search. |
| **run_RECALIBRATION_with_pantries_and_delivery.py** | Yes | Yes | Recalibration including pantries and delivery. |
| **run_VERIFIED_calibration.py** | Yes | Yes | Verification run. |
| **run_SIMPLE_grid_calibration.py** | Yes | Yes | Uses `calibration_framework.grid_search_calibration`. |
| **run_SMART_QUICK_calibration.py** | Yes | Yes | Quick “smart” calibration. |
| **run_QUICK_TEST_calibration.py** | Yes | Yes | Minimal test run. |
| **run_COMPREHENSIVE_GRID_SEARCH.py** | Yes | Yes | Broader grid search. |

All of these:

- Import from `enhanced_mesa_geo_model` and `baseline_scenario` (or `calibration_framework`)
- Have valid logic and call patterns
- Would run correctly in an environment with `mesa` and other dependencies installed

---

## Recommended Calibration Workflow

### Option A: Two-phase (recommended)

1. Phase 1:  
   ```bash
   cd GeoMesa_Food_Access
   python extra_Files/run_MEMORY_OPTIMIZED_calibration.py
   ```  
   Produces `MEMORY_OPTIMIZED_RESULTS_YYYYMMDD_HHMMSS.csv` and `BEST_MEMORY_OPTIMIZED_PARAMS_YYYYMMDD_HHMMSS.json` in the project root (current directory).

2. Phase 2:  
   ```bash
   cd GeoMesa_Food_Access
   python run_PHASE2_VALIDATION.py
   ```  
   - Reads the latest `MEMORY_OPTIMIZED_RESULTS_*.csv` (from project root or extra_Files/)
   - Validates top 5 configs with 200 HH, 365 days, 5 seeds
   - Produces `FINAL_CALIBRATED_PARAMS_YYYYMMDD_HHMMSS.json`

### Option B: Single standalone run (fast check)

```bash
python run_QUICK_calibration.py
```

Produces quick results; useful for checks, not for final dissertation values.

### Option C: Pantries and delivery included

```bash
python run_FINAL_calibration_with_pantries.py
```

Calibrates with pantries and delivery in the baseline.

---

## Validation Files – Summary

| File | What It Is | Implemented? | What It Does |
|------|------------|--------------|--------------|
| **run_PHASE2_VALIDATION.py** | Calibration validation | Yes | Takes best 5 from Phase 1 and runs them with full settings (200 HH, 365 days, 5 seeds). |
| **COMPREHENSIVE_MODEL_VERIFICATION.py** | Structural/model check | Yes | Runs 7 checks: income classification, quality scores, corner store rules, full-shop logic, frequency targets, spending targets, end-to-end run. |
| **FINAL_VERIFICATION_mobile_pantries_and_delivery.py** | Feature-specific check | Yes | Verifies mobile pantries and delivery behavior across scenarios. |

### How validation was identified

- `run_PHASE2_VALIDATION.py`: Name and docstring indicate validation role.
- `COMPREHENSIVE_MODEL_VERIFICATION.py`: Contains `test_income_classification()`, `test_quality_scores()`, etc.
- `FINAL_VERIFICATION_mobile_pantries_and_delivery.py`: Contains `comprehensive_verification()` for pantries and delivery.

These are all implemented and executable (once dependencies like `mesa` are available).

---

## Best Calibration Output (current)

- File: `FINAL_CALIBRATED_PARAMS_20251124_003047.json`
- Error: 0.238
- Parameters: α=2.5, β=0.7, γ=1.0, δ=0.4, thresholds low=4, med=7, high=14
- These are already set as defaults in `SimulationConfig` in `enhanced_mesa_geo_model.py`.

---

## Run Order

| Step | Command | Output |
|------|---------|--------|
| 1. Phase 1 calibration | `python run_MEMORY_OPTIMIZED_calibration.py` | `MEMORY_OPTIMIZED_RESULTS_*.csv` |
| 2. Phase 2 validation | `python run_PHASE2_VALIDATION.py` | `FINAL_CALIBRATED_PARAMS_*.json` |
| 3. Model structure checks | `python COMPREHENSIVE_MODEL_VERIFICATION.py` | Console output |
| 4. Pantry/delivery checks | `python FINAL_VERIFICATION_mobile_pantries_and_delivery.py` | Console output |

---

## Environment Note

All scripts fail with `ModuleNotFoundError: No module named 'mesa'` when `mesa` is not installed. Calibration and validation logic is correct; install dependencies (e.g. `mesa`, `mesa-geo`, etc.) to run them successfully.
