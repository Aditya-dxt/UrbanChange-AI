# Proposed Optional Contract Additions (ML Microservice)

This document specifies **strictly non-breaking, optional** additions to the `POST /ml/detect-change` response contract, proposed by the ML / Computer Vision Engineer (Person 1) for Person 4 (Backend Integration).

Existing request and response fields remain 100% identical and backward compatible.

---

## 1. Summary of Proposed Optional Fields

| Field Name | Type | Container | Purpose |
| :--- | :--- | :--- | :--- |
| `vehicles` | `object` (optional) | Root response | Vehicle counts and detections for high-res imagery ($\le 0.5\text{ m}$). |
| `profile_used` | `string` (optional) | Root response | Indicates whether `"hires"` ($\le 1\text{ m}$) or `"sentinel2"` ($\approx 10\text{ m}$) inference profile was executed. |
| `thresholds_used` | `object` (optional) | Root response | Operational parameters applied during inference (`threshold`, `min_area_m2`). |
| `semantic_summary` | `object` (optional) | Root response | Scene-wide land cover dynamics (proportions of building gain, tree loss, vegetation loss). |
| `class_detail` | `object` (optional) | `change_regions[]` | Per-region land cover transition breakdown. |

---

## 2. Detailed Schema Definitions

### A. `vehicles` Object

Returned on root `POST /ml/detect-change` response:
```json
{
  "vehicles": {
    "supported": true,
    "reason": null,
    "before_count": 14,
    "after_count": 18,
    "detections_before": [
      {
        "box": [45, 120, 65, 138],
        "class": "car",
        "score": 0.92
      }
    ],
    "detections_after": [
      {
        "box": [48, 122, 68, 140],
        "class": "car",
        "score": 0.89
      }
    ]
  }
}
```

When resolution $> 0.5\text{ m}$ (e.g. Sentinel-2):
```json
{
  "vehicles": {
    "supported": false,
    "reason": "Vehicles are not resolvable at this ground resolution",
    "before_count": 0,
    "after_count": 0,
    "detections_before": [],
    "detections_after": []
  }
}
```

### B. `semantic_summary` Object

```json
{
  "semantic_summary": {
    "building_gain": 0.42,
    "tree_loss": 0.0,
    "veg_loss": 0.12,
    "infra_gain": 0.05,
    "bare_gain": 0.08
  }
}
```

---

## 3. Full Example Response Payload

```json
{
  "change_detected": true,
  "confidence": 0.9319,
  "changed_area_pixels": 14007,
  "changed_area_m2": 3501.75,
  "change_mask_path": "/data/storage/masks/mask_9b1deb4d.png",
  "mask_preview_path": "/data/storage/previews/preview_9b1deb4d.png",
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
      "label": "construction",
      "class_detail": {
        "building_gain": 0.65,
        "tree_loss": 0.0,
        "veg_loss": 0.05
      }
    }
  ],
  "classification": {
    "label": "construction",
    "confidence": 0.9319
  },
  "model_version": "SatQuery-Siamese-UNet-v1.0",
  "preprocessing_version": "v1.0-imagenet-norm-sliding-window",
  "threshold": 0.5,
  "profile_used": "hires",
  "thresholds_used": {
    "threshold": 0.5,
    "min_area_m2": 50.0
  },
  "semantic_summary": {
    "building_gain": 0.65,
    "tree_loss": 0.0,
    "veg_loss": 0.05,
    "infra_gain": 0.02,
    "bare_gain": 0.08
  },
  "vehicles": {
    "supported": true,
    "reason": null,
    "before_count": 3,
    "after_count": 4,
    "detections_before": [],
    "detections_after": []
  }
}
```
