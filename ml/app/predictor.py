"""
Inference engine for SatQuery Siamese U-Net Change Detection.
Handles GeoTIFF (Sentinel-2) and PNG/JPEG images, sliding window tiling,
georeferencing, morphological post-processing, and spectral/shape classification.
"""
from __future__ import annotations

import logging
import math
import os
import uuid
from pathlib import Path
from typing import Any, List, Optional, Tuple

import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F
from scipy import ndimage
from shapely.geometry import Polygon, mapping

try:
    from app.model import SiameseUNetAttention
    from app.schemas import ChangeRegion, ClassificationResult, MLDetectChangeResponse
except ImportError:
    from ml.app.model import SiameseUNetAttention
    from ml.app.schemas import ChangeRegion, ClassificationResult, MLDetectChangeResponse

log = logging.getLogger("ml.predictor")

# Constants
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 1, 3)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 1, 3)
PATCH_SIZE = 256
OVERLAP = 32
STRIDE = PATCH_SIZE - OVERLAP  # 224


class ChangePredictor:
    """Manages model lifecycle and end-to-end change detection inference."""

    def __init__(self, weights_path: Path | str, device: Optional[str] = None):
        self.weights_path = Path(weights_path).resolve()
        if device:
            self.device = torch.device(device)
        else:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        log.info("Initializing ChangePredictor on device: %s", self.device)
        self.model = SiameseUNetAttention().to(self.device)
        self._load_weights()
        self.model.eval()

    def _load_weights(self) -> None:
        if not self.weights_path.exists():
            try:
                from scripts.download_weights import ensure_weights
            except ImportError:
                from ml.scripts.download_weights import ensure_weights
            log.info("Weights not found at %s. Attempting to ensure weights...", self.weights_path)
            ensure_weights(self.weights_path)

        log.info("Loading model weights from: %s", self.weights_path)
        checkpoint = torch.load(str(self.weights_path), map_location=self.device)
        state_dict = checkpoint["model_state_dict"] if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint else checkpoint
        res = self.model.load_state_dict(state_dict)
        log.info("Model loaded successfully: %s", res)

    # ── Image Loading & Preprocessing ──────────────────────────────────────────

    def load_image_data(self, file_path: str | Path) -> Tuple[np.ndarray, Optional[np.ndarray], Optional[dict]]:
        """
        Loads an image file (GeoTIFF, PNG, JPEG).
        Returns:
            rgb_norm: (H, W, 3) float32 normalized with ImageNet stats
            nir_band: (H, W) float32 in [0, 1] if available (e.g. Sentinel-2 B08), else None
            geo_info: Dict with {crs, transform, bounds, width, height} if georeferenced, else None
        """
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Input image not found: {path}")

        # Try reading with rasterio for GeoTIFF
        geo_info = None
        nir_band = None

        if path.suffix.lower() in [".tif", ".tiff"]:
            try:
                import rasterio
                from rasterio.warp import transform_bounds

                with rasterio.open(path) as src:
                    count = src.count
                    crs_str = str(src.crs) if src.crs else None
                    transform = src.transform
                    width, height = src.width, src.height

                    # Sentinel-2 4-band stack convention: [B02, B03, B04, B08] (Blue, Green, Red, NIR)
                    if count >= 4:
                        b02 = src.read(1).astype(np.float32)  # Blue
                        b03 = src.read(2).astype(np.float32)  # Green
                        b04 = src.read(3).astype(np.float32)  # Red
                        b08 = src.read(4).astype(np.float32)  # NIR
                        # Scale Sentinel-2 reflectance (typically 0-10000, 3000 max for normal surface)
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

                    # Compute WGS84 bounds
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

        # Standard PNG/JPEG loading via PIL
        pil_img = Image.open(path).convert("RGB")
        rgb_raw = np.array(pil_img, dtype=np.float32) / 255.0
        rgb_norm = (rgb_raw - IMAGENET_MEAN) / IMAGENET_STD
        return rgb_norm.astype(np.float32), None, None

    # ── Inference with Sliding Window ──────────────────────────────────────────

    def predict_change_prob(self, img1: np.ndarray, img2: np.ndarray) -> np.ndarray:
        """
        Runs model inference on two normalized images (H, W, 3).
        Handles arbitrary sizes via overlapping sliding window.
        Returns probability map (H, W) in [0, 1].
        """
        h1, w1, _ = img1.shape
        h2, w2, _ = img2.shape
        h = min(h1, h2)
        w = min(w1, w2)
        img1 = img1[:h, :w]
        img2 = img2[:h, :w]

        # Case 1: Exact tile size (256, 256)
        if h == PATCH_SIZE and w == PATCH_SIZE:
            t1 = torch.from_numpy(img1.transpose(2, 0, 1)).unsqueeze(0).to(self.device)
            t2 = torch.from_numpy(img2.transpose(2, 0, 1)).unsqueeze(0).to(self.device)
            with torch.no_grad():
                logits = self.model(t1, t2)
                prob = torch.sigmoid(logits).squeeze().cpu().numpy()
            return np.clip(prob, 0.0, 1.0)

        # Case 2: Arbitrary size - sliding window with smooth Hann weight blending
        prob_accum = np.zeros((h, w), dtype=np.float32)
        weight_accum = np.zeros((h, w), dtype=np.float32)

        # Create 2D Hann window for overlap feathering
        hann_1d = np.hanning(PATCH_SIZE)
        hann_2d = np.outer(hann_1d, hann_1d).astype(np.float32)
        hann_2d = np.maximum(hann_2d, 1e-4)

        y_steps = max(1, math.ceil((h - PATCH_SIZE) / STRIDE) + 1) if h > PATCH_SIZE else 1
        x_steps = max(1, math.ceil((w - PATCH_SIZE) / STRIDE) + 1) if w > PATCH_SIZE else 1

        y_coords = [min(i * STRIDE, h - PATCH_SIZE) for i in range(y_steps)] if h >= PATCH_SIZE else [0]
        x_coords = [min(j * STRIDE, w - PATCH_SIZE) for j in range(x_steps)] if w >= PATCH_SIZE else [0]
        y_coords = sorted(list(set(y_coords)))
        x_coords = sorted(list(set(x_coords)))

        batch_t1 = []
        batch_t2 = []
        positions = []

        for y in y_coords:
            for x in x_coords:
                patch1 = img1[y : y + PATCH_SIZE, x : x + PATCH_SIZE]
                patch2 = img2[y : y + PATCH_SIZE, x : x + PATCH_SIZE]

                # Pad if image is smaller than 256
                ph, pw, _ = patch1.shape
                if ph < PATCH_SIZE or pw < PATCH_SIZE:
                    pad_patch1 = np.zeros((PATCH_SIZE, PATCH_SIZE, 3), dtype=np.float32)
                    pad_patch2 = np.zeros((PATCH_SIZE, PATCH_SIZE, 3), dtype=np.float32)
                    pad_patch1[:ph, :pw] = patch1
                    pad_patch2[:ph, :pw] = patch2
                    patch1, patch2 = pad_patch1, pad_patch2

                batch_t1.append(patch1.transpose(2, 0, 1))
                batch_t2.append(patch2.transpose(2, 0, 1))
                positions.append((y, x, ph, pw))

        # Forward pass in batches of 8
        BATCH_SIZE = 8
        for i in range(0, len(positions), BATCH_SIZE):
            b1 = torch.from_numpy(np.stack(batch_t1[i : i + BATCH_SIZE])).to(self.device)
            b2 = torch.from_numpy(np.stack(batch_t2[i : i + BATCH_SIZE])).to(self.device)

            with torch.no_grad():
                logits = self.model(b1, b2)
                probs = torch.sigmoid(logits).squeeze(1).cpu().numpy()

            if probs.ndim == 2:
                probs = probs[np.newaxis, ...]

            for idx, p_tile in enumerate(probs):
                y, x, ph, pw = positions[i + idx]
                effective_h = min(ph, PATCH_SIZE)
                effective_w = min(pw, PATCH_SIZE)
                prob_accum[y : y + effective_h, x : x + effective_w] += (
                    p_tile[:effective_h, :effective_w] * hann_2d[:effective_h, :effective_w]
                )
                weight_accum[y : y + effective_h, x : x + effective_w] += hann_2d[:effective_h, :effective_w]

        # Normalize by blended weights
        mask_valid = weight_accum > 0
        prob_map = np.zeros((h, w), dtype=np.float32)
        prob_map[mask_valid] = prob_accum[mask_valid] / weight_accum[mask_valid]
        return np.clip(prob_map, 0.0, 1.0)

    # ── Post-Processing & Vectorization ────────────────────────────────────────

    def postprocess_mask(
        self,
        prob_map: np.ndarray,
        threshold: float = 0.5,
        min_pixels: int = 20,
    ) -> Tuple[np.ndarray, np.ndarray, int]:
        """
        Applies binary threshold, morphological opening (5x5 kernel),
        and removes connected components smaller than min_pixels.
        Returns:
            binary_mask: (H, W) uint8 {0, 1}
            labeled_mask: (H, W) int32 connected component labels
            num_features: int
        """
        raw_binary = (prob_map >= threshold).astype(np.uint8)

        # Morphological opening with 5x5 structuring element to clean salt-and-pepper noise
        struct = ndimage.generate_binary_structure(2, 2)  # 3x3 8-connectivity
        opened = ndimage.binary_opening(raw_binary, structure=struct, iterations=2).astype(np.uint8)

        # Label connected components
        labeled_mask, num_features = ndimage.label(opened, structure=struct)
        if num_features == 0:
            return np.zeros_like(opened), labeled_mask, 0

        # Filter small areas
        counts = np.bincount(labeled_mask.ravel())
        too_small = counts < min_pixels
        too_small[0] = False  # background
        labeled_mask[too_small[labeled_mask]] = 0

        clean_binary = (labeled_mask > 0).astype(np.uint8)
        # Re-label clean components
        clean_labeled, clean_count = ndimage.label(clean_binary, structure=struct)
        return clean_binary, clean_labeled, clean_count

    # ── Geometry Vectorization & Classification ────────────────────────────────

    def extract_change_regions(
        self,
        clean_labeled: np.ndarray,
        prob_map: np.ndarray,
        num_features: int,
        geo_info: Optional[dict],
        pixel_size_m: float = 0.5,
        nir1: Optional[np.ndarray] = None,
        nir2: Optional[np.ndarray] = None,
        rgb1_raw: Optional[np.ndarray] = None,
        rgb2_raw: Optional[np.ndarray] = None,
    ) -> Tuple[List[ChangeRegion], ClassificationResult]:
        """
        Extracts GeoJSON Polygon features for each connected component.
        Computes accurate area in m^2, confidence, and assigns semantic classification.
        """
        if num_features == 0:
            return [], ClassificationResult(label="no_change", confidence=0.0)

        regions: List[ChangeRegion] = []
        labels_counts = {}

        h, w = clean_labeled.shape
        pixel_area_m2 = (pixel_size_m ** 2)

        # Setup coordinate transformation if georeferenced
        affine = geo_info.get("transform") if geo_info else None
        src_crs = geo_info.get("crs") if geo_info else None

        for comp_id in range(1, num_features + 1):
            comp_mask = clean_labeled == comp_id
            pixel_count = int(np.sum(comp_mask))
            if pixel_count <= 0:
                continue

            comp_probs = prob_map[comp_mask]
            comp_confidence = float(np.mean(comp_probs))

            # Bounding box of component
            ys, xs = np.where(comp_mask)
            y_min, y_max = int(np.min(ys)), int(np.max(ys))
            x_min, x_max = int(np.min(xs)), int(np.max(xs))
            box_h = max(1, y_max - y_min + 1)
            box_w = max(1, x_max - x_min + 1)
            aspect_ratio = max(box_h / box_w, box_w / box_h)

            # Approximate perimeter via boundary pixels
            eroded = ndimage.binary_erosion(comp_mask)
            perimeter_pixels = max(4, int(np.sum(comp_mask ^ eroded)))
            compactness = float((4.0 * math.pi * pixel_count) / (perimeter_pixels ** 2))

            # Classification rules:
            # 1. Spectral NDVI difference if NIR available
            region_class = "construction"
            if nir1 is not None and nir2 is not None and rgb1_raw is not None and rgb2_raw is not None:
                r1 = rgb1_raw[:, :, 0]
                r2 = rgb2_raw[:, :, 0]
                ndvi1 = (nir1 - r1) / (nir1 + r1 + 1e-6)
                ndvi2 = (nir2 - r2) / (nir2 + r2 + 1e-6)
                mean_ndvi1 = float(np.mean(ndvi1[comp_mask]))
                mean_ndvi2 = float(np.mean(ndvi2[comp_mask]))
                d_ndvi = mean_ndvi2 - mean_ndvi1
                if mean_ndvi1 > 0.25 and d_ndvi < -0.15:
                    region_class = "vegetation_loss" if d_ndvi > -0.35 else "deforestation"
            else:
                # 2. Shape-based classification
                if aspect_ratio > 3.2 and (pixel_count * pixel_area_m2) > 800:
                    region_class = "infrastructure"  # elongated road, railway, pipeline
                elif compactness > 0.35 and comp_confidence > 0.65:
                    region_class = "construction"   # compact building/site
                elif compactness < 0.2 and pixel_count * pixel_area_m2 > 1500:
                    region_class = "excavation"     # irregular earthworks/quarry
                else:
                    region_class = "other"

            labels_counts[region_class] = labels_counts.get(region_class, 0) + pixel_count

            # Extract polygon ring
            # We construct a simplified bounding polygon or boundary trace
            # For robustness and exact WGS84 GeoJSON validity, we trace coordinates
            poly_coords = []
            if affine and src_crs:
                # Georeferenced: transform pixel coordinates to geographic coordinates
                # We sample boundary vertices
                box_pts = [
                    (x_min, y_min),
                    (x_max, y_min),
                    (x_max, y_max),
                    (x_min, y_max),
                    (x_min, y_min),
                ]
                import rasterio.transform
                geo_pts = [rasterio.transform.xy(affine, py, px) for px, py in box_pts]

                # Convert to WGS84 (lon, lat) if projected
                if "4326" not in src_crs:
                    import pyproj
                    transformer = pyproj.Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)
                    wgs_pts = [list(transformer.transform(gx, gy)) for gx, gy in geo_pts]
                else:
                    wgs_pts = [[float(gx), float(gy)] for gx, gy in geo_pts]

                # Validate coordinates range
                wgs_pts = [
                    [
                        max(-180.0, min(180.0, float(pt[0]))),
                        max(-90.0, min(90.0, float(pt[1]))),
                    ]
                    for pt in wgs_pts
                ]
                poly_coords = [wgs_pts]
                area_m2 = pixel_count * pixel_area_m2
            else:
                # Non-georeferenced: output normalized [0, 1] coordinates
                # Lon, lat in [0, 1] satisfies [-180, 180] and [-90, 90] bounds strictly
                norm_pts = [
                    [float(x_min) / w, float(y_min) / h],
                    [float(x_max) / w, float(y_min) / h],
                    [float(x_max) / w, float(y_max) / h],
                    [float(x_min) / w, float(y_max) / h],
                    [float(x_min) / w, float(y_min) / h],
                ]
                poly_coords = [norm_pts]
                area_m2 = pixel_count * pixel_area_m2

            geom_dict = {"type": "Polygon", "coordinates": poly_coords}

            regions.append(
                ChangeRegion(
                    geometry=geom_dict,
                    area_pixels=pixel_count,
                    area_m2=round(area_m2, 2),
                    confidence=round(comp_confidence, 4),
                    label=region_class,
                )
            )

        # Determine dominant scene classification
        dominant_label = max(labels_counts.items(), key=lambda item: item[1])[0] if labels_counts else "other"
        total_pixels = sum(r.area_pixels for r in regions if r.area_pixels)
        weighted_conf = (
            sum(r.confidence * r.area_pixels for r in regions if r.confidence and r.area_pixels) / total_pixels
            if total_pixels > 0
            else float(np.mean(prob_map[clean_labeled > 0])) if np.any(clean_labeled > 0) else 0.5
        )

        return regions, ClassificationResult(label=dominant_label, confidence=round(weighted_conf, 4))

    # ── Artifact Generation (Mask & Overlay Preview) ───────────────────────────

    def save_artifacts(
        self,
        clean_binary: np.ndarray,
        rgb_raw_after: np.ndarray,
        storage_root: Path | str,
        investigation_id: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Saves change mask and semi-transparent red overlay preview to storage_root.
        Returns relative asset paths: (mask_path, preview_path).
        """
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

        # Save binary mask (0 or 255)
        mask_img = Image.fromarray((clean_binary * 255).astype(np.uint8), mode="L")
        mask_img.save(mask_file_path)

        # Save RGB preview with red highlighted change regions
        h, w = clean_binary.shape
        after_uint8 = np.clip(rgb_raw_after * 255.0, 0, 255).astype(np.uint8)
        if after_uint8.ndim == 2:
            after_uint8 = np.stack([after_uint8] * 3, axis=-1)

        # Create semi-transparent overlay: red tint on changed pixels
        overlay = after_uint8.copy()
        change_idx = clean_binary > 0
        # Blend 60% red ([239, 68, 68]) + 40% original
        red_tint = np.array([239, 68, 68], dtype=np.float32)
        overlay[change_idx] = np.clip(
            0.6 * red_tint + 0.4 * after_uint8[change_idx].astype(np.float32), 0, 255
        ).astype(np.uint8)

        preview_img = Image.fromarray(overlay, mode="RGB")
        preview_img.save(preview_file_path)

        # Return storage paths (relative or absolute, backend accepts both)
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
        """
        Executes complete change detection pipeline on before/after pair.
        """
        log.info(
            "Running detect: before=%s after=%s threshold=%.2f min_area=%.1f",
            before_path, after_path, threshold, min_area_m2,
        )

        # Load both images
        img1_norm, nir1, geo1 = self.load_image_data(before_path)
        img2_norm, nir2, geo2 = self.load_image_data(after_path)

        # Resolve pixel resolution
        resolved_pixel_size = pixel_size_m or 0.5
        if geo1 and geo1.get("crs"):
            # If GeoTIFF with Sentinel-2 resolution
            resolved_pixel_size = 10.0

        min_pixels = max(4, int(min_area_m2 / (resolved_pixel_size ** 2)))

        # Run model inference
        prob_map = self.predict_change_prob(img1_norm, img2_norm)

        # Post-process binary mask
        clean_binary, clean_labeled, num_features = self.postprocess_mask(
            prob_map, threshold=threshold, min_pixels=min_pixels
        )

        changed_pixels = int(np.sum(clean_binary))
        change_detected = changed_pixels >= min_pixels and num_features > 0

        # Overall confidence
        if change_detected:
            overall_conf = float(np.mean(prob_map[clean_binary > 0]))
        else:
            # If no change detected, confidence of 'no change'
            overall_conf = float(1.0 - np.mean(prob_map))
        overall_conf = float(np.clip(overall_conf, 0.0, 1.0))

        # Reconstruct unnormalized raw RGB for previews
        rgb2_raw = np.clip(img2_norm * IMAGENET_STD + IMAGENET_MEAN, 0.0, 1.0)
        rgb1_raw = np.clip(img1_norm * IMAGENET_STD + IMAGENET_MEAN, 0.0, 1.0)

        # Extract vector regions & classification
        regions, classification = self.extract_change_regions(
            clean_labeled=clean_labeled,
            prob_map=prob_map,
            num_features=num_features,
            geo_info=geo1 or geo2,
            pixel_size_m=resolved_pixel_size,
            nir1=nir1,
            nir2=nir2,
            rgb1_raw=rgb1_raw,
            rgb2_raw=rgb2_raw,
        )

        # Save mask and preview artifacts
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
            preview_path=preview_path,
            bounds=bounds,
            change_regions=regions,
            classification=classification if change_detected else ClassificationResult(label="no_change", confidence=round(overall_conf, 4)),
            model_version="SatQuery-Siamese-UNet-v1.0",
            preprocessing_version="v1.0-imagenet-norm-sliding-window",
            threshold=threshold,
        )
