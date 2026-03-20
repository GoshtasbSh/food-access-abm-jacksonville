"""
Census Tract Data Loader for Household Demographics
===================================================

This module loads census tract data and generates households with
demographics matching the actual census statistics.

Author: ABM Team
Date: 2024
"""

import pandas as pd
import numpy as np
import random
from typing import Dict, List, Tuple
from shapely.geometry import Point
import geopandas as gpd

from enhanced_mesa_geo_model import (
    IncomeLevel, IncomeClassifier, CensusTractData
)


class CensusTractLoader:
    """
    Loads and processes census tract data for household demographics
    
    Supports loading from CSV or shapefile with demographic attributes
    """
    
    def __init__(self, data_source: str = None):
        """
        Initialize census tract loader
        
        Args:
            data_source: Path to census data file (CSV or shapefile)
                        If None, uses default/mock data
        """
        self.data_source = data_source
        self.tract_data: Dict[str, CensusTractData] = {}
        self.default_tract = CensusTractData()  # Fallback default
        
        if data_source:
            self.load_data(data_source)
    
    def load_data(self, file_path: str):
        """
        Load census tract data from file
        
        Expected columns in CSV:
        - tract_id: Census tract identifier
        - pct_low_income, pct_medium_income, pct_high_income: Income distribution
        - avg_household_size: Average household size
        - pct_size_1, pct_size_2, ... pct_size_5_plus: Household size distribution
        - pct_vehicle_low, pct_vehicle_medium, pct_vehicle_high: Vehicle availability by income
        - pct_white, pct_black, pct_hispanic, pct_asian, pct_other: Race distribution
        - snap_eligible_white, snap_eligible_black, etc.: SNAP eligibility by race
        
        Args:
            file_path: Path to data file
        """
        try:
            # Try loading as shapefile first
            if file_path.endswith('.shp'):
                gdf = gpd.read_file(file_path)
                df = pd.DataFrame(gdf.drop(columns='geometry'))
            else:
                # Load as CSV
                df = pd.read_csv(file_path)
            
            # Process each tract
            for _, row in df.iterrows():
                tract_id = str(row.get('tract_id', row.get('GEOID', 'unknown')))
                
                # Create CensusTractData object
                tract = CensusTractData(
                    tract_id=tract_id,
                    
                    # Income distribution
                    pct_low_income=float(row.get('pct_low_income', 0.45)),
                    pct_medium_income=float(row.get('pct_medium_income', 0.35)),
                    pct_high_income=float(row.get('pct_high_income', 0.20)),
                    
                    # Household size
                    avg_household_size=float(row.get('avg_household_size', 2.5)),
                    pct_size_1=float(row.get('pct_size_1', 0.30)),
                    pct_size_2=float(row.get('pct_size_2', 0.30)),
                    pct_size_3=float(row.get('pct_size_3', 0.20)),
                    pct_size_4=float(row.get('pct_size_4', 0.12)),
                    pct_size_5_plus=float(row.get('pct_size_5_plus', 0.08)),
                    
                    # Vehicle availability
                    pct_vehicle_low=float(row.get('pct_vehicle_low', 0.40)),
                    pct_vehicle_medium=float(row.get('pct_vehicle_medium', 0.70)),
                    pct_vehicle_high=float(row.get('pct_vehicle_high', 0.90)),
                    
                    # Race distribution
                    pct_white=float(row.get('pct_white', 0.35)),
                    pct_black=float(row.get('pct_black', 0.55)),
                    pct_hispanic=float(row.get('pct_hispanic', 0.05)),
                    pct_asian=float(row.get('pct_asian', 0.03)),
                    pct_other=float(row.get('pct_other', 0.02)),
                )
                
                # SNAP eligibility by race
                tract.snap_eligible_by_race = {
                    'white': float(row.get('snap_eligible_white', 0.25)),
                    'black': float(row.get('snap_eligible_black', 0.45)),
                    'hispanic': float(row.get('snap_eligible_hispanic', 0.40)),
                    'asian': float(row.get('snap_eligible_asian', 0.20)),
                    'other': float(row.get('snap_eligible_other', 0.30)),
                }
                
                self.tract_data[tract_id] = tract
            
            print(f"✅ Loaded {len(self.tract_data)} census tracts from {file_path}")
            
        except Exception as e:
            print(f"⚠️  Warning: Could not load census data from {file_path}: {e}")
            print(f"   Using default demographics")
            self.tract_data = {}
    
    def get_tract_data(self, tract_id: str = None) -> CensusTractData:
        """
        Get census tract data for a specific tract
        
        Args:
            tract_id: Census tract identifier (if None, returns default)
        
        Returns:
            CensusTractData object
        """
        if tract_id and tract_id in self.tract_data:
            return self.tract_data[tract_id]
        return self.default_tract
    
    def generate_household_demographics(self, tract_id: str = None, 
                                       location: Point = None) -> Dict:
        """
        Generate household demographics based on census tract data
        
        Args:
            tract_id: Census tract identifier (optional)
            location: Point location to determine tract (optional)
        
        Returns:
            Dictionary with household attributes:
            - income: IncomeLevel
            - vehicle_available: bool
            - household_size: int
            - race: str
            - snap_eligible: bool
            - annual_income: float
            - census_tract: str
        """
        # Get tract data
        tract = self.get_tract_data(tract_id)
        
        # 1. Select income level based on tract distribution
        income = np.random.choice(
            [IncomeLevel.LOW, IncomeLevel.MEDIUM, IncomeLevel.HIGH],
            p=[tract.pct_low_income, tract.pct_medium_income, tract.pct_high_income]
        )
        
        # 2. Generate actual annual income within category
        annual_income = IncomeClassifier.generate_random_income(income)
        
        # 3. Determine vehicle availability based on income
        vehicle_prob = {
            IncomeLevel.LOW: tract.pct_vehicle_low,
            IncomeLevel.MEDIUM: tract.pct_vehicle_medium,
            IncomeLevel.HIGH: tract.pct_vehicle_high
        }
        vehicle_available = random.random() < vehicle_prob[income]
        
        # 4. Determine household size
        size_distribution = [
            tract.pct_size_1,
            tract.pct_size_2,
            tract.pct_size_3,
            tract.pct_size_4,
            tract.pct_size_5_plus
        ]
        size_values = [1, 2, 3, 4, 5]  # 5 represents 5+
        household_size = np.random.choice(size_values, p=size_distribution)
        
        # 5. Determine race
        race = np.random.choice(
            ['white', 'black', 'hispanic', 'asian', 'other'],
            p=[tract.pct_white, tract.pct_black, tract.pct_hispanic, 
               tract.pct_asian, tract.pct_other]
        )
        
        # 6. Determine SNAP eligibility based on race and income
        # More likely for low income and varies by race
        snap_base_prob = tract.snap_eligible_by_race.get(race, 0.30)
        if income == IncomeLevel.LOW:
            snap_prob = snap_base_prob
        elif income == IncomeLevel.MEDIUM:
            snap_prob = snap_base_prob * 0.3
        else:  # HIGH
            snap_prob = snap_base_prob * 0.1
        
        snap_eligible = random.random() < snap_prob
        
        return {
            'income': income,
            'vehicle_available': vehicle_available,
            'household_size': household_size,
            'race': race,
            'snap_eligible': snap_eligible,
            'annual_income': annual_income,
            'census_tract': tract_id or 'unknown'
        }
    
    def generate_households_for_model(self, num_households: int, 
                                     tract_id: str = None) -> List[Dict]:
        """
        Generate multiple households with demographics
        
        Args:
            num_households: Number of households to generate
            tract_id: Census tract (if None, uses default)
        
        Returns:
            List of household demographic dictionaries
        """
        households = []
        for i in range(num_households):
            household = self.generate_household_demographics(tract_id)
            households.append(household)
        
        return households
    
    def get_summary_statistics(self, tract_id: str = None) -> Dict:
        """
        Get summary statistics for a census tract
        
        Args:
            tract_id: Census tract identifier
        
        Returns:
            Dictionary with summary statistics
        """
        tract = self.get_tract_data(tract_id)
        
        return {
            'tract_id': tract.tract_id,
            'income_distribution': {
                'low': f"{tract.pct_low_income*100:.1f}%",
                'medium': f"{tract.pct_medium_income*100:.1f}%",
                'high': f"{tract.pct_high_income*100:.1f}%"
            },
            'avg_household_size': tract.avg_household_size,
            'vehicle_availability': {
                'low_income': f"{tract.pct_vehicle_low*100:.1f}%",
                'medium_income': f"{tract.pct_vehicle_medium*100:.1f}%",
                'high_income': f"{tract.pct_vehicle_high*100:.1f}%"
            },
            'race_distribution': {
                'white': f"{tract.pct_white*100:.1f}%",
                'black': f"{tract.pct_black*100:.1f}%",
                'hispanic': f"{tract.pct_hispanic*100:.1f}%",
                'asian': f"{tract.pct_asian*100:.1f}%",
                'other': f"{tract.pct_other*100:.1f}%"
            }
        }


