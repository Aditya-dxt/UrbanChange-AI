"""
GIS mapper.

The ONLY place that translates external GIS field names → internal schema.

Integration-first rules:
  - Unknown fields logged at DEBUG
  - Missing changed_area_m2 → MapperError
  - sensitive_intersections and nearby_features mapped defensively
  - Returns (GISResultInternal, raw_payload_dict)
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from app.errors import MapperError
from app.schemas.internal.gis import (
    GISResultInternal,
    NearbyFeatureInternal,
    SensitiveIntersectionInternal,
)

log = logging.getLogger(__name__)

_KNOWN_KEYS = frozenset({
    "changed_area_m2", "sensitive_intersections", "overlap_percentages",
    "nearby_features", "geojson", "layer_versions", "distances",
})

_INTERSECTION_KNOWN = frozenset({
    "layer_name", "layer_id", "overlap_pct", "geometry",
})

_NEARBY_KNOWN = frozenset({
    "feature_type", "name", "distance_m", "geometry",
})


def _log_extra(raw: dict, context: str) -> None:
    known = _KNOWN_KEYS if context == "root" else (
        _INTERSECTION_KNOWN if context == "intersection" else _NEARBY_KNOWN
    )
    extra = set(raw.keys()) - known
    if extra:
        log.debug("gis_mapper[%s]: ignoring unknown fields %s", context, extra)


def _map_intersection(raw: dict, idx: int) -> Optional[SensitiveIntersectionInternal]:
    _log_extra(raw, "intersection")
    if not raw.get("layer_name"):
        log.warning("gis_mapper: sensitive_intersections[%d] missing layer_name — skipping", idx)
        return None
    if raw.get("overlap_pct") is None:
        log.warning("gis_mapper: sensitive_intersections[%d] missing overlap_pct — skipping", idx)
        return None
    return SensitiveIntersectionInternal(
        layer_name=raw["layer_name"],
        layer_id=raw.get("layer_id"),
        overlap_pct=float(raw["overlap_pct"]),
        geometry=raw.get("geometry"),
    )


def _map_nearby(raw: dict, idx: int) -> Optional[NearbyFeatureInternal]:
    _log_extra(raw, "nearby")
    if not raw.get("feature_type"):
        log.warning("gis_mapper: nearby_features[%d] missing feature_type — skipping", idx)
        return None
    if raw.get("distance_m") is None:
        log.warning("gis_mapper: nearby_features[%d] missing distance_m — skipping", idx)
        return None
    return NearbyFeatureInternal(
        feature_type=raw["feature_type"],
        name=raw.get("name"),
        distance_m=float(raw["distance_m"]),
        geometry=raw.get("geometry"),
    )


def map_gis_analyze_change(raw: dict) -> tuple[GISResultInternal, dict]:
    """
    Map raw /gis/analyze-change response.
    Returns (GISResultInternal, raw_payload_dict).
    Raises MapperError if changed_area_m2 is absent.
    """
    log.debug("gis_mapper: raw keys=%s", list(raw.keys()))
    _log_extra(raw, "root")

    if raw.get("changed_area_m2") is None:
        raise MapperError("gis", "analyze_change", "changed_area_m2")

    intersections = [
        mapped
        for i, item in enumerate(raw.get("sensitive_intersections", []))
        if (mapped := _map_intersection(item, i)) is not None
    ]

    nearby = [
        mapped
        for i, item in enumerate(raw.get("nearby_features", []))
        if (mapped := _map_nearby(item, i)) is not None
    ]

    overlap = raw.get("overlap_percentages") or {}
    if not isinstance(overlap, dict):
        log.warning("gis_mapper: overlap_percentages is not a dict — using empty dict")
        overlap = {}

    distances = raw.get("distances")
    if distances is not None and not isinstance(distances, dict):
        log.warning("gis_mapper: distances is not a dict — ignoring")
        distances = None

    result = GISResultInternal(
        changed_area_m2=float(raw["changed_area_m2"]),
        sensitive_intersections=intersections,
        overlap_percentages={str(k): float(v) for k, v in overlap.items()},
        nearby_features=nearby,
        geojson=raw.get("geojson"),
        layer_versions=raw.get("layer_versions"),
        distances=distances,
    )

    return result, raw
