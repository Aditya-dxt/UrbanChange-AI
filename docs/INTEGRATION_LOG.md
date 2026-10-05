# UrbanChange AI — Module Integration Log

This document tracks integration readiness across all teammate domain services and the Person 4 backend hub.
Run `python backend/scripts/check_modules.py` to verify all modules against contract fixtures.

---

## Module Status Overview

| Module | Owner | Adapter Mode | Last Check Result | Open Issues / Next Steps |
|---|---|---|---|---|
| **Satellite** | Person 2 (Vaibhav) | `mock` / `http` | **PASS (MOCK)** | In mock mode: verified against `search_request.json`, `search_response.json`, `fetch_request.json`, `fetch_response.json`. On integration day: set `SATELLITE_ADAPTER=http` and ensure Copernicus credentials / STAC service is reachable at `SATELLITE_BASE_URL`. |
| **ML Change Detection** | Person 1 (Sonakshi) | `mock` / `http` | **PASS (MOCK)** | In mock mode: verified against `request.json` (`image_path`, `acquisition_date`) and `response.json`. Supports optional `mask_preview_path` and `mask_bounds`. Strict WGS84 GeoJSON Polygon validation active on `change_regions[].geometry`. |
| **GIS Analysis** | Person 3 (Zaina) | `mock` / `http` | **PASS (MOCK)** | In mock mode: verified against `request.json` and `response.json`. On integration day: ensure GIS service returns projected $m^2$ calculations and GeoJSON intersections. |
| **Intelligence Engine** | Person 6 (Varun) | `mock` / `http` / `python` | **PASS (MOCK)** | In mock mode: verified against `request.json` and `response.json`. Both `/intelligence/analyze` and `/intelligence/assistant` verified. Always returns `explanation.status = "requires_human_verification"`. |
| **Frontend Integration** | Person 5 (Yati) | `http` (REST) | **PASS** | API schemas and endpoints live on port 8000. `DetectionOut` exposes `change_mask_url`, `mask_preview_url`, `mask_preview_available`, and `bounds` (null-safe defaults). Rate limiting active on `/run`. |

---

## Check Log History

### Check: 2026-10-05 (Follow-up Fixes Verification)
- **Command:** `python backend/scripts/check_modules.py`
- **Result:**
  ```text
  UrbanChange AI — Module Integration Checker
  CONTRACT_VERSION: 0.1.0

  MODULE                    MODE        RESULT    DETAIL
  ------------------------------------------------------------------------------------------
  satellite                 mock        MOCK         
  ml                        mock        MOCK         
  gis                       mock        MOCK         
  intelligence              mock        MOCK         
  intelligence/assistant    mock        MOCK         

  All checked modules PASS. Ready for integration.
  ```
- **Changes verified:**
  1. ML request field alignment: `image_path` and `acquisition_date` verified across contract, schemas, and adapters. Backward-compatible aliases (`path`, `date`) handled in `ml_mapper.py`.
  2. Fixture lookup centralized in `MODULE_FIXTURES` with automatic disk presence verification on boot.
  3. ML mask preview support: `mask_preview_path` and `mask_bounds` (`[west, south, east, north]`) mapped into `DetectionOut` as `mask_preview_url` and `bounds`.
  4. Geometry validation: `change_regions[].geometry` validated as GeoJSON Polygon in WGS84 (EPSG:4326), `[longitude, latitude]`.
