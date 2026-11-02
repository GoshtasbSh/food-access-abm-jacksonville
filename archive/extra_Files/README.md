# Extra Files

This directory contains files moved from the main GeoMesa_Food_Access project that are not needed for day-to-day use:

## Scripts (obsolete / one-off)
- **Obsolete calibration runners**: run_SIMPLE_calibration, run_QUICK_calibration, run_CORRECTED_CALIBRATION, run_FOCUSED_RECALIBRATION, etc. — superseded by `run_PHASE2_VALIDATION.py` and `run_ALL_SCENARIOS_calibrated.py`
- **Test/diagnostic scripts**: test_*.py, verify_*.py, DIAGNOSE_*.py, check_dashboard_params.py, MINIMAL_calibration_test.py
- **Utilities**: extract_hz1_census_summary.py, calculate_optimal_multipliers.py, calibrate_choice_model.py

## Output artifacts
- **Logs**: dashboard.log, comprehensive_grid_search_live.log
- **Run outputs**: *output.txt, *output_FIXED.txt, etc.
- **Calibration progress**: calibration_progress_*.csv (intermediate snapshots)
- **Result files**: JSON params, CSV results from various calibration runs

## Documentation (historical)
- Status/process notes: PRE_CALIBRATION_*, CALIBRATION_COMPLETE_FINAL, CRITICAL_FIXES, etc.

These files are kept for reference and reproducibility but are not required to run the main dashboard (`live_enhanced_mesa_dash.py`) or scenario comparison.
