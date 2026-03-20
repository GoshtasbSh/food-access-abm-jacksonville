#!/usr/bin/env python
"""
Temporary 30-day diagnostic test: 50 HH, 30 days, trip counts by type.
Run: conda activate abm310 && python temp_30day_diagnostic_test.py
"""
import sys
import random
import numpy as np

sys.path.insert(0, '/Users/goshtasbshahriari/Desktop/Code/GeoMesa_Food_Access')

from enhanced_mesa_geo_model import SimulationConfig
from baseline_scenario import create_baseline_scenario

random.seed(42)
np.random.seed(42)

config = SimulationConfig(
    num_consumers=50,
    simulation_days=30,
)
model = create_baseline_scenario(config)

for _ in range(30):
    model.step()

# Count trips by type
trips = {'grocery': 0, 'corner': 0, 'pantry': 0, 'delivery': 0, 'other': 0}
total = 0
for hh in model.consumers:
    for trip in hh.shopping_history:
        pt = trip.get('provider_type', 'other')
        used_delivery = trip.get('used_delivery', False)
        if used_delivery:
            trips['delivery'] += 1
        elif 'grocery' in pt or 'supermarket' in pt or 'supercenter' in pt:
            trips['grocery'] += 1
        elif 'corner' in pt or 'convenience' in pt:
            trips['corner'] += 1
        elif 'pantry' in pt or 'mobile' in pt:
            trips['pantry'] += 1
        elif 'delivery' in pt:
            trips['delivery'] += 1
        else:
            trips['other'] += 1
        total += 1

print('=== 30-DAY DIAGNOSTIC TEST ===')
if total > 0:
    for k, v in trips.items():
        print(f'  {k:10s}: {v:4d} ({v/total*100:.1f}%)')
    print(f'  TOTAL     : {total}')
else:
    print('  No trips recorded.')
print()

# Spending check
spend_low = [
    sum(t.get('basket_cost', 0) for t in hh.shopping_history)
    for hh in model.consumers
    if hasattr(hh, 'income') and hh.income.value == 'low'
]
if spend_low:
    print(f'  avg_spend_low (30d): ${np.mean(spend_low):.0f}  (target ~$435)')
else:
    print('  avg_spend_low (30d): N/A (no low-income shoppers)')
print(f'  pantry share target: 4-8%')
if total > 0:
    print(f'  pantry share actual: {trips["pantry"]/total*100:.1f}%')
else:
    print(f'  pantry share actual: N/A')
print()

# Distance check
car_dists = []
nocar_dists = []
for hh in model.consumers:
    for trip in hh.shopping_history:
        td = trip.get('travel_distance', 0)
        if td > 0:
            if hh.vehicle_available:
                car_dists.append(td)
            else:
                nocar_dists.append(td)

print(f'  avg_dist_car   : {np.mean(car_dists):.3f} km (n={len(car_dists)})' if car_dists else '  avg_dist_car: no trips')
print(f'  avg_dist_nocar : {np.mean(nocar_dists):.3f} km (n={len(nocar_dists)})' if nocar_dists else '  avg_dist_nocar: no trips')
print()
