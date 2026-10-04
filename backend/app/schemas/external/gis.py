"""
External schema: GIS module (Person 3)

What POST /gis/analyze-change must return.

Fields marked  # ASSUMED  inferred from README §GIS→Backend contract.
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class _TolerantBase(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


# ---------------------------------------------------------------------------
# POST /gis/analyze-change  – Request
# ---------------------------------------------------------------------------

class GISAnalyzeRequest(BaseModel):
    """Body sent BY the backend TO the GIS service."""
    change_regions: list[dict[str, Any]]   # GeoJSON Feature list from ML
    bbox: list[float]                       # [west, south, east, north]
    context_layer_ids: list[str] = Field(default_factory=list)
    investigation_id: Optional[str] = None


# ---------------------------------------------------------------------------
# POST /gis/analyze-change  – Response
# ---------------------------------------------------------------------------

class SensitiveIntersection(_TolerantBase):
    """One layer that the change region intersects."""
    layer_name: str
    layer_id: Optional[str] = None          # ASSUMED
    overlap_pct: float = Field(ge=0, le=100)
    # ASSUMED: geometry of the intersection as GeoJSON
    geometry: Optional[dict[str, Any]] = None


class NearbyFeature(_TolerantBase):
    """A notable feature near (but not necessarily overlapping) the change."""
    feature_type: str                       # e.g. "road", "water_body"
    name: Optional[str] = None
    distance_m: float = Field(ge=0)
    geometry: Optional[dict[str, Any]] = None  # ASSUMED


class GISAnalyzeChangeResponse(_TolerantBase):
    """Response from POST /gis/analyze-change (README §GIS→Backend contract)."""
    changed_area_m2: float = Field(ge=0)
    sensitive_intersections: list[SensitiveIntersection] = Field(default_factory=list)
    # ASSUMED: dict of layer_name → overlap percentage (0-100)
    overlap_percentages: dict[str, float] = Field(default_factory=dict)
    nearby_features: list[NearbyFeature] = Field(default_factory=list)
    # GeoJSON FeatureCollection of the analysed change geometry
    geojson: Optional[dict[str, Any]] = None
    # ASSUMED: versions of context layers used, for reproducibility
    layer_versions: Optional[dict[str, str]] = None
    # ASSUMED: distances dict  feature_type → nearest distance in metres
    distances: Optional[dict[str, float]] = None
