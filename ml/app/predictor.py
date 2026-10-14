"""
Inference engine for UrbanChange AI Change Detection & Vehicle Perception.
Supports:
- Dual Engine: 'legacy' (SiameseUNetAttention) and 'v2' (MultiTaskSiameseChangeNet)
- Dual Profile: 'hires' (GSD <= 1m) and 'sentinel2' (GSD ~ 10m)
- Vehicle Detection: Cars and Buses (GSD <= 0.5m)
- GeoTIFF (Sentinel-2 4-band/3-band) and standard PNG/JPEG images
- Sliding window inference with Hann window feathering
- Optical spectral vegetation fusion (GLI/ExG/NDVI)
- GeoJSON vectorization (WGS84 EPSG:4326 or normalized [0, 1])
"""
from __future__ import annotations

import logging
import math
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F
from scipy import ndimage

try:
    from app.model import SiameseUNetAttention
    from app.model_v2 import MultiTaskSiameseChangeNet, classify_semantic_transition
    from app.vehicles import VehicleDetectorService
    from app.schemas import (
        ChangeRegion,
        ClassificationResult,
        MLDetectChangeResponse,
        VehiclesResult,
    )
except ImportError:
    from ml.app.model import SiameseUNetAttention
    from ml.app.model_v2 import MultiTaskSiameseChangeNet, classify_semantic_transition
    from ml.app.vehicles import VehicleDetectorService
    from ml.app.schemas import (
        ChangeRegion,
        ClassificationResult,
        MLDetectChangeResponse,
        VehiclesResult,
    )

log = logging.getLogger("ml.predictor")

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 1, 3)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 1, 3)
PATCH_SIZE = 256
OVERLAP = 32
STRIDE = PATCH_SIZE - OVERLAP  # 224


