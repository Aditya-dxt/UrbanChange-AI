# UrbanChange AI - Model Card & Technical Specifications

This Model Card documents the architecture, datasets, licensing, training protocol, benchmark evaluation, and known limitations for UrbanChange AI's change-detection and vehicle perception models.

---

## 1. Model Overview

| Property | Specification |
| :--- | :--- |
| **Model Names** | `SatQuery-Siamese-UNet-v1.0` (Production Default) / `UrbanChange-MultiTask-v2.0` |
| **Architecture** | Siamese Temporal Attention Network (ResNet-34 twin backbone + Spatial/Temporal Difference Attention + Multi-Task Decoders) |
| **Tasks** | 1. Bitemporal Binary Change Segmentation<br>2. Multi-class Land-Cover Dynamics (Building, Tree, Vegetation, Infrastructure, Excavation)<br>3. Overhead Vehicle Perception (Cars, Buses) |
| **Input Modalities** | 1. High-Resolution Optical RGB (Drone / Aerial / Satellite, GSD $\le 1.0\text{ m}$)<br>2. Multispectral Sentinel-2 L2A (10 m B02, B03, B04, B08 GeoTIFF / TCI) |
| **Inference Hardware** | CPU (x86_64, AVX2) and NVIDIA CUDA (TensorRT / FP16 compatible) |
| **Framework** | PyTorch 2.3+ |

---

## 2. Dataset Catalog & Licences

All training and evaluation datasets are curated from verified academic and public access archives:

| Dataset | Modality / GSD | Scope / Classes | Licence | Reference |
| :--- | :--- | :--- | :--- | :--- |
| **LEVIR-CD** | Aerial / 0.5 m | 637 bitemporal pairs ($1024 \times 1024$), building appearance | Open Access / Research | Chen & Shi, 2020 |
| **WHU-CD** | Aerial / 0.2 m | Building change detection ($15354 \times 32507$ total) | Non-commercial research | Ji et al., 2018 |
| **SECOND** | Aerial / 0.5–3.0 m | 4662 pairs ($512 \times 512$), 6 semantic land cover categories | Academic research | Yang et al., 2021 |
| **SpaceNet 7** | Satellite / 4.0 m | Multi-temporal Planet imagery, urban footprint evolution | CC BY-SA 4.0 | Van Etten et al., 2021 |
| **OSCD** | Sentinel-2 / 10 m | 24 multispectral city pairs, urban change | IEEE Open Access / Onera | Daudt et al., 2018 |
| **COWC** | Aerial / 0.15 m | Vehicle counts and detection (Cars) | Open Access (LLNL) | Mundhenk et al., 2016 |
| **VEDAI** | Aerial / 0.125 m | Multi-class vehicles (Car, Truck, Bus, Van, Tractor) | Academic Research (Inria) | Razakarivony & Jurie, 2016 |
| **DOTA v1.0** | Aerial / 0.1–1.0 m | Small Vehicle, Large Vehicle oriented bounding boxes | CC BY-NC 4.0 | Xia et al., 2018 |

---

## 3. Architecture & Resolution Profiles

To resolve the scale disparity between drone/aerial imagery ($\le 0.5\text{ m}$) and spaceborne Sentinel-2 ($10\text{ m}$), the pipeline provides two specialized resolution profiles:

### A. Profile `hires` (GSD $\le 1.0\text{ m}$)
- **Target:** Drone surveys, aerial photography, high-resolution commercial satellite imagery.
- **Tiling:** $256 \times 256$ sliding window with $32\text{ px}$ overlap and 2D Hann window feathering.
- **Vehicle Perception:** Active when $\text{GSD} \le 0.5\text{ m}$. Detects and counts cars and buses on $T_1$ and $T_2$ independently. Vehicle movements are tracked without being erroneously flagged as terrain change.

### B. Profile `sentinel2` (GSD $\approx 10.0\text{ m}$)
- **Target:** Sentinel-2 L2A BOA surface reflectance COGs.
- **Fusion:** Neural temporal difference combined with B08/B04 Normalized Difference Vegetation Index ($\Delta\text{NDVI}$) and optical Green Leaf Index ($\Delta\text{GLI}$).
- **Vehicle Perception:** Explicitly marked `supported: false` with explanation: `"Vehicles are not resolvable at this ground resolution"`. Prevents hallucinations.

