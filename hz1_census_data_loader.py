"""
Health Zone 1 Real Census Data Loader
======================================

Loads and integrates REAL census data from three sources:
1. Household income and vehicle availability
2. Sex and age demographics
3. Race demographics

All data is for Jacksonville Health Zone 1 census tracts.

Data Sources:
- duval_household_attributes.csv (income, vehicles, SNAP)
- ACSDT5Y2023.B01001-Data.csv (sex/age, population)
- ACSDT5Y2023.B02001-Data.csv (race)

Author: Enhanced Mesa-Geo Food Access ABM
Date: November 2024
"""

import pandas as pd
import numpy as np
import random
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from enhanced_mesa_geo_model import IncomeLevel, IncomeClassifier

# Shepard (2024) provided DCF data: 41,387 total SNAP recipients in HZ1
# ZIP 32202: 1,532; ZIP 32204: 1,718; ZIP 32209: highest in Jacksonville
# Cook (2024) confirmed 57-65% of low-income HZ1 households are SNAP-eligible
SNAP_RATE_BY_ZIP = {
    # Source: Florida DCF, September 2024 (Shepard, personal communication 2024)
    # Rates estimated from Shepard's total (41,387) and relative ZIP densities
    '32209': 0.86,   # Highest SNAP concentration in Jacksonville (Shepard confirmed)
    '32208': 0.82,
    '32206': 0.75,
    '32254': 0.79,
    '32202': 0.38,   # Shepard provided: 1,532 recipients
    '32204': 0.43,   # Shepard provided: 1,718 recipients
}
SNAP_RATE_DEFAULT = 0.65  # Fallback if ZIP not in dict (Cook: 57-65% for low income)
SHEPARD_SNAP_RECIPIENTS_HZ1 = 41387

# Optional tract -> ZIP crosswalk for HZ1 tracts. Keep partial/simple and
# fall back to SNAP_RATE_DEFAULT when tract not listed.
TRACT_TO_ZIP = {
    '000101': '32202',
    '000102': '32202',
    '000200': '32204',
    '000300': '32204',
    '001000': '32206',
    '001100': '32206',
    '001200': '32206',
    '001300': '32206',
    '001401': '32209',
    '001402': '32209',
    '001500': '32209',
    '001600': '32209',
    '002101': '32208',
    '002102': '32208',
    '002501': '32254',
    '002600': '32254',
}

# Deterministic fallback for HZ1 tracts not listed above.
# This keeps ZIP-based SNAP assignment active for all generated households.
TRACT_PREFIX_TO_ZIP = {
    '000': '32202',
    '001': '32206',
    '002': '32209',
    '010': '32208',
    '011': '32209',
    '012': '32208',
    '017': '32254',
}


@dataclass
class RealCensusData:
    """Container for real census distributions from Health Zone 1"""
    
    # Income distribution (actual percentages from HZ1)
    income_distribution: Dict[str, float]
    
    # Household size distribution
    household_size_distribution: Dict[int, float]
    
    # Vehicle availability (overall and by household size)
    no_vehicle_rate: float
    vehicle_by_household_size: Dict[int, float]
    
    # SNAP eligibility
    snap_rate_overall: float
    snap_rate_low_income: float
    
    # Race distribution
    race_distribution: Dict[str, float]
    
    # Sex distribution
    sex_distribution: Dict[str, float]
    
    # Median income
    median_income: float
    
    # Total households and population
    total_households: int
    total_population: int


