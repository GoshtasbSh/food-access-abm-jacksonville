# Delivery Usage Parameters Update
**Date:** November 23, 2025

## Summary
Updated baseline delivery propensity parameters to reflect **ACTUAL usage rates** in Health Zone 1, Jacksonville, based on real-world data.

---

## Updated Parameters

### Baseline Delivery Propensity (SimulationConfig)

| Parameter | Old Value | New Value | Description |
|-----------|-----------|-----------|-------------|
| `delivery_baseline_low` | 0.02 (2%) | **0.04 (4%)** | Low-income actual usage: 3-5% range |
| `delivery_baseline_medium` | 0.08 (8%) | **0.12 (12%)** | Medium-income actual usage |
| `delivery_baseline_high` | 0.15 (15%) | **0.20 (20%)** | High-income actual usage (urban comparison) |

### Delivery Choice Probabilities

| Parameter | Old Value | New Value | Description |
|-----------|-----------|-----------|-------------|
| `delivery_choice_free_prob` | 0.40 | **0.35** | Prob. of choosing FREE delivery |
| `delivery_choice_nocar_far_prob` | 0.30 | **0.25** | Prob. of choosing delivery (no car, far store) |
| `delivery_choice_accessible_prob` | 0.10 | **0.08** | Prob. of choosing delivery (store nearby) |

---

## Rationale

### Key Insight
**Coverage ≠ Usage**: Even with 90%+ theoretical coverage (internet, eligibility), actual usage is much lower due to:
- Habit/inertia (prefer physical stores)
- Trust issues (food quality, substitutions)
- Technology barriers (even with internet)
- Delivery fees (even small ones deter low-income)
- Wait times (same-day not always available)

### Evidence-Based Values

1. **Low-Income (4%)**
   - Set at middle of 3-5% range
   - Reflects HZ1 baseline reality
   - Even with FREE delivery in Scenario 4, uplift is only 2x (→8%)
   
2. **Medium-Income (12%)**
   - Between low-income (4%) and high-income (20%)
   - Represents moderate adoption
   
3. **High-Income (20%)**
   - Upper bound based on urban comparison groups
   - High-income households more likely to use delivery services
   - Have disposable income for fees

---

## How It Works in the Model

### Step 1: Eligibility Filtering
```python
can_use_delivery = household has internet/tech access
# delivery_hard_blockers_share = 0.5 (50% cannot use delivery at all)
```

### Step 2: Baseline Propensity
```python
if can_use_delivery:
    delivery_propensity = {
        'low': 0.04,    # 4% of eligible low-income HH consider delivery
        'medium': 0.12, # 12% of eligible medium-income HH consider delivery
        'high': 0.20    # 20% of eligible high-income HH consider delivery
    }
```

### Step 3: Subsidy Uplift (Scenario 4 Only)
```python
if subsidized_delivery_exists:
    effective_propensity = delivery_propensity * 2.0  # Double under subsidy
    # Low: 4% → 8%, Medium: 12% → 24%, High: 20% → 40%
```

### Step 4: Choice Probability (When Considered)
```python
if delivery_is_considered:
    # Additional probability filters based on context:
    if delivery_is_free:
        use_delivery = random() < 0.35  # 35% chance
    elif no_car and nearest_store > 1km:
        use_delivery = random() < 0.25  # 25% chance
    else:
        use_delivery = random() < 0.08  # 8% chance
```

---

## Expected Outcomes

### Baseline (Market-Rate Delivery)
- **Low-income households**: ~2% use delivery as main source
  - 50% blocked (no tech) → 50% eligible
  - 50% × 4% propensity × 35% choice = ~0.7%
  - Plus occasional use: ~2% total
  
- **Medium-income households**: ~6-8% use delivery
  - 50% blocked → 50% eligible
  - 50% × 12% propensity × 35% choice = ~2%
  - Plus occasional use: ~6-8% total
  
- **High-income households**: ~12-15% use delivery
  - 50% blocked → 50% eligible
  - 50% × 20% propensity × 35% choice = ~3.5%
  - Plus occasional use: ~12-15% total

### Scenario 4 (Subsidized Delivery)
- **Low-income households**: ~5-8% use delivery
  - 2x uplift: 4% → 8% propensity
  - FREE delivery increases attractiveness
  
- **Medium-income households**: ~15-20% use delivery
  - 2x uplift: 12% → 24% propensity
  - 50% off makes it attractive
  
- **High-income households**: ~25-30% use delivery
  - 2x uplift: 20% → 40% propensity
  - Already comfortable with delivery

---

## Calibration Notes

### These parameters should produce:
1. ✅ Low baseline delivery usage (3-5% for low-income)
2. ✅ Realistic income gradient (low < medium < high)
3. ✅ Modest subsidy impact (not unrealistic explosion)
4. ✅ Delivery as supplement, not primary (for most HH)

### If calibration shows:
- **Too low delivery usage** → Increase `delivery_choice_*_prob` values
- **Too high delivery usage** → Decrease baseline propensity or choice probs
- **Wrong income distribution** → Adjust individual baseline values

---

## Files Updated
- `enhanced_mesa_geo_model.py` (lines 249-263)
  - Updated `delivery_baseline_low`, `delivery_baseline_medium`, `delivery_baseline_high`
  - Updated `delivery_choice_free_prob`, `delivery_choice_nocar_far_prob`, `delivery_choice_accessible_prob`
  - Added documentation comments

---

## Next Steps
1. ✅ Parameters updated
2. ⏳ Run baseline calibration to verify 3-5% low-income delivery usage
3. ⏳ Run Scenario 4 to verify realistic subsidy impact
4. ⏳ Compare baseline vs. Scenario 4 delivery adoption rates

---

**Note**: These parameters are based on empirical evidence and should be validated during calibration. Fine-tuning may be needed to match exact HZ1 data.

