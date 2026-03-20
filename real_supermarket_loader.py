"""
Real Supermarket Data Loader
==============================

Loads actual supermarket data from CSV and integrates with the ABM model.

Handles:
- Loading CSV with store information
- Geocoding addresses to lat/lon coordinates
- Mapping store categories to provider types
- Assigning appropriate capacities
- Creating provider agents

Author: Enhanced Mesa-Geo Food Access ABM
Date: October 2025
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from shapely.geometry import Point
import warnings
warnings.filterwarnings('ignore')

# Try to import geocoding libraries
try:
    from geopy.geocoders import Nominatim
    from geopy.extra.rate_limiter import RateLimiter
    GEOCODING_AVAILABLE = True
except ImportError:
    print("⚠️  geopy not installed. Geocoding will use fallback coordinates.")
    GEOCODING_AVAILABLE = False

from enhanced_mesa_geo_model import ProviderType


class SupermarketDataLoader:
    """
    Loader for real supermarket data from CSV
    
    Handles geocoding, category mapping, and capacity assignment
    """
    
    def __init__(self, csv_path: str, use_geocoding: bool = True):
        """
        Initialize loader
        
        Args:
            csv_path: Path to supermarket CSV file
            use_geocoding: Whether to geocode addresses (requires geopy)
        """
        self.csv_path = csv_path
        self.use_geocoding = use_geocoding and GEOCODING_AVAILABLE
        self.df = None
        self.geocoder = None
        
        # Initialize geocoder if available
        if self.use_geocoding:
            try:
                self.geocoder = Nominatim(user_agent="food_access_abm")
                # Add rate limiting (1 request per second)
                self.geocode = RateLimiter(self.geocoder.geocode, min_delay_seconds=1)
                print("✅ Geocoding enabled (using Nominatim)")
            except Exception as e:
                print(f"⚠️  Geocoding failed to initialize: {e}")
                self.use_geocoding = False
        
        # Fallback coordinates for Health Zone 1 (if geocoding fails)
        self.health_zone_center = (-81.690, 30.355)
        self.health_zone_bounds = {
            'min_lon': -81.75,
            'max_lon': -81.63,
            'min_lat': 30.30,
            'max_lat': 30.40
        }
        
        self.load_data()
    
    def load_data(self):
        """Load supermarket data from CSV"""
        try:
            # Try UTF-8 first, then latin-1
            try:
                self.df = pd.read_csv(self.csv_path)
            except UnicodeDecodeError:
                self.df = pd.read_csv(self.csv_path, encoding='latin-1')
            
            print(f"✅ Loaded {len(self.df)} stores from CSV")
            
            # Clean column names (remove special characters)
            self.df.columns = self.df.columns.str.replace('Ê', ' ').str.strip()
            
            # Show summary
            print(f"   Categories: {self.df['Category'].nunique()} unique")
            
        except Exception as e:
            print(f"❌ Error loading CSV: {e}")
            self.df = pd.DataFrame()
    
    def geocode_address(self, address: str, zip_code: str) -> Optional[Tuple[float, float]]:
        """
        Geocode an address to (lon, lat)
        
        Args:
            address: Street address
            zip_code: ZIP code
        
        Returns:
            (longitude, latitude) or None if geocoding fails
        """
        if not self.use_geocoding or pd.isna(address):
            return None
        
        try:
            # Construct full address
            full_address = f"{address}, {zip_code}"
            
            # Geocode
            location = self.geocode(full_address, timeout=10)
            
            if location:
                # Return (lon, lat)
                return (location.longitude, location.latitude)
            else:
                return None
        
        except Exception as e:
            print(f"⚠️  Geocoding failed for '{address}': {e}")
            return None
    
    def get_fallback_coordinates(self, index: int) -> Tuple[float, float]:
        """
        Get fallback coordinates within Health Zone 1
        
        Distributes stores evenly across the zone
        """
        bounds = self.health_zone_bounds
        
        # Create a grid pattern
        total_stores = len(self.df)
        grid_size = int(np.ceil(np.sqrt(total_stores)))
        
        row = index // grid_size
        col = index % grid_size
        
        # Calculate position in grid
        lon = bounds['min_lon'] + (col / grid_size) * (bounds['max_lon'] - bounds['min_lon'])
        lat = bounds['min_lat'] + (row / grid_size) * (bounds['max_lat'] - bounds['min_lat'])
        
        # Add small random offset
        lon += np.random.uniform(-0.01, 0.01)
        lat += np.random.uniform(-0.01, 0.01)
        
        return (lon, lat)
    
    def map_category_to_provider_type(self, category: str) -> ProviderType:
        """
        Map store category to ProviderType enum
        
        Args:
            category: Store category from CSV
        
        Returns:
            ProviderType enum
        """
        if pd.isna(category):
            return ProviderType.CORNER_STORE  # Default
        
        category_lower = category.lower().replace('ê', ' ').strip()
        
        # Supermarkets and full-service grocery stores
        if any(keyword in category_lower for keyword in [
            'supermarket', 'super market', 'publix', 'winn', 'harvey'
        ]):
            return ProviderType.GROCERY_STORE
        
        # Large grocery stores
        if 'grocery' in category_lower and 'corner' not in category_lower:
            return ProviderType.GROCERY_STORE
        
        # Dollar stores, corner stores, convenience stores
        if any(keyword in category_lower for keyword in [
            'dollar', 'corner', 'convenience', 'gas', 'mart'
        ]):
            return ProviderType.CORNER_STORE
        
        # Default to corner store
        return ProviderType.CORNER_STORE
    
    def assign_capacity(self, category: str, provider_type: ProviderType, 
                       price_level: str = None) -> int:
        """
        Assign store capacity based on category and type
        
        Args:
            category: Store category
            provider_type: Mapped provider type
            price_level: Price level ($, $$, $$$)
        
        Returns:
            Daily customer capacity
        """
        category_lower = str(category).lower().replace('ê', ' ').strip()
        
        # Large supermarkets
        if provider_type == ProviderType.GROCERY_STORE:
            # Check for specific large chains
            if any(keyword in category_lower for keyword in ['publix', 'fresh market']):
                return 800  # Large full-service
            elif any(keyword in category_lower for keyword in ['winn', 'harvey', 'aldi']):
                return 600  # Medium discount
            else:
                return 700  # Default grocery
        
        # Corner/convenience stores
        else:
            if 'dollar' in category_lower:
                return 80  # Dollar stores have higher capacity
            else:
                return 50  # Small corner stores
    
    def get_store_data(self, use_geocoding: bool = None) -> List[Dict]:
        """
        Get processed store data ready for model integration
        
        Args:
            use_geocoding: Override geocoding setting (None = use default)
        
        Returns:
            List of dicts with store information
        """
        if use_geocoding is None:
            use_geocoding = self.use_geocoding
        
        stores = []
        geocoding_failures = 0
        
        print(f"\n📍 Processing {len(self.df)} stores...")
        if use_geocoding:
            print("   Using geocoding (this may take a few minutes)...")
        else:
            print("   Using pre-geocoded coordinates from CSV columns")
        
        for idx, row in self.df.iterrows():
            # Get basic info
            name = str(row.get('Name', f'Store {idx}')).replace('Ê', ' ').strip()
            address = str(row.get('Address', '')).replace('Ê', ' ').strip()
            zip_code = str(row.get('ZipCode', row.get('Zip Code', row.get('ZipÊCode', '')))).strip()
            category = str(row.get('Category', '')).replace('Ê', ' ').strip()
            price_level = str(row.get('Price Level', row.get('PriceÊLevel', ''))).replace('Ê', '').strip()
            rating = row.get('Rating', None)
            
            # Get coordinates — prefer pre-existing columns over geocoding/fallback
            lat_val = row.get('Latitude', None) or row.get('latitude', None)
            lon_val = row.get('Longitude', None) or row.get('longitude', None)

            if pd.notna(lat_val) and pd.notna(lon_val):
                coords = (float(lon_val), float(lat_val))
            elif use_geocoding:
                coords = self.geocode_address(address, zip_code)
                if coords is None:
                    coords = self.get_fallback_coordinates(idx)
                    geocoding_failures += 1
            else:
                coords = self.get_fallback_coordinates(idx)
            
            lon, lat = coords
            
            # Map category to provider type
            provider_type = self.map_category_to_provider_type(category)
            
            # Use CSV Capacity column if present and valid; else assign from category
            cap_val = row.get('Capacity', row.get('capacity', None))
            if pd.notna(cap_val) and cap_val != '' and int(float(cap_val)) > 0:
                capacity = int(float(cap_val))
            else:
                capacity = self.assign_capacity(category, provider_type, price_level)
            
            # Create store dict
            store_data = {
                'name': name,
                'address': address,
                'zip_code': zip_code,
                'category': category,
                'provider_type': provider_type,
                'longitude': lon,
                'latitude': lat,
                'capacity': capacity,
                'price_level': price_level,
                'rating': rating
            }
            
            stores.append(store_data)
        
        if use_geocoding and geocoding_failures > 0:
            print(f"   ⚠️  {geocoding_failures} addresses used fallback coordinates")
        
        print(f"   ✅ Processed {len(stores)} stores successfully")
        
        # Print summary by type
        type_counts = {}
        for store in stores:
            ptype = store['provider_type']
            type_counts[ptype] = type_counts.get(ptype, 0) + 1
        
        print(f"\n   Store Type Summary:")
        for ptype, count in type_counts.items():
            print(f"      • {ptype.value}: {count} stores")
        
        return stores
    
    def filter_by_type(self, stores: List[Dict], 
                      provider_type: ProviderType) -> List[Dict]:
        """
        Filter stores by provider type
        
        Args:
            stores: List of store dicts
            provider_type: Type to filter for
        
        Returns:
            Filtered list
        """
        return [s for s in stores if s['provider_type'] == provider_type]
    
    def export_to_csv(self, stores: List[Dict], output_path: str):
        """
        Export processed store data to CSV (with coordinates)
        
        Args:
            stores: List of store dicts
            output_path: Path to save CSV
        """
        df = pd.DataFrame(stores)
        df.to_csv(output_path, index=False)
        print(f"✅ Exported store data to: {output_path}")


# ============================================================================
# Convenience Functions
# ============================================================================

def load_real_supermarkets(csv_path: str, 
                          use_geocoding: bool = False) -> List[Dict]:
    """
    Convenience function to load real supermarket data
    
    Args:
        csv_path: Path to CSV file
        use_geocoding: Whether to geocode addresses (slow, requires geopy)
    
    Returns:
        List of store dicts
    
    Usage:
        stores = load_real_supermarkets('Supermarket.csv')
        grocery_stores = [s for s in stores if s['provider_type'] == ProviderType.GROCERY_STORE]
    """
    loader = SupermarketDataLoader(csv_path, use_geocoding)
    return loader.get_store_data()


def get_stores_for_model(csv_path: str, 
                        use_geocoding: bool = False) -> Tuple[List, List]:
    """
    Get grocery stores and corner stores separately for model
    
    Args:
        csv_path: Path to CSV file
        use_geocoding: Whether to geocode addresses
    
    Returns:
        (grocery_stores, corner_stores) - each as list of tuples (name, lon, lat, capacity)
    
    Usage:
        grocery, corner = get_stores_for_model('Supermarket.csv')
    """
    stores = load_real_supermarkets(csv_path, use_geocoding)
    
    # Filter by type
    grocery_stores = [
        (s['name'], s['longitude'], s['latitude'], s['capacity'])
        for s in stores if s['provider_type'] == ProviderType.GROCERY_STORE
    ]
    
    corner_stores = [
        (s['name'], s['longitude'], s['latitude'], s['capacity'])
        for s in stores if s['provider_type'] == ProviderType.CORNER_STORE
    ]
    
    return grocery_stores, corner_stores


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    print("="*80)
    print("REAL SUPERMARKET DATA LOADER - EXAMPLE")
    print("="*80)
    
    csv_path = "/Users/goshtasbshahriari/UFL Dropbox/PhD_Dissertation/Code/Data/SuperMarkets/Supermarket.csv"
    
    # Example 1: Load without geocoding (fast)
    print("\n1. Loading with fallback coordinates (fast):")
    stores = load_real_supermarkets(csv_path, use_geocoding=False)
    
    print(f"\n   First 3 stores:")
    for store in stores[:3]:
        print(f"      • {store['name']}")
        print(f"        Type: {store['provider_type'].value}")
        print(f"        Location: ({store['longitude']:.4f}, {store['latitude']:.4f})")
        print(f"        Capacity: {store['capacity']}")
    
    # Example 2: Get stores for model
    print("\n2. Getting stores for model:")
    grocery, corner = get_stores_for_model(csv_path, use_geocoding=False)
    
    print(f"   Grocery stores: {len(grocery)}")
    print(f"   Corner stores: {len(corner)}")
    
    # Example 3: Export with coordinates
    print("\n3. Exporting processed data:")
    loader = SupermarketDataLoader(csv_path, use_geocoding=False)
    stores = loader.get_store_data()
    output_path = "/Users/goshtasbshahriari/Desktop/Code/GeoMesa_Food_Access/supermarkets_with_coords.csv"
    loader.export_to_csv(stores, output_path)
    
    print("\n" + "="*80)
    print("DONE! Use these stores in baseline_scenario.py")
    print("="*80)

