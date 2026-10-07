# GIS Engine Documentation (Role 3 — Zaina)

## Overview
The GIS Engine provides high-precision spatial analysis for detected urban change polygons. It projects spatial geometries into local cartographic projections to compute true metric areas ($m^2$), calculates spatial intersections against sensitive zones, and enriches changes with contextual land use data.

---

## 1. Projected Area Calculation ($m^2$)
- **Geodetic vs Projected Rules:**
  Calculations are **never** performed on unprojected angular degree units (WGS84 EPSG:4326).
- **Dynamic UTM Reprojection:**
  The engine dynamically determines the optimal UTM zone based on the centroid longitude:
  $$\text{Zone} = \lfloor(\text{longitude} + 180) / 6\rfloor + 1$$
  $$\text{EPSG} = 32600 + \text{Zone}\ (\text{Northern Hemisphere})\quad\text{or}\quad 32700 + \text{Zone}\ (\text{Southern Hemisphere})$$
- Geometries are transformed using `pyproj.Transformer` and area is computed via `shapely.geometry.Polygon.area`.

---

## 2. Sensitive Zone Overlays
- **Data Layers:**
  Pluggable GeoJSON layers loaded from `/gis/data/*.geojson`.
  - Eco-Sensitive Zones (ESZ)
  - Floodplains and River Buffer Zones
  - Forest and Protected Wildlife Reserves
  - Demo Sample Layer: `gis/data/sample_sensitive_zones.geojson`
- **Intersection Metrics:**
  For each detected change polygon and sensitive zone pair:
  - `overlap_area_m2`: Exact intersection area in square meters.
  - `overlap_percent`: Intersection area divided by total change polygon area $\times 100$.
  - `layer_name` and `authority_source`: Source reference.
- **Statutory Neutrality Policy:**
  The engine reports objective geometric overlap facts only. It never asserts illegality or ownership titles.

---

## 3. Contextual Data
- **ESA WorldCover:** Land cover classification (Tree cover, Shrubland, Grassland, Cropland, Built-up, Bare / sparse vegetation, Water).
- **OpenStreetMap (OSM) via Overpass API:**
  - Queries nearby highways, waterways, and industrial zones within a 500m buffer.
  - Responses are cached locally to reduce API roundtrips.

---

## 4. Endpoints & API Contract

### `POST /gis/analyze-change` (Alias: `POST /gis/analyze`)
**Request:**
```json
{
  "change_regions": [
    {
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[77.10, 28.60], [77.12, 28.60], [77.12, 28.62], [77.10, 28.62], [77.10, 28.60]]]
      },
      "label": "construction",
      "confidence": 0.88
    }
  ],
  "aoi": [77.10, 28.60, 77.20, 28.70]
}
```
**Response:**
```json
{
  "changed_area_m2": 42150.75,
  "sensitive_intersections": [
    {
      "layer_name": "Eco-Sensitive Buffer Zone",
      "overlap_area_m2": 12400.5,
      "overlap_percent": 29.42,
      "authority_source": "State Environmental Authority"
    }
  ],
  "nearby_features": [
    {
      "name": "State Highway 14",
      "category": "transportation",
      "distance_meters": 180.0
    }
  ],
  "context_layers": {
    "worldcover_primary_class": "Built-up"
  }
}
```
