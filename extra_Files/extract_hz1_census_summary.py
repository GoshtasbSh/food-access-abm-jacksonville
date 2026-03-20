#!/usr/bin/env python3
"""
Health Zone 1 Census Data Extraction Script
===========================================

Extracts raw counts from Health Zone 1 census data for:
- Overall population and households
- Household sizes (1-5 persons)
- Income categories (low, medium, high)
- SNAP participants
- Vehicle availability (with/without car)
- Census tract count
- Race/ethnicity counts

Data Sources (same as hz1_census_data_loader.py):
- duval_household_attributes.csv
- ACSDT5Y2023.B01001-Data.csv (population)
- ACSDT5Y2023.B02001-Data.csv (race)

Income cutoffs (2023 Jacksonville): Low <$28,262, Medium $28,262-$90,239, High >$90,239
"""

import math
import os
import pandas as pd
import re
import sys
from pathlib import Path


# Health Zone 1 census tracts (TRACTCE20 format - 6 digits)
# Same list as hz1_census_data_loader.py
HZ1_TRACT_IDS = [
    '000101', '000102', '000200', '000300', '001000', '001100',
    '001200', '001300', '001401', '001402', '001500', '001600',
    '002101', '002102', '002501', '002600', '002701', '002702',
    '002801', '002802', '002901', '002902', '010202', '010401',
    '010402', '010503', '010601', '010700', '010800', '010900',
    '011000', '011100', '011200', '011300', '011400', '011500',
    '011600', '011700', '011800', '011901', '012100', '017101',
    '017102', '017200', '017400'
]


def _normalize_tract_id(tract_str) -> str:
    """
    Normalize tract ID to 6-digit format for matching.
    Handles: '101' -> '000101', '102.02' -> '010202', '000101' -> '000101'
    """
    if tract_str is None or (isinstance(tract_str, float) and math.isnan(tract_str)):
        return ""
    s = str(tract_str).strip()
    if not s:
        return ""
    try:
        if "." in s:
            parts = s.split(".", 1)
            whole = int(parts[0]) if parts[0].lstrip("-").isdigit() else 0
            frac_str = (parts[1][:2] + "0")[:2] if len(parts) > 1 else "00"
            frac = int(frac_str) if frac_str.isdigit() else 0
            tract_num = whole * 100 + frac
        else:
            tract_num = int(s) if s.lstrip("-").isdigit() else 0
        return str(max(0, tract_num)).zfill(6)
    except (ValueError, TypeError):
        return ""

# Income cutoffs (2023 Jacksonville)
LOW_THRESHOLD = 28262.0
HIGH_THRESHOLD = 90239.0


def _find_column(df: pd.DataFrame, candidates: list, exact_first: bool = True) -> str:
    """Find first matching column name (handles variations). Prefers exact match."""
    for c in candidates:
        if exact_first:
            exact = [col for col in df.columns if str(col).strip() == c]
            if exact:
                return exact[0]
        matches = [col for col in df.columns if c in str(col)]
        if matches:
            return matches[0]
    return None


def _extract_tract_from_household_geo(geo_val) -> str:
    """Extract tract ID from household CSV geo column. Handles multiple formats."""
    g = str(geo_val)
    # Format 1: Census API GEOID "14000US12031000101" - tract is last 6 digits
    m = re.search(r'US12031(\d{6})', g)
    if m:
        return m.group(1)
    # Format 2: "tract:101" or "tract:000101" or "tract:102.02"
    m = re.search(r'tract:([\d.]+)', g, re.I)
    if m:
        return _normalize_tract_id(m.group(1))
    # Format 3: GEOID column with 11+ digits (state+county+tract)
    m = re.search(r'12031(\d{6})', g)
    if m:
        return m.group(1)
    return ""


def load_household_data(data_dir: str) -> pd.DataFrame:
    """Load household income/vehicle/SNAP data"""
    path = Path(data_dir) / "duval_household_attributes.csv"
    if not path.exists():
        raise FileNotFoundError(f"Household data not found: {path}")
    
    try:
        df = pd.read_csv(path, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding='latin-1')
    
    # Find geo column (could be 'geo' or 'Geography' or 'GEOID')
    geo_col = next((c for c in ['geo', 'Geography', 'GEOID'] if c in df.columns), None)
    if not geo_col:
        raise ValueError("Household CSV must have 'geo', 'Geography', or 'GEOID' column")
    
    # Extract and normalize tract IDs
    df['tract_id'] = df[geo_col].apply(_extract_tract_from_household_geo)
    df = df[df['tract_id'].isin(HZ1_TRACT_IDS)]
    
    return df


