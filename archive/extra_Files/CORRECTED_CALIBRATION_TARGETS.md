# ✅ CORRECTED CALIBRATION TARGETS

**Date**: November 24, 2025  
**Source**: User-provided table + clarifications

---

## 📊 OFFICIAL CALIBRATION TARGETS (FROM YOUR TABLE)

| # | Pattern | Target Value | Source | Tolerance | Status |
|---|---------|--------------|--------|-----------|--------|
| 1 | Annual spending (low-income) | **$5,270/year** | USDA ERS 2023 | ±15% (≤$790) | ✅ UPDATED |
| 2 | Annual spending (medium) | **$8,989/year** | USDA ERS 2023 | ±10% (MAPE ≤15%) | ✅ UPDATED |
| 3 | Annual spending (high) | **$16,996/year** | USDA ERS 2023 | ±10% (MAPE ≤15%) | ✅ UPDATED |
| 4 | Weekly shopping frequency | **40% of households** | Consumer surveys | ≤15% | ✅ SET |
| 5 | Sub-weekly frequency | **22% of households** | Consumer surveys | ±8% | ✅ SET |
| 6 | Travel distance (car) | **3.4 miles (5.5 km)** | USDA ERS 2015 | ±25% | ✅ SET |
| 7 | Travel distance (no-car) | **1.0 mile (1.6 km)** | USDA ERS 2015 | ±25% | ✅ CORRECTED |
| 8 | Small store patronage | **≤10% of trips** | Literature | Hard constraint | ✅ SET |
| 9 | Pantry utilization | **12.5% of households** | PMC8378669 | ±2.5% | ✅ NOTED |

---

## 🔧 CRITICAL CORRECTIONS MADE

### Correction #1: Annual Spending
**Old (WRONG)**:
- Low: $5,254/year
- Medium: $9,004/year
- High: $17,004/year

**New (CORRECT)**:
- Low: **$5,270/year** ($101.35/week)
- Medium: **$8,989/year** ($172.87/week)
- High: **$16,996/year** ($326.85/week)

### Correction #2: No-Car Distance
**Old (WRONG)**: 2.2 miles (3.5 km)  
**New (CORRECT)**: **1.0 mile (1.6 km)** - User specified

**Impact**: This is MUCH more restrictive! Without a car, households can only reach stores within 1 mile.

### Correction #3: Small Store Share
**Old (WRONG)**: Target ~8%  
**New (CORRECT)**: **Hard constraint ≤10%**

### Correction #4: Pantry Usage Interpretation
**Clarified**: "10-15% of urban low-income households use a food pantry **at least once** in a month/year"

**Meaning**: 
- NOT 12.5% of trips
- NOT 12.5% of shopping events
- **12.5% of households use pantry at least once during simulation**

---

## 🎯 UPDATED BASKET SIZE CALCULATIONS

With new targets, required baskets:

### Low-Income ($5,270/year = $101.35/week):
- **With 2 trips/week**: $51/trip ✓ (Current: 0.25 multiplier = $51)
- **Range**: $30-$80 per trip

### Medium-Income ($8,989/year = $172.87/week):
- **With 1 trip/week**: $173/trip ✓ (Current: 0.85 multiplier = $173)
- **Range**: $120-$230 per trip

### High-Income ($16,996/year = $326.85/week):
- **With 0.9 trips/week**: $363/trip 
- **Current**: 1.70 multiplier = $347/trip
- **Adjustment needed**: Increase to **1.78 multiplier** → $363/trip

---

## 🔧 FINAL PARAMETER ADJUSTMENTS

<function_calls>
<invoke name="search_replace">
<parameter name="file_path">/Users/goshtasbshahriari/Desktop/Code/GeoMesa_Food_Access/enhanced_mesa_geo_model.py
