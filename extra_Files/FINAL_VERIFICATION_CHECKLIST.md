# FINAL VERIFICATION CHECKLIST

## Values You Provided vs. Current Implementation

### 1. MOBILE PANTRIES (Real FNEFL Data)
**Your Requirement**: Use real monthly schedules from Feeding Northeast Florida

| Site | Your Data | Current Model | ✓/✗ |
|------|-----------|---------------|-----|
| JaxPAL | 3rd Tuesday monthly | monthly_schedule=(3, 1) | ✓ |
| Bethany Ministries | 2nd Tuesday monthly | monthly_schedule=(2, 1) | ✓ |
| Paxon Revival Center | 2nd & 5th Wed monthly | monthly_schedule=[(2,2), (5,2)] | ✓ |

### 2. DELIVERY BASELINE USAGE
**Your Requirement**: "Set baseline delivery use among low-income households in HZ1 at 3–5%. For higher-income or tech-enabled households, up to ~20%."

| Income Level | Your Target | Current Propensity | After 50% Blockers | ✓/✗ |
|--------------|-------------|-------------------|-------------------|-----|
| Low | 3-5% actual | 8% propensity | 4% actual | ✓ |
| Medium | 8-12% actual | 20% propensity | 10% actual | ✓ |
| High | 15-20% actual | 35% propensity | 17.5% actual | ✓ |

### 3. IDEA #1: FULL-SHOP vs TOP-UP
**Your Requirement**: Separate full shops from top-ups with specific values

| Parameter | Your Value | Current Model | ✓/✗ |
|-----------|------------|---------------|-----|
| Full-shop threshold | max(0.5 × weekly_budget, $50) | Implemented | ✓ |
| Corner basket cap | $25 | Implemented | ✓ |
| Corner price index | 1.16 | Implemented | ✓ |
| Corner quality penalty | Use absolute level 0.30 | NOT SET - needs check | ? |

### 4. ANNUAL SPENDING TARGETS (USDA)
**Your Requirement**: Use USDA ERS data

| Income Level | Your Target | Current Target | ✓/✗ |
|--------------|-------------|----------------|-----|
| Low (<$25K) | $5,254/year ($101/week) | $5,254 | ✓ |
| Medium ($25K-$99K) | $9,004/year ($173/week) | $9,004 | ✓ |
| High (≥$100K) | $17,004/year ($327/week) | $17,004 | ✓ |

### 5. BASKET SIZE ADJUSTMENTS
**Your Concern**: "basket not always above 100 for low income"

| Parameter | Old Value | New Value | Expected Result | ✓/✗ |
|-----------|-----------|-----------|-----------------|-----|
| basket_multiplier_low | 0.50 ($102) | 0.25 ($51) | ~$102/week total | ✓ |
| basket_multiplier_medium | 0.85 ($173) | 0.85 ($173) | ~$173/week total | ✓ |
| basket_multiplier_high | 1.30 ($265) | 1.30 ($265) | ~$327/week total | ✓ |

### 6. WEEKLY BUDGETS
**From USDA Targets**

| Income | Weekly Budget | Current Model | ✓/✗ |
|--------|---------------|---------------|-----|
| Low | $101/week | $101.0 | ✓ |
| Medium | $173/week | $173.0 | ✓ |
| High | $327/week | $327.0 | ✓ |

### 7. DEMOGRAPHICS (HZ1 Census Data)
**Your Requirement**: Use REAL HZ1 census data for all scenarios

| Scenario | Uses HZ1CensusDataLoader? | ✓/✗ |
|----------|---------------------------|-----|
| Baseline | Yes | ✓ |
| Scenario 1 | Yes | ✓ |
| Scenario 2 | Yes | ✓ |
| Scenario 3 | Yes | ✓ |
| Scenario 4 | Yes | ✓ |

### 8. BASELINE PROVIDERS IN ALL SCENARIOS
**Your Requirement**: All scenarios must include baseline mobile pantries & delivery

| Scenario | Has Baseline Pantries? | Has Baseline Delivery? | ✓/✗ |
|----------|------------------------|------------------------|-----|
| Baseline | Yes (3 pantries) | Yes (market-rate) | ✓ |
| Scenario 1 | add_baseline_mobile_pantries() | add_baseline_delivery_service() | ✓ |
| Scenario 2 | add_baseline_mobile_pantries() | add_baseline_delivery_service() | ✓ |
| Scenario 3 | add_baseline_mobile_pantries() + 2 more | add_baseline_delivery_service() | ✓ |
| Scenario 4 | add_baseline_mobile_pantries() | Subsidized delivery | ✓ |

---

## ITEMS NEEDING VERIFICATION:

### ⚠️ 1. Corner Store Quality Score
**Need to check**: Is corner quality set to 0.30 as specified?

### ⚠️ 2. Shopping Frequency Distribution
**Need to verify**: Does freq_low_income=(3,5) produce realistic patterns?

### ⚠️ 3. Pantry Propensity
**Current values**: 
- pantry_propensity_eligible: 0.75
- pantry_propensity_ineligible: 0.15

**Question**: Are these your specified values or my defaults?

### ⚠️ 4. Store Quality Scores
**Need to check**: What quality scores are assigned to each store type?