def _extract_tract_from_acs_geo(geo_val) -> str:
    """Extract 6-digit tract ID from ACS Geography column (e.g. 14000US12031000101)."""
    g = str(geo_val)
    m = re.search(r'US12031(\d{6})', g)
    return m.group(1) if m else ""


def load_population_data(data_dir: str) -> pd.DataFrame:
    """Load sex/age data (contains total population) - ACS B01001"""
    path = Path(data_dir) / "ACSDT5Y2023.B01001-Data.csv"
    if not path.exists():
        raise FileNotFoundError(f"Population data not found: {path}")
    
    try:
        df = pd.read_csv(path, encoding='utf-8', skiprows=1)
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding='latin-1', skiprows=1)
    
    geo_col = next((c for c in ['Geography', 'GEO_ID', 'geo'] if c in df.columns), None)
    if not geo_col:
        raise ValueError(f"Population CSV must have Geography column. Found: {list(df.columns)[:5]}...")
    
    df['tract_id'] = df[geo_col].apply(_extract_tract_from_acs_geo)
    df = df[df['tract_id'].isin(HZ1_TRACT_IDS)]
    # B01001 has ~49 rows per tract (Total + Male/Female age breakdowns).
    # Keep one row per tract - use the one with Total (B01001_001, usually first).
    df = df.drop_duplicates(subset=['tract_id'], keep='first')
    return df


def load_race_data(data_dir: str) -> pd.DataFrame:
    """Load race/ethnicity data - ACS B02001 (Race)"""
    path = Path(data_dir) / "ACSDT5Y2023.B02001-Data.csv"
    if not path.exists():
        raise FileNotFoundError(f"Race data not found: {path}")
    
    try:
        df = pd.read_csv(path, encoding='utf-8', skiprows=1)
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding='latin-1', skiprows=1)
    
    geo_col = next((c for c in ['Geography', 'GEO_ID', 'geo'] if c in df.columns), None)
    if not geo_col:
        raise ValueError(f"Race CSV must have Geography column. Found: {list(df.columns)[:5]}...")
    
    df['tract_id'] = df[geo_col].apply(_extract_tract_from_acs_geo)
    df = df[df['tract_id'].isin(HZ1_TRACT_IDS)]
    # B02001 has multiple rows per tract (race subgroups).
    # Keep only ONE row per tract to avoid overcounting.
    df = df.drop_duplicates(subset=['tract_id'], keep='first')
    return df


def safe_sum(df: pd.DataFrame, col: str) -> int:
    """Safely sum a column, handling missing column"""
    if col not in df.columns:
        # Try partial match
        matches = [c for c in df.columns if col in str(c)]
        if matches:
            return int(df[matches[0]].sum())
        return 0
    return int(df[col].sum())


