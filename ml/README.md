# UrbanChange AI - Machine Learning & Computer Vision Microservice

The `/ml` microservice provides deep learning change detection and overhead vehicle perception for satellite and aerial imagery.

---

## 1. Architecture & Capabilities

### A. Dual Engine Design
- **Production Engine (`ML_ENGINE=legacy`, Default):**
  - **Architecture:** `SiameseUNetAttention` (ResNet-34 twin backbone + Spatial-Temporal Attention Modules + 4-stage transposed conv decoder).
  - **Weights:** Trained on LEVIR-CD (285 MB `best_siamese_model.pth`).
  - **Features:** 24.87M parameters, calibrated decision boundaries, zero false positives on unchanged urban/forest scenes.
- **Multi-Task Engine (`ML_ENGINE=v2`):**
  - **Architecture:** `MultiTaskSiameseChangeNet` (ResNet-34 twin backbone + Multi-Scale Feature Difference Fusion + Attention).
  - **Multi-Task Outputs:** Binary change map $(B, 1, H, W)$ and dual semantic segmentation heads for $T_1$ and $T_2$ $(B, 7, H, W)$.
  - **Semantic Classes:** Background (0), Building (1), Tree/Forest (2), Low Vegetation (3), Water (4), Infrastructure/Road (5), Bare Ground/Excavation (6).

### B. Dual Resolution Profiles
1. **Profile `hires` (GSD $\le 1.0\text{ m}$):**
   - Active for drone, aerial photography, and high-res satellite uploads.
   - Sliding-window tiled inference ($256 \times 256$, stride $224$, 2D Hann window feathering).
   - **Vehicle Perception:** Automatically enabled when $\text{GSD} \le 0.5\text{ m}$. Detects and counts cars and buses on both dates without mistaking vehicle traffic for terrain change.
2. **Profile `sentinel2` (GSD $\approx 10\text{ m}$):**
   - Specialized for Sentinel-2 L2A BOA surface reflectance COGs.
   - Neural temporal difference fused with spectral indices ($\Delta\text{NDVI}$, $\Delta\text{GLI}$, $\Delta\text{ExG}$).
   - Returns `vehicles.supported = false` with explanation: `"Vehicles are not resolvable at this ground resolution"`.

---

## 2. API Endpoints

### `GET /ml/health`
Liveness probe returning engine and profile statuses:
```json
{
  "status": "ok",
  "model_loaded": true,
  "device": "cpu",
  "model_version": "SatQuery-Siamese-UNet-v1.0",
  "engine": "legacy",
  "profiles_available": ["hires", "sentinel2"],
  "vehicles_supported": true
}
```

### `GET /ml/model-info`
Architectural metadata and parameter metrics:
```json
{
  "model_version": "SatQuery-Siamese-UNet-v1.0",
  "architecture": "SiameseUNetAttention (Shared ResNet-34 + Spatial-Temporal Attention Modules)",
  "device": "cpu",
  "threshold": 0.5,
  "parameter_count": 24872157,
  "val_f1": 0.8475,
  "test_f1": 0.8184,
  "status": "ready",
  "input_resolution_trained_m": 0.5,
  "supported_formats": ["GeoTIFF (.tif, .tiff)", "PNG (.png)", "JPEG (.jpg, .jpeg)"],
  "supported_classes": ["construction", "deforestation", "vegetation_loss", "excavation", "infrastructure", "other"],
  "engine": "legacy",
  "profiles": {
    "hires": {"resolution_m": "<=1.0", "sensor": "Drone/Aerial/Upload", "vehicles": true},
    "sentinel2": {"resolution_m": "10.0", "sensor": "Sentinel-2 MSI", "vehicles": false}
  },
  "vehicles_enabled": true
}
```

