"""
Configuration for GeoMesa Food Access ABM
=========================================

Data paths can be overridden via environment variables:
  GEOMESA_DATA_DIR     - Base directory for external data (shapefiles, etc.)
  GEOMESA_PROJECT_DIR  - Project root (default: directory containing this file)
"""

import os

_PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.environ.get("GEOMESA_DATA_DIR", os.path.join(os.path.dirname(_PROJECT_DIR), "Data"))
_PROJECT_DIR_OVERRIDE = os.environ.get("GEOMESA_PROJECT_DIR", _PROJECT_DIR)

def get_health_zone_shapefile() -> str:
    """Path to Health Zone 1 and 4 shapefile. Override via GEOMESA_DATA_DIR."""
    default = os.path.join(_DATA_DIR, "HealthZones1and4", "Health_Zones_1_and_4.shp")
    return os.environ.get("GEOMESA_HEALTH_ZONE_SHP", default)

def get_roads_shapefile() -> str:
    """Path to Jacksonville roads shapefile. Override via GEOMESA_DATA_DIR."""
    default = os.path.join(_DATA_DIR, "Roads", "All Jacksonville Roads.shp")
    return os.environ.get("GEOMESA_ROADS_SHP", default)

def get_project_dir() -> str:
    """Project root directory."""
    return _PROJECT_DIR_OVERRIDE

def get_supermarket_csv() -> str:
    """Path to curated supermarket CSV (in project)."""
    return os.path.join(get_project_dir(), "supermarkets_with_coords_CURATED.csv")

def get_census_data_dir() -> str:
    """Path to census data (duval_household_attributes.csv, ACS* files). Override via GEOMESA_CENSUS_DATA_DIR."""
    default = os.path.join(get_project_dir(), "census_data")
    return os.environ.get("GEOMESA_CENSUS_DATA_DIR", default)