def extract_census_summary(data_dir: str) -> dict:
    """
    Extract all requested census values for Health Zone 1.
    
    Returns dict with counts for all requested metrics.
    """
    df_hh = load_household_data(data_dir)
    df_pop = load_population_data(data_dir)
    df_race = load_race_data(data_dir)
    
    # --- Population --- (B01001_001E = total; prefer exact match to avoid Estimate!!Total:!!Male: etc.)
    pop_col = (
        next((c for c in df_pop.columns if str(c).strip() == 'Estimate!!Total:'), None) or
        next((c for c in df_pop.columns if str(c).strip() == 'B01001_001E'), None) or
        _find_column(df_pop, ['Total'])
    )
    total_population = int(df_pop[pop_col].sum()) if pop_col else 0
    
    # --- Households --- (use exact 'Total:' to avoid matching Total:_size, Total:_veh, etc.)
    total_col = next((c for c in df_hh.columns if str(c).strip() == 'Total:'), None)
    total_households = int(df_hh[total_col].sum()) if total_col else 0
    
    # --- Household sizes (1-5 persons) ---
    def get_hh_size_count(size: int) -> int:
        if size == 1:
            col1 = _find_column(df_hh, ['1-person household'])
            if not col1:
                return 0
            count = df_hh[col1].sum()
            # Check for duplicate column (e.g. '1-person household.1')
            for c in df_hh.columns:
                if '1-person household' in str(c) and c != col1:
                    count += df_hh[c].sum()
                    break
            return int(count)
        else:
            base = f'{size}-person household'
            cols = [c for c in df_hh.columns if base in str(c)]
            return int(sum(df_hh[c].sum() for c in cols)) if cols else 0
    
    hh_size_1 = get_hh_size_count(1)
    hh_size_2 = get_hh_size_count(2)
    hh_size_3 = get_hh_size_count(3)
    hh_size_4 = get_hh_size_count(4)
    hh_size_5 = get_hh_size_count(5)
    
    # --- Income categories (using same brackets as loader) ---
    low_income = (
        safe_sum(df_hh, 'Less than $10,000') +
        safe_sum(df_hh, '$10,000 to $14,999') +
        safe_sum(df_hh, '$15,000 to $19,999') +
        safe_sum(df_hh, '$20,000 to $24,999') +
        safe_sum(df_hh, '$25,000 to $29,999')  # Whole bracket as low per loader
    )
    
    medium_income = (
        safe_sum(df_hh, '$30,000 to $34,999') +
        safe_sum(df_hh, '$35,000 to $39,999') +
        safe_sum(df_hh, '$40,000 to $44,999') +
        safe_sum(df_hh, '$45,000 to $49,999') +
        safe_sum(df_hh, '$50,000 to $59,999') +
        safe_sum(df_hh, '$60,000 to $74,999') +
        safe_sum(df_hh, '$75,000 to $99,999')
    )
    
    high_income = (
        safe_sum(df_hh, '$100,000 to $124,999') +
        safe_sum(df_hh, '$125,000 to $149,999') +
        safe_sum(df_hh, '$150,000 to $199,999') +
        safe_sum(df_hh, '$200,000 or more')
    )
    
    # --- SNAP participants (households that received SNAP) ---
    snap_col = _find_column(df_hh, ['Household received Food Stamps/SNAP', 'SNAP'])
    snap_total_col = _find_column(df_hh, ['Total:_snap', 'Total'])
    if snap_col:
        snap_participants = int(df_hh[snap_col].sum())
    else:
        snap_participants = 0
    
    # --- Vehicle availability ---
    no_veh_col = _find_column(df_hh, ['No vehicle available'])
    total_veh_col = _find_column(df_hh, ['Total:_veh'])
    if total_veh_col and no_veh_col:
        households_without_car = int(df_hh[no_veh_col].sum())
        total_for_veh = int(df_hh[total_veh_col].sum())
        households_with_car = total_for_veh - households_without_car
    else:
        households_without_car = 0
        households_with_car = 0
    
    # --- Census tract count ---
    # HZ1 has 45 tracts per health_zone_1_census_tracts.txt; household data may cover fewer
    num_census_tracts_hh = len(df_hh)  # tracts with household data
    num_census_tracts = len(HZ1_TRACT_IDS)  # official HZ1 tract count (45)
    
    # --- Race/ethnicity counts ---
    race_mappings = [
        ('white', ['Estimate!!Total:!!White alone', 'White alone']),
        ('black', ['Estimate!!Total:!!Black or African American alone', 'Black or African American alone']),
        ('american_indian_alaska_native', ['Estimate!!Total:!!American Indian and Alaska Native alone', 'American Indian']),
        ('asian', ['Estimate!!Total:!!Asian alone', 'Asian alone']),
        ('native_hawaiian_pacific_islander', ['Estimate!!Total:!!Native Hawaiian and Other Pacific Islander alone', 'Native Hawaiian']),
        ('some_other_race', ['Estimate!!Total:!!Some Other Race alone', 'Some Other Race alone']),
        # Note: B02001 uses "Two or More Races:" with trailing colon
        ('two_or_more_races', ['Estimate!!Total:!!Two or More Races:', 'Two or More Races']),
    ]
    
    race_counts = {}
    for key, col_candidates in race_mappings:
        for cand in col_candidates:
            col = _find_column(df_race, [cand])
            if col:
                race_counts[key] = int(df_race[col].sum())
                break
        else:
            race_counts[key] = 0
    
    # Check for Hispanic/Latino (usually in B03003 table - may not be in B02001)
    hispanic_col = _find_column(df_race, ['Hispanic', 'Latino'])
    if hispanic_col:
        race_counts['hispanic_latino'] = int(df_race[hispanic_col].sum())
    else:
        race_counts['hispanic_latino'] = None  # Not in B02001; would need B03003
    
    results = {
        'overall_population': total_population,
        'overall_households': total_households,
        'tracts_with_household_data': num_census_tracts_hh,
        'household_size_1': hh_size_1,
        'household_size_2': hh_size_2,
        'household_size_3': hh_size_3,
        'household_size_4': hh_size_4,
        'household_size_5': hh_size_5,
        'households_low_income': low_income,
        'households_medium_income': medium_income,
        'households_high_income': high_income,
        'snap_participants': snap_participants,
        'households_with_car': households_with_car,
        'households_without_car': households_without_car,
        'number_of_census_tracts': num_census_tracts,
        'race_ethnicity': race_counts,
    }
    
    # Validation: income categories should sum to total households (income table universe)
    income_sum = low_income + medium_income + high_income
    results['_validation'] = {
        'income_sum': income_sum,
        'income_matches_total': abs(income_sum - total_households) <= max(10, total_households * 0.01),
    }
    
    return results


