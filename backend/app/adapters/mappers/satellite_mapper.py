"""
Satellite mapper.

The ONLY place that translates external satellite field names → internal schema.

Integration-first rules:
  - Tolerant reader: unknown fields logged at DEBUG, never raise
  - Alias support: cloud_score → cloud_cover, file_path → image_path
  - Strict on required fields: missing required field → MapperError
  - Returns (SatelliteStageResult, raw_payload_dict)
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Optional

from app.errors import MapperError
from app.schemas.internal.satellite import ObservationInternal, SatelliteStageResult

log = logging.getLogger(__name__)

# Expected top-level keys in the fetch response
_FETCH_KNOWN_KEYS = frozenset({"success", "reason", "before", "after", "intermediate"})
# Expected keys in a single scene dict
_SCENE_KNOWN_KEYS = frozenset({
    "scene_id", "acquisition_date", "sensor",
    "image_path", "file_path",            # aliases
    "preview_path",
    "cloud_cover", "cloud_score",         # aliases
    "crs", "resolution", "bounds",
})


# ── Private helpers ────────────────────────────────────────────────────────────

def _cloud_cover(raw: dict) -> Optional[float]:
    """Accept cloud_cover OR cloud_score (alias)."""
    v = raw.get("cloud_cover")
    if v is None:
        v = raw.get("cloud_score")
    return float(v) if v is not None else None


def _image_path(raw: dict) -> Optional[str]:
    """Accept image_path OR file_path (alias)."""
    return raw.get("image_path") or raw.get("file_path")


def _log_extra_scene(raw: dict, stage: str) -> None:
    extra = set(raw.keys()) - _SCENE_KNOWN_KEYS
    if extra:
        log.debug("satellite_mapper[%s]: ignoring unknown scene fields %s", stage, extra)


def _map_scene(raw: dict, role: str, stage: str) -> ObservationInternal:
    """Map a single raw scene dict to ObservationInternal."""
    _log_extra_scene(raw, stage)

    scene_id = raw.get("scene_id")
    if not scene_id:
        raise MapperError("satellite", stage, "scene_id")

    acq_raw = raw.get("acquisition_date")
    if not acq_raw:
        raise MapperError("satellite", stage, "acquisition_date")

    try:
        acquisition_date = date.fromisoformat(str(acq_raw))
    except ValueError:
        raise MapperError("satellite", stage, "acquisition_date")  # invalid format

    bounds = raw.get("bounds")
    if bounds is not None and len(bounds) != 4:
        log.warning(
            "satellite_mapper[%s]: bounds has %d elements (expected 4), ignoring",
            stage, len(bounds),
        )
        bounds = None

    return ObservationInternal(
        scene_id=scene_id,
        sensor=raw.get("sensor", "Sentinel-2"),
        acquisition_date=acquisition_date,
        cloud_cover=_cloud_cover(raw),
        crs=raw.get("crs"),
        resolution=raw.get("resolution"),
        image_path=_image_path(raw),
        preview_path=raw.get("preview_path"),
        bounds=bounds,
        role=role,
    )


# ── Public API ─────────────────────────────────────────────────────────────────

def map_satellite_search(raw: dict) -> tuple[list[dict], dict]:
    """
    Map raw /satellite/search response.
    Returns (list of scene raw dicts for selection, raw_payload).
    No internal model needed here; orchestrator picks best scenes.
    """
    log.debug("satellite_mapper.search: raw keys=%s", list(raw.keys()))
    return raw.get("scenes", []), raw


def map_satellite_fetch(raw: dict) -> tuple[SatelliteStageResult, dict]:
    """
    Map raw /satellite/fetch response → (SatelliteStageResult, raw_payload).

    Raises MapperError if a required field is absent on a non-failure response.
    A success=False response is valid — returns SatelliteStageResult(success=False).
    """
    log.debug("satellite_mapper.fetch: raw keys=%s", list(raw.keys()))

    # Log unknown top-level keys
    extra = set(raw.keys()) - _FETCH_KNOWN_KEYS
    if extra:
        log.debug("satellite_mapper.fetch: ignoring unknown top-level fields %s", extra)

    # Explicit no-image or error result (valid, not an error)
    if not raw.get("success", True) or ("detail" in raw and "before" not in raw):
        reason = raw.get("reason") or raw.get("detail") or "no_suitable_image: reason not provided by module"
        log.info("satellite_mapper.fetch: module returned success=false reason=%s", reason)
        return SatelliteStageResult(success=False, failure_reason=reason), raw

    before_raw = raw.get("before")
    if not before_raw:
        raise MapperError("satellite", "fetch", "before")

    after_raw = raw.get("after")
    if not after_raw:
        raise MapperError("satellite", "fetch", "after")

    before = _map_scene(before_raw, role="before", stage="fetch.before")
    after = _map_scene(after_raw, role="after", stage="fetch.after")

    intermediate = [
        _map_scene(s, role="intermediate", stage=f"fetch.intermediate[{i}]")
        for i, s in enumerate(raw.get("intermediate", []))
    ]

    return (
        SatelliteStageResult(
            success=True,
            before=before,
            after=after,
            intermediate=intermediate,
        ),
        raw,
    )
