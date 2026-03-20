"""Minimal calibration test to show progress immediately"""
import sys
import time

print("="*80, flush=True)
print("STARTING CALIBRATION TEST", flush=True)
print("="*80, flush=True)
print("", flush=True)

print("Step 1: Importing libraries...", flush=True)
sys.path.append('/Users/goshtasbshahriari/Desktop/Code/GeoMesa_Food_Access')

try:
    from enhanced_mesa_geo_model import SimulationConfig, IncomeLevel, EnhancedHouseholdAgent
    print("  ✓ Model imported", flush=True)
    
    from baseline_scenario import create_baseline_scenario
    print("  ✓ Baseline scenario imported", flush=True)
    print("", flush=True)
    
    print("Step 2: Running 1 quick test configuration...", flush=True)
    print("  Config: α=2.0 β=1.0 γ=1.5", flush=True)
    
    config = SimulationConfig(
        num_consumers=50,  # Small for speed
        simulation_days=30,  # Short run
        alpha_distance=2.0,
        beta_price_budget=1.0,
        gamma_quality_variety=1.5
    )
    
    print("  Creating model...", flush=True)
    model = create_baseline_scenario(config=config)
    
    print("  Running 30 days...", flush=True)
    for day in range(30):
        model.step()
        if (day + 1) % 10 == 0:
            print(f"    Day {day+1}/30", flush=True)
    
    print("  ✓ Simulation complete!", flush=True)
    print("", flush=True)
    
    # Quick metrics
    households = [a for a in model.schedule.agents if isinstance(a, EnhancedHouseholdAgent)]
    total_trips = sum(len(hh.shopping_history) for hh in households)
    
    print(f"Results: {len(households)} households made {total_trips} trips", flush=True)
    print("", flush=True)
    print("="*80, flush=True)
    print("TEST SUCCESSFUL - Full calibration script should work!", flush=True)
    print("="*80, flush=True)
    
except Exception as e:
    print(f"ERROR: {e}", flush=True)
    import traceback
    traceback.print_exc()


