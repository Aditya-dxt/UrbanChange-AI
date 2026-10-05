"""
External schema: ML module (Person 1)

What POST /ml/detect-change must return.

Fields marked  # ASSUMED  were inferred from the README / project context.
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _TolerantBase(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


# ---------------------------------------------------------------------------
# POST /ml/detect-change  – Request
# ---------------------------------------------------------------------------

class MLImagePair(BaseModel):
    """Single image descriptor sent to the ML service."""
    image_path: str
    acquisition_date: str       # ISO date string  e.g. "2025-04-14"
    sensor: str = "Sentinel-2"
    crs: Optional[str] = None
    resolution: Optional[float] = None


class MLDetectRequest(BaseModel):
    """Body sent BY the backend TO the ML service."""
    before: MLImagePair
    after: MLImagePair
    sensor: str = "Sentinel-2"
    investigation_id: Optional[str] = None  # for tracing in ML logs


# ---------------------------------------------------------------------------
# POST /ml/detect-change  – Response
# ---------------------------------------------------------------------------

class ChangeRegion(_TolerantBase):
    """
    A single spatially-localised change region returned by ML.
    Geometry MUST be a GeoJSON Polygon in WGS84 (EPSG:4326), [longitude, latitude].
    """
    geometry: Optional[dict[str, Any]] = None
    area_pixels: Optional[int] = None
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    label: Optional[str] = None


class ClassificationResult(_TolerantBase):
    """Top-level change classification for the whole scene."""
    label: str                           # e.g. "construction"
    confidence: float = Field(ge=0, le=1)


class MLDetectChangeResponse(_TolerantBase):
    """Response from POST /ml/detect-change (from README §ML→Backend contract)."""
    change_detected: bool
    confidence: float = Field(ge=0, le=1)
    changed_area_pixels: int = Field(ge=0)
    # Alias: change_mask_path vs mask_path (both accepted by mapper)
    change_mask_path: Optional[str] = Field(
        default=None,
        alias="mask_path",
    )
    mask_preview_path: Optional[str] = Field(
        default=None,
        alias="preview_path",
    )
    mask_bounds: Optional[list[float]] = Field(
        default=None,
        alias="bounds",
        min_length=4,
        max_length=4,
    )
    change_regions: list[ChangeRegion] = Field(default_factory=list)
    classification: Optional[ClassificationResult] = None
    model_version: str
    # Optional preprocessing/pipeline version
    preprocessing_version: Optional[str] = None
    # Decision threshold used
    threshold: Optional[float] = Field(default=None, ge=0, le=1)

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    @field_validator("mask_bounds")
    @classmethod
    def _validate_bounds(cls, v: Optional[list[float]]) -> Optional[list[float]]:
        if v is None:
            return None
        if len(v) != 4:
            raise ValueError("mask_bounds must have exactly 4 elements: [west, south, east, north]")
        west, south, east, north = v
        if not (-180.0 <= west <= 180.0 and -180.0 <= east <= 180.0):
            raise ValueError("mask_bounds longitude values must be in [-180, 180]")
        if not (-90.0 <= south <= 90.0 and -90.0 <= north <= 90.0):
            raise ValueError("mask_bounds latitude values must be in [-90, 90]")
        return v
