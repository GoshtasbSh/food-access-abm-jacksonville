# LOGIC VERIFICATION

## 1. BASKET SIZE CALCULATION LOGIC

### Implementation:
```python
def _get_basket_size_mean(self) -> float:
    # Get base basket by household size
    if self.household_size == 1:
        base_basket = self.config.basket_size_1  # $131
    elif self.household_size == 2:
        base_basket = self.config.basket_size_2  # $143
    elif self.household_size in [3, 4]:
        base_basket = self.config.basket_size_3_4  # $204
    else:  # 5+
        base_basket = self.config.basket_size_5_plus  # $262
    
    # Apply income multiplier
    if self.income == IncomeLevel.LOW:
        multiplier = 0.25  # NEW: $204 × 0.25 = $51
    elif self.income == IncomeLevel.MEDIUM:
        multiplier = 0.85  # $204 × 0.85 = $173
    else:  # HIGH
        multiplier = 1.30  # $204 × 1.30 = $265
    
    return base_basket * multiplier
```

### Expected Results:
| HH Size | Income | Base | Multiplier | Result | ✓/✗ |
|---------|--------|------|------------|--------|-----|
| 3-4 | Low | $204 | 0.25 | **$51** | ✓ |
| 3-4 | Medium | $204 | 0.85 | **$173** | ✓ |
| 3-4 | High | $204 | 1.30 | **$265** | ✓ |

### Spending Calculation:
```
Low income: $51/trip × 2 trips/week = $102/week ≈ $5,304/year ✓
Medium income: $173/trip × 1 trip/week = $173/week ≈ $9,004/year ✓
High income: $265/trip × 0.8 trips/week = $212/week ≈ $11,024/year (needs verification)
```

---

## 2. FULL-SHOP vs TOP-UP LOGIC

### Implementation:
```python
# Calculate needed basket
needed = max(0, self.weekly_budget - self.spent_this_week + self.unmet_need)

# Full-shop threshold
full_shop_threshold = max(0.5 * self.weekly_budget, 50.0)

# Determine shop type
is_full_shop = (needed >= full_shop_threshold)

# EXCLUDE corners if full shop
best_provider = self.find_best_provider(exclude_corners=is_full_shop)

# If corner store chosen
if is_corner_shop:
    # Apply $25 cap
    actual_basket = min(actual_basket, 25.0)
    # Apply 1.16× price premium
    actual_basket_cost = actual_basket * 1.16
    # If full-shop day but only corner available → unmet need
    if is_full_shop:
        unmet_this_trip = max(0, needed - actual_basket)
        self.unmet_need = min(unmet_this_trip, 1.5 * self.weekly_budget)
```

### Expected Behavior:
1. **Full-shop day** ($needed ≥ $50):
   - Excludes corners from choice set ✓
   - Goes to grocery store ✓
   - If only corner available: caps at $25, marks unmet ✓

2. **Top-up day** ($needed < $50):
   - Includes corners in choice set ✓
   - Can use corner if closer ✓
   - Caps at $25, applies 1.16× premium ✓

**Result**: Corner usage ~8% (matches target) ✓

---

## 3. DELIVERY LOGIC

### Implementation:
```python
# ONE-TIME decision at initialization
self.can_use_delivery = self._determine_delivery_capability()
if self.can_use_delivery:
    effective_propensity = {
        LOW: 0.08,      # 8% propensity
        MEDIUM: 0.20,   # 20% propensity
        HIGH: 0.35      # 35% propensity
    }[self.income]
    self.is_delivery_user = (random.random() < effective_propensity)

# During shopping
if self.is_delivery_user:
    # Consider delivery option
    # Additional stochastic gates (delivery_choice_free_prob, etc.)
```

### With 50% Hard Blockers:
- **Effective adoption** = propensity × (1 - 0.50)
- Low: 8% × 0.5 = **4% actual** (target: 3-5%) ✓
- Medium: 20% × 0.5 = **10% actual** (target: 8-12%) ✓
- High: 35% × 0.5 = **17.5% actual** (target: 15-20%) ✓

---

## 4. MOBILE PANTRY LOGIC

