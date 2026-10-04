# UrbanChange AI — API Contracts

> **CONTRACT_VERSION = `0.1.0`**
> Increment the minor version when any field is added; increment the major version
> on any breaking removal or rename.  Update this file and re-run
> `python backend/scripts/export_schemas.py` after every change.

---

## Table of Contents
1. [Backend → Frontend endpoints](#1-backend--frontend-endpoints)
2. [What Satellite (Person 2) must implement](#2-satellite-module-contract)
3. [What ML (Person 1) must implement](#3-ml-module-contract)
4. [What GIS (Person 3) must implement](#4-gis-module-contract)
5. [What Intelligence (Person 6) must implement](#5-intelligence-module-contract)
6. [Fields needing confirmation](#6-fields-needing-confirmation)
7. [Assumed aliases table](#7-assumed-aliases)
8. [Error shape](#8-error-shape)

---

## 1. Backend → Frontend Endpoints

All paths are consumed ONLY by Person 5 (Frontend).

### POST `/api/investigations`
Create a new investigation (status = `pending`).

**Request**
```json
{
  "bbox": [77.1, 28.5, 77.3, 28.7],
  "historical_date": "2025-04-01",
  "current_date": "2026-01-01"
}
```
- `bbox`: `[west, south, east, north]` in WGS-84 (longitude, latitude)
- `current_date`: optional; backend uses today if omitted

**Response `201`**
```json
{ "id": "<uuid>", "status": "pending" }
```

---

### POST `/api/investigations/{id}/run`
Enqueue the full detection pipeline.

**Response `202`**
```json
{ "id": "<uuid>", "status": "running" }
```

---

### GET `/api/investigations/{id}`
Full investigation result. Fields are `null` until their stage completes.

**Response `200`** — see `shared/schemas/api/investigation_response.json` for the full JSON Schema.

Key fields:
| Field | Type | Notes |
|---|---|---|
| `id` | uuid | |
| `status` | string | `pending\|running\|completed\|partial\|failed` |
| `stage` | string\|null | Current or last pipeline stage name |
| `failed_stage` | string\|null | Set when `status=partial\|failed` |
| `bbox` | float[4] | `[west,south,east,north]` |
| `historical_date` | date | |
| `current_date` | date\|null | |
| `observations[]` | array | Each has `scene_id`, `sensor`, `acquisition_date`, `cloud_cover`, `crs`, `resolution`, `image_url`, `preview_url`, `preview_available`, `bounds`, `role` |
| `detection` | object\|null | `change_detected`, `confidence`, `changed_area_pixels`, `change_mask_url`, `change_regions`, `classification`, `model_version` |
| `gis` | object\|null | `changed_area_m2`, `sensitive_intersections`, `overlap_percentages`, `nearby_features`, `distances`, `geojson` |
| `fingerprint` | object\|null | `fingerprint_id`, `change_type`, `confidence`, `temporal_behavior`, … |
| `temporal_reconstruction` | object\|null | `events[]`, `first_persistent_interval`, `summary` |
| `evidence[]` | array | `id`, `evidence_type`, `source_reference`, `metadata` |
| `explanation` | object\|null | `text`, `evidence_ids`, `status` |
| `satellite_failure_reason` | string\|null | Set when satellite found no suitable imagery |

---

### GET `/api/investigations/{id}/timeline`
```json
{
  "investigation_id": "<uuid>",
  "events": [...],
  "observations": [...]
}
```

---

### POST `/api/investigations/{id}/assistant`
**Request:** `{ "question": "What changed in this area?" }`

**Response `200`**
```json
{
  "id": "<uuid>",
  "investigation_id": "<uuid>",
  "role": "assistant",
  "answer": "Significant construction activity was detected…",
  "evidence_ids": ["ev_001"],
  "uncertainty_notes": "Requires human verification before legal conclusions.",
  "status": "requires_human_verification",
  "created_at": "2026-10-04T07:00:00Z"
}
```

---

### GET `/api/assets/{path}`
Serves files from within `STORAGE_ROOT`.

- Path traversal (`../`) returns `400 PATH_TRAVERSAL`
- Outside `STORAGE_ROOT` returns `400 PATH_TRAVERSAL`
- Whitelisted content types: `image/png`, `image/jpeg`, `image/tiff`, `application/json`, `application/geo+json`

---

### GET `/health`
```json
{ "status": "ok", "version": "0.1.0", "contract_version": "0.1.0", "timestamp": "…" }
```

### GET `/health/ready`
```json
{
  "ready": true,
  "database": { "reachable": true },
  "modules": {
    "satellite":    { "mode": "mock", "reachable": true },
    "ml":           { "mode": "mock", "reachable": true },
    "gis":          { "mode": "mock", "reachable": true },
    "intelligence": { "mode": "mock", "reachable": true }
  },
  "timestamp": "…"
}
```
Returns `503` if the database is unreachable.

---

## 2. Satellite Module Contract

**Owner:** Person 2  
**Adapter config:** `SATELLITE_ADAPTER=http`, `SATELLITE_BASE_URL`, `SATELLITE_TIMEOUT_SECONDS`

### POST `/satellite/search`

**Request (sent by backend):**
```json
{
  "bbox": [77.1, 28.5, 77.3, 28.7],
  "historical_date": "2025-04-01",
  "current_date": "2026-01-01",
  "max_cloud_cover": 30.0,
  "max_observations": 2
}
```

**Response (must return):**
```json
{
  "success": true,
  "reason": null,
  "scenes": [
    {
      "scene_id": "S2A_MSIL2A_20250414…",
      "acquisition_date": "2025-04-14",
      "cloud_cover": 8.3,
      "sensor": "Sentinel-2",
      "crs": "EPSG:32643",
      "resolution": 10.0,
      "bounds": [77.09, 28.49, 77.31, 28.71]
    }
  ]
}
```

**No-image case** — return `success: false`, not an HTTP error:
```json
{ "success": false, "reason": "no_suitable_image: all scenes exceed cloud cover threshold", "scenes": [] }
```

### POST `/satellite/fetch`

**Request (sent by backend):**
```json
{ "scene_id": "S2A_MSIL2A_…", "bbox": [77.1, 28.5, 77.3, 28.7] }
```

**Response (must return):**
```json
{
  "success": true,
  "before": { "scene_id": "…", "acquisition_date": "2025-04-14", "sensor": "Sentinel-2",
              "image_path": "sentinel2/2025/before.tif", "preview_path": "sentinel2/2025/before_preview.png",
              "cloud_cover": 8.3, "crs": "EPSG:32643", "resolution": 10.0, "bounds": […] },
  "after":  { … },
  "intermediate": []
}
```

> Full JSON Schema: `shared/schemas/external/satellite_fetch_response.json`
> Example fixtures: `backend/tests/contracts/satellite/`

---

## 3. ML Module Contract

**Owner:** Person 1  
**Adapter config:** `ML_ADAPTER=http`, `ML_BASE_URL`, `ML_TIMEOUT_SECONDS`

### POST `/ml/detect-change`

**Request (sent by backend):**
```json
{
  "before": { "path": "sentinel2/2025/before.tif", "date": "2025-04-14", "sensor": "Sentinel-2", "crs": "EPSG:32643", "resolution": 10.0 },
  "after":  { "path": "sentinel2/2026/after.tif",  "date": "2026-01-18", "sensor": "Sentinel-2", "crs": "EPSG:32643", "resolution": 10.0 },
  "investigation_id": "<uuid>"
}
```

**Response (must return):**
```json
{
  "change_detected": true,
  "confidence": 0.94,
  "changed_area_pixels": 38420,
  "change_mask_path": "outputs/masks/investigation_001.tif",
  "change_regions": [ { "geometry": { "type": "Polygon", "coordinates": […] }, "area_pixels": 38420, "confidence": 0.94, "label": "construction" } ],
  "classification": { "label": "construction", "confidence": 0.91 },
  "model_version": "siamese-unet-attention-v1",
  "preprocessing_version": "v1.0",
  "threshold": 0.5
}
```

> Alias accepted by mapper: `mask_path` → `change_mask_path`
> Full JSON Schema: `shared/schemas/external/ml_detect_change_response.json`
> Example fixtures: `backend/tests/contracts/ml/`

---

## 4. GIS Module Contract

**Owner:** Person 3  
**Adapter config:** `GIS_ADAPTER=http`, `GIS_BASE_URL`, `GIS_TIMEOUT_SECONDS`

### POST `/gis/analyze-change`

**Request (sent by backend):**
```json
{
  "change_regions": [ { "type": "Feature", "geometry": { … }, "properties": { "confidence": 0.94 } } ],
  "bbox": [77.1, 28.5, 77.3, 28.7],
  "context_layer_ids": ["protected_forest", "water_bodies"],
  "investigation_id": "<uuid>"
}
```

**Response (must return):**
```json
{
  "changed_area_m2": 3842.0,
  "sensitive_intersections": [ { "layer_name": "protected_forest", "layer_id": "pf_001", "overlap_pct": 64.0, "geometry": { … } } ],
  "overlap_percentages": { "protected_forest": 64.0, "water_bodies": 0.0 },
  "nearby_features": [ { "feature_type": "road", "name": "NH-48", "distance_m": 120.5 } ],
  "geojson": { "type": "FeatureCollection", "features": [] },
  "layer_versions": { "protected_forest": "2024-Q4" },
  "distances": { "road": 120.5 }
}
```

> Full JSON Schema: `shared/schemas/external/gis_analyze_change_response.json`
> Example fixtures: `backend/tests/contracts/gis/`

---

## 5. Intelligence Module Contract

**Owner:** Person 6  
**Adapter config:** `INTELLIGENCE_ADAPTER=mock|http|python`  
For `http`: `INTELLIGENCE_BASE_URL`, `INTELLIGENCE_TIMEOUT_SECONDS`  
For `python`: `INTELLIGENCE_PYTHON_ENTRYPOINT=package.module:function`

### Interface (HTTP or Python callable — both accepted)

**Request payload (sent by backend):**
```json
{
  "investigation_id": "<uuid>",
  "bbox": [77.1, 28.5, 77.3, 28.7],
  "historical_date": "2025-04-14",
  "current_date": "2026-01-18",
  "observations": [ … ],
  "detection": { … },
  "gis": { … }
}
```

**Response (must return):**
```json
{
  "fingerprint": {
    "fingerprint_id": "UC-2026-A91F",
    "change_type": "construction",
    "changed_area_m2": 3842.0,
    "confidence": 0.94,
    "temporal_behavior": "progressive",
    "sensitive_overlap": { "percentage": 64.0, "layers": ["protected_forest"] },
    "first_observed": "2025-04-14",
    "model_version": "siamese-unet-attention-v1"
  },
  "temporal_reconstruction": {
    "events": [ { "observation_date": "2025-04-14", "event_type": "ground_disturbance", "confidence": 0.81, "area_delta_m2": 1200.0 } ],
    "first_persistent_interval": "2025-04-14/2026-01-18",
    "summary": "Progressive construction observed…"
  },
  "evidence": [ { "evidence_type": "satellite_observation", "source_reference": "scene_id:…", "metadata": {} } ],
  "evidence_graph": { … },
  "explanation": {
    "text": "Significant construction activity was detected…",
    "evidence_ids": ["ev_001"],
    "status": "requires_human_verification"
  }
}
```

> Full JSON Schema: `shared/schemas/external/intelligence_response.json`
> Example fixtures: `backend/tests/contracts/intelligence/`

### Assistant endpoint

The backend proxies `POST /api/investigations/{id}/assistant` to Intelligence.

**Request:** `{ "investigation_id": "<uuid>", "question": "…", "evidence_ids": [] }`

**Response:**
```json
{ "answer": "…", "evidence_ids": ["ev_001"], "uncertainty_notes": "…", "status": "requires_human_verification" }
```

---

## 6. Fields Needing Confirmation

These fields were **inferred** from the README or project context.
Each is marked `# ASSUMED: confirm with owner` in the schema file.

| # | Module | Field | Assumed shape | Confirm with |
|---|---|---|---|---|
| 1 | Satellite | `bounds` on SceneCandidate | `[west, south, east, north]` float array | Person 2 |
| 2 | Satellite | `preview_path` on FetchedScene | relative path to PNG/JPEG preview | Person 2 |
| 3 | Satellite | `image_path` alias | also accepts `file_path` | Person 2 |
| 4 | ML | `change_mask_path` alias | also accepts `mask_path` | Person 1 |
| 5 | ML | `preprocessing_version` | string, e.g. `"v1.0"` | Person 1 |
| 6 | ML | `threshold` | float 0–1 used for mask generation | Person 1 |
| 7 | ML | `change_regions[].geometry` | GeoJSON Polygon in lon/lat | Person 1 |
| 8 | GIS | `layer_versions` | dict of layer_name → version string | Person 3 |
| 9 | GIS | `distances` | dict of feature_type → nearest dist (m) | Person 3 |
| 10 | GIS | `nearby_features[].geometry` | GeoJSON Point or null | Person 3 |
| 11 | Intelligence | Interface type | HTTP vs Python callable — **not fixed** | Person 6 |
| 12 | Intelligence | `temporal_reconstruction.first_persistent_interval` | ISO 8601 interval string | Person 6 |
| 13 | Intelligence | `temporal_event.area_delta_m2` | area change at each step | Person 6 |
| 14 | Intelligence | `evidence_graph` | structure of graph object | Person 6 |
| 15 | All modules | `browser preview image` | PNG/JPEG preview of GeoTIFF output | All |

> Until confirmed, the backend returns `preview_url: null` and `preview_available: false`
> when no `preview_path` is provided.

---

## 7. Assumed Aliases

Aliases are resolved **inside the mapper only** — nothing else in the backend knows about them.

| Module | Canonical field | Also accepted |
|---|---|---|
| Satellite | `cloud_cover` | `cloud_score` |
| Satellite | `image_path` | `file_path` |
| ML | `change_mask_path` | `mask_path` |

---

## 8. Error Shape

All error responses from this backend have the form:
```json
{
  "code":       "INVESTIGATION_NOT_FOUND",
  "message":    "Investigation '…' does not exist.",
  "reason":     null,
  "request_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

| Code | HTTP status | Meaning |
|---|---|---|
| `HTTP_404` | 404 | Resource not found |
| `INVESTIGATION_NOT_FOUND` | 404 | Investigation ID unknown |
| `ASSET_NOT_FOUND` | 404 | File not in storage |
| `PATH_TRAVERSAL` | 400 | Asset path outside STORAGE_ROOT |
| `UNSUPPORTED_MEDIA_TYPE` | 415 | Content-type not whitelisted |
| `VALIDATION_ERROR` | 422 | Request body/params invalid |
| `MAPPER_ERROR` | 502 | Module returned payload missing a required field |
| `ADAPTER_ERROR` | 502 | Module call failed (network/timeout/non-2xx) |
| `HTTP_5xx` | 5xx | Unexpected server error |
