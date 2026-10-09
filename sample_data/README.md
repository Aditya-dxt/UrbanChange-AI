# UrbanChange AI - Sample Dataset Pairs

This directory contains standardized, curated bi-temporal image pairs to test the UrbanChange AI change detection pipeline end-to-end without needing external Copernicus or satellite downloads.

---

## Included Pairs

### 1. `pairs/pair_01_construction/`
- **Description:** Rapid new residential urban development in a suburban area.
- **Sensor:** High-Resolution Optical / Aerial (0.5 m resolution).
- **Files:** `before.png`, `after.png`, `metadata.json`.
- **Expected Result:** `change_detected: true`, label: `construction`, multiple high-confidence structural change polygons.

### 2. `pairs/pair_02_deforestation/`
- **Description:** Clearing of dense green forest canopy for ground alteration.
- **Sensor:** High-Resolution Optical (0.5 m resolution).
- **Files:** `before.png`, `after.png`, `metadata.json`.
- **Expected Result:** `change_detected: true`, label: `vegetation_loss` / `deforestation`.

### 3. `pairs/pair_03_road_infra/`
- **Description:** New linear transportation highway corridor across rural terrain.
- **Sensor:** High-Resolution Optical / Drone (0.5 m resolution).
- **Files:** `before.png`, `after.png`, `metadata.json`.
- **Expected Result:** `change_detected: true`, label: `infrastructure`, high-aspect-ratio polygon.

### 4. `pairs/pair_04_no_change/`
- **Description:** Unchanged landscape with seasonal illumination variation.
- **Sensor:** High-Resolution Optical (0.5 m resolution).
- **Files:** `before.png`, `after.png`, `metadata.json`.
- **Expected Result:** `change_detected: false`, confidence: >0.90, `change_regions: []`.

### 5. `pairs/pair_05_sentinel2_geotiff/`
- **Description:** Real georeferenced 4-band Sentinel-2 L2A tile stack (`[B02, B03, B04, B08]`).
- **CRS:** EPSG:4326 (WGS84).
- **Resolution:** 10.0 m / pixel.
- **BBox:** `[80.32, 26.42, 80.36, 26.46]` (Kanpur, Uttar Pradesh).
- **Files:** `before.tif`, `after.tif`, `metadata.json`.
- **Expected Result:** `change_detected: true`, reprojected WGS84 GeoJSON polygons with area computed in square meters. Triggers full GIS sensitive zoning layer intersection analysis.

---

## How to Test

### Manual Web UI Upload
1. Navigate to the **Upload** page in the UI (`/upload`).
2. Select any pair from the **Load sample pair** preset dropdown (or drag and drop `before` and `after` images).
3. Click **Detect Change**.
4. The system uploads both images, triggers ML inference with the trained SatQuery Siamese U-Net, correlates with GIS zoning layers, synthesizes an evidence graph, and displays the result.

### Direct API Test via cURL
```bash
curl -X POST http://localhost:8000/api/investigations/upload \
  -F "before=@sample_data/pairs/pair_01_construction/before.png" \
  -F "after=@sample_data/pairs/pair_01_construction/after.png" \
  -F "historical_date=2023-03-10" \
  -F "current_date=2024-02-15"
```
