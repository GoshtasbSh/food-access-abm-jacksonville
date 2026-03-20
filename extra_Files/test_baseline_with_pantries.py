"""
TEST: Verify baseline includes mobile pantries with correct schedules
=====================================================================
"""

import sys
sys.path.append('/Users/goshtasbshahriari/Desktop/Code/GeoMesa_Food_Access')

from enhanced_mesa_geo_model import SimulationConfig, EnhancedMobilePantry
from baseline_scenario import create_baseline_scenario

def test_mobile_pantry_schedule():
    """Test that mobile pantries operate on correct monthly schedule"""
    
    print("="*80)
    print("TESTING: Baseline Mobile Pantries")
    print("="*80)
    print()
    
    # Create baseline with just 10 households for quick test
    config = SimulationConfig(
        num_consumers=10,
        simulation_days=60  # 2 months to see multiple distributions
    )
    
    print("📊 Creating baseline scenario...")
    model = create_baseline_scenario(config=config)
    print()
    
    # Find mobile pantries
    pantries = [p for p in model.food_providers if isinstance(p, EnhancedMobilePantry)]
    
    print(f"✅ Found {len(pantries)} mobile pantries in baseline:")
    for pantry in pantries:
        print(f"   • {pantry.name}")
        print(f"     Location: {pantry.current_location_name}")
        print(f"     Schedule: {pantry.monthly_schedule}")
        print(f"     Capacity: {pantry.capacity} HH per distribution")
    print()
    
    # Test schedule over 60 days (2 months)
    print("="*80)
    print("TESTING: Pantry Activity Schedule (60 days = 2 months)")
    print("="*80)
    print()
    
    # Track which days each pantry is active
    pantry_activity = {p.name: [] for p in pantries}
    
    for day in range(60):
        model.current_day = day
        
        # Update each pantry's daily status
        for pantry in pantries:
            pantry.update_daily_status()
            if pantry.active_today:
                weekday = day % 7
                day_of_month = day % 30
                week_of_month = (day_of_month // 7) + 1
                weekday_name = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][weekday]
                pantry_activity[pantry.name].append(f"Day {day} ({weekday_name}, Week {week_of_month})")
    
    # Print results
    for pantry_name, active_days in pantry_activity.items():
        print(f"\n{pantry_name}:")
        print(f"   Active {len(active_days)} times in 60 days (expected ~2 per month)")
        for day_info in active_days:
            print(f"      ✅ {day_info}")
    
    print()
    print("="*80)
    print("EXPECTED SCHEDULES:")
    print("="*80)
    print("• JaxPAL: 3rd Tuesday of each month → Week 3, Tuesday")
    print("• Bethany Ministries: 2nd Tuesday of each month → Week 2, Tuesday")
    print("• Paxon Revival Center: 2nd & 5th Wednesday of each month → Week 2 & 5, Wednesday")
    print()
    
    # Validate
    jaxpal_count = len(pantry_activity.get('JaxPAL Mobile Pantry', []))
    bethany_count = len(pantry_activity.get('Bethany Ministries Mobile Pantry', []))
    paxon_count = len(pantry_activity.get('Paxon Revival Center Mobile Pantry', []))
    
    print("="*80)
    print("VALIDATION:")
    print("="*80)
    success = True
    
    # JaxPAL should operate ~2 times (3rd Tuesday × 2 months)
    if jaxpal_count >= 2 and jaxpal_count <= 3:
        print(f"✅ JaxPAL operated {jaxpal_count} times (expected 2-3)")
    else:
        print(f"⚠️  JaxPAL operated {jaxpal_count} times (expected 2-3)")
        success = False
    
    # Bethany should operate ~2 times (2nd Tuesday × 2 months)
    if bethany_count >= 2 and bethany_count <= 3:
        print(f"✅ Bethany operated {bethany_count} times (expected 2-3)")
    else:
        print(f"⚠️  Bethany operated {bethany_count} times (expected 2-3)")
        success = False
    
    # Paxon should operate ~3-4 times (2nd & 5th Wednesday × 2 months)
    if paxon_count >= 3 and paxon_count <= 5:
        print(f"✅ Paxon operated {paxon_count} times (expected 3-5)")
    else:
        print(f"⚠️  Paxon operated {paxon_count} times (expected 3-5)")
        success = False
    
    print()
    if success:
        print("✅ ALL MOBILE PANTRIES WORKING CORRECTLY!")
    else:
        print("⚠️  Some pantries may have scheduling issues")
    print("="*80)
    
    return success

if __name__ == "__main__":
    success = test_mobile_pantry_schedule()
    sys.exit(0 if success else 1)