# ========================================================================
# CONVENIENCE FUNCTIONS
# ========================================================================

def load_census_data(file_path: str) -> CensusTractLoader:
    """
    Convenience function to load census data
    
    Args:
        file_path: Path to census data file
    
    Returns:
        CensusTractLoader instance
    """
    return CensusTractLoader(file_path)


def generate_default_households(num_households: int) -> List[Dict]:
    """
    Generate households using default demographics
    
    Args:
        num_households: Number of households
    
    Returns:
        List of household demographic dictionaries
    """
    loader = CensusTractLoader()
    return loader.generate_households_for_model(num_households)


# ========================================================================
# EXAMPLE USAGE
# ========================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("CENSUS TRACT DATA LOADER - EXAMPLE")
    print("=" * 70)
    
    # Example 1: Using default data
    print("\n1. Using Default Demographics:")
    loader = CensusTractLoader()
    print(f"   Default tract summary:")
    summary = loader.get_summary_statistics()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    
    # Example 2: Generate sample households
    print("\n2. Generating 5 Sample Households:")
    households = loader.generate_households_for_model(5)
    for i, hh in enumerate(households, 1):
        print(f"   Household {i}:")
        print(f"      Income: {hh['income'].value} (${hh['annual_income']:,.0f}/year)")
        print(f"      Size: {hh['household_size']} members")
        print(f"      Vehicle: {'Yes' if hh['vehicle_available'] else 'No'}")
        print(f"      Race: {hh['race']}")
        print(f"      SNAP: {'Yes' if hh['snap_eligible'] else 'No'}")
    
    # Example 3: Load from file (when you have real data)
    print("\n3. To Load Real Census Data:")
    print("   loader = CensusTractLoader('path/to/census_data.csv')")
    print("   households = loader.generate_households_for_model(500, tract_id='12031001100')")
    
    print("\n" + "=" * 70)

