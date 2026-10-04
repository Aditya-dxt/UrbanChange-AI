"""
ML mapper.

The ONLY place that translates external ML field names → internal schema.

Integration-first rules:
  - Alias: mask_path → change_mask_path
  - Unknown fields logged at DEBUG
  - Missing required field → MapperError(module="ml", stage, field)
  - Returns (DetectionInternal, ClassificationInternal|None, raw_payload_dict)
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from app.errors import MapperError
from app.schemas.internal.ml import ClassificationInternal, DetectionInternal

log = logging.getLogger(__name__)

_KNOWN_KEYS = frozenset({
    "change_detected", "confidence", "changed_area_pixels",
    "change_mask_path", "mask_path",    # aliases
    "change_regions", "classification",
    "model_version", "preprocessing_version", "threshold",
})


def _mask_path(raw: dict) -> Optional[str]:
    """Accept change_mask_path OR mask_path (alias)."""
    return raw.get("change_mask_path") or raw.get("mask_path")


def _log_extra(raw: dict) -> None:
    extra = set(raw.keys()) - _KNOWN_KEYS
    if extra:
        log.debug("ml_mapper: ignoring unknown fields %s", extra)


def map_ml_detect_change(
    raw: dict,
) -> tuple[DetectionInternal, dict]:
    """
    Map raw /ml/detect-change response.
    Returns (DetectionInternal, raw_payload_dict).
    ClassificationInternal is embedded inside DetectionInternal.
    Raises MapperError on missing required fields.
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

    # ── Change regions ───────────────────────────────────────────────────────
    regions = raw.get("change_regions", [])
    if not isinstance(regions, list):
        log.warning("ml_mapper: change_regions is not a list — using empty list")
        regions = []

    detection = DetectionInternal(
        change_detected=bool(raw["change_detected"]),
        confidence=float(raw["confidence"]),
        changed_area_pixels=int(raw["changed_area_pixels"]),
        change_mask_path=_mask_path(raw),
        change_regions=regions,
        classification=classification,
        model_version=str(raw["model_version"]),
        preprocessing_version=raw.get("preprocessing_version"),
        threshold=float(raw["threshold"]) if raw.get("threshold") is not None else None,
    )

    return detection, raw
