FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for rasterio and shapely
RUN sed -i 's|http://|https://|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true; sed -i 's|http://|https://|g' /etc/apt/sources.list 2>/dev/null || true
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU-only wheel (~150MB instead of 3GB GPU bundle)
RUN pip install --no-cache-dir torch==2.3.0 --index-url https://download.pytorch.org/whl/cpu

# Install application dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and scripts
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY weights/ ./weights/

# Ensure weights exist (copies local if mapped, otherwise downloads)
RUN python scripts/download_weights.py || true

ENV PORT=8002 \
    STORAGE_ROOT=/data/storage \
    ML_WEIGHTS_PATH=/app/weights/best_siamese_model.pth

EXPOSE 8002

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8002/ml/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
