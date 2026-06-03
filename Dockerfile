# Dockerfile — GeoMesa Food Access ABM (both dashboards), for Hugging Face Spaces
# ----------------------------------------------------------------------------
# Why Docker: it bakes the full geospatial stack (geopandas / fiona / shapely /
# pyproj via binary wheels) into a fixed image, so the "can't load my libraries"
# build failures you hit on Render's free tier cannot happen here.
#
# Serves the COMBINED app from app.py:
#   *  /          -> live interactive dashboard (live_enhanced_mesa_dash)
#   *  /results/  -> dissertation results dashboard (abm_dashboard_dissertation)
#
# Hugging Face Spaces note: create the Space with SDK = "docker" and make sure
# the Space README.md front-matter contains:
#       ---
#       title: Food Access ABM (Jacksonville HZ1)
#       sdk: docker
#       app_port: 7860
#       ---
# HF runs this container on its own servers (16 GB RAM, free) — your laptop does
# not need to stay on. The app listens on port 7860 (the HF default).
# ----------------------------------------------------------------------------
FROM python:3.10-slim

# Runtime libs: libgomp1 for numpy/scikit-learn OpenMP. Geospatial deps come
# from manylinux binary wheels, so no system GDAL/GEOS build is required.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLCONFIGDIR=/tmp/mplconfig \
    COMBINED_APP=1 \
    DASH_LIVE_PREFIX=/ \
    DASH_DISS_PREFIX=/results/ \
    PORT=7860

WORKDIR /app

# Install Python deps first (better layer caching). We install from the PINNED
# lock so the image reproduces the validated env exactly (Mesa 3.0.3, pyogrio
# engine) rather than the stale `mesa<3.0` in the root requirements.txt.
COPY requirements-lock.txt ./
RUN pip install --upgrade pip && pip install -r requirements-lock.txt

# App code + data (census_data/, scenarios_results/, CSVs are committed in the repo).
COPY . .

# Run as a non-root user (HF best practice) so the app can write outputs/caches.
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser
ENV HOME=/home/appuser

EXPOSE 7860

# Single worker (the live dashboard keeps simulation state in memory across the
# user's polling requests) + threads for concurrency. Long timeout so a heavy
# live run is never killed mid-request.
# Bind to $PORT if the platform sets one (Render/Railway), else 7860 (HF default).
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-7860} --workers 1 --threads 8 --timeout 600 app:application"]
