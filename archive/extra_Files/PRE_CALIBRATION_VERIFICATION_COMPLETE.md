# ✅ PRE-CALIBRATION VERIFICATION COMPLETE

## Date: November 24, 2025

## All Systems Verified and Ready for Calibration

### ✅ 1. Delivery Parameters (CORRECTED)
```python
delivery_baseline_low: 0.08      # 8% propensity → ~4% actual (after 50% hard blockers)
delivery_baseline_medium: 0.20   # 20% propensity → ~10% actual
delivery_baseline_high: 0.35     # 35% propensity → ~17-20% actual
delivery_hard_blockers_share: 0.50
```

**Expected Calibration Targets**:
- Low income: 3-5% delivery usage ✅
- Medium income: 8-12% delivery usage ✅
- High income: 15-20% delivery usage ✅

---

### ✅ 2. Mobile Pantry Schedules (REAL DATA - MONTHLY)
```python
# JaxPAL: 3rd Tuesday of each month
monthly_schedule=(3, 1)

# Bethany Ministries: 2nd Tuesday of each month
monthly_schedule=(2, 1)

# Paxon Revival Center: 2nd and 5th Wednesday of each month
monthly_schedule=[(2, 2), (5, 2)]
```

**Source**: Feeding Northeast Florida official schedule
**Expected Usage**: 3-4% (limited by monthly availability - this is realistic)

---

### ✅ 3. Pantry Utility Boosts (IMPLEMENTED)
```python
if store_type_str in ['mobile_pantry', 'pantry', 'food_pantry']:
    pantry_boost = 10.0  # Base boost
    if self.income == IncomeLevel.LOW:
        pantry_boost += 5.0  # +15.0 total for low income
    if self.snap_eligible:
        pantry_boost += 3.0  # +18.0 total for SNAP-eligible
    utility += pantry_boost
```

**Propensity Parameters**:
- SNAP-eligible: 75%
- Non-eligible: 15%

**Effect**: When pantries are active, eligible households will strongly prefer them despite distance

---

### ✅ 4. All Scenarios Include Baseline Providers
- **Scenario 1** (New Grocery): ✅ Calls `add_baseline_mobile_pantries()` and `add_baseline_delivery_service()`
- **Scenario 2** (Food Hub): ✅ Calls `add_baseline_mobile_pantries()` and `add_baseline_delivery_service()`
- **Scenario 3** (Mobile Pantries): ✅ Calls `add_baseline_mobile_pantries()` and `add_baseline_delivery_service()`
- **Scenario 4** (Subsidized Delivery): ✅ Calls `add_baseline_mobile_pantries()` + own subsidized delivery

---

### ✅ 5. Basket Sizes Fixed (CRITICAL BUG)
**Problem Found**: Basket sizes were only based on household size, causing massive overspending for low-income households.

**Solution Applied**:
```python
# Income-based multipliers
basket_multiplier_low_income: 0.50    # 50% of base
basket_multiplier_medium_income: 0.85  # 85% of base  
basket_multiplier_high_income: 1.30    # 130% of base

# Applied in _get_basket_size_mean()
return base_basket * multiplier
```

**New Expected Basket Sizes (3-person household)**:
- Low income: $204 × 0.50 = **$102/trip** (vs. $101/week budget) ✅
- Medium income: $204 × 0.85 = **$173/trip** (vs. $173/week budget) ✅
- High income: $204 × 1.30 = **$265/trip** (vs. $327/week budget) ✅

---

## Calibration Targets (REALISTIC)

### Annual Spending by Income Level
- Low income (<$25K): $5,254/year ($101/week) → Target within ±15%
- Medium income ($25K-$99K): $9,004/year ($173/week) → Target within ±15%
- High income (≥$100K): $17,004/year ($327/week) → Target within ±15%

### Provider Usage
- Grocery stores (primary): ~85-90%
- Corner stores (primary): <10% (with Idea #1 full-shop/top-up logic)
- Mobile pantries: 3-4% (realistic given monthly availability)
- Delivery: 3-20% (varies by income)

### Travel Distance
- With car: ≤5.5 km (~3.4 miles)
- Without car: ≤3.5 km (~2.2 miles)

---

## Calibration Strategy

### Phase 1: Focused Grid Search (90 days, 50 HH, 1 seed)
- **Parameters to tune**:
  - `alpha_distance`: [0.8, 1.0, 1.2]
  - `beta_price_budget`: [0.6, 0.8, 1.0]
  - `gamma_quality_variety`: [0.4, 0.6, 0.8]
  - `go_shop_threshold_low`: [2.0, 2.5, 3.0]
  - `go_shop_threshold_medium`: [5.5, 6.5, 7.5]
  - `go_shop_threshold_high`: [12.0, 14.0, 16.0]

- **Total configs**: 3×3×3×3×3×3 = 729 configs
- **Expected time**: ~4-6 hours
- **Output**: Top 10 parameter sets by calibration error

### Phase 2: Validation (365 days, 200 HH, 5 seeds)
- Run top 5 parameter sets from Phase 1
- Full simulation settings for dissertation-quality results
- **Expected time**: ~2-3 hours
- **Output**: Final calibrated parameters with mean ± std

---

## Files Ready for Calibration

1. ✅ `enhanced_mesa_geo_model.py` - All fixes applied
2. ✅ `baseline_scenario.py` - Real monthly pantry schedules
3. ✅ `enhanced_scenario_1.py` - Baseline providers included
4. ✅ `enhanced_scenario_2.py` - Baseline providers included
5. ✅ `enhanced_scenario_3.py` - Baseline providers included
6. ✅ `enhanced_scenario_4.py` - Baseline providers included
7. ✅ `calibration_framework.py` - Grid search framework ready

---

## Ready to Proceed ✅

All critical issues have been identified and fixed:
- ✅ Delivery parameters corrected
- ✅ Pantry schedules reverted to real monthly data
- ✅ Utility boosts implemented
- ✅ Basket size income multipliers added
- ✅ All scenarios verified

**The model is now ready for calibration.**

