# UrbanChange AI – Frontend (Person 5)

React + Vite + Tailwind + TypeScript + Leaflet. Runs on mock JSON by default.

```bash
npm install
cp .env.example .env     # VITE_USE_MOCK=true
npm run dev
```
Switch to the real backend: set `VITE_USE_MOCK=false` (Vite proxies `/api` to `http://localhost:8000`, see `vite.config.ts`). Only `src/api/client.ts` and `src/api/mock.ts` change; components never call `fetch`.

Conventions: GeoJSON `[longitude, latitude]` everywhere; `BBox = [west, south, east, north]`. Leaflet's `[lat, lng]` conversion is confined to `MapView.tsx`.

## Endpoints used
| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/api/investigations` | `{bbox, historical_date:"YYYY-MM"}` | `{id}` |
| GET | `/api/investigations/{id}` | – | `Investigation` (polled every 1.5 s until `complete`/`partial`/`failed`) |
| POST | `/api/uploads` | multipart `before`, `after` (GeoTIFF/PNG/JPEG) | `{id}` then same polling via GET |
| POST | `/api/investigations/{id}/assistant` | `{question}` | `{answer, evidence_ids[]}` |

## Investigation JSON fields used
- `id`, `status` (`queued|running|partial|complete|failed`), `progress_step` (0–4), `error`, `bbox`
- `observations.t1|t2`: `scene_id`, `date`, `cloud`, `quality`, `image_url`
- `detection` (null = no change): `polygon` (GeoJSON Polygon), `area_m2`, `confidence` (0–1), `class`, `class_score`, `priority`, `model_version`, `mask_url`
- `gis` (nullable): `sensitive[]` {`layer`,`source`,`overlap_percent`,`distance_m`}, `sensitive_geojson` (FeatureCollection), `landcover`, `georeferenced`
- `temporal` (null = unavailable): `[{date,state,magnitude,image_url}]`
- `fingerprint`: `id,type,area_m2,confidence,temporal_behavior,sensitive_overlap_percent,compactness,rectangularity,landcover`
- `evidence[]`: `id,type,text`; `explanation` (string)

## States handled
loading steps · empty (no change) · partial (no timeline) · low confidence (<60%) · failure + retry · non-georeferenced upload warning · independently toggleable map layers.

## Structure
`src/types.ts` contract · `src/api/` service layer + mock · `src/hooks/useInvestigation.ts` state · `src/components/` UI.
Wording rule: results are "potential" and "require human verification"; never state ownership or illegality as proven.
