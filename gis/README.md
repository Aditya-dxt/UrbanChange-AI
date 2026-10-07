# UrbanChange AI - GIS Engine (Role 3)

FastAPI microservice for spatial intersection analysis against authoritative zoning and environmental buffer layers.

## Features
- **Projected Area**: Strictly calculates area in $m^2$ via dynamic local UTM projection (never in degree coordinates).
- **Pluggable Sensitive Layers**: Dynamically discovers and loads all `.geojson` files in `gis/data/`.
- **Sample Demonstration Layer**: Includes clearly labeled `sample_sensitive_zones.geojson`.
- **Nearby Context**: Integrates OpenStreetMap features (canals, roadways, protected forests) with caching.
- **Contract Conforming**: Implements `POST /gis/analyze-change` (and `POST /gis/analyze`) adhering to `shared/schemas/external/gis_analyze_change_response.json`.

## Endpoints
- `POST /gis/analyze-change`: Computes `changed_area_m2`, `sensitive_intersections`, and GeoJSON overlays.
- `GET /health`: Healthcheck.

## Running Locally
```bash
uvicorn app.main:app --port 8003 --reload
```
