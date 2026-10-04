# UrbanChange AI — Backend

> **Person 4 owns this folder.**
> Everyone else reads it; no-one edits it without raising it with Person 4 first.

> **Build status:** All 9 Phases complete. Full backend orchestration, DB models + migrations, mock + HTTP + python adapters, REST API routers, 128 automated tests passing, Docker Compose deployment ready.
> _Last updated: Phase 9 — Production Docker Deployment & Root Configuration_

> [!NOTE]
> **Mock Data Notice:** **YES, mock data is currently used by default.** All four domain adapters (`SATELLITE_ADAPTER`, `ML_ADAPTER`, `GIS_ADAPTER`, `INTELLIGENCE_ADAPTER`) default to `"mock"` mode and serve high-fidelity synthetic fixture data. No external GPU, Copernicus satellite account, or live GIS server is required to develop, run, test, or integrate with the frontend. See [How to plug in your real module](#5-how-to-plug-in-your-real-module-integration-day) to switch any adapter from mock to live HTTP/Python.

---

## Table of Contents

1. [What this service does](#1-what-this-service-does)
2. [Quick-start (all-mock mode)](#2-quick-start-all-mock-mode)
3. [Environment variables — full reference](#3-environment-variables--full-reference)
4. [How the adapter system works](#4-how-the-adapter-system-works)
5. [How to plug in your real module (integration day)](#5-how-to-plug-in-your-real-module-integration-day)
   - [Person 1 — ML](#person-1--ml)
   - [Person 2 — Satellite](#person-2--satellite)
   - [Person 3 — GIS](#person-3--gis)
   - [Person 6 — Intelligence](#person-6--intelligence)
6. [What each module must return (contract summary)](#6-what-each-module-must-return-contract-summary)
7. [Shared schemas — JSON Schema files for your module](#7-shared-schemas--json-schema-files-for-your-module)
8. [Pipeline stages and status machine](#8-pipeline-stages-and-status-machine)
9. [Database](#9-database)
10. [Running tests](#10-running-tests)
11. [Integration Checker — check_modules.py](#11-integration-checker--check_modulespy)
12. [Docker](#12-docker)
13. [Integration-day checklist](#13-integration-day-checklist)
14. [FAQ / Troubleshooting](#14-faq--troubleshooting)

---

## 1. What this service does

The backend is the **integration hub** for all five other modules.
It exposes a single REST API to the frontend (Person 5) and orchestrates:

```
POST /api/investigations       ← Frontend triggers an investigation
         │
         ▼
POST /satellite/search         ← Satellite service (Person 2)
POST /satellite/fetch
         │
         ▼
POST /ml/detect-change         ← ML service (Person 1)
         │
         ▼
POST /gis/analyze-change       ← GIS service (Person 3)
         │
         ▼
Intelligence module            ← Intelligence service (Person 6)
  fingerprint + temporal
  evidence graph + explanation
         │
         ▼
GET  /api/investigations/{id}  ← Frontend polls result
```

The backend **never** touches model internals, GIS math, Copernicus APIs, or LLM code.
Its only job is to call your module, validate the response against the contract,
translate it into the internal schema, persist it, and serve it to the frontend.

---

## 2. Quick-start (all-mock mode)

> **Requires:** Python 3.10+, a running PostgreSQL+PostGIS instance.
> All four modules run as in-process mocks by default — no other services needed.

```bash
# 1. Clone and enter the repo
git clone https://github.com/Aditya-dxt/UrbanChange-AI.git
cd UrbanChange-AI/backend

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy the example env file and edit it
cp ../.env.example .env
# Open .env and at minimum set DATABASE_URL to point to your Postgres instance

# 5. Run Alembic migrations (creates PostGIS extension + all tables)
alembic upgrade head

# 6. Start the API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health:** http://localhost:8000/health
- **Readiness:** http://localhost:8000/health/ready

All adapters default to `mock` — you get realistic fixture responses immediately,
no satellites, no GPUs, no LLMs required.

---

## 3. Environment variables — full reference

Copy `.env.example` to `.env` and edit. **Never commit `.env`.**

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `development` | `development \| staging \| production` |
| `SECRET_KEY` | `change-me-in-production` | App secret (change in prod) |
| `LOG_LEVEL` | `INFO` | `DEBUG \| INFO \| WARNING \| ERROR` |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed origins |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:password@localhost:5432/urbanchange` | Async SQLAlchemy URL |
| `STORAGE_ROOT` | `/data/storage` | **Shared file root.** Modules write here; backend reads from here. All asset paths are relative to this root. |
| **Adapter modes** | | |
| `SATELLITE_ADAPTER` | `mock` | `mock \| http` |
| `ML_ADAPTER` | `mock` | `mock \| http` |
| `GIS_ADAPTER` | `mock` | `mock \| http` |
| `INTELLIGENCE_ADAPTER` | `mock` | `mock \| http \| python` |
| **HTTP adapter URLs** | | *(only used when mode = http)* |
| `SATELLITE_BASE_URL` | `http://localhost:8001` | Your satellite service URL |
| `SATELLITE_TIMEOUT_SECONDS` | `30` | |
| `ML_BASE_URL` | `http://localhost:8002` | Your ML service URL |
| `ML_TIMEOUT_SECONDS` | `60` | |
| `GIS_BASE_URL` | `http://localhost:8003` | Your GIS service URL |
| `GIS_TIMEOUT_SECONDS` | `30` | |
| `INTELLIGENCE_BASE_URL` | `http://localhost:8004` | Your intelligence service URL |
| `INTELLIGENCE_TIMEOUT_SECONDS` | `60` | |
| **Python module adapter** | | *(Intelligence only)* |
| `INTELLIGENCE_PYTHON_ENTRYPOINT` | *(empty)* | e.g. `intelligence.engine:run` — the function the backend will call directly |
| **Pipeline** | | |
| `CONTEXT_LAYER_IDS` | *(empty)* | Comma-separated GIS context layer IDs sent to GIS adapter |
| `TEMPORAL_MAX_OBSERVATIONS` | `0` | `0` = MVP two-date mode; `>0` enables intermediate temporal observations |
| `RUN_RATE_LIMIT_PER_MINUTE` | `10` | Max /run calls per minute per IP |

---

## 4. How the adapter system works

```
app/adapters/
  base.py           ← Abstract classes (SatelliteAdapter, MLAdapter, GISAdapter, IntelligenceAdapter)
  factory.py        ← Reads env vars → returns the right adapter instance
  mock/             ← Realistic fixture-driven mocks for all four modules
  http/             ← httpx clients (timeouts + retries) for all four modules
  python_module/    ← Loads INTELLIGENCE_PYTHON_ENTRYPOINT via importlib (Intelligence only)
  mappers/          ← ONE mapper per module: the ONLY place external ↔ internal translation happens
    satellite_mapper.py
    ml_mapper.py
    gis_mapper.py
    intelligence_mapper.py
```

### The isolation guarantee

```
Orchestrator
    │  calls abstract adapter interface only
    ▼
AdapterBase  (base.py)
    │  implemented by:
    ├── MockSatelliteAdapter   (fixtures)
    ├── HttpSatelliteAdapter   (httpx)
    └── ... etc.
         │
         │  raw response (dict)
         ▼
    satellite_mapper.py
         │  translates external field names → internal schema
         │  resolves aliases: cloud_score → cloud_cover, file_path → image_path
         │  logs unknown fields at DEBUG
         │  raises MapperError(module, stage, missing_field) on required-field absence
         ▼
    SatelliteStageResult  (internal/satellite.py)
         │
         ▼
    Database (raw_payload JSONB stored alongside mapped result)
```

**Switching a module from mock → real requires:**
1. One env var change: `SATELLITE_ADAPTER=http`
2. If their field names differ from the contract: **at most one mapper file change** (`satellite_mapper.py`)
3. Nothing else in the backend changes.

---

## 5. How to plug in your real module (integration day)

### Person 1 — ML

**You expose:** `POST /ml/detect-change`

**Backend sends you:**
```json
{
  "before": { "path": "sentinel2/2025/before.tif", "date": "2025-04-14", "sensor": "Sentinel-2", "crs": "EPSG:32643", "resolution": 10.0 },
  "after":  { "path": "sentinel2/2026/after.tif",  "date": "2026-01-18", "sensor": "Sentinel-2", "crs": "EPSG:32643", "resolution": 10.0 },
  "investigation_id": "<uuid>"
}
```

**You must return** (minimum required fields):
```json
{
  "change_detected": true,
  "confidence": 0.94,
  "changed_area_pixels": 38420,
  "change_mask_path": "outputs/masks/investigation_001.tif",
  "change_regions": [ ... ],
  "classification": { "label": "construction", "confidence": 0.91 },
  "model_version": "siamese-unet-attention-v1"
}
```

**Integration steps:**
1. Set `ML_ADAPTER=http` and `ML_BASE_URL=http://<your-host>:8002` in `.env`
2. Run `python scripts/check_modules.py` — it will call your endpoint with the example payload and print a PASS/FAIL table
3. If any field names differ from the contract, tell Person 4 — they update `ml_mapper.py` only

> **Alias:** The backend also accepts `mask_path` as an alias for `change_mask_path`.
> Full schema: `shared/schemas/external/ml_detect_change_response.json`
> Full example: `backend/tests/contracts/ml/response.json`

---

### Person 2 — Satellite

**You expose:** `POST /satellite/search` and `POST /satellite/fetch`

**Backend sends to /satellite/search:**
```json
{
  "bbox": [77.1, 28.5, 77.3, 28.7],
  "historical_date": "2025-04-01",
  "current_date": "2026-01-01",
  "max_cloud_cover": 30.0,
  "max_observations": 2
}
```

**You must return from /satellite/search:**
```json
{
  "success": true,
  "scenes": [
    { "scene_id": "S2A_…", "acquisition_date": "2025-04-14", "cloud_cover": 8.3, "sensor": "Sentinel-2", "crs": "EPSG:32643", "resolution": 10.0, "bounds": [77.09, 28.49, 77.31, 28.71] }
  ]
}
```

**When no suitable image exists — return `success: false`, NOT an HTTP error:**
```json
{ "success": false, "reason": "no_suitable_image: all scenes exceed cloud threshold", "scenes": [] }
```

**You must return from /satellite/fetch:**
```json
{
  "success": true,
  "before": { "scene_id": "…", "acquisition_date": "2025-04-14", "image_path": "sentinel2/2025/before.tif", "preview_path": "sentinel2/2025/before_preview.png", "cloud_cover": 8.3, "crs": "EPSG:32643", "resolution": 10.0, "bounds": […] },
  "after":  { … },
  "intermediate": []
}
```

**Important:**
- Paths in `image_path` and `preview_path` must be **relative to `STORAGE_ROOT`** or absolute paths that start with `STORAGE_ROOT`.
- If no browser-friendly preview is available, omit `preview_path` — the backend returns `preview_url: null` to the frontend (this is expected).
- The `bounds` field `[west, south, east, north]` is used for map overlays. If you don't provide it, the investigation bbox is used instead.

> **Alias:** The backend also accepts `cloud_score` (alias for `cloud_cover`) and `file_path` (alias for `image_path`).
> Full schema: `shared/schemas/external/satellite_fetch_response.json`
> Full example: `backend/tests/contracts/satellite/fetch_response.json`

**Integration steps:**
1. Set `SATELLITE_ADAPTER=http` and `SATELLITE_BASE_URL=http://<your-host>:8001`
2. Run `python scripts/check_modules.py`

---

### Person 3 — GIS

**You expose:** `POST /gis/analyze-change`

**Backend sends you:**
```json
{
  "change_regions": [ { "type": "Feature", "geometry": { … }, "properties": { "confidence": 0.94 } } ],
  "bbox": [77.1, 28.5, 77.3, 28.7],
  "context_layer_ids": ["protected_forest", "water_bodies"],
  "investigation_id": "<uuid>"
}
```

**You must return:**
```json
{
  "changed_area_m2": 3842.0,
  "sensitive_intersections": [
    { "layer_name": "protected_forest", "overlap_pct": 64.0 }
  ],
  "overlap_percentages": { "protected_forest": 64.0, "water_bodies": 0.0 },
  "nearby_features": [ { "feature_type": "road", "name": "NH-48", "distance_m": 120.5 } ],
  "geojson": { "type": "FeatureCollection", "features": [] }
}
```

**Notes:**
- `changed_area_m2` is a **pass-through** — the backend stores and serves it; it does NOT recalculate area.
- All geometries in `geojson` must be `[longitude, latitude]` (GeoJSON standard).
- Optional fields `layer_versions` and `distances` are welcomed for reproducibility.

> Full schema: `shared/schemas/external/gis_analyze_change_response.json`
> Full example: `backend/tests/contracts/gis/response.json`

**Integration steps:**
1. Set `GIS_ADAPTER=http` and `GIS_BASE_URL=http://<your-host>:8003`
2. Run `python scripts/check_modules.py`

---

### Person 6 — Intelligence

**Your interface is flexible** — you can expose an HTTP endpoint **or** a Python callable.
Tell Person 4 which you prefer; they'll configure the adapter.

#### Option A: HTTP endpoint (INTELLIGENCE_ADAPTER=http)

Set `INTELLIGENCE_BASE_URL=http://<your-host>:8004`.

The backend POSTs the following payload to `<your-host>/intelligence/analyze` (exact path TBC):

```json
{
  "investigation_id": "<uuid>",
  "bbox": [77.1, 28.5, 77.3, 28.7],
  "historical_date": "2025-04-14",
  "current_date": "2026-01-18",
  "observations": [ { "scene_id": "…", "role": "before", "acquisition_date": "2025-04-14" }, … ],
  "detection": { "change_detected": true, "confidence": 0.94, … },
  "gis": { "changed_area_m2": 3842.0, "sensitive_intersections": [ … ] }
}
```

#### Option B: Python callable (INTELLIGENCE_ADAPTER=python)

Set `INTELLIGENCE_PYTHON_ENTRYPOINT=your_package.module:function_name`.
The function receives the same payload as a Python dict and returns a Python dict.

Example:
```python
# In intelligence/engine.py
def run(payload: dict) -> dict:
    ...
    return {
        "fingerprint": { ... },
        "temporal_reconstruction": { ... },
        "evidence": [ ... ],
        "explanation": { ... }
    }
```

Then set: `INTELLIGENCE_PYTHON_ENTRYPOINT=intelligence.engine:run`

**You must return:**
```json
{
  "fingerprint": {
    "fingerprint_id": "UC-2026-A91F",
    "change_type": "construction",
    "changed_area_m2": 3842.0,
    "confidence": 0.94,
    "temporal_behavior": "progressive",
    "sensitive_overlap": { "percentage": 64.0, "layers": ["protected_forest"] },
    "first_observed": "2025-04-14"
  },
  "temporal_reconstruction": {
    "events": [ { "observation_date": "2025-04-14", "event_type": "ground_disturbance", "confidence": 0.81 } ],
    "summary": "Progressive construction observed…"
  },
  "evidence": [ { "evidence_type": "satellite_observation", "source_reference": "scene_id:S2A_…", "metadata": {} } ],
  "explanation": {
    "text": "Significant construction activity was detected…",
    "evidence_ids": ["ev_001"],
    "status": "requires_human_verification"
  }
}
```

> **Important:** Always set `explanation.status = "requires_human_verification"`.
> The backend passes this through verbatim to the frontend. Never assert illegality or ownership.
>
> Full schema: `shared/schemas/external/intelligence_response.json`
> Full example: `backend/tests/contracts/intelligence/response.json`

**For the Assistant endpoint** (`POST /api/investigations/{id}/assistant`):
The backend calls your assistant sub-function with:
```json
{ "investigation_id": "<uuid>", "question": "What changed?", "evidence_ids": [] }
```
You return:
```json
{ "answer": "…", "evidence_ids": ["ev_001"], "uncertainty_notes": "…", "status": "requires_human_verification" }
```

---

## 6. What each module must return (contract summary)

| Module | Required fields (missing any → 502 MAPPER_ERROR) |
|---|---|
| **Satellite /search** | `success`, `scenes[].scene_id`, `scenes[].acquisition_date` |
| **Satellite /fetch** | `success`, `before.scene_id`, `before.acquisition_date`, `after.scene_id`, `after.acquisition_date` |
| **ML** | `change_detected`, `confidence`, `changed_area_pixels`, `model_version` |
| **GIS** | `changed_area_m2` |
| **Intelligence** | `fingerprint.fingerprint_id`, `fingerprint.change_type` |
| **Assistant** | `answer` |

Extra/unknown fields in your response are **silently ignored** (logged at DEBUG).
Required fields being absent raises a `MapperError` that tells you exactly which field is missing.

---

## 7. Shared schemas — JSON Schema files for your module

Once Person 4 commits Phase 2, the folder `shared/schemas/` contains machine-readable
JSON Schema files you can use to **validate your module's output locally**:

```
shared/schemas/
  external/
    satellite_search_response.json   ← validate Person 2's /search response
    satellite_fetch_response.json    ← validate Person 2's /fetch response
    ml_detect_change_response.json   ← validate Person 1's response
    gis_analyze_change_response.json ← validate Person 3's response
    intelligence_response.json       ← validate Person 6's response
    assistant_response.json          ← validate Person 6's assistant response
  api/
    investigation_response.json      ← what the frontend receives
    error_response.json
    ...
```

To validate your response against the schema in Python:

```python
import json, jsonschema, pathlib

schema = json.loads(pathlib.Path("shared/schemas/external/ml_detect_change_response.json").read_text())
your_response = { "change_detected": True, ... }
jsonschema.validate(your_response, schema)   # raises if invalid
print("Schema valid!")
```

Or with a CLI tool:
```bash
pip install check-jsonschema
check-jsonschema --schemafile shared/schemas/external/ml_detect_change_response.json your_response.json
```

---

## 8. Pipeline stages and status machine

### Investigation statuses

```
pending   → created, not yet started
running   → pipeline executing
completed → all stages succeeded
partial   → one or more stages failed; earlier results are returned
failed    → pipeline could not produce any results
```

### Stage names (for progress polling via GET /api/investigations/{id})

| Stage | What happens |
|---|---|
| `searching_catalog` | Satellite search request sent |
| `quality_filtering` | Scenes scored by cloud cover / quality |
| `retrieving_imagery` | Satellite fetch request sent |
| `preprocessing` | Paths normalised, before/after pair validated |
| `change_detection` | ML detect-change call |
| `gis_analysis` | GIS analyze-change call |
| `building_evidence` | Intelligence call (fingerprint, temporal, evidence, explanation) |

### Stage failure behaviour

If **Intelligence** fails:
- Satellite, ML and GIS results are already persisted
- `status = "partial"`, `failed_stage = "building_evidence"`
- Frontend gets all earlier fields; `fingerprint`, `temporal_reconstruction`, `evidence`, `explanation` are `null`

If **Satellite** finds no suitable imagery:
- `satellite_failure_reason` is set on the response (e.g. `"no_suitable_image: all scenes exceed cloud threshold"`)
- Pipeline stops gracefully; status = `partial`
- **Never** a crash, **never** a silent date substitution

---

## 9. Database

### PostgreSQL + PostGIS

```bash
# Create the database
psql -U postgres -c "CREATE DATABASE urbanchange;"

# Run migrations (creates PostGIS extension + all tables)
alembic upgrade head

# Rollback one step
alembic downgrade -1

# See current version
alembic current

# Generate a new migration (after changing models.py)
alembic revision --autogenerate -m "describe your change"
```

### Tables (summary)

| Table | Purpose |
|---|---|
| `investigations` | Root record, AOI geometry (PostGIS), status, stage |
| `satellite_observations` | Before/after/intermediate scenes with paths and metadata |
| `detections` | ML change-detection results |
| `classifications` | ML change classification |
| `gis_results` | GIS analysis output |
| `sensitive_intersections` | Per-layer intersection records |
| `nearby_features` | Features near the change area |
| `change_fingerprints` | Intelligence fingerprint |
| `temporal_events` | Individual events in temporal reconstruction |
| `evidence` | Evidence graph items |
| `assistant_messages` | Chat history per investigation |

Every module-result table has a `raw_payload JSONB` column that stores the
**exact unmodified response** from the module, for debugging and traceability.

Full schema documentation: [`docs/DATABASE_SCHEMA.md`](../docs/DATABASE_SCHEMA.md)

---

## 10. Running tests

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Run specific test groups
pytest tests/unit/             # mapper tests (no DB needed)
pytest tests/contract/         # schema validation tests
pytest tests/integration/      # requires DB
```

### What's tested

| Test file | Tests | What it verifies |
|---|---|---|
| `tests/unit/test_mappers.py` | 33 | Happy path, alias resolution (`cloud_score`, `mask_path`, `file_path`), missing required fields raise `MapperError`, malformed sub-items skipped, extra fields ignored |
| `tests/unit/test_asset_service.py` | 17 | Path resolution, path traversal attack protection (`../`, absolute paths outside storage root), content-type whitelist enforcement, missing assets 404 |
| `tests/contract/test_contracts.py` | 13 | Every fixture in `tests/contracts/<module>/` validates against mappers; mock adapter outputs match contracts; request models validate bbox ranges |
| `tests/integration/test_endpoints.py` | 65 (matrix) | HTTP endpoints via httpx ASGI transport: `/health` liveness/readiness, bbox 422 validation, asset security (traversal/404), `/run` rate limiting (429), and OpenAPI schema definitions |

**Status:** 128 tests passing across unit, contract, and integration suites.

---

## 11. Integration Checker — check_modules.py

Before integration day, run this script to verify every non-mock module is reachable, returns a valid response, and maps cleanly to the internal schema:

```bash
# From the backend/ directory
python scripts/check_modules.py
```

**What it does:**
1. For each module set to `http` (or `python` for Intelligence), calls it with the example contract JSON from `tests/contracts/<module>/`
2. Validates and maps the response through the mapper
3. Prints a colour-coded `PASS / FAIL / MOCK` table per module with the exact missing/mismatched fields

**Example output (all http, all passing):**
```
UrbanChange AI - Module Integration Checker
CONTRACT_VERSION: 0.1.0

MODULE                    MODE        RESULT    DETAIL
------------------------------------------------------------------------------------------
satellite                 http        PASS      success=True before=S2A_MSIL2A_20250414T
ml                        http        PASS      change_detected=True confidence=0.94
gis                       http        PASS      changed_area_m2=3842.0 intersections=1
intelligence              http        PASS      fingerprint_id=UC-... evidence=3
intelligence/assistant    http        PASS      answer_len=312 status=requires_human_verification

All checked modules PASS. Ready for integration.
```

**Example output (one module failing):**
```
satellite                 http        FAIL      MapperError: satellite[fetch.before]: required field 'acquisition_date' is absent
```

**To switch a module from mock to http:**
```bash
# In .env
SATELLITE_ADAPTER=http
SATELLITE_BASE_URL=http://<satellite-service-host>:8001
```
Then re-run `python scripts/check_modules.py`. Fix any FAIL before integration day.

**Exit codes:** `0` = all pass, `1` = at least one failure, `2` = config/import error.

---

## 12. Docker

The entire platform (FastAPI Backend + PostgreSQL with PostGIS) can be launched with a single command via the root `docker-compose.yml`:

```bash
# 1. From the repo root, copy .env.example
cp .env.example .env

# 2. Build and start services in the background
docker compose up -d --build

# 3. View backend logs (entrypoint automatically runs alembic migrations on boot)
docker compose logs -f backend

# 4. Check platform readiness
curl http://localhost:8000/health/ready

# 5. Stop services and preserve data
docker compose down
```

**Services launched:**
- `urbanchange-postgres` (`postgis/postgis:16-3.4`): PostgreSQL 16 + PostGIS on port 5432 with continuous healthchecks.
- `urbanchange-backend`: Python 3.10 slim container on port 8000. Automatically runs `alembic upgrade head` before serving traffic.

---

## 13. Integration-day checklist

Use this before switching any adapter from `mock` to `http`.

### For Person 2 (Satellite)
- [ ] Service is running and reachable at `SATELLITE_BASE_URL`
- [ ] `GET /health` returns 200 on the satellite service
- [ ] `/satellite/search` returns the correct shape (validate against `shared/schemas/external/satellite_search_response.json`)
- [ ] `/satellite/fetch` returns `before` and `after` with valid `image_path` values that exist inside `STORAGE_ROOT`
- [ ] "No suitable image" case returns `{ "success": false, "reason": "…" }` (not 4xx/5xx)
- [ ] `python scripts/check_modules.py` prints **PASS** for `satellite`
- [ ] Set `SATELLITE_ADAPTER=http` in `.env` and run `GET /health/ready` — satellite shows `reachable: true`

### For Person 1 (ML)
- [ ] Service running at `ML_BASE_URL`
- [ ] `/ml/detect-change` returns correct shape (validate against `shared/schemas/external/ml_detect_change_response.json`)
- [ ] `change_mask_path` points to a file inside `STORAGE_ROOT`
- [ ] `python scripts/check_modules.py` prints **PASS** for `ml`
- [ ] Set `ML_ADAPTER=http`

### For Person 3 (GIS)
- [ ] Service running at `GIS_BASE_URL`
- [ ] `/gis/analyze-change` returns correct shape
- [ ] All geometries are `[longitude, latitude]` GeoJSON
- [ ] `python scripts/check_modules.py` prints **PASS** for `gis`
- [ ] Set `GIS_ADAPTER=http`

### For Person 6 (Intelligence)
- [ ] Decide HTTP or Python callable — tell Person 4
- [ ] Response matches `shared/schemas/external/intelligence_response.json`
- [ ] `explanation.status = "requires_human_verification"` always set
- [ ] Assistant response returns `answer` field
- [ ] `python scripts/check_modules.py` prints **PASS** for `intelligence`
- [ ] Set `INTELLIGENCE_ADAPTER=http` (or `python`)

### Final integration checks
- [ ] `GET /health/ready` shows all four modules `reachable: true`
- [ ] Run the full test suite: `pytest` — all green (128 passing tests)
- [ ] POST a real investigation and poll until `status = completed`
- [ ] Confirm all `_url` fields in the response resolve to accessible files via `/api/assets/<path>`

---

## 14. FAQ / Troubleshooting

**Q: I changed a field name in my module. What breaks?**
A: Only the mapper file for your module needs updating (`adapters/mappers/<your_module>_mapper.py`).
Tell Person 4 the old name and the new name; they'll add it as an alias or rename the canonical field.
Nothing else in the backend changes.

**Q: My module returns extra fields that aren't in the contract.**
A: That's fine. All external schemas use `extra='ignore'` — unknown fields are silently dropped
(logged at DEBUG level). No action needed.

**Q: My module is returning a 500 error. What happens?**
A: The adapter catches the error, logs it, and raises `AdapterError(module, stage, detail)`.
The orchestrator catches this, sets `status = "partial"`, `failed_stage = "<stage>"`, and returns
whatever results were already collected. The frontend still gets a valid response.

**Q: How do I test my module locally before integration day?**
A: 
1. Copy `backend/tests/contracts/<your_module>/request.json` — that's what the backend sends you.
2. Run your module with that input and compare your output to `response.json`.
3. Validate against `shared/schemas/external/<your_module>_*.json`.

**Q: Where do image/raster files go?**
A: All module outputs (GeoTIFFs, masks, previews) go inside `STORAGE_ROOT`.
The backend never stores raster binaries in PostgreSQL or Git.
Paths returned by modules must be **relative to `STORAGE_ROOT`** or absolute paths starting with it.

**Q: What's the difference between `image_url` and `image_path`?**
A: `image_path` is what modules return (a filesystem path). `image_url` is what the frontend sees
(an `/api/assets/…` URL). The asset service handles the translation and path traversal prevention.

**Q: I want to use Celery/RQ instead of FastAPI BackgroundTasks.**
A: The `JobRunner` interface (`backend/app/jobs/runner.py`) is abstract. Tell Person 4 and they'll
swap in a Celery implementation — no other code changes.

**Q: The DB migration failed.**
A: Make sure PostGIS is installed: `CREATE EXTENSION IF NOT EXISTS postgis;`
The first migration does this automatically, but your Postgres user needs `SUPERUSER` or at least
`CREATE` privilege on the database.

---

*Last updated: All 9 Phases complete — Full backend orchestration, schemas, database, adapters, routers, tests, and Docker deployment ready.*
*Update this file whenever the contract version bumps or a new adapter is added.*
