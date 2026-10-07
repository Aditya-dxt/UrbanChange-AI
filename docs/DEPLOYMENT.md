# Deployment & Operations Guide

## Overview
UrbanChange AI can be deployed either as a complete containerized stack using Docker Compose or run locally in modular development mode.

---

## 1. Profiles & Architecture

```
                    ┌─────────────────────────┐
                    │    Frontend (React)     │
                    │      Port 80 / 5173     │
                    └───────────┬─────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │   Backend Hub (FastAPI) │
                    │        Port 8000        │
                    └───────┬───────┬─────────┘
        ┌───────────────────┼───────┴───────────────┐
        ▼                   ▼                       ▼
┌──────────────┐    ┌──────────────┐        ┌──────────────┐
│  Satellite   │    │  GIS Engine  │        │ Intelligence │
│  Port 8001   │    │  Port 8003   │        │  Port 8004   │
└──────────────┘    └──────────────┘        └──────────────┘
        │                   │                       │
        └─────────┬─────────┴───────────────────────┘
                  ▼
          ┌──────────────┐
          │ Shared Data  │
          │/data/storage │
          └──────────────┘
```

The system provides two execution profiles:

### A. Demo Profile (`demo` or default)
- **Use Case:** Standalone demonstrations, pitch expo, offline evaluation.
- **Behavior:** The backend runs with internal mock adapters (`SATELLITE_ADAPTER=mock`, `ML_ADAPTER=mock`, `GIS_ADAPTER=mock`, `INTELLIGENCE_ADAPTER=mock`).
- **External Dependencies:** Zero external APIs or heavy models required.
- **Command:**
  ```bash
  docker compose up --build
  # or
  docker compose --profile demo up --build
  ```

### B. Live Profile (`live`)
- **Use Case:** Production deployment with real satellite data discovery, projected GIS computations, and full LLM retrieval. ML change detection remains safely on the verified mock adapter (`ML_ADAPTER=mock`).
- **Behavior:** Starts containerized `satellite`, `gis`, and `intelligence` services alongside `backend`, `frontend`, and `postgres`.
- **Command:**
  ```bash
  docker compose --profile live up --build
  ```

---

## 2. Environment Variables (.env)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Key configuration settings:
- `REQUIRE_AUTH=false`: Set to `true` to require `X-API-Key` or `Authorization: Bearer <key>`.
- `API_KEY=your-secret-key`: Authentication token when auth is required.
- `STORAGE_ROOT=/data/storage`: Mount point for shared GeoTIFF rasters and assets.
- `COPERNICUS_CLIENT_ID` / `COPERNICUS_CLIENT_SECRET`: Optional credentials for CDSE.
- `OLLAMA_BASE_URL`: URL of the Ollama server for local LLM inference.

---

## 3. Container Services & Ports

| Container Name | Service | Internal Port | Host Port | Profile |
|---|---|---|---|---|
| `urbanchange-postgres` | PostgreSQL 16 + PostGIS 3.4 | 5432 | 5432 | default |
| `urbanchange-backend` | FastAPI Backend Hub | 8000 | 8000 | default |
| `urbanchange-frontend` | React UI + Leaflet (Nginx) | 80 | 80 / 5173 | default |
| `urbanchange-satellite` | Satellite Service | 8001 | 8001 | `live` |
| `urbanchange-gis` | GIS Spatial Engine | 8003 | 8003 | `live` |
| `urbanchange-intelligence` | Intelligence & Q&A Engine | 8004 | 8004 | `live` |
| `urbanchange-ollama` | Local LLM inference (Llama 3) | 11434 | 11434 | `ollama` |

---

## 4. Health Checks
All services provide automated liveness and readiness probes:
- Backend: `curl http://localhost:8000/health` (Readiness: `http://localhost:8000/health/ready`)
- Satellite: `curl http://localhost:8001/health`
- GIS: `curl http://localhost:8003/health`
- Intelligence: `curl http://localhost:8004/health`
- Frontend: `curl http://localhost:80/`

---

## 5. End-to-End Verification
To test the complete stack after starting containers:
```bash
python scripts/test_e2e_demo.py --url http://localhost:8000
```