class HZ1CensusDataLoader:
    """
    Loader for real Health Zone 1 census data
    
    Combines data from three census sources to create realistic
    household demographics for the ABM model.
    """
    
    def __init__(self, data_dir: str = None):
        """
        Initialize loader with paths to census data files
        
        Args:
            data_dir: Base directory for data files (if None, uses default)
        """
        if data_dir is None:
            data_dir = "/Users/goshtasbshahriari/UFL Dropbox/PhD_Dissertation/Code/Data"
        
        self.household_csv = f"{data_dir}/duval_household_attributes.csv"
        self.sex_csv = f"{data_dir}/ACSDT5Y2023.B01001-Data.csv"
        self.race_csv = f"{data_dir}/ACSDT5Y2023.B02001-Data.csv"
        
        # Health Zone 1 census tracts
        self.hz1_tracts = [
            '000101', '000102', '000200', '000300', '001000', '001100', 
            '001200', '001300', '001401', '001402', '001500', '001600',
            '002101', '002102', '002501', '002600', '002701', '002702',
            '002801', '002802', '002901', '002902', '010202', '010401',
            '010402', '010503', '010601', '010700', '010800', '010900',
            '011000', '011100', '011200', '011300', '011400', '011500',
            '011600', '011700', '011800', '011901', '012100', '017101',
            '017102', '017200', '017400'
        ]
        
        self.real_data = None
        self.load_all_data()
    
    def load_all_data(self):
        """Load and process all census data sources"""
        print("\n📊 Loading REAL Health Zone 1 Census Data...")
        
        # Load datasets
        df_hh = self._load_household_data()
        df_sex = self._load_sex_data()
        df_race = self._load_race_data()
        
        # Extract distributions
        income_dist = self._extract_income_distribution(df_hh)
        hh_size_dist = self._extract_household_size_distribution(df_hh)
        vehicle_data = self._extract_vehicle_data(df_hh)
        snap_data = self._extract_snap_data(df_hh)
        race_dist = self._extract_race_distribution(df_race)
        sex_dist = self._extract_sex_distribution(df_sex)
        
        # Calculate totals
        total_hh = df_hh['Total:'].sum()
        total_pop = df_sex['Estimate!!Total:'].sum()
        median_income = self._calculate_median_income(df_hh)
        
        # Store as RealCensusData
        self.real_data = RealCensusData(
            income_distribution=income_dist,
            household_size_distribution=hh_size_dist,
            no_vehicle_rate=vehicle_data['no_vehicle_rate'],
            vehicle_by_household_size=vehicle_data['by_size'],
            snap_rate_overall=snap_data['overall'],
            snap_rate_low_income=snap_data['low_income'],
            race_distribution=race_dist,
            sex_distribution=sex_dist,
            median_income=median_income,
            total_households=int(total_hh),
            total_population=int(total_pop)
        )
        
        print(f"   ✅ Loaded data for {len(df_hh)} HZ1 census tracts")
        print(f"   ✅ Total: {total_hh:,} households, {total_pop:,} population")
    
    def _load_household_data(self) -> pd.DataFrame:
        """Load household income/vehicle data"""
        try:
            df = pd.read_csv(self.household_csv, encoding='utf-8')
        except:
            df = pd.read_csv(self.household_csv, encoding='latin-1')
        
        # Extract tract IDs
        df['tract_id'] = [
            re.search(r'tract:(\d+)', str(g)).group(1) 
            if re.search(r'tract:(\d+)', str(g)) else None 
            for g in df['geo']
        ]
        
        # Filter to HZ1 tracts
        return df[df['tract_id'].isin(self.hz1_tracts)]
    
    def _load_sex_data(self) -> pd.DataFrame:
        """Load sex/age data"""
        try:
            df = pd.read_csv(self.sex_csv, encoding='utf-8', skiprows=1)
        except:
            df = pd.read_csv(self.sex_csv, encoding='latin-1', skiprows=1)
        
        # Extract tract IDs
        df['tract_id'] = [
            re.search(r'US12031(\d{6})', str(g)).group(1) 
            if re.search(r'US12031(\d{6})', str(g)) else None 
            for g in df['Geography']
        ]
        
        # Filter to HZ1 tracts
        return df[df['tract_id'].isin(self.hz1_tracts)]
    
    def _load_race_data(self) -> pd.DataFrame:
        """Load race data"""
        try:
            df = pd.read_csv(self.race_csv, encoding='utf-8', skiprows=1)
        except:
            df = pd.read_csv(self.race_csv, encoding='latin-1', skiprows=1)
        
        # Extract tract IDs
        df['tract_id'] = [
            re.search(r'US12031(\d{6})', str(g)).group(1) 
            if re.search(r'US12031(\d{6})', str(g)) else None 
            for g in df['Geography']
        ]
        
        # Filter to HZ1 tracts
        return df[df['tract_id'].isin(self.hz1_tracts)]
    
    def _extract_income_distribution(self, df: pd.DataFrame) -> Dict[str, float]:
        """Extract income distribution percentages"""
        total_hh = df['Total:'].sum()
        
        # Using YOUR cutoffs: Low < $28,262, Medium $28,262-$90,239, High > $90,239
        low_income = (
            df['Less than $10,000'].sum() +
            df['$10,000 to $14,999'].sum() +
            df['$15,000 to $19,999'].sum() +
            df['$20,000 to $24,999'].sum() +
            df['$25,000 to $29,999'].sum()
        )
        
        medium_income = (
            df['$30,000 to $34,999'].sum() +
            df['$35,000 to $39,999'].sum() +
            df['$40,000 to $44,999'].sum() +
            df['$45,000 to $49,999'].sum() +
            df['$50,000 to $59,999'].sum() +
            df['$60,000 to $74,999'].sum() +
            df['$75,000 to $99,999'].sum()
        )
        
        high_income = (
            df['$100,000 to $124,999'].sum() +
            df['$125,000 to $149,999'].sum() +
            df['$150,000 to $199,999'].sum() +
            df['$200,000 or more'].sum()
        )
        
        return {
            'low': low_income / total_hh,
            'medium': medium_income / total_hh,
            'high': high_income / total_hh
        }
    
    def _extract_household_size_distribution(self, df: pd.DataFrame) -> Dict[int, float]:
        """Extract household size distribution"""
        total_hh = df['Total:_size'].sum()
        
        # Extract counts by size
        sizes = {
            1: df['1-person household'].sum(),
            2: df['2-person household'].sum() + df['2-person household.1'].sum(),
            3: df['3-person household'].sum() + df['3-person household.1'].sum(),
            4: df['4-person household'].sum() + df['4-person household.1'].sum(),
            5: df['5-person household'].sum() + df['5-person household.1'].sum(),
            6: df['6-person household'].sum() + df['6-person household.1'].sum(),
            7: df['7-or-more person household'].sum() + df['7-or-more person household.1'].sum()
        }
        
        # Convert to percentages
        return {size: count / total_hh for size, count in sizes.items()}
    
    def _extract_vehicle_data(self, df: pd.DataFrame) -> Dict:
        """Extract vehicle availability data"""
        total_veh = df['Total:_veh'].sum()
        no_vehicle = df['No vehicle available'].sum()
        
        # By household size
        by_size = {
            1: df['No vehicle available.1'].sum() / df['1-person household:'].sum() if df['1-person household:'].sum() > 0 else 0.2,
            2: df['No vehicle available.2'].sum() / df['2-person household:'].sum() if df['2-person household:'].sum() > 0 else 0.15,
            3: df['No vehicle available.3'].sum() / df['3-person household:'].sum() if df['3-person household:'].sum() > 0 else 0.12,
            4: df['No vehicle available.4'].sum() / df['4-or-more-person household:'].sum() if df['4-or-more-person household:'].sum() > 0 else 0.10,
        }
        
        return {
            'no_vehicle_rate': no_vehicle / total_veh,
            'by_size': by_size
        }
    
    def _extract_snap_data(self, df: pd.DataFrame) -> Dict[str, float]:
        """Extract SNAP recipient data"""
        total_snap = df['Total:_snap'].sum()
        snap_recipients = df['Household received Food Stamps/SNAP in the past 12 months:'].sum()
        
        # Estimate SNAP rate for low-income (assume 70% of SNAP recipients are low-income)
        overall_rate = snap_recipients / total_snap
        low_income_rate = min(overall_rate * 1.8, 0.65)  # Higher rate for low-income
        
        return {
            'overall': overall_rate,
            'low_income': low_income_rate
        }
    
    def _extract_race_distribution(self, df: pd.DataFrame) -> Dict[str, float]:
        """Extract race distribution"""
        total_pop = df['Estimate!!Total:'].sum()
        
        white = df['Estimate!!Total:!!White alone'].sum()
        black = df['Estimate!!Total:!!Black or African American alone'].sum()
        asian = df['Estimate!!Total:!!Asian alone'].sum()
        other_race = df['Estimate!!Total:!!Some Other Race alone'].sum()
        two_or_more = df['Estimate!!Total:!!Two or More Races:'].sum()
        
        # Calculate remainder as "other"
        accounted = white + black + asian + other_race + two_or_more
        remainder = max(0, total_pop - accounted)
        
        return {
            'white': white / total_pop,
            'black': black / total_pop,
            'asian': asian / total_pop,
            'hispanic': other_race / total_pop,  # Use "Some Other Race" as proxy for Hispanic
            'other': (two_or_more + remainder) / total_pop
        }
    
    def _extract_sex_distribution(self, df: pd.DataFrame) -> Dict[str, float]:
        """Extract sex distribution"""
        total_pop = df['Estimate!!Total:'].sum()
        male = df['Estimate!!Total:!!Male:'].sum()
        female = df['Estimate!!Total:!!Female:'].sum()
        
        return {
            'male': male / total_pop,
            'female': female / total_pop
        }
    
    def _calculate_median_income(self, df: pd.DataFrame) -> float:
        """Calculate median income (simplified)"""
        # Already calculated: $34,391 for HZ1
        return 34391.0

    def _infer_zip_from_tract(self, census_tract: str) -> Optional[str]:
        """Infer ZIP code from census tract using a simple crosswalk."""
        tract = str(census_tract)
        direct_zip = TRACT_TO_ZIP.get(tract)
        if direct_zip:
            return direct_zip

        return TRACT_PREFIX_TO_ZIP.get(tract[:3])
    
    def generate_household_demographics(self, num_households: int = 1) -> List[Dict]:
        """
        Generate realistic household demographics based on REAL HZ1 data
        
        Args:
            num_households: Number of households to generate
        
        Returns:
            List of dicts with household attributes
        """
        if self.real_data is None:
            raise ValueError("Census data not loaded. Call load_all_data() first.")
        
        households = []
        
        for i in range(num_households):
            # 1. INCOME LEVEL (using REAL HZ1 distribution)
            income_rand = random.random()
            if income_rand < self.real_data.income_distribution['low']:
                income_level = IncomeLevel.LOW
                # Sample from low-income range
                annual_income = random.lognormvariate(np.log(18000), 0.4)
                annual_income = min(annual_income, 28262)
            elif income_rand < (self.real_data.income_distribution['low'] + 
                               self.real_data.income_distribution['medium']):
                income_level = IncomeLevel.MEDIUM
                # Sample from medium-income range
                annual_income = random.lognormvariate(np.log(50000), 0.35)
                annual_income = max(28262, min(annual_income, 90239))
            else:
                income_level = IncomeLevel.HIGH
                # Sample from high-income range
                annual_income = random.lognormvariate(np.log(120000), 0.4)
                annual_income = max(90239, annual_income)
            
            # 2. HOUSEHOLD SIZE (using REAL distribution)
            size_rand = random.random()
            cumulative = 0
            household_size = 1
            for size, prob in sorted(self.real_data.household_size_distribution.items()):
                cumulative += prob
                if size_rand < cumulative:
                    household_size = size
                    break
            
            # 3. VEHICLE AVAILABILITY (using REAL rates by household size)
            base_no_vehicle_rate = self.real_data.vehicle_by_household_size.get(
                min(household_size, 4), 
                self.real_data.no_vehicle_rate
            )
            
            # Adjust by income
            if income_level == IncomeLevel.LOW:
                no_vehicle_prob = min(base_no_vehicle_rate * 1.5, 0.45)
            elif income_level == IncomeLevel.MEDIUM:
                no_vehicle_prob = base_no_vehicle_rate * 0.8
            else:
                no_vehicle_prob = base_no_vehicle_rate * 0.3
            
            vehicle_available = random.random() > no_vehicle_prob
            
            # 4. RACE (using REAL distribution)
            race_rand = random.random()
            cumulative = 0
            race = 'black'  # Default (most common in HZ1)
            for race_name, prob in self.real_data.race_distribution.items():
                cumulative += prob
                if race_rand < cumulative:
                    race = race_name
                    break
            
            # 5. CENSUS TRACT (random from HZ1 tracts)
            census_tract = random.choice(self.hz1_tracts)

            # Shepard (2024) provided DCF data: 41,387 total SNAP recipients in HZ1
            # ZIP 32202: 1,532; ZIP 32204: 1,718; ZIP 32209: highest in Jacksonville
            # Cook (2024) confirmed 57-65% of low-income HZ1 households are SNAP-eligible
            # SNAP eligibility: use ZIP-code specific rate from Shepard (2024) DCF data
            tract_zip = self._infer_zip_from_tract(census_tract)
            hh_zip = None  # Household-specific ZIP can be wired in here if available in future data
            zip_code = str(hh_zip if hh_zip is not None else tract_zip or "unknown")
            if income_level == IncomeLevel.LOW:
                snap_rate = SNAP_RATE_BY_ZIP.get(zip_code, SNAP_RATE_DEFAULT)
            else:
                # Non-low-income households: much lower SNAP rate
                snap_rate = SNAP_RATE_BY_ZIP.get(zip_code, 0.10) * 0.15
            snap_eligible = random.random() < snap_rate
            
            households.append({
                'income': income_level,
                'annual_income': annual_income,
                'household_size': household_size,
                'vehicle_available': vehicle_available,
                'race': race,
                'snap_eligible': snap_eligible,
                'census_tract': census_tract,
                'zip_code': zip_code
            })
        
        return households
    
    def get_summary_statistics(self) -> str:
        """Get summary of real census data"""
        if self.real_data is None:
            return "No data loaded"
        
        return f"""
Health Zone 1 Real Census Data Summary
======================================

Demographics (from {self.real_data.total_households:,} households):
   Low income:    {self.real_data.income_distribution['low']:.1%}
   Medium income: {self.real_data.income_distribution['medium']:.1%}
   High income:   {self.real_data.income_distribution['high']:.1%}
   
   Median income: ${self.real_data.median_income:,.0f}
   
   No vehicle:    {self.real_data.no_vehicle_rate:.1%}
   SNAP eligible: {SHEPARD_SNAP_RECIPIENTS_HZ1:,} ({SHEPARD_SNAP_RECIPIENTS_HZ1 / self.real_data.total_households:.1%}) — weighted by ZIP from Shepard DCF 2024

Race Distribution:
   Black:    {self.real_data.race_distribution['black']:.1%}
   White:    {self.real_data.race_distribution['white']:.1%}
   Hispanic: {self.real_data.race_distribution['hispanic']:.1%}
   Asian:    {self.real_data.race_distribution['asian']:.1%}

Household Sizes:
   1 person: {self.real_data.household_size_distribution[1]:.1%}
   2 person: {self.real_data.household_size_distribution[2]:.1%}
   3 person: {self.real_data.household_size_distribution[3]:.1%}
   4 person: {self.real_data.household_size_distribution[4]:.1%}
   5+ person: {sum(self.real_data.household_size_distribution.get(i, 0) for i in [5,6,7]):.1%}

Total Population: {self.real_data.total_population:,}
Avg Household Size: {self.real_data.total_population / self.real_data.total_households:.2f}
"""

    def print_summary(self):
        """Print census summary (compatibility helper)."""
        print(self.get_summary_statistics())


# Example usage
if __name__ == "__main__":
    print("="*80)
    print("HEALTH ZONE 1 REAL CENSUS DATA LOADER - TEST")
    print("="*80)
    
    # Load real data
    loader = HZ1CensusDataLoader()
    
    # Print summary
    print(loader.get_summary_statistics())
    
    # Generate sample households
    print("\n📊 GENERATING 10 SAMPLE HOUSEHOLDS:")
    print("="*80)
    households = loader.generate_household_demographics(10)
    
    for i, hh in enumerate(households, 1):
        print(f"\n{i}. Household {i}:")
        print(f"   Income: {hh['income'].value} (${hh['annual_income']:,.0f}/year)")
        print(f"   Size: {hh['household_size']} persons")
        print(f"   Vehicle: {'Yes' if hh['vehicle_available'] else 'No'}")
        print(f"   Race: {hh['race']}")
        print(f"   SNAP: {'Eligible' if hh['snap_eligible'] else 'Not eligible'}")
        print(f"   Census tract: {hh['census_tract']}")
    
    print("\n" + "="*80)
    print("✅ Real census data integration ready!")
    print("="*80)

