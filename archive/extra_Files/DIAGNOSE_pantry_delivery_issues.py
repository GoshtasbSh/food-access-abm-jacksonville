"""
CRITICAL DIAGNOSTIC: Why are pantries 0% and delivery 44%?
"""

import sys
import random
import numpy as np
from baseline_scenario import create_baseline_scenario
from enhanced_mesa_geo_model import SimulationConfig

def diagnose_issues():
    print("=" * 80)
    print("🔍 DIAGNOSTIC: Investigating Pantry & Delivery Issues")
    print("=" * 80)
    
    # Create baseline model with custom config
    config = SimulationConfig()
    config.num_consumers = 50
    config.num_days = 21
    config.random_seed = 42
    
    model = create_baseline_scenario(config=config)
    
    # === PANTRY DIAGNOSTICS ===
    print("\n📋 PANTRY DIAGNOSTICS:")
    print("-" * 80)
    
    pantries = [p for p in model.food_providers if hasattr(p, 'monthly_schedule')]
    print(f"\n1. Number of mobile pantries in model: {len(pantries)}")
    
    if pantries:
        for i, pantry in enumerate(pantries, 1):
            print(f"\n   Pantry {i}:")
            print(f"   - Name: {getattr(pantry, 'name', 'Unnamed')}")
            print(f"   - Location: {pantry.geometry}")
            print(f"   - Capacity: {pantry.capacity}")
            print(f"   - Monthly schedule: {pantry.monthly_schedule}")
            print(f"   - Weekly schedule (.schedule attribute): {pantry.schedule}")
            print(f"   - Active today (day 0): {pantry.active_today}")
    
    # === SIMULATE 21 DAYS AND TRACK PANTRY ACTIVITY ===
    print("\n2. Simulating 21 days to track pantry activity:")
    print("   Day | Mon Tue Wed Thu Fri Sat Sun | Pantries Active")
    print("   " + "-" * 60)
    
    pantry_active_days = {i: [] for i in range(len(pantries))}
    pantry_visits = {i: 0 for i in range(len(pantries))}
    
    for day in range(21):
        # Run one step
        model.step()
        
        # Check pantry status
        active_pantries = []
        for i, pantry in enumerate(pantries):
            if pantry.active_today:
                active_pantries.append(i)
                pantry_active_days[i].append(day)
        
        # Count households that used pantries today
        for hh in model.consumers:
            if hh.shopping_history and hh.shopping_history[-1]['day'] == day:
                last_event = hh.shopping_history[-1]
                if last_event['provider_type'] == 'mobile_pantry':
                    for i, pantry in enumerate(pantries):
                        if last_event['provider_id'] == pantry.unique_id:
                            pantry_visits[i] += 1
        
        # Print day info
        weekday = day % 7
        weekday_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        day_marker = weekday_names[weekday]
        print(f"   {day:3d} | {' ' * (weekday * 4)}{day_marker:3s}{' ' * ((6-weekday) * 4)} | {active_pantries}")
    
    # Summary
    print("\n3. Pantry Activity Summary (21 days):")
    for i, pantry in enumerate(pantries):
        active_days = pantry_active_days[i]
        visits = pantry_visits[i]
        print(f"   Pantry {i}: Active on {len(active_days)} days ({active_days[:5]}...), {visits} visits")
    
    # === DELIVERY DIAGNOSTICS ===
    print("\n\n📦 DELIVERY DIAGNOSTICS:")
    print("-" * 80)
    
    # Check delivery services
    delivery_services = [p for p in model.food_providers if hasattr(p, 'subsidized')]
    print(f"\n1. Number of delivery services in model: {len(delivery_services)}")
    
    for i, service in enumerate(delivery_services, 1):
        print(f"   Service {i}: Subsidized={getattr(service, 'subsidized', 'N/A')}")
    
    # Check household delivery capability
    print("\n2. Household Delivery Capability:")
    delivery_capable = sum(1 for hh in model.consumers if hh.can_use_delivery)
    delivery_users = sum(1 for hh in model.consumers if getattr(hh, 'is_delivery_user', False))
    
    print(f"   - Total households: {len(model.consumers)}")
    print(f"   - Can use delivery (tech access, no hard blockers): {delivery_capable} ({100*delivery_capable/len(model.consumers):.1f}%)")
    print(f"   - Marked as 'delivery users' (is_delivery_user=True): {delivery_users} ({100*delivery_users/len(model.consumers):.1f}%)")
    
    # By income
    print("\n3. Delivery Users by Income Level:")
    for income_name in ['LOW', 'MEDIUM', 'HIGH']:
        hhs_in_group = [hh for hh in model.consumers if hh.income.name == income_name]
        users_in_group = [hh for hh in hhs_in_group if getattr(hh, 'is_delivery_user', False)]
        if hhs_in_group:
            print(f"   - {income_name:6s}: {len(users_in_group)}/{len(hhs_in_group)} ({100*len(users_in_group)/len(hhs_in_group):.1f}%)")
    
    # Check delivery config parameters
    print("\n4. Delivery Configuration Parameters:")
    print(f"   - delivery_baseline_low: {model.config.delivery_baseline_low:.2%} (target propensity for low income)")
    print(f"   - delivery_baseline_medium: {model.config.delivery_baseline_medium:.2%}")
    print(f"   - delivery_baseline_high: {model.config.delivery_baseline_high:.2%}")
    print(f"   - delivery_hard_blockers_share: {model.config.delivery_hard_blockers_share:.2%}")
    print(f"   - delivery_choice_free_prob: {model.config.delivery_choice_free_prob:.2%} (when delivery is FREE)")
    print(f"   - delivery_choice_nocar_far_prob: {model.config.delivery_choice_nocar_far_prob:.2%} (no car, far store)")
    print(f"   - delivery_choice_accessible_prob: {model.config.delivery_choice_accessible_prob:.2%} (store is accessible)")
    
    # Analyze actual delivery usage
    print("\n5. Actual Delivery Usage from 21-day Simulation:")
    total_shopping_events = sum(len(hh.shopping_history) for hh in model.consumers)
    delivery_events = sum(1 for hh in model.consumers for event in hh.shopping_history if event.get('used_delivery', False))
    
    print(f"   - Total shopping events: {total_shopping_events}")
    print(f"   - Delivery events: {delivery_events} ({100*delivery_events/total_shopping_events:.1f}%)")
    
    # By income
    print("\n6. Delivery Usage by Income Level (from shopping events):")
    for income_name in ['LOW', 'MEDIUM', 'HIGH']:
        hhs_in_group = [hh for hh in model.consumers if hh.income.name == income_name]
        events_in_group = sum(len(hh.shopping_history) for hh in hhs_in_group)
        delivery_in_group = sum(1 for hh in hhs_in_group for event in hh.shopping_history if event.get('used_delivery', False))
        if events_in_group > 0:
            print(f"   - {income_name:6s}: {delivery_in_group}/{events_in_group} ({100*delivery_in_group/events_in_group:.1f}%)")
    
    # === THE PROBLEM ===
    print("\n\n🚨 THE PROBLEM:")
    print("-" * 80)
    print("""
DELIVERY ISSUE:
   Even though is_delivery_user is set ONCE at initialization (good!),
   there are ADDITIONAL stochastic rolls EVERY shopping trip:
   
   Line 897: if self.is_delivery_user:  ← First gate (e.g., 8% of low income HH)
   Line 912:     use_delivery = (random.random() < delivery_choice_free_prob)  ← SECOND gate!
   
   So if delivery_choice_free_prob = 0.8, then:
   - 8% of HH are delivery users
   - But of those, 80% of their shopping trips use delivery
   - This gives: 8% × multiple trips × 80% each trip = MUCH higher than 8%
   
   FIX: Either:
   1. Make is_delivery_user the ONLY decision (remove secondary stochastic checks)
   2. OR set delivery_choice_* parameters much lower (e.g., 0.1-0.2)

PANTRY ISSUE:
   Need to verify if pantries are being included in available_providers list.
   If they're active but not being chosen, the utility boost may be insufficient.
    """)
    
    print("\n" + "=" * 80)
    print("Diagnostic complete. See analysis above.")
    print("=" * 80)

if __name__ == '__main__':
    diagnose_issues()