### C. Multi-Task Semantic Transition Logic
Pixel-level semantic segmentations ($S_1, S_2$) inside each detected polygon determine the final classification label:
- $\text{Non-Building} \to \text{Building}$: `"construction"`
- $\text{Tree} \to \text{Bare/Cleared Ground}$: `"deforestation"`
- $\text{Vegetation} \to \text{Non-Vegetation}$: `"vegetation_loss"`
- $\text{Elongated Imp/Road} \land \text{Aspect Ratio} > 3.0$: `"infrastructure"`
- $\text{Bare Ground} \land \text{Compactness} < 0.25$: `"excavation"`
- $\Delta\text{Water} > 0.25$: `"water_change"`

---

## 4. Checkpoints & Integrity Hashes

| Checkpoint Identifier | Target Path | File Size | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| **Legacy Production Model** | `ml/weights/best_siamese_model.pth` | 284.97 MB | `9f1db97e894ebb48473775d874932bdbc06a72b902bf6b8ec2672d3f94a4db6d` |
| **Multi-Task Hires Best** | `ml/runs/hires/best_model.pth` | 396.19 MB | `69e5f3b39b6e5c7529607825a4ebc041a7b404fabc5db29a975445e2cf630fef` |
| **Multi-Task Sentinel2 Best** | `ml/runs/sentinel2/best_model.pth` | 396.19 MB | `b0e94489f744590645625200548d5d561df76a517f7b581c0175724e1c634cc7` |

---

## 5. Performance Metrics & Comparative Regression

### A. Academic Benchmark Evaluation

| Model Architecture | Dataset / Profile | F1-Score | IoU / Jaccard | Precision | Recall |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SatQuery-Siamese-UNet (Legacy)** | LEVIR-CD (Test) | **81.84%** | **69.26%** | **82.51%** | **81.18%** |
| **SatQuery-Siamese-UNet (Legacy)** | LEVIR-CD (Val) | 84.75% | 73.53% | 85.12% | 84.38% |
| **UrbanChange-MultiTask-v2** | Hires Val (5 Ep) | 50.46% | 33.75% | 33.75% | 100.0% |
| **UrbanChange-MultiTask-v2** | Sentinel-2 Val | 0.34% | 0.17% | 0.17% | 100.0% |

### B. Observed Regression on Repository Sample Pairs (`sample_data/pairs/`)

| Sample Identifier | Scenario | Legacy Detected Pixels | Legacy Conf | New Model Label | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `pair_01_construction` | New housing development | 14,007 px | 0.9319 | `construction` | **PASS** (Zero false positives on existing structures) |
| `pair_02_deforestation` | Clear-cutting in forest | 8,420 px (Fused) | 0.9127 | `deforestation` | **PASS** (Correctly categorized as deforestation) |
| `pair_03_road_infra` | Highway extension | 1,024 px | 0.8405 | `infrastructure` | **PASS** (Elongated polygon tracked) |
| `pair_04_no_change` | Unchanged residential | 0 px | 0.9107 | `no_change` | **PASS** (Completely quiet, 0 false alarms) |
| `pair_05_sentinel2_geotiff` | 4-band GeoTIFF | 13,702 px | 0.9305 | `construction` | **PASS** (WGS84 EPSG:4326 GeoJSON validated) |

> **Production Recommendation:** The legacy `best_siamese_model.pth` achieves superior specificity (zero false positives on no-change imagery) and higher F1 on building boundaries. Therefore, `ML_ENGINE=legacy` is retained as the default production engine, while `ML_ENGINE=v2` is accessible via feature flag for multi-task research.

---

## 6. Known Limitations & Operational Guidance

1. **Resolution Limits:** Sentinel-2 pixels are $10\text{ m} \times 10\text{ m}$ ($100\text{ m}^2$). Physical developments smaller than $50\text{ m}^2$ (individual small shacks, single trees) cannot be resolved.
2. **Legal Admissibility:** Model outputs constitute geospatial intelligence indicators and **do not constitute legal proof** of unauthorized development. Field inspection or human analyst verification is required before administrative actions.
3. **Severe Cloud Shadows & Parallax:** Thick cloud shadows or extreme off-nadir view angle discrepancies between dates can induce localized false alarms.
4. **Vehicle Detection Range:** Vehicle counts are only valid for optical imagery with GSD $\le 0.5\text{ m}$. For satellite feeds, the system returns `vehicles.supported = false`.
