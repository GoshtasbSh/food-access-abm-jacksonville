# Delivery Usage Parameters - FINAL VALUES
**Date:** November 23, 2025  
**Target:** 3-5% of low-income households use delivery in baseline

---

## ✅ FINAL PARAMETER VALUES

### Delivery Propensity (SimulationConfig)

```python
delivery_baseline_low: float = 0.08     # 8% of eligible low-income HH
delivery_baseline_medium: float = 0.20  # 20% of eligible medium-income HH  
delivery_baseline_high: float = 0.35    # 35% of eligible high-income HH
```

### Key Supporting Parameters

```python
delivery_hard_blockers_share: float = 0.5  # 50% cannot use delivery (no internet/tech)
delivery_subsidy_uplift: float = 2.0       # 2x multiplier under subsidy (Scenario 4)
```

---

## 📊 EXPECTED OUTCOMES

### Baseline (Market-Rate Delivery)

| Income Level | Eligible | Propensity | Expected Usage* |
|--------------|----------|------------|-----------------|
| **Low**      | 50%      | 8%         | **~4%** (target: 3-5%) |
| **Medium**   | 50%      | 20%        | **~10%** |
| **High**     | 50%      | 35%        | **~17%** (target: up to 20%) |

\* Expected usage = eligibility_rate × propensity

### Scenario 4 (Subsidized Delivery)

With 2x subsidy uplift:

| Income Level | Propensity (subsidized) | Expected Usage |
|--------------|-------------------------|----------------|
| **Low**      | 16% (8% × 2)            | **~8%** |
| **Medium**   | 40% (20% × 2)           | **~20%** |
| **High**     | 70% (35% × 2, capped)   | **~35%** |

---

## 🎯 RATIONALE

### Why These Values?

**User Requirement:**
> "Set baseline delivery use among low-income households in HZ1 at 3–5%. This reflects actual, not merely possible, usage—even though coverage may be 90%+."

### Calculation Logic:

1. **Target**: 3-5% of ALL low-income households use delivery
2. **Hard Blockers**: 50% of households cannot use delivery (no internet, technology barriers)
3. **Eligible Population**: Only 50% CAN use delivery
4. **Required Propensity**: To achieve 3-5% overall, propensity among eligible must be:
   - 3-5% ÷ 50% = **6-10%**
   - Set to **8%** (middle of range)

### Income Gradient:

Research shows delivery adoption increases with income:
- **Low**: 8% → 4% overall (3-5% target)
- **Medium**: 20% → 10% overall (~2.5x low-income)
- **High**: 35% → 17% overall (~4x low-income, approaching 20% upper bound)

---

## 🔄 MODEL MECHANICS

### Step-by-Step Process:

1. **Eligibility Check** (`can_use_delivery`)
   ```python
   # 50% of households are hard blockers (no internet/tech)
   can_use_delivery = random() > 0.5
   ```

2. **Propensity Assignment** (`delivery_propensity`)
   ```python
   if can_use_delivery:
       if income == LOW:
           propensity = 0.08  # 8%
   ```

3. **Daily Decision** (`_should_use_delivery_today()`)
   ```python
   # Stochastic choice each day
   if subsidized_delivery_exists:
       effective_propensity = propensity * 2.0  # Subsidy uplift
   
   use_delivery_today = random() < effective_propensity
   ```

4. **Provider Choice** (if delivery considered)
   - Additional context-dependent probabilities apply
   - Free delivery: 35% choice rate
   - No car + far store: 25% choice rate
   - Store accessible: 8% choice rate

---

## 📈 COMPARISON TO REALITY

### HZ1 Jacksonville Baseline Data:

| Metric | Real World | Model (Baseline) | Model (Scenario 4) |
|--------|------------|------------------|---------------------|
| **Low-income delivery usage** | 3-5% | ~4% ✅ | ~8% (2x uplift) |
| **Coverage (eligible)** | 90%+ | 50% hard blockers | 50% hard blockers |
| **Subsidy impact** | Unknown | Modest (2x) | 2x baseline |

### Key Insight:

**Coverage ≠ Usage**  
Even with 90%+ theoretical access, actual usage is much lower due to:
- Habit/inertia (prefer physical stores)
- Trust issues (food quality, substitutions)
- Technology barriers (even with internet)
- Delivery fees (even small ones deter low-income)
- Wait times (same-day not always available)

---

## ✅ VALIDATION CHECKLIST

These parameters should produce:
- ✅ **3-5% delivery usage** among low-income HH (baseline)
- ✅ **Realistic income gradient** (low < medium < high)
- ✅ **Modest subsidy impact** (2x, not unrealistic explosion)
- ✅ **Delivery as supplement**, not primary for most HH
- ✅ **~50% hard blockers** (no tech/internet access)

---

## 🔧 CALIBRATION NOTES

### If Observed Usage is:

**Too Low (<3%)**:
- Increase `delivery_baseline_low` (try 0.10-0.12)
- OR decrease `delivery_hard_blockers_share` (try 0.4)
- OR increase `delivery_choice_*_prob` values

**Too High (>5%)**:
- Decrease `delivery_baseline_low` (try 0.06)
- OR increase `delivery_hard_blockers_share` (try 0.6)
- OR decrease `delivery_choice_*_prob` values

**Wrong Income Distribution**:
- Adjust individual `delivery_baseline_*` values independently
- Maintain income gradient: low < medium < high

---

## 📝 FILES UPDATED

1. `enhanced_mesa_geo_model.py` (lines 249-256)
   - `delivery_baseline_low = 0.08`
   - `delivery_baseline_medium = 0.20`
   - `delivery_baseline_high = 0.35`
   - Updated documentation comments

2. `DELIVERY_USAGE_PARAMETERS_FINAL.md` (this file)
   - Complete documentation of parameters and rationale

---

## 🚀 NEXT STEPS

1. ✅ Parameters updated in model
2. ⏳ Run baseline calibration to validate 3-5% low-income delivery usage
3. ⏳ Run Scenario 4 to validate subsidy impact (2x uplift)
4. ⏳ Compare outcomes against HZ1 empirical data
5. ⏳ Fine-tune if needed based on full simulation results

---

**Note**: These values are initial estimates based on target usage rates. Full calibration with 200 HH × 365 days × multiple seeds will provide empirical validation and may require minor adjustments.

