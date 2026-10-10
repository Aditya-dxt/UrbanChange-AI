FROM python:3.10-slim

WORKDIR /app

# Rewrite debian repositories to HTTPS to avoid plain HTTP mirror connection timeouts
RUN sed -i 's|http://|https://|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true; sed -i 's|http://|https://|g' /etc/apt/sources.list 2>/dev/null || true

# Install curl for healthchecks and libexpat1 for rasterio
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libexpat1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
