from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, List, Tuple
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

from app.services.geometry import (
    compute_projected_area_m2,
    estimate_utm_epsg,
    project_geometry,
    unproject_geometry,
)

log = logging.getLogger(__name__)


class SensitiveLayerManager:
    """
    Loads pluggable authoritative sensitive zoning layers from GeoJSON files.
    Calculates exact projected polygon overlap percentages and intersecting geometries.
    """

    def __init__(self, data_dir: str = "gis/data"):
        self.data_dir = Path(data_dir)
        self._layers: list[dict[str, Any]] = []
        self.load_layers()

    def load_layers(self) -> None:
        self._layers = []
        if not self.data_dir.exists():
            log.warning("Sensitive layer directory does not exist: %s", self.data_dir)
            return

        for path in self.data_dir.glob("*.geojson"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                layer_id = data.get("metadata", {}).get("layer_id", path.stem)
                layer_name = data.get("metadata", {}).get(
                    "layer_name", f"Authoritative Layer ({path.stem})"
                )

                # Union all polygon features in the file
                geoms = []
                for feat in data.get("features", []):
                    geom = feat.get("geometry")
                    if geom:
                        s = shape(geom)
                        if not s.is_valid:
                            from shapely.validation import make_valid
                            s = make_valid(s)
                        geoms.append(s)

                if geoms:
                    combined = unary_union(geoms)
                    self._layers.append({
                        "id": layer_id,
                        "name": layer_name,
                        "geometry": combined,
                        "source_file": path.name,
                    })
                    log.info("Loaded sensitive layer: %s (%s)", layer_name, path.name)
            except Exception as e:
                log.error("Failed to load sensitive layer from %s: %s", path, e)

    def analyze_intersections(
        self,
        change_geom: Any,
        change_area_m2: float,
    ) -> list[dict[str, Any]]:
        """
        Calculates intersection area and percentage against all loaded layers.
        """
        intersections = []
        if change_geom is None or change_geom.is_empty or change_area_m2 <= 0:
            return intersections

        centroid = change_geom.centroid
        epsg = estimate_utm_epsg(centroid.x, centroid.y)
        change_proj = project_geometry(change_geom, epsg)

        for layer in self._layers:
            layer_geom = layer["geometry"]
            if not change_geom.intersects(layer_geom):
                continue

            # Intersection in WGS84
            raw_intersection = change_geom.intersection(layer_geom)
            if raw_intersection.is_empty:
                continue

            # Measure projected overlap area
            intersection_proj = project_geometry(raw_intersection, epsg)
            overlap_area_m2 = float(intersection_proj.area)
            overlap_pct = min(1.0, max(0.0, overlap_area_m2 / change_area_m2))

            intersections.append({
                "layer_name": layer["name"],
                "layer_id": layer["id"],
                "overlap_pct": round(overlap_pct, 4),
                "overlap_area_m2": round(overlap_area_m2, 2),
                "geometry": mapping(raw_intersection),
            })

        return intersections
