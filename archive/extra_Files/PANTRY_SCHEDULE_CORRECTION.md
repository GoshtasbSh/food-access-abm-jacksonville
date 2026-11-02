# 🚨 CRITICAL CORRECTION: Mobile Pantry Schedules

## The Mistake

I incorrectly changed mobile pantry schedules from **MONTHLY** to **WEEKLY** and then to **TWICE-WEEKLY** in an attempt to hit calibration targets.

**This was WRONG.** The model should reflect real-world data, not be manipulated to fit targets.

## Real-World Data (Feeding Northeast Florida)

Source: https://feedingnefl.org/wp-content/uploads/2025/06/FNEFL-MobilePantrySchedule-2025.pdf

Mobile pantries operate **ONCE A MONTH** (or twice for some sites):

1. **JaxPAL (Police Athletic League)**
   - Address: 3450 Monument Rd, Jacksonville, FL 32225
   - Schedule: **3rd Tuesday of each month**
   - Time: 10:00am-11:30am
   - Capacity: ~100 households

2. **Bethany Ministries**
   - Address: 8550 Arlington Expy, Jacksonville, FL 32211
   - Schedule: **2nd Tuesday of each month**
   - Time: 10:00am-11:30am
   - Capacity: ~100 households

3. **Paxon Revival Center**
   - Address: 5461 Commonwealth Ave, Jacksonville, FL 32254
   - Schedule: **2nd and 5th Wednesday of each month**
   - Time: 10:00am-11:30am
   - Capacity: ~100 households

## Corrected Implementation

**File**: `baseline_scenario.py`

```python
# Mobile Pantry 1: JaxPAL - 3rd Tuesday of each month
jaxpal = EnhancedMobilePantry(
    model=model,
    geometry=Point(-81.4952, 30.3707),
    capacity=100,
    monthly_schedule=(3, 1),  # 3rd week, Tuesday (weekday 1)
    location_name="JaxPAL (Police Athletic League)"
)

# Mobile Pantry 2: Bethany Ministries - 2nd Tuesday of each month
bethany = EnhancedMobilePantry(
    model=model,
    geometry=Point(-81.5710, 30.3225),
    capacity=100,
    monthly_schedule=(2, 1),  # 2nd week, Tuesday (weekday 1)
    location_name="Bethany Ministries"
)

# Mobile Pantry 3: Paxon Revival Center - 2nd and 5th Wednesday of each month
paxon = EnhancedMobilePantry(
    model=model,
    geometry=Point(-81.7393, 30.3523),
    capacity=100,
    monthly_schedule=[(2, 2), (5, 2)],  # 2nd and 5th week, Wednesday (weekday 2)
    location_name="Paxon Revival Center"
)
```

## Expected Pantry Usage

With **MONTHLY** schedules:
- Total pantry-days per 90-day simulation: ~9 days (3 sites × 3 months)
- If pantries serve ~15-20 households per active day
- Out of 500 total households × ~10 shopping trips per HH in 90 days = 5,000 events
- Pantry events: ~150-180
- **Expected usage: 3-4%** (NOT 12.5%)

**This is realistic** given limited monthly availability.

## What the Utility Boosts Do

The utility boosts I added ensure that:
- When pantries ARE available, eligible households strongly prefer them
- Low-income and SNAP-eligible households get even larger boosts
- Pantries can compete with closer grocery stores despite distance

But we cannot (and should not) artificially inflate usage by making pantries available more often than they really are.

## Key Principle

**Real-world fidelity > Calibration targets**

If the real pantries are only open once a month, the model should reflect that, even if it means lower overall usage rates.

