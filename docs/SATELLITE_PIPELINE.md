# Satellite Pipeline Documentation (Role 2 — Vaibhav)

## Overview
The Satellite Acquisition and Preprocessing service is responsible for discovering, filtering, windowing, and coregistering Copernicus Sentinel-2 Level-2A surface reflectance imagery for any bounding box and date pair.

---

## 1. Catalog Search & Selection Rules
- **Data Sources:**
  - Copernicus Data Space Ecosystem (CDSE) STAC API (`https://catalogue.dataspace.copernicus.eu/stac/`)
  - AWS Open Data Earth Search STAC API (`https://earth-search.aws.element84.com/v1`)
  - Fallback: Deterministic synthetic orbital pass generator for offline demonstrations
- **Bounding Box Convention:**
  - WGS84 (EPSG:4326) coordinates: `[west, south, east, north]`
- **Cloud & Quality Filtering:**
  - Hard cloud cover threshold: configurable via `max_cloud_cover_percent` (default 20%).
  - Scene ranking algorithm:
    $$\text{Score} = \alpha \cdot |\text{Days from target}| + \beta \cdot (\text{Cloud Cover \%})$$
  - "Latest suitable observation" rule: prioritizes scenes with valid surface reflectance within a $\pm 30$-day temporal window.

---

## 2. Windowed COG Streaming & Preprocessing
To eliminate multi-gigabyte ZIP downloads, the pipeline uses Cloud-Optimized GeoTIFF (COG) windowed reads:
1. **Windowed Read:** Reads only the bounding box pixel window from cloud-hosted COG assets (B02, B03, B04, B08, B11, B12).
2. **Grid Reprojection & Resampling:**
   - Reprojects the observation to a shared projected UTM grid using bilinear interpolation.
   - Coregisters both before and after observations onto the exact same pixel dimensions (typically $512 \times 512$ or $1024 \times 1024$).
3. **Radiometric Normalization:**
   - Converts Level-2A DN values to Surface Reflectance (SR) floats: $SR = DN / 10000.0$.
   - Normalizes contrast and generates 8-bit RGB preview PNG assets for UI presentation.
4. **Asset Storage:**
   - Writes GeoTIFFs and preview PNGs to the shared container volume at `/data/storage/satellite/{obs_id}/`.

---

## 3. Endpoints & API Contract

### `POST /satellite/search`
**Request:**
```json
{
  "bbox": [80.30, 26.40, 80.40, 26.50],
  "start_date": "2023-01-01",
  "end_date": "2023-03-01",
  "max_cloud_cover_percent": 20.0
}
```
**Response:**
```json
{
  "total_found": 3,
  "scenes": [
    {
      "scene_id": "S2A_MSIL2A_20230115T051051_N0509_R062_T44RKR_20230115T072944",
      "acquisition_date": "2023-01-15T05:10:51Z",
      "cloud_cover_percent": 3.42,
      "preview_url": "https://...",
      "bbox": [80.30, 26.40, 80.40, 26.50]
    }
  ]
}
```

### `POST /satellite/fetch`
Fetches and coregisters the before and after rasters for the investigation.
**Request:**
```json
{
  "bbox": [80.30, 26.40, 80.40, 26.50],
  "baseline_date": "2023-01-15",
  "target_date": "2024-01-15"
}
```
**Response:**
```json
{
  "baseline_image_path": "/data/storage/satellite/baseline_20230115.tif",
  "target_image_path": "/data/storage/satellite/target_20240115.tif",
  "crs": "EPSG:32644",
  "resolution_meters": 10.0,
  "metadata": {
    "baseline_scene_id": "S2A_MSIL2A_20230115T051051",
    "target_scene_id": "S2B_MSIL2A_20240115T051059",
    "baseline_cloud_cover": 2.1,
    "target_cloud_cover": 4.5
  }
}
```
