#!/usr/bin/env bash
set -e

# Install system dependencies for geopandas/fiona
apt-get update && apt-get install -y gdal-bin libgdal-dev || true

pip install --upgrade pip
pip install -r requirements.txt