def print_summary(results: dict):
    """Print formatted summary of extracted data"""
    print("=" * 60)
    print("HEALTH ZONE 1 CENSUS DATA SUMMARY")
    print("=" * 60)
    
    # Show validation warning if income sum doesn't match
    if '_validation' in results:
        v = results['_validation']
        if not v.get('income_matches_total', True):
            print(f"\n  ⚠ Validation: Income sum ({v['income_sum']:,}) differs from total households")
    print()
    print("POPULATION & HOUSEHOLDS")
    print("-" * 40)
    print(f"  Overall population:        {results['overall_population']:,}")
    print(f"  Overall households:       {results['overall_households']:,}")
    print()
    print("HOUSEHOLD SIZES (count)")
    print("-" * 40)
    print(f"  1-person households:     {results['household_size_1']:,}")
    print(f"  2-person households:     {results['household_size_2']:,}")
    print(f"  3-person households:     {results['household_size_3']:,}")
    print(f"  4-person households:     {results['household_size_4']:,}")
    print(f"  5-person households:     {results['household_size_5']:,}")
    print()
    print("INCOME CATEGORIES (count)")
    print("-" * 40)
    print(f"  Low income (<$28,262):    {results['households_low_income']:,}")
    print(f"  Medium income ($28k-$90k): {results['households_medium_income']:,}")
    print(f"  High income (>$90,239):   {results['households_high_income']:,}")
    print()
    print("SNAP & VEHICLES")
    print("-" * 40)
    print(f"  SNAP participants:        {results['snap_participants']:,}")
    print(f"  Households with car:      {results['households_with_car']:,}")
    print(f"  Households without car:   {results['households_without_car']:,}")
    print()
    print("GEOGRAPHY")
    print("-" * 40)
    print(f"  Census tracts in HZ1:     {results['number_of_census_tracts']}")
    if 'tracts_with_household_data' in results:
        print(f"  (Household data covers:   {results['tracts_with_household_data']} tracts)")
    print()
    print("RACE/ETHNICITY (count)")
    print("-" * 40)
    for label, count in results['race_ethnicity'].items():
        if count is not None:
            print(f"  {label}: {count:,}")
        else:
            print(f"  {label}: (not in B02001 - need B03003 for Hispanic)")
    print()
    print("=" * 60)


def main():
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import get_census_data_dir
    default_data_dir = get_census_data_dir()
    
    # Allow override via command line (first non-flag arg is data dir)
    args = [a for a in sys.argv[1:] if a.startswith('-') is False]
    data_dir = args[0] if args else default_data_dir
    
    print(f"Data directory: {data_dir}\n")
    
    try:
        results = extract_census_summary(data_dir)
        print_summary(results)
        
        # Also output as JSON for programmatic use
        if '--json' in sys.argv:
            import json
            # Convert for JSON (exclude internal _validation)
            j = {k: v for k, v in results.items() if k not in ('race_ethnicity', '_validation')}
            j['race_ethnicity'] = {k: v for k, v in results['race_ethnicity'].items() if v is not None}
            if '_validation' in results and '--validate' in sys.argv:
                j['_validation'] = results['_validation']
            print("\nJSON output:")
            print(json.dumps(j, indent=2))
            
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        print("\nPlease ensure the following files exist in the data directory:")
        print("  - duval_household_attributes.csv")
        print("  - ACSDT5Y2023.B01001-Data.csv")
        print("  - ACSDT5Y2023.B02001-Data.csv")
        print(f"\nUsage: python extract_hz1_census_summary.py [data_directory] [--json]")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
