# UrbanChange AI - ML Change Detection Microservice

The `/ml` microservice hosts the trained **SatQuery Siamese U-Net** deep learning model for bi-temporal satellite and aerial change detection.

---

## 1. Model Overview

- **Architecture:** `SiameseUNetAttention`
  - **Encoder Backbone:** Shared twin ResNet-34 encoders extracting 5-scale feature pyramids ($[64, 128, 256, 512]$ channels).
  - **Fusion:** Spatial-Temporal Attention Difference Modules (`SpatialTemporalAttentionModule`) applying channel and spatial gating on absolute feature differences to suppress seasonal/lighting noise.
  - **Decoder:** 4-stage transposed convolutional decoder with skip connections from encoder pyramids.
  - **Total Parameters:** 24,872,157 (~24.87M).
- **Weights:** Trained on LEVIR-CD (bitemporal building and urban change detection dataset).
  - **Best Validation F1:** 84.75%
  - **Test Set F1:** 81.84%
  - **Precision:** 82.51%
  - **Recall:** 81.18%
  - **Artifact:** `best_siamese_model.pth` (285 MB).

---

## 2. API Endpoints

### `GET /ml/health`
Health check for Docker Compose and Kubernetes liveness probes.
- **Response:**
  ```json
  {
    "status": "ok",
    "model_loaded": true,
    "device": "cpu",
    "model_version": "SatQuery-Siamese-UNet-v1.0"
  }
  ```

### `GET /ml/model-info`
Detailed model metadata and performance metrics.
- **Response:**
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
    "supported_classes": ["construction", "deforestation", "vegetation_loss", "excavation", "infrastructure", "other"]
  }
  ```

### `POST /ml/detect-change`
Runs bi-temporal inference on a before/after image pair. Strictly matches `/shared/schemas/external/ml_detect_request.json` and `/shared/schemas/external/ml_detect_change_response.json`.

- **Request Body:**
  ```json
  {
    "before": {
      "image_path": "/data/storage/uploads/pair1/before.png",
      "acquisition_date": "2024-01-15",
      "sensor": "Sentinel-2",
      "crs": "EPSG:4326",
      "resolution": 10.0
    },
    "after": {
      "image_path": "/data/storage/uploads/pair1/after.png",
      "acquisition_date": "2024-07-20",
      "sensor": "Sentinel-2",
      "crs": "EPSG:4326",
      "resolution": 10.0
    },
    "sensor": "Sentinel-2",
    "investigation_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "threshold": 0.5,
    "min_area_m2": 50.0
  }
  ```

- **Response Body:**
  ```json
  {
    "change_detected": true,
    "confidence": 0.9421,
    "changed_area_pixels": 4210,
    "changed_area_m2": 1052.5,
    "mask_path": "/data/storage/masks/mask_9b1deb4d.png",
    "preview_path": "/data/storage/previews/preview_9b1deb4d.png",
    "bounds": [80.32, 26.41, 80.38, 26.49],
    "change_regions": [
      {
        "geometry": {
          "type": "Polygon",
          "coordinates": [[[80.32, 26.41], [80.35, 26.41], [80.35, 26.44], [80.32, 26.44], [80.32, 26.41]]]
        },
        "area_pixels": 4210,
        "area_m2": 1052.5,
        "confidence": 0.9421,
        "label": "construction"
      }
    ],
    "classification": {
      "label": "construction",
      "confidence": 0.9421
    },
    "model_version": "SatQuery-Siamese-UNet-v1.0",
    "preprocessing_version": "v1.0-imagenet-norm-sliding-window",
    "threshold": 0.5
  }
  ```

---

## 3. Running Locally

```bash
# 1. Download/verify model weights
python scripts/download_weights.py

# 2. Run test suite
pytest tests/

# 3. Start development server
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```
