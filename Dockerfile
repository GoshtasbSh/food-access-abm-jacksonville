# Dockerfile — food-access ABM dashboards (Hugging Face Space, Docker SDK)
# ----------------------------------------------------------------------------
# Serves the combined app from app.py on port 7860:
#   /          -> live interactive simulation (live_enhanced_mesa_dash.py)
#   /results/  -> results dashboard for the manuscript build
#                 (abm_dashboard_dissertation.py)
#
# Local use:
#   docker build -t food-access-abm .
#   docker run -p 7860:7860 food-access-abm      # then open http://localhost:7860
# ----------------------------------------------------------------------------
FROM python:3.10-slim

# Runtime libs:
#   libgomp1  -> OpenMP for numpy/scikit-learn
#   libexpat1 -> provides libexpat.so.1, required by rasterio (pulled in by
#                mesa-geo). The geospatial wheels bundle GDAL/GEOS/PROJ but
#                still link the system libexpat, which python:3.10-slim omits.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        libexpat1 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLCONFIGDIR=/tmp/mplconfig \
    COMBINED_APP=1 \
    DASH_LIVE_PREFIX=/ \
    DASH_DISS_PREFIX=/results/ \
    PORT=7860

WORKDIR /app

# Install Python deps first (better layer caching), from the pinned lock file
# (the exact versions used for the manuscript: Mesa 3.0.3, Mesa-Geo 0.9.1).
COPY requirements-lock.txt ./
RUN pip install --upgrade pip && pip install -r requirements-lock.txt

# App code + input data + paper parameters and results (archive/ is excluded).
COPY . .

# Run as a non-root user (HF best practice) so the app can write outputs/caches.
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser
ENV HOME=/home/appuser

EXPOSE 7860

# Single worker + threads for concurrency. Long timeout so a heavy live run is
# never killed mid-request.
# IMPORTANT: --workers 1 is REQUIRED, not just preferred. Two reasons:
#   (1) the live dashboard keeps simulation state in memory across polling requests;
#   (2) the results dashboard's seed-set selector swaps a process-global dataset
#       under a thread lock — correct within one process, but multiple worker
#       PROCESSES would each hold independent state and could diverge.
# Bind to $PORT if the platform sets one (Render/Railway), else 7860 (HF default).
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-7860} --workers 1 --threads 8 --timeout 600 app:application"]
