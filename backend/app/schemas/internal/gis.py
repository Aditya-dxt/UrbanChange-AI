"""
Internal schema: GIS stage results.

Canonical backend representation after mapping from GISAnalyzeChangeResponse.
No GIS math is done here — values are passed through from the GIS adapter.
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class SensitiveIntersectionInternal(BaseModel):
    layer_name: str
    layer_id: Optional[str] = None
    overlap_pct: float = Field(ge=0, le=100)
    geometry: Optional[dict[str, Any]] = None


class NearbyFeatureInternal(BaseModel):
    feature_type: str
    name: Optional[str] = None
    distance_m: float = Field(ge=0)
    geometry: Optional[dict[str, Any]] = None


class GISResultInternal(BaseModel):
    """Fully normalised GIS analysis result."""
    changed_area_m2: float = Field(ge=0)
    sensitive_intersections: list[SensitiveIntersectionInternal] = Field(
        default_factory=list
    )
    overlap_percentages: dict[str, float] = Field(default_factory=dict)
    nearby_features: list[NearbyFeatureInternal] = Field(default_factory=list)
    geojson: Optional[dict[str, Any]] = None
    layer_versions: Optional[dict[str, str]] = None
    distances: Optional[dict[str, float]] = None