class ChangePredictor:
    """Manages model lifecycle, profile switching, and end-to-end change detection inference."""

    def __init__(
        self,
        weights_path: Optional[Path | str] = None,
        device: Optional[str] = None,
        engine: Optional[str] = None,
    ):
        if device:
            self.device = torch.device(device)
        else:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.engine = (engine or os.environ.get("ML_ENGINE", "legacy")).lower()
        self.enable_spectral_fusion = os.environ.get("ML_ENABLE_SPECTRAL_FUSION", "true").lower() in [
            "1",
            "true",
            "yes",
        ]

        # Weights paths from environment or default locations
        default_legacy_weights = Path(__file__).resolve().parent.parent / "weights" / "best_siamese_model.pth"
        self.legacy_weights_path = Path(
            os.environ.get("ML_WEIGHTS_PATH", weights_path or default_legacy_weights)
        ).resolve()

        self.hires_weights_path = Path(
            os.environ.get(
                "ML_WEIGHTS_HIRES_PATH",
                Path(__file__).resolve().parent.parent / "runs" / "hires" / "best_model.pth",
            )
        ).resolve()

        self.s2_weights_path = Path(
            os.environ.get(
                "ML_WEIGHTS_S2_PATH",
                Path(__file__).resolve().parent.parent / "runs" / "sentinel2" / "best_model.pth",
            )
        ).resolve()

        self.vehicle_weights_path = os.environ.get("ML_VEHICLE_WEIGHTS_PATH", None)

        log.info(
            "Initializing ChangePredictor: device=%s, engine=%s, spectral_fusion=%s",
            self.device,
            self.engine,
            self.enable_spectral_fusion,
        )

        # Initialize models
        self.legacy_model = None
        self.v2_hires_model = None
        self.v2_s2_model = None
        self.vehicle_service = VehicleDetectorService(
            weights_path=self.vehicle_weights_path, device=str(self.device)
        )

        self._init_models()

    def _init_models(self) -> None:
        """Loads weights with graceful fallback to legacy model."""
        # 1. Always ensure legacy model is ready as reliable fallback
        if self.legacy_weights_path.exists():
            log.info("Loading legacy model weights: %s", self.legacy_weights_path)
            self.legacy_model = SiameseUNetAttention().to(self.device)
            ckpt = torch.load(str(self.legacy_weights_path), map_location=self.device)
            state = ckpt.get("model_state_dict", ckpt)
            self.legacy_model.load_state_dict(state)
            self.legacy_model.eval()
        else:
            log.warning("Legacy weights not found at %s. Attempting download...", self.legacy_weights_path)
            try:
                from scripts.download_weights import ensure_weights
                ensure_weights(self.legacy_weights_path)
                self.legacy_model = SiameseUNetAttention().to(self.device)
                ckpt = torch.load(str(self.legacy_weights_path), map_location=self.device)
                self.legacy_model.load_state_dict(ckpt.get("model_state_dict", ckpt))
                self.legacy_model.eval()
            except Exception as exc:
                log.error("Failed to load legacy weights: %s", exc)

        # 2. If v2 engine requested, load hires and sentinel2 models
        if self.engine == "v2":
            if self.hires_weights_path.exists():
                log.info("Loading v2 Hires model: %s", self.hires_weights_path)
                self.v2_hires_model = MultiTaskSiameseChangeNet().to(self.device)
                ckpt_h = torch.load(str(self.hires_weights_path), map_location=self.device)
                self.v2_hires_model.load_state_dict(ckpt_h.get("model_state_dict", ckpt_h), strict=False)
                self.v2_hires_model.eval()
            else:
                log.warning(
                    "v2 Hires weights not found at %s. Will fallback to legacy model.",
                    self.hires_weights_path,
                )

            if self.s2_weights_path.exists():
                log.info("Loading v2 Sentinel-2 model: %s", self.s2_weights_path)
                self.v2_s2_model = MultiTaskSiameseChangeNet().to(self.device)
                ckpt_s = torch.load(str(self.s2_weights_path), map_location=self.device)
                self.v2_s2_model.load_state_dict(ckpt_s.get("model_state_dict", ckpt_s), strict=False)
                self.v2_s2_model.eval()
            else:
                log.warning(
                    "v2 Sentinel-2 weights not found at %s. Will fallback to legacy model.",
                    self.s2_weights_path,
                )

    @property
    def model(self) -> torch.nn.Module:
        """Compatibility property for legacy health and info checks."""
        return self.legacy_model if self.legacy_model is not None else self.v2_hires_model

    # ── Image Loading & Preprocessing ──────────────────────────────────────────

    def load_image_data(
        self, file_path: str | Path
    ) -> Tuple[np.ndarray, Optional[np.ndarray], Optional[dict]]:
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Input image not found: {path}")

        geo_info = None
        nir_band = None

        is_tiff = path.suffix.lower() in [".tif", ".tiff"]
        if not is_tiff:
            try:
                with open(path, "rb") as f_check:
                    header = f_check.read(4)
                    if header in (b"II*\x00", b"MM\x00*"):
                        is_tiff = True
            except Exception:
                pass

        if is_tiff:
            try:
                import rasterio
                from rasterio.warp import transform_bounds

                with rasterio.open(path) as src:
                    count = src.count
                    crs_str = str(src.crs) if src.crs else None
                    transform = src.transform
                    width, height = src.width, src.height

                    if count >= 4:
                        b02 = src.read(1).astype(np.float32)
                        b03 = src.read(2).astype(np.float32)
                        b04 = src.read(3).astype(np.float32)
                        b08 = src.read(4).astype(np.float32)
                        scale = 1.0 / 3000.0
                        rgb_raw = np.stack([b04, b03, b02], axis=-1) * scale
                        rgb_raw = np.clip(rgb_raw, 0.0, 1.0)
                        nir_band = np.clip(b08 * scale, 0.0, 1.0)
                    elif count == 3:
                        r = src.read(1).astype(np.float32)
                        g = src.read(2).astype(np.float32)
                        b = src.read(3).astype(np.float32)
                        rgb_raw = np.stack([r, g, b], axis=-1)
                        if rgb_raw.max() > 1.0:
                            rgb_raw = rgb_raw / 255.0
                        rgb_raw = np.clip(rgb_raw, 0.0, 1.0)
                    else:
                        gray = src.read(1).astype(np.float32)
                        if gray.max() > 1.0:
                            gray = gray / 255.0
                        rgb_raw = np.stack([gray, gray, gray], axis=-1)

                    wgs84_bounds = None
                    if src.crs:
                        try:
                            w, s, e, n = transform_bounds(src.crs, "EPSG:4326", *src.bounds)
                            wgs84_bounds = [float(w), float(s), float(e), float(n)]
                        except Exception as e:
                            log.warning("Could not transform bounds to EPSG:4326: %s", e)

                    geo_info = {
                        "crs": crs_str,
                        "transform": transform,
                        "bounds": wgs84_bounds,
                        "width": width,
                        "height": height,
                    }
                    rgb_norm = (rgb_raw - IMAGENET_MEAN) / IMAGENET_STD
                    return rgb_norm.astype(np.float32), nir_band, geo_info
            except Exception as exc:
                log.warning("Rasterio read failed for %s (%s). Falling back to PIL...", path.name, exc)

        try:
            pil_img = Image.open(path).convert("RGB")
            rgb_raw = np.array(pil_img, dtype=np.float32) / 255.0
            rgb_norm = (rgb_raw - IMAGENET_MEAN) / IMAGENET_STD
            return rgb_norm.astype(np.float32), None, None
        except Exception as pil_exc:
            log.warning("PIL failed to open %s (%s). Attempting rasterio fallback...", path.name, pil_exc)
            import rasterio
            with rasterio.open(path) as src:
                r = src.read(1).astype(np.float32)
                g = src.read(2 if src.count >= 2 else 1).astype(np.float32)
                b = src.read(3 if src.count >= 3 else 1).astype(np.float32)
                rgb_raw = np.stack([r, g, b], axis=-1)
                if rgb_raw.max() > 1.0:
                    rgb_raw = rgb_raw / 255.0
                rgb_norm = (np.clip(rgb_raw, 0.0, 1.0) - IMAGENET_MEAN) / IMAGENET_STD
                return rgb_norm.astype(np.float32), None, None

    # ── Inference with Sliding Window ──────────────────────────────────────────

    def predict_change_prob(
        self, img1: np.ndarray, img2: np.ndarray, profile: str = "hires"
    ) -> Tuple[np.ndarray, Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Runs model inference on two normalized images (H, W, 3).
        Returns:
            prob_map: (H, W) in [0, 1]
            sem1_map: (H, W) class indices if v2, else None
            sem2_map: (H, W) class indices if v2, else None
        """
        h = min(img1.shape[0], img2.shape[0])
        w = min(img1.shape[1], img2.shape[1])
        img1 = img1[:h, :w]
        img2 = img2[:h, :w]

        # Select model based on engine and profile
        active_model = self.legacy_model
        is_v2 = False
        if self.engine == "v2":
            if profile == "sentinel2" and self.v2_s2_model is not None:
                active_model = self.v2_s2_model
                is_v2 = True
            elif self.v2_hires_model is not None:
                active_model = self.v2_hires_model
                is_v2 = True

        if active_model is None:
            raise RuntimeError("No change detection model is available to execute inference.")

        prob_accum = np.zeros((h, w), dtype=np.float32)
        weight_accum = np.zeros((h, w), dtype=np.float32)
        sem1_accum = np.zeros((7, h, w), dtype=np.float32) if is_v2 else None
        sem2_accum = np.zeros((7, h, w), dtype=np.float32) if is_v2 else None

        hann_1d = np.hanning(PATCH_SIZE)
        hann_2d = np.outer(hann_1d, hann_1d).astype(np.float32)
        hann_2d = np.maximum(hann_2d, 1e-4)

        y_steps = max(1, math.ceil((h - PATCH_SIZE) / STRIDE) + 1) if h > PATCH_SIZE else 1
        x_steps = max(1, math.ceil((w - PATCH_SIZE) / STRIDE) + 1) if w > PATCH_SIZE else 1

        y_coords = [min(i * STRIDE, h - PATCH_SIZE) for i in range(y_steps)] if h >= PATCH_SIZE else [0]
        x_coords = [min(j * STRIDE, w - PATCH_SIZE) for j in range(x_steps)] if w >= PATCH_SIZE else [0]
        y_coords = sorted(list(set(y_coords)))
        x_coords = sorted(list(set(x_coords)))

        batch_t1, batch_t2, positions = [], [], []

        for y in y_coords:
            for x in x_coords:
                patch1 = img1[y : y + PATCH_SIZE, x : x + PATCH_SIZE]
                patch2 = img2[y : y + PATCH_SIZE, x : x + PATCH_SIZE]

                ph, pw = patch1.shape[:2]
                if ph < PATCH_SIZE or pw < PATCH_SIZE:
                    pad1 = np.zeros((PATCH_SIZE, PATCH_SIZE, 3), dtype=np.float32)
                    pad2 = np.zeros((PATCH_SIZE, PATCH_SIZE, 3), dtype=np.float32)
                    pad1[:ph, :pw] = patch1
                    pad2[:ph, :pw] = patch2
                    patch1, patch2 = pad1, pad2

                batch_t1.append(patch1.transpose(2, 0, 1))
                batch_t2.append(patch2.transpose(2, 0, 1))
                positions.append((y, x, ph, pw))

        BATCH_SIZE = 8
        for i in range(0, len(positions), BATCH_SIZE):
            b1 = torch.from_numpy(np.stack(batch_t1[i : i + BATCH_SIZE])).to(self.device)
            b2 = torch.from_numpy(np.stack(batch_t2[i : i + BATCH_SIZE])).to(self.device)

            with torch.no_grad():
                out = active_model(b1, b2)
                if is_v2:
                    change_logits, s1_logits, s2_logits = out
                    probs = torch.sigmoid(change_logits).squeeze(1).cpu().numpy()
                    s1_probs = F.softmax(s1_logits, dim=1).cpu().numpy()
                    s2_probs = F.softmax(s2_logits, dim=1).cpu().numpy()
                else:
                    probs = torch.sigmoid(out).squeeze(1).cpu().numpy()
                    s1_probs, s2_probs = None, None

            if probs.ndim == 2:
                probs = probs[np.newaxis, ...]

            for idx, p_tile in enumerate(probs):
                y, x, ph, pw = positions[i + idx]
                eh = min(ph, PATCH_SIZE)
                ew = min(pw, PATCH_SIZE)
                prob_accum[y : y + eh, x : x + ew] += p_tile[:eh, :ew] * hann_2d[:eh, :ew]
                weight_accum[y : y + eh, x : x + ew] += hann_2d[:eh, :ew]

                if is_v2 and s1_probs is not None:
                    sem1_accum[:, y : y + eh, x : x + ew] += s1_probs[idx, :, :eh, :ew] * hann_2d[:eh, :ew]
                    sem2_accum[:, y : y + eh, x : x + ew] += s2_probs[idx, :, :eh, :ew] * hann_2d[:eh, :ew]

        mask_valid = weight_accum > 0
        prob_map = np.zeros((h, w), dtype=np.float32)
        prob_map[mask_valid] = prob_accum[mask_valid] / weight_accum[mask_valid]

        sem1_map = np.argmax(sem1_accum, axis=0) if is_v2 else None
        sem2_map = np.argmax(sem2_accum, axis=0) if is_v2 else None

        return np.clip(prob_map, 0.0, 1.0), sem1_map, sem2_map

    # ── Post-Processing & Vectorization ────────────────────────────────────────

    def postprocess_mask(
        self,
        prob_map: np.ndarray,
        threshold: float = 0.5,
        min_pixels: int = 20,
    ) -> Tuple[np.ndarray, np.ndarray, int]:
        binary_mask = (prob_map >= threshold).astype(np.uint8)

        struct = ndimage.generate_binary_structure(2, 2)
        cleaned = ndimage.binary_opening(binary_mask, structure=struct, iterations=1)
        cleaned = ndimage.binary_closing(cleaned, structure=struct, iterations=1)

        labeled_array, num_features = ndimage.label(cleaned, structure=struct)

        if num_features == 0:
            return np.zeros_like(cleaned, dtype=np.uint8), labeled_array, 0

        component_sizes = np.bincount(labeled_array.ravel())
        too_small = component_sizes < min_pixels
        too_small_mask = too_small[labeled_array]
        cleaned[too_small_mask] = 0

        relabeled_array, num_clean_features = ndimage.label(cleaned, structure=struct)
        return cleaned.astype(np.uint8), relabeled_array, num_clean_features

    def extract_change_regions(
        self,
        clean_labeled: np.ndarray,
        prob_map: np.ndarray,
        num_features: int,
        geo_info: Optional[dict] = None,
        pixel_size_m: float = 0.5,
        nir1: Optional[np.ndarray] = None,
        nir2: Optional[np.ndarray] = None,
        rgb1_raw: Optional[np.ndarray] = None,
        rgb2_raw: Optional[np.ndarray] = None,
        sem1_map: Optional[np.ndarray] = None,
        sem2_map: Optional[np.ndarray] = None,
    ) -> Tuple[List[ChangeRegion], ClassificationResult, Optional[Dict[str, float]]]:
        regions = []
        labels_counts = {}
        h, w = clean_labeled.shape
        pixel_area_m2 = pixel_size_m ** 2

        affine = geo_info.get("transform") if geo_info else None
        src_crs = geo_info.get("crs") if geo_info else None

        scene_summary = {"building_gain": 0.0, "tree_loss": 0.0, "veg_loss": 0.0, "infra_gain": 0.0, "bare_gain": 0.0}

        for comp_id in range(1, num_features + 1):
            comp_mask = clean_labeled == comp_id
            pixel_count = int(np.sum(comp_mask))
            if pixel_count == 0:
                continue

            comp_confidence = float(np.mean(prob_map[comp_mask]))
            ys, xs = np.where(comp_mask)
            y_min, y_max = int(np.min(ys)), int(np.max(ys))
            x_min, x_max = int(np.min(xs)), int(np.max(xs))

            bbox_w = max(1, x_max - x_min + 1)
            bbox_h = max(1, y_max - y_min + 1)
            aspect_ratio = max(bbox_w / bbox_h, bbox_h / bbox_w)
            bbox_area = bbox_w * bbox_h
            compactness = float(pixel_count / bbox_area) if bbox_area > 0 else 0.0
            area_m2 = pixel_count * pixel_area_m2

            region_class = "other"
            class_detail = None

            # 1. If v2 semantic segmentation maps available
            if sem1_map is not None and sem2_map is not None:
                region_class, class_detail = classify_semantic_transition(
                    sem1_mask=sem1_map,
                    sem2_mask=sem2_map,
                    region_mask=comp_mask,
                    aspect_ratio=aspect_ratio,
                    compactness=compactness,
                    area_m2=area_m2,
                    confidence=comp_confidence,
                )
                for k, v in class_detail.items():
                    scene_summary[k] = scene_summary.get(k, 0.0) + v * pixel_count

            # 2. Spectral NDVI for Sentinel-2 GeoTIFF
            elif nir1 is not None and nir2 is not None and rgb1_raw is not None and rgb2_raw is not None:
                n1, n2 = nir1[:h, :w], nir2[:h, :w]
                r1, r2 = rgb1_raw[:, :, 0], rgb2_raw[:, :, 0]
                ndvi1 = (n1 - r1) / (n1 + r1 + 1e-6)
                ndvi2 = (n2 - r2) / (n2 + r2 + 1e-6)
                mean_ndvi1 = float(np.mean(ndvi1[comp_mask]))
                mean_ndvi2 = float(np.mean(ndvi2[comp_mask]))
                d_ndvi = mean_ndvi1 - mean_ndvi2

                if mean_ndvi1 > 0.25 and d_ndvi > 0.15:
                    region_class = "vegetation_loss" if d_ndvi < 0.35 else "deforestation"
                elif aspect_ratio > 3.0 and pixel_count * pixel_area_m2 > 800:
                    region_class = "infrastructure"
                elif compactness > 0.35 and comp_confidence > 0.65:
                    region_class = "construction"
                elif compactness < 0.25 and pixel_count * pixel_area_m2 > 1200:
                    region_class = "excavation"
                else:
                    region_class = "construction" if comp_confidence > 0.70 else "other"

            # 3. Spectral optical GLI / ExG for standard RGB imagery
            elif rgb1_raw is not None and rgb2_raw is not None:
                r1, g1, b1 = rgb1_raw[:, :, 0], rgb1_raw[:, :, 1], rgb1_raw[:, :, 2]
                r2, g2, b2 = rgb2_raw[:, :, 0], rgb2_raw[:, :, 1], rgb2_raw[:, :, 2]

                denom1 = 2.0 * g1 + r1 + b1 + 1e-6
                denom2 = 2.0 * g2 + r2 + b2 + 1e-6
                gli1 = (2.0 * g1 - r1 - b1) / denom1
                gli2 = (2.0 * g2 - r2 - b2) / denom2

                mean_gli1 = float(np.mean(gli1[comp_mask]))
                mean_gli2 = float(np.mean(gli2[comp_mask]))
                d_gli = mean_gli1 - mean_gli2

                exg1 = 2.0 * g1 - r1 - b1
                exg2 = 2.0 * g2 - r2 - b2
                mean_exg1 = float(np.mean(exg1[comp_mask]))
                d_exg = mean_exg1 - float(np.mean(exg2[comp_mask]))

                is_deforestation = (mean_gli1 > 0.18 and d_gli > 0.18)
                is_vegetation_loss = (
                    (mean_gli1 > 0.10 or mean_exg1 > 0.08) and
                    (d_gli > 0.08 or d_exg > 0.08)
                )

                if is_deforestation:
                    region_class = "deforestation"
                elif compactness > 0.25 and comp_confidence > 0.65:
                    region_class = "construction"
                elif is_vegetation_loss:
                    region_class = "vegetation_loss"
                elif aspect_ratio > 3.2 and (pixel_count * pixel_area_m2) > 800:
                    region_class = "infrastructure"
                elif compactness < 0.2 and pixel_count * pixel_area_m2 > 1500:
                    region_class = "excavation"
                else:
                    region_class = "construction" if comp_confidence > 0.75 else "other"
            else:
                region_class = "construction" if compactness > 0.35 else "other"

            labels_counts[region_class] = labels_counts.get(region_class, 0) + pixel_count

            # Trace polygon vertices
            if affine and src_crs:
                box_pts = [
                    (x_min, y_min),
                    (x_max, y_min),
                    (x_max, y_max),
                    (x_min, y_max),
                    (x_min, y_min),
                ]
                import rasterio.transform
                geo_pts = [rasterio.transform.xy(affine, py, px) for px, py in box_pts]

                if "4326" not in src_crs:
                    import pyproj
                    transformer = pyproj.Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)
                    wgs_pts = [list(transformer.transform(gx, gy)) for gx, gy in geo_pts]
                else:
                    wgs_pts = [[float(gx), float(gy)] for gx, gy in geo_pts]

                wgs_pts = [
                    [
                        max(-180.0, min(180.0, float(pt[0]))),
                        max(-90.0, min(90.0, float(pt[1]))),
                    ]
                    for pt in wgs_pts
                ]
                poly_coords = [wgs_pts]
            else:
                norm_pts = [
                    [float(x_min) / w, float(y_min) / h],
                    [float(x_max) / w, float(y_min) / h],
                    [float(x_max) / w, float(y_max) / h],
                    [float(x_min) / w, float(y_max) / h],
                    [float(x_min) / w, float(y_min) / h],
                ]
                poly_coords = [norm_pts]

            geom_dict = {"type": "Polygon", "coordinates": poly_coords}

            regions.append(
                ChangeRegion(
                    geometry=geom_dict,
                    area_pixels=pixel_count,
                    area_m2=round(area_m2, 2),
                    confidence=round(comp_confidence, 4),
                    label=region_class,
                    class_detail=class_detail,
                )
            )

        dominant_label = max(labels_counts.items(), key=lambda item: item[1])[0] if labels_counts else "other"
        total_pixels = sum(r.area_pixels for r in regions if r.area_pixels)
        weighted_conf = (
            sum(r.confidence * r.area_pixels for r in regions if r.confidence and r.area_pixels) / total_pixels
            if total_pixels > 0
            else float(np.mean(prob_map[clean_labeled > 0])) if np.any(clean_labeled > 0) else 0.5
        )

        # Normalize scene summary
        if total_pixels > 0:
            for k in scene_summary:
                scene_summary[k] = round(scene_summary[k] / total_pixels, 3)

        return (
            regions,
            ClassificationResult(label=dominant_label, confidence=round(weighted_conf, 4)),
            scene_summary if any(v > 0 for v in scene_summary.values()) else None,
        )

    # ── Artifact Generation (Mask & Overlay Preview) ───────────────────────────

    def save_artifacts(
        self,
        clean_binary: np.ndarray,
        rgb_raw_after: np.ndarray,
        storage_root: Path | str,
        investigation_id: Optional[str] = None,
    ) -> Tuple[str, str]:
        root = Path(storage_root).resolve()
        masks_dir = root / "masks"
        previews_dir = root / "previews"
        masks_dir.mkdir(parents=True, exist_ok=True)
        previews_dir.mkdir(parents=True, exist_ok=True)

        token = investigation_id or str(uuid.uuid4())
        mask_filename = f"mask_{token}.png"
        preview_filename = f"preview_{token}.png"

        mask_file_path = masks_dir / mask_filename
        preview_file_path = previews_dir / preview_filename

        mask_img = Image.fromarray((clean_binary * 255).astype(np.uint8), mode="L")
        mask_img.save(mask_file_path)

        after_uint8 = np.clip(rgb_raw_after * 255.0, 0, 255).astype(np.uint8)
        if after_uint8.ndim == 2:
            after_uint8 = np.stack([after_uint8] * 3, axis=-1)

        overlay = after_uint8.copy()
        change_idx = clean_binary > 0
        red_tint = np.array([239, 68, 68], dtype=np.float32)
        overlay[change_idx] = np.clip(
            0.6 * red_tint + 0.4 * after_uint8[change_idx].astype(np.float32), 0, 255
        ).astype(np.uint8)

        preview_img = Image.fromarray(overlay, mode="RGB")
        preview_img.save(preview_file_path)

        return str(mask_file_path), str(preview_file_path)

    # ── Main Entrypoint ────────────────────────────────────────────────────────

    def detect(
        self,
        before_path: str | Path,
        after_path: str | Path,
        storage_root: Path | str,
        investigation_id: Optional[str] = None,
        threshold: float = 0.5,
        min_area_m2: float = 50.0,
        pixel_size_m: Optional[float] = None,
    ) -> MLDetectChangeResponse:
        log.info(
            "Running detect: before=%s after=%s threshold=%.2f min_area=%.1f engine=%s",
            before_path,
            after_path,
            threshold,
            min_area_m2,
            self.engine,
        )

        img1_norm, nir1, geo1 = self.load_image_data(before_path)
        img2_norm, nir2, geo2 = self.load_image_data(after_path)

        # Determine GSD and Profile
        resolved_pixel_size = pixel_size_m or 0.5
        if (geo1 and geo1.get("crs")) or (geo2 and geo2.get("crs")):
            resolved_pixel_size = 10.0

        profile = "hires" if resolved_pixel_size <= 1.0 else "sentinel2"
        min_pixels = max(4, int(min_area_m2 / (resolved_pixel_size ** 2)))

        h = min(img1_norm.shape[0], img2_norm.shape[0])
        w = min(img1_norm.shape[1], img2_norm.shape[1])
        img1_norm = img1_norm[:h, :w]
        img2_norm = img2_norm[:h, :w]

        rgb1_raw = np.clip(img1_norm * IMAGENET_STD + IMAGENET_MEAN, 0.0, 1.0)
        rgb2_raw = np.clip(img2_norm * IMAGENET_STD + IMAGENET_MEAN, 0.0, 1.0)

        # 1. Neural network change probability
        neural_prob, sem1_map, sem2_map = self.predict_change_prob(img1_norm, img2_norm, profile=profile)

        # 2. Optical Spectral Vegetation Loss Fusion (if enabled)
        veg_loss_prob = np.zeros_like(neural_prob)
        if self.enable_spectral_fusion:
            if nir1 is not None and nir2 is not None:
                n1 = nir1[:h, :w]
                n2 = nir2[:h, :w]
                r1 = rgb1_raw[:, :, 0]
                r2 = rgb2_raw[:, :, 0]
                ndvi1 = (n1 - r1) / (n1 + r1 + 1e-6)
                ndvi2 = (n2 - r2) / (n2 + r2 + 1e-6)
                d_ndvi = ndvi1 - ndvi2
                veg_loss_prob = (1.0 / (1.0 + np.exp(-12.0 * (d_ndvi - 0.15)))) * (ndvi1 > 0.18).astype(np.float32)
            elif rgb1_raw is not None and rgb2_raw is not None:
                r1, g1, b1 = rgb1_raw[:, :, 0], rgb1_raw[:, :, 1], rgb1_raw[:, :, 2]
                r2, g2, b2 = rgb2_raw[:, :, 0], rgb2_raw[:, :, 1], rgb2_raw[:, :, 2]
                gli1 = (2.0 * g1 - r1 - b1) / (2.0 * g1 + r1 + b1 + 1e-6)
                gli2 = (2.0 * g2 - r2 - b2) / (2.0 * g2 + r2 + b2 + 1e-6)
                d_gli = gli1 - gli2
                veg_loss_prob = (1.0 / (1.0 + np.exp(-12.0 * (d_gli - 0.09)))) * (gli1 > 0.05).astype(np.float32)

        prob_map = np.maximum(neural_prob, veg_loss_prob)

        # 3. Post-process binary mask
        clean_binary, clean_labeled, num_features = self.postprocess_mask(
            prob_map, threshold=threshold, min_pixels=min_pixels
        )

        changed_pixels = int(np.sum(clean_binary))
        change_detected = changed_pixels >= min_pixels and num_features > 0

        overall_conf = float(np.mean(prob_map[clean_binary > 0])) if change_detected else float(1.0 - np.mean(prob_map))
        overall_conf = float(np.clip(overall_conf, 0.0, 1.0))

        # 4. Extract vector regions and classification
        regions, classification, sem_summary = self.extract_change_regions(
            clean_labeled=clean_labeled,
            prob_map=prob_map,
            num_features=num_features,
            geo_info=geo1 or geo2,
            pixel_size_m=resolved_pixel_size,
            nir1=nir1,
            nir2=nir2,
            rgb1_raw=rgb1_raw,
            rgb2_raw=rgb2_raw,
            sem1_map=sem1_map,
            sem2_map=sem2_map,
        )

        # 5. Vehicle Detection (Resolution-constrained: GSD <= 0.5m)
        vehicle_res = self.vehicle_service.analyze_pair(
            rgb1_raw=rgb1_raw,
            rgb2_raw=rgb2_raw,
            pixel_size_m=resolved_pixel_size,
        )

        # 6. Save artifacts
        mask_path, preview_path = self.save_artifacts(
            clean_binary=clean_binary,
            rgb_raw_after=rgb2_raw,
            storage_root=storage_root,
            investigation_id=investigation_id,
        )

        bounds = None
        if geo1 and geo1.get("bounds"):
            bounds = geo1["bounds"]
        elif geo2 and geo2.get("bounds"):
            bounds = geo2["bounds"]

        total_area_m2 = round(changed_pixels * (resolved_pixel_size ** 2), 2)

        return MLDetectChangeResponse(
            change_detected=change_detected,
            confidence=round(overall_conf, 4),
            changed_area_pixels=changed_pixels,
            changed_area_m2=total_area_m2,
            mask_path=mask_path,
            change_mask_path=mask_path,
            preview_path=preview_path,
            mask_preview_path=preview_path,
            bounds=bounds,
            mask_bounds=bounds,
            change_regions=regions,
            classification=classification if change_detected else ClassificationResult(label="no_change", confidence=round(overall_conf, 4)),
            model_version=f"SatQuery-Siamese-UNet-v1.0 ({self.engine})",
            preprocessing_version="v1.0-imagenet-norm-sliding-window",
            threshold=threshold,
            profile_used=profile,
            thresholds_used={"threshold": threshold, "min_area_m2": min_area_m2},
            semantic_summary=sem_summary,
            vehicles=VehiclesResult(**vehicle_res),
        )
