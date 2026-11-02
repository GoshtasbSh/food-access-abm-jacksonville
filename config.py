"""
Configuration for GeoMesa Food Access ABM
=========================================

All defaults point at files shipped in this repository, so a fresh clone
reproduces the manuscript results with no further setup. Overrides:
  GEOMESA_DATA_DIR         - external GIS directory holding HealthZones1and4/
  GEOMESA_HEALTH_ZONE_SHP  - explicit Health Zone shapefile
  GEOMESA_SUPERMARKET_CSV  - alternative store inventory
  GEOMESA_CENSUS_DATA_DIR  - alternative census directory
  GEOMESA_PROJECT_DIR      - project root (default: directory of this file)
"""

import os

_PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.environ.get("GEOMESA_DATA_DIR", os.path.join(os.path.dirname(_PROJECT_DIR), "Data"))
# Health Zone 1 boundary shipped with the repository (byte-identical to the
# file used for the manuscript runs).
_BUNDLED_HZ_SHP = os.path.join(_PROJECT_DIR, "geodata", "HealthZones1and4",
                               "Health_Zones_1_and_4.shp")
_PROJECT_DIR_OVERRIDE = os.environ.get("GEOMESA_PROJECT_DIR", _PROJECT_DIR)

def get_health_zone_shapefile() -> str:
    """Path to Health Zone 1 and 4 shapefile.

    Default: the copy bundled under geodata/. GEOMESA_DATA_DIR (external GIS
    directory) or GEOMESA_HEALTH_ZONE_SHP (explicit file) override it."""
    if "GEOMESA_HEALTH_ZONE_SHP" in os.environ:
        return os.environ["GEOMESA_HEALTH_ZONE_SHP"]
    external = os.path.join(_DATA_DIR, "HealthZones1and4", "Health_Zones_1_and_4.shp")
    if "GEOMESA_DATA_DIR" in os.environ or not os.path.isfile(_BUNDLED_HZ_SHP):
        return external
    return _BUNDLED_HZ_SHP

def get_roads_shapefile() -> str:
    """Path to Jacksonville roads shapefile (recorded in the run config only;
    the model does not read it). Override via GEOMESA_DATA_DIR."""
    default = os.path.join(_DATA_DIR, "Roads", "All Jacksonville Roads.shp")
    return os.environ.get("GEOMESA_ROADS_SHP", default)

def get_project_dir() -> str:
    """Project root directory."""
    return _PROJECT_DIR_OVERRIDE

def get_supermarket_csv() -> str:
    """Path to the baseline store inventory.

    Default: store_FINAL_6g_11c.csv (6 grocery stores + 11 corner stores from
    the USDA SNAP Retailer Locator, clipped to Health Zone 1), the inventory
    used for every result in the manuscript. Override via
    GEOMESA_SUPERMARKET_CSV."""
    default = os.path.join(get_project_dir(), "store_FINAL_6g_11c.csv")
    return os.environ.get("GEOMESA_SUPERMARKET_CSV", default)

def get_census_data_dir() -> str:
    """Path to census data (duval_household_attributes.csv, ACS* files). Override via GEOMESA_CENSUS_DATA_DIR."""
    default = os.path.join(get_project_dir(), "census_data")
    return os.environ.get("GEOMESA_CENSUS_DATA_DIR", default)
