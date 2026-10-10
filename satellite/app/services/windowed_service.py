"""
Windowed Sentinel-2 COG service.
Performs efficient AOI-windowed reads from Sentinel-2 COGs on AWS S3,
computes SCL-based AOI cloud cover, aligns grids to same CRS & dimensions,
and outputs GeoTIFF rasters and web PNG previews.
"""
from __future__ import annotations

import hashlib
import logging
import os
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

log = logging.getLogger(__name__)


def compute_cache_key(scene_ids: List[str], bbox: List[float]) -> str:
    """Generate deterministic hash from scene IDs and AOI coordinates."""
    key_str = "_".join(scene_ids) + "_" + "_".join(f"{coord:.5f}" for coord in bbox)
    return hashlib.sha256(key_str.encode("utf-8")).hexdigest()[:16]


class WindowedSentinelService:
    def __init__(self, storage_root: str = "/data/storage"):
        self.storage_root = Path(storage_root).resolve()
        self.satellite_dir = self.storage_root / "satellite"
        self.satellite_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_asset_url(item: dict, asset_key: str) -> Optional[str]:
        """Extract HTTP/HTTPS asset URL from a STAC item."""
        assets = item.get("assets", {})
        if asset_key in assets:
            href = assets[asset_key].get("href")
            if href:
                return href
        return None

    def compute_aoi_cloud_fraction(self, item: dict, bbox: List[float]) -> float:
        """
        Compute cloud fraction INSIDE the AOI using the SCL asset.
        SCL classes for clouds/shadows:
          3: Cloud shadow
          8: Cloud medium probability
          9: Cloud high probability
          10: Thin cirrus
        """
        scl_url = self.get_asset_url(item, "scl")
        if not scl_url:
            # Fallback to scene-level metadata
            return float(item.get("properties", {}).get("eo:cloud_cover", 0.0))

        try:
            import rasterio
            from rasterio.windows import from_bounds
            from rasterio.warp import transform_bounds

            with rasterio.open(scl_url) as src:
                w, s, e, n = transform_bounds("EPSG:4326", src.crs, *bbox)
                win = from_bounds(w, s, e, n, src.transform)
                scl_data = src.read(1, window=win)
                if scl_data.size == 0:
                    return float(item.get("properties", {}).get("eo:cloud_cover", 0.0))
                cloud_mask = np.isin(scl_data, [3, 8, 9, 10])
                return float(cloud_mask.mean() * 100.0)
        except Exception as e:
            log.warning("Could not read SCL cloud mask for %s: %s", item.get("id"), e)
            return float(item.get("properties", {}).get("eo:cloud_cover", 0.0))

    def fetch_and_align_pair(
        self,
        before_item: dict,
        after_item: dict,
        bbox: List[float],
    ) -> Tuple[Path, Path, Path, Path, str, List[float]]:
        """
        Fetch visual RGB rasters for before & after, project older onto newer grid,
        save 3-band GeoTIFFs and PNG previews in storage_root/satellite/<hash>/.

        Returns:
            (before_tif, before_png, after_tif, after_png, crs_str, aligned_bounds)
        """
        import rasterio
        from rasterio.windows import from_bounds
        from rasterio.warp import transform_bounds, reproject, Resampling

        before_id = before_item.get("id", "before")
        after_id = after_item.get("id", "after")
        cache_id = compute_cache_key([before_id, after_id], bbox)

        pair_dir = self.satellite_dir / cache_id
        pair_dir.mkdir(parents=True, exist_ok=True)

        before_tif = pair_dir / "before.tif"
        before_png = pair_dir / "before_preview.png"
        after_tif = pair_dir / "after.tif"
        after_png = pair_dir / "after_preview.png"

        before_url = self.get_asset_url(before_item, "visual")
        after_url = self.get_asset_url(after_item, "visual")

        if not before_url or not after_url:
            raise ValueError(f"Missing visual RGB asset in STAC items: before={before_url}, after={after_url}")

        # Check existing cache
        if (
            before_tif.exists()
            and before_png.exists()
            and after_tif.exists()
            and after_png.exists()
            and before_tif.stat().st_size > 1000
        ):
            log.info("windowed_service: cache hit for %s", cache_id)
            with rasterio.open(after_tif) as ref:
                crs_str = ref.crs.to_string() if ref.crs else "EPSG:32644"
            return before_tif, before_png, after_tif, after_png, crs_str, bbox

        log.info("windowed_service: fetching and windowing COG for before=%s, after=%s", before_id, after_id)

        # 1. Read After scene as master grid
        with rasterio.open(after_url) as src_after:
            w_after, s_after, e_after, n_after = transform_bounds("EPSG:4326", src_after.crs, *bbox)
            win_after = from_bounds(w_after, s_after, e_after, n_after, src_after.transform)
            transform_after = src_after.window_transform(win_after)
            after_data = src_after.read([1, 2, 3], window=win_after)
            crs_after = src_after.crs
            crs_str = crs_after.to_string() if crs_after else "EPSG:32644"

        channels, height, width = after_data.shape
        if height == 0 or width == 0:
            raise ValueError(f"AOI resulted in empty raster window for bbox {bbox}")

        # 2. Read Before scene and reproject onto after grid
        with rasterio.open(before_url) as src_before:
            before_data = np.zeros((channels, height, width), dtype=np.uint8)
            for b_idx in range(channels):
                reproject(
                    source=rasterio.band(src_before, b_idx + 1),
                    destination=before_data[b_idx],
                    src_transform=src_before.transform,
                    src_crs=src_before.crs,
                    dst_transform=transform_after,
                    dst_crs=crs_after,
                    resampling=Resampling.bilinear,
                )

        # 3. Write GeoTIFF files
        out_profile = {
            "driver": "GTiff",
            "height": height,
            "width": width,
            "count": 3,
            "dtype": rasterio.uint8,
            "crs": crs_after,
            "transform": transform_after,
            "compress": "deflate",
        }

        with rasterio.open(after_tif, "w", **out_profile) as dst:
            dst.write(after_data)

        with rasterio.open(before_tif, "w", **out_profile) as dst:
            dst.write(before_data)

        # 4. Write web-friendly PNG previews
        self._write_png_preview(before_data, before_png)
        self._write_png_preview(after_data, after_png)

        log.info("windowed_service: saved aligned pair to %s", pair_dir)
        return before_tif, before_png, after_tif, after_png, crs_str, bbox

    @staticmethod
    def _write_png_preview(rgb_arr: np.ndarray, out_png: Path) -> None:
        """Save (3, H, W) uint8 raster as an RGB PNG."""
        # Transpose from (3, H, W) to (H, W, 3)
        img_arr = np.transpose(rgb_arr, (1, 2, 0))
        img = Image.fromarray(img_arr, mode="RGB")
        out_png.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_png, format="PNG")
