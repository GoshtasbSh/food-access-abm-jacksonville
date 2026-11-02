# VERIFY BASKET SIZE LOGIC

## Current Situation

### Literature Values (FIXED):
- **Weekly budgets**: $101 (low), $173 (medium), $327 (high)
- **Base basket sizes**: $131, $143, $204, $262 (by HH size)
- **Annual spending targets**: $5,270, $8,989, $16,996

### Derived Multipliers (CALCULATED):
- Low: 0.25 × $204 = **$51 per trip**
- Medium: 0.85 × $204 = **$173 per trip**
- High: 1.78 × $204 = **$363 per trip**

---

## The Problem

### Expected vs Actual:

**Low Income:**
- Expected: $51 × 2 trips/week = $102/week
- **Actual: $83/week** (18% too low)
- **Why?** Not shopping enough OR budget constraints too restrictive

**High Income:**
- Expected: $363 × 0.9 trips/week = $327/week
- **Actual: $465/week** (42% too high)
- **Why?** Shopping MORE than expected (1.28 trips/week instead of 0.9)

---

## Root Cause Analysis

### Issue #1: Budget Constraints May Be Too Strict for Low-Income
```python
# Current logic:
needed = max(0, self.weekly_budget - self.spent_this_week + self.unmet_need)
```
If budget runs out mid-week, household stops shopping even if they need food!

**Question**: Should low-income households be able to slightly overspend their budget occasionally?

### Issue #2: High-Income Shopping Too Frequently
```python
# Current settings:
freq_high_income = (10, 30)  # Every 10-30 days
go_shop_threshold_high = 14.0  # Calibration sets this
```

If threshold is too low, high-income shops more often than intended.

**Current calibration**: threshold_low = 3.0, but what about threshold_medium and threshold_high?

---

## Questions to Resolve

### Q1: Are Budget Constraints Realistic?
Should households:
- **A)** Strictly stay within weekly budget (current)
- **B)** Be able to overspend slightly if needed
- **C)** Have budget accumulate over weeks if underspent

### Q2: What Should We Actually Calibrate?
Options:
1. **Alpha, Beta, Gamma, Delta** (utility weights)
2. **Go-shop thresholds** (all three: low, medium, high)
3. **Basket multipliers** (BUT these should match budgets!)
4. **Shopping frequency ranges** (BUT these come from surveys!)

### Q3: Are Basket Multipliers "Literature Values"?
- **NO**: They are derived to match weekly budgets
- **YES**: But they must be consistent with budgets

**Current approach**: Multipliers are FIXED to match budgets, then we calibrate behavior parameters to achieve targets

---

## Recommended Approach for Quick Test

**Test whether we can hit targets by calibrating:**
1. ✅ **Alpha** (distance weight)
2. ✅ **Gamma** (quality weight)  
3. ✅ **Go-shop threshold LOW** (when low-income shops)
4. ⚠️ **ALSO test**: Go-shop threshold MEDIUM and HIGH

**Keep FIXED:**
- Basket multipliers (0.25, 0.85, 1.78)
- Weekly budgets ($101, $173, $327)
- Base basket sizes ($131, $143, $204, $262)
- Shopping frequency ranges (3-5 days, 6-8 days, 10-30 days)

---

## If Quick Test Shows High Error...

Then we need to consider:
1. **Budget constraints are too restrictive** → Allow slight overspending
2. **Basket multipliers need recalculation** → But must still align with budgets
3. **Shopping frequency ranges are wrong** → But they come from surveys!
4. **The model structure itself has issues** → Major rethink needed

---

## Expected Result from Quick Test

If calibration works well (error < 2.5):
- ✅ Proceed with FULL grid search (more configs, longer run)

If calibration is moderate (error 2.5-3.5):
- ⚠️ Review specific failing metrics
- Possibly adjust parameter ranges
- Run another quick test

If calibration fails (error > 3.5):
- ❌ Need to rethink fundamental approach
- Check if literature values are compatible
- Consider relaxing budget constraints

