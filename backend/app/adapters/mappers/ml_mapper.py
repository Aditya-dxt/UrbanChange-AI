"""
ML mapper.

The ONLY place that translates external ML field names → internal schema.

Integration-first rules:
  - Aliases:
      mask_path → change_mask_path
      preview_path → mask_preview_path
      bounds → mask_bounds
      path → image_path (in request mapping)
      date → acquisition_date (in request mapping)
  - Unknown fields logged at DEBUG
  - Missing required field → MapperError(module="ml", stage, field)
  - Returns (DetectionInternal, raw_payload_dict)
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from app.errors import MapperError
from app.schemas.internal.ml import ClassificationInternal, DetectionInternal

log = logging.getLogger(__name__)

_KNOWN_KEYS = frozenset({
    "change_detected", "confidence", "changed_area_pixels",
    "change_mask_path", "mask_path",                            # mask aliases
    "mask_preview_path", "preview_path",                        # preview aliases
    "mask_bounds", "bounds",                                    # bounds aliases
    "change_regions", "classification",
    "model_version", "preprocessing_version", "threshold",
})


def _mask_path(raw: dict) -> Optional[str]:
    """Accept change_mask_path OR mask_path (alias)."""
    return raw.get("change_mask_path") or raw.get("mask_path")


def _mask_preview_path(raw: dict) -> Optional[str]:
    """Accept mask_preview_path OR preview_path (alias)."""
    return raw.get("mask_preview_path") or raw.get("preview_path")


def _mask_bounds(raw: dict) -> Optional[list[float]]:
    """Accept mask_bounds OR bounds (alias). Validate 4 coordinates [west, south, east, north]."""
    val = raw.get("mask_bounds") or raw.get("bounds")
    if val is None:
        return None
    if isinstance(val, (list, tuple)) and len(val) == 4:
        try:
            west, south, east, north = (float(x) for x in val)
            if -180.0 <= west <= 180.0 and -180.0 <= east <= 180.0 and -90.0 <= south <= 90.0 and -90.0 <= north <= 90.0:
                return [west, south, east, north]
            log.warning("ml_mapper: mask_bounds coordinates out of WGS84 range: %s", val)
        except (ValueError, TypeError):
            log.warning("ml_mapper: mask_bounds contains non-numeric values: %s", val)
    else:
        log.warning("ml_mapper: mask_bounds must have 4 elements, got: %s", val)
    return None


def _log_extra(raw: dict) -> None:
    extra = set(raw.keys()) - _KNOWN_KEYS
    if extra:
        log.debug("ml_mapper: ignoring unknown fields %s", extra)


def map_ml_request(raw: dict) -> dict:
    """
    Map an outgoing ML detect-change request body, resolving aliases:
      before/after: path -> image_path, date -> acquisition_date
    """
    out = dict(raw)
    for key in ("before", "after"):
        if key in out and isinstance(out[key], dict):
            pair = dict(out[key])
            if "image_path" not in pair and "path" in pair:
                pair["image_path"] = pair.pop("path")
            if "acquisition_date" not in pair and "date" in pair:
                pair["acquisition_date"] = pair.pop("date")
            out[key] = pair
    return out


def _validate_change_regions(raw_regions: Any) -> list[dict[str, Any]]:
    """
    Validate that change_regions is a list of items where each geometry
    is a GeoJSON Polygon in WGS84 (EPSG:4326), [longitude, latitude].
    Raises MapperError naming module 'ml' and 'change_regions[].geometry' if validation fails.
    """
    if raw_regions is None:
        return []
    if not isinstance(raw_regions, list):
        log.warning("ml_mapper: change_regions is not a list — using empty list")
        return []

    validated: list[dict[str, Any]] = []
    for idx, region in enumerate(raw_regions):
        if not isinstance(region, dict):
            raise MapperError(
                module="ml",
                stage="detect_change",
                missing_field=f"change_regions[{idx}]",
                reason="each change region must be a dictionary",
                message=f"Module 'ml' returned an invalid payload at stage 'detect_change': change_regions[{idx}] must be a dictionary.",
            )

        # Geometry can be at region["geometry"] (GeoJSON Feature / dict) or region itself
        geom = region.get("geometry")
        if geom is None and region.get("type") == "Polygon":
            geom = region

        if geom is None:
            raise MapperError(
                module="ml",
                stage="detect_change",
                missing_field="change_regions[].geometry",
                reason=f"change_regions[{idx}] missing 'geometry'",
                message=f"Module 'ml' returned an invalid payload at stage 'detect_change': change_regions[{idx}].geometry is required and must be a GeoJSON Polygon in WGS84 (EPSG:4326), [longitude, latitude].",
            )

        if not isinstance(geom, dict):
            raise MapperError(
                module="ml",
                stage="detect_change",
                missing_field="change_regions[].geometry",
                reason=f"change_regions[{idx}].geometry must be a dictionary",
                message=f"Module 'ml' returned an invalid payload at stage 'detect_change': change_regions[{idx}].geometry must be a GeoJSON Polygon dict.",
            )

        g_type = geom.get("type")
        if g_type != "Polygon":
            raise MapperError(
                module="ml",
                stage="detect_change",
                missing_field="change_regions[].geometry",
                reason=f"change_regions[{idx}].geometry.type must be 'Polygon', got {g_type!r}",
                message=f"Module 'ml' returned an invalid payload at stage 'detect_change': change_regions[{idx}].geometry must be a GeoJSON Polygon in WGS84 (EPSG:4326), [longitude, latitude].",
            )

        coords = geom.get("coordinates")
        if not isinstance(coords, list) or len(coords) == 0:
            raise MapperError(
                module="ml",
                stage="detect_change",
                missing_field="change_regions[].geometry",
                reason=f"change_regions[{idx}].geometry.coordinates must be a non-empty list of linear rings",
                message=f"Module 'ml' returned an invalid payload at stage 'detect_change': change_regions[{idx}].geometry.coordinates must be a non-empty list of linear rings.",
            )

        for ring_idx, ring in enumerate(coords):
            if not isinstance(ring, list) or len(ring) < 4:
                raise MapperError(
                    module="ml",
                    stage="detect_change",
                    missing_field="change_regions[].geometry",
                    reason=f"change_regions[{idx}].geometry ring {ring_idx} must contain at least 4 coordinates",
                    message=f"Module 'ml' returned an invalid payload at stage 'detect_change': change_regions[{idx}].geometry ring {ring_idx} must contain at least 4 coordinates (closed linear ring).",
                )
            for pt_idx, pt in enumerate(ring):
                if not isinstance(pt, (list, tuple)) or len(pt) < 2:
                    raise MapperError(
                        module="ml",
                        stage="detect_change",
                        missing_field="change_regions[].geometry",
                        reason=f"coordinate {pt_idx} in ring {ring_idx} must be [longitude, latitude]",
                        message=f"Module 'ml' returned an invalid payload at stage 'detect_change': change_regions[{idx}].geometry coordinate must be [longitude, latitude].",
                    )
                lon, lat = pt[0], pt[1]
                if not isinstance(lon, (int, float)) or not isinstance(lat, (int, float)):
                    raise MapperError(
                        module="ml",
                        stage="detect_change",
                        missing_field="change_regions[].geometry",
                        reason=f"coordinate numbers required, got lon={lon!r}, lat={lat!r}",
                        message=f"Module 'ml' returned an invalid payload at stage 'detect_change': change_regions[{idx}].geometry coordinate numbers required.",
                    )
                if not (-180.0 <= float(lon) <= 180.0):
                    raise MapperError(
                        module="ml",
                        stage="detect_change",
                        missing_field="change_regions[].geometry",
                        reason=f"longitude {lon} out of WGS84 range [-180, 180]",
                        message=f"Module 'ml' returned an invalid payload at stage 'detect_change': change_regions[{idx}].geometry longitude {lon} out of WGS84 range [-180, 180].",
                    )
                if not (-90.0 <= float(lat) <= 90.0):
                    raise MapperError(
                        module="ml",
                        stage="detect_change",
                        missing_field="change_regions[].geometry",
                        reason=f"latitude {lat} out of WGS84 range [-90, 90]",
                        message=f"Module 'ml' returned an invalid payload at stage 'detect_change': change_regions[{idx}].geometry latitude {lat} out of WGS84 range [-90, 90].",
                    )

        validated.append(region)

    return validated


def map_ml_detect_change(
    raw: dict,
) -> tuple[DetectionInternal, dict]:
    """
    Map raw /ml/detect-change response.
    Returns (DetectionInternal, raw_payload_dict).
    ClassificationInternal is embedded inside DetectionInternal.
    Raises MapperError on missing required fields or invalid change_regions geometry.
    """
    log.debug("ml_mapper: raw keys=%s", list(raw.keys()))
    _log_extra(raw)

    # ── Required fields ──────────────────────────────────────────────────────
    if "change_detected" not in raw:
        raise MapperError("ml", "detect_change", "change_detected")
    if raw.get("confidence") is None:
        raise MapperError("ml", "detect_change", "confidence")
    if raw.get("changed_area_pixels") is None:
        raise MapperError("ml", "detect_change", "changed_area_pixels")
    if not raw.get("model_version"):
        raise MapperError("ml", "detect_change", "model_version")

    # ── Classification (optional) ────────────────────────────────────────────
    cls_raw = raw.get("classification")
    classification: Optional[ClassificationInternal] = None
    if cls_raw:
        if not cls_raw.get("label"):
            log.warning("ml_mapper: classification present but label missing — skipping")
        elif cls_raw.get("confidence") is None:
            log.warning("ml_mapper: classification present but confidence missing — skipping")
        else:
            classification = ClassificationInternal(
                label=cls_raw["label"],
                confidence=float(cls_raw["confidence"]),
            )

    # ── Change regions validation (GeoJSON Polygon in WGS84 [lon, lat]) ──────
    regions = _validate_change_regions(raw.get("change_regions", []))

    detection = DetectionInternal(
        change_detected=bool(raw["change_detected"]),
        confidence=float(raw["confidence"]),
        changed_area_pixels=int(raw["changed_area_pixels"]),
        change_mask_path=_mask_path(raw),
        mask_preview_path=_mask_preview_path(raw),
        mask_bounds=_mask_bounds(raw),
        change_regions=regions,
        classification=classification,
        model_version=str(raw["model_version"]),
        preprocessing_version=raw.get("preprocessing_version"),
        threshold=float(raw["threshold"]) if raw.get("threshold") is not None else None,
    )

    return detection, raw
