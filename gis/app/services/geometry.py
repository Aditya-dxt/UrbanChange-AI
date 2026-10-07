from __future__ import annotations

import logging
import math
from typing import Any, Tuple
from shapely.geometry import shape, mapping, Polygon, MultiPolygon
from shapely.ops import transform
import pyproj

log = logging.getLogger(__name__)


def estimate_utm_epsg(lon: float, lat: float) -> int:
    """Estimate the UTM EPSG code for a given WGS84 (lon, lat) point."""
    zone = int((lon + 180) / 6) + 1
    zone = max(1, min(60, zone))
    return (32600 + zone) if lat >= 0 else (32700 + zone)


def project_geometry(geom: Any, target_epsg: int) -> Any:
    """Project a Shapely geometry from EPSG:4326 to a target projected CRS."""
    transformer = pyproj.Transformer.from_crs("EPSG:4326", f"EPSG:{target_epsg}", always_xy=True)
    return transform(transformer.transform, geom)


def unproject_geometry(geom: Any, source_epsg: int) -> Any:
    """Project a Shapely geometry from a projected CRS back to EPSG:4326."""
    transformer = pyproj.Transformer.from_crs(f"EPSG:{source_epsg}", "EPSG:4326", always_xy=True)
    return transform(transformer.transform, geom)


def compute_projected_area_m2(geom: Any) -> float:
    """
    Compute area strictly in square meters using a projected equal-area or local UTM CRS.
    Never computes area directly in degree coordinates.
    """
    if geom is None or geom.is_empty:
        return 0.0

    centroid = geom.centroid
    epsg = estimate_utm_epsg(centroid.x, centroid.y)
    geom_proj = project_geometry(geom, epsg)
    return float(geom_proj.area)


def parse_geojson_geometry(geom_dict: dict[str, Any]) -> Any:
    """Parse and validate a GeoJSON geometry dictionary into a Shapely geometry."""
    try:
        s = shape(geom_dict)
        if not s.is_valid:
            from shapely.validation import make_valid
            s = make_valid(s)
        return s
    except Exception as exc:
        log.warning("Could not parse GeoJSON geometry: %s", exc)
        return None