### `POST /ml/detect-change`
Primary change detection and vehicle perception endpoint. Strictly satisfies the shared API contract:
```json
{
  "change_detected": true,
  "confidence": 0.9319,
  "changed_area_pixels": 14007,
  "changed_area_m2": 3501.75,
  "mask_path": "/data/storage/masks/mask_9b1deb4d.png",
  "change_mask_path": "/data/storage/masks/mask_9b1deb4d.png",
  "preview_path": "/data/storage/previews/preview_9b1deb4d.png",
  "mask_preview_path": "/data/storage/previews/preview_9b1deb4d.png",
  "bounds": [80.32, 26.41, 80.38, 26.49],
  "mask_bounds": [80.32, 26.41, 80.38, 26.49],
  "change_regions": [
    {
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[80.32, 26.41], [80.35, 26.41], [80.35, 26.44], [80.32, 26.44], [80.32, 26.41]]]
      },
      "area_pixels": 14007,
      "area_m2": 3501.75,
      "confidence": 0.9319,
      "label": "construction"
    }
  ],
  "classification": {
    "label": "construction",
    "confidence": 0.9319
  },
  "model_version": "SatQuery-Siamese-UNet-v1.0 (legacy)",
  "preprocessing_version": "v1.0-imagenet-norm-sliding-window",
  "threshold": 0.5,
  "profile_used": "hires",
  "thresholds_used": {"threshold": 0.5, "min_area_m2": 50.0},
  "vehicles": {
    "supported": true,
    "reason": null,
    "before_count": 5,
    "after_count": 6,
    "detections_before": [],
    "detections_after": []
  }
}
```

---

## 3. Dataset Pipeline & Preparation

Dataset catalog and automated acquisition:
```bash
# Set up benchmark samples and synthetic Sentinel-2 calibration:
python ml/scripts/download_data.py --action setup

# Verify directory counts, shapes, and pixel ranges:
python ml/scripts/download_data.py --action verify
```

Official catalog links and licenses are documented in `ml/data/README.md` and `docs/ML_MODEL_CARD.md`.

---

## 4. Training & Fine-Tuning Pipeline

Training dependencies are kept separate in `ml/requirements-train.txt` to keep the Docker image lightweight.

```bash
# 1. Install training dependencies
pip install -r ml/requirements-train.txt

# 2. Run smoke training test (1 epoch)
python ml/train/train.py --profile hires --smoke

# 3. Train Hires Profile
python ml/train/train.py --profile hires --epochs 10 --batch_size 4

# 4. Train Sentinel-2 Profile
python ml/train/train.py --profile sentinel2 --epochs 10 --batch_size 4

# 5. Evaluate and Compare with Legacy Model
python ml/train/eval.py
```

---

## 5. Configuration & Environment Variables

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `ML_ENGINE` | `legacy` | Engine mode: `legacy` (SiameseUNetAttention) or `v2` (MultiTaskSiameseChangeNet). |
| `ML_WEIGHTS_PATH` | `/app/weights/best_siamese_model.pth` | Path to primary legacy weights. |
| `ML_WEIGHTS_HIRES_PATH` | `/app/runs/hires/best_model.pth` | Path to v2 Hires profile weights. |
| `ML_WEIGHTS_S2_PATH` | `/app/runs/sentinel2/best_model.pth` | Path to v2 Sentinel-2 profile weights. |
| `ML_VEHICLE_WEIGHTS_PATH` | `None` | Path to vehicle detector weights. |
| `ML_ENABLE_SPECTRAL_FUSION` | `true` | Enables optical NDVI/GLI/ExG spectral fusion for vegetation loss detection. |
| `PORT` | `8002` | Port for FastAPI HTTP microservice. |
| `STORAGE_ROOT` | `/data/storage` | Shared storage directory for masks and overlay previews. |

---

## 6. Integration Guide for Teammates

- **Person 2 (GIS Engine):**
  - All polygon geometries in `change_regions[].geometry` are standard GeoJSON Polygons.
  - For GeoTIFF inputs, coordinates are EPSG:4326 `[longitude, latitude]` bounds.
  - For standard uploaded PNGs, coordinates are normalized `[0, 1]` pixel space.
- **Person 3 (Satellite Pipeline):**
  - Sentinel-2 GeoTIFF stacks should supply 4 bands: `[B02 (Blue), B03 (Green), B04 (Red), B08 (NIR)]` scaled to surface reflectance ($0 - 3000$).
  - When CRS is present, the ML service automatically activates the `sentinel2` profile ($10\text{ m}$ pixel resolution) and sets `vehicles.supported = false`.
- **Person 4 (Backend Orchestrator):**
  - The response payload provides full dual alias support: `change_mask_path` and `mask_path`, `mask_preview_path` and `preview_path`, `mask_bounds` and `bounds`.
  - All new fields (`vehicles`, `profile_used`, `thresholds_used`, `semantic_summary`) are optional and non-breaking.
