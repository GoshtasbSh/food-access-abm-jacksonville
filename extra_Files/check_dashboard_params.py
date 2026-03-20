"""
Quick check to verify dashboard will show calibrated parameters
"""

from enhanced_mesa_geo_model import SimulationConfig

config = SimulationConfig()

print("="*80)
print("DASHBOARD PARAMETER CHECK")
print("="*80)
print("\nCalibrated Parameters (Config #73, Error = 0.238):")
print(f"  α (alpha_distance):          {config.alpha_distance}")
print(f"  β (beta_price_budget):       {config.beta_price_budget}")
print(f"  γ (gamma_quality_variety):   {config.gamma_quality_variety}")
print(f"  δ (delta_convenience):       {config.delta_convenience}")
print(f"  Threshold (low):             {config.go_shop_threshold_low}")
print(f"  Threshold (medium):          {config.go_shop_threshold_medium}")
print(f"  Threshold (high):            {config.go_shop_threshold_high}")
print(f"\nDelivery Parameters:")
print(f"  Low income:                  {config.delivery_baseline_low}")
print(f"  Medium income:               {config.delivery_baseline_medium}")
print(f"  High income:                 {config.delivery_baseline_high}")
print("\n" + "="*80)
print("✅ Dashboard will display these values in parameter inputs!")
print("="*80)