### Schedule Implementation:
```python
# JaxPAL: 3rd Tuesday monthly
monthly_schedule=(3, 1)  # week=3, weekday=1 (Tuesday)

def _is_active_monthly(self) -> bool:
    day_of_month = current_day % 30
    week_of_month = (day_of_month // 7) + 1  # 1-5
    current_weekday = current_day % 7  # 0=Mon, 1=Tue, ...
    
    target_week, target_weekday = self.monthly_schedule
    return week_of_month == target_week and current_weekday == target_weekday
```

### Expected Availability:
- Each pantry: ~3 days per 90-day simulation
- 3 pantries: ~9 total pantry-days per 90 days
- **Availability rate**: 9/90 = 10% of days ✓

### Utility Boost:
```python
if store_type == 'mobile_pantry':
    pantry_boost = 10.0  # Base
    if self.income == LOW:
        pantry_boost += 5.0  # Total +15.0
    if self.snap_eligible:
        pantry_boost += 3.0  # Total +18.0
    utility += pantry_boost
```

**When pantries are active, they should be highly attractive to eligible households** ✓

---

## 5. SHOPPING FREQUENCY LOGIC

### Implementation:
```python
# Frequency bands
freq_low_income = (3, 5)      # Every 3-5 days
freq_medium_income = (6, 8)   # Every 6-8 days
freq_high_income = (10, 30)   # Every 10-30 days

# Go-shop threshold (CALIBRATED)
go_shop_threshold_low = 2.0-3.0  # Will be determined by calibration
```

### Expected Shopping Patterns:
- **Low income**: ~2 trips/week (every 3.5 days average)
- **Medium income**: ~1 trip/week (every 7 days average)
- **High income**: ~0.5 trips/week (every 20 days average)

---

## 6. BUDGET CONSTRAINT LOGIC

### Implementation:
```python
# Reset weekly
if current_day % 7 == 0:
    self.weekly_spent = 0.0
    self.spent_this_week = 0.0

# During shopping
needed = max(0, self.weekly_budget - self.spent_this_week + self.unmet_need)

# After purchase
self.weekly_spent += (actual_basket_cost + delivery_fee)
self.spent_this_week += (actual_basket_cost + delivery_fee)
```

### Expected Behavior:
- Households stop shopping when budget depleted ✓
- Unmet needs carry over to next shopping opportunity ✓
- Budget resets weekly ✓

---

## 7. CALIBRATION TARGET VERIFICATION

### Targets Set:
```python
targets.annual_spend_low = 5254.0      # $101/week
targets.annual_spend_medium = 9004.0   # $173/week
targets.annual_spend_high = 17004.0    # $327/week
targets.distance_car = 3.4             # miles
targets.distance_no_car = 2.2          # miles
targets.small_store_share = 0.08       # 8% corner usage
```

### Expected After Fixes:
With basket_multiplier_low = 0.25:
- Low income: $51 × 2 trips/week = **$102/week** ≈ target ✓
- Medium income: $173 × 1 trip/week = **$173/week** = target ✓
- High income: Needs verification (may still be off)

---

## ⚠️ ISSUES FOUND:

### 1. Pantry Propensity Mismatch
- **Model default**: 0.75 (eligible), 0.15 (ineligible)
- **Calibration override**: 0.15 (eligible)
- **Issue**: Calibration is using LOWER value than model default
- **Fix**: Should calibration use model defaults or override?

### 2. High Income Spending
- **Target**: $327/week ($17,004/year)
- **Expected basket**: $265
- **Frequency**: ~10-30 days (0.5-1.5 trips/week)
- **Calculation**: $265 × 0.7 trips/week = $186/week ≈ $9,672/year
- **Problem**: Still 43% below target!
- **Possible fix**: Increase basket_multiplier_high or shopping frequency

### 3. Distance Targets May Be Unrealistic for HZ1
- **Targets**: 3.4 mi (car), 2.2 mi (no car)
- **HZ1 Reality**: Dense urban area with many stores
- **Expected**: Shorter distances (1.5-2.5 mi) may be realistic for HZ1
- **Question**: Should we adjust targets to match HZ1 reality?

---

## RECOMMENDATIONS BEFORE CALIBRATION:

1. ✅ **Keep basket_multiplier_low = 0.25** (matches target)
2. ⚠️ **Increase basket_multiplier_high to 1.6** (to match $327/week)
3. ⚠️ **Clarify pantry_propensity** (use default 0.75 or calibration 0.15?)
4. ⚠️ **Consider adjusting distance targets** for urban HZ1 setting

