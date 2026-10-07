from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GISAnalyzeRequest(BaseModel):
    change_regions: List[Dict[str, Any]] = Field(default_factory=list)
    bbox: List[float] = Field(..., min_length=4, max_length=4)
    context_layer_ids: List[str] = Field(default_factory=list)
    investigation_id: Optional[str] = None


class SensitiveIntersection(BaseModel):
    layer_name: str
    layer_id: Optional[str] = None
    overlap_pct: float = Field(..., ge=0.0)
    geometry: Optional[Dict[str, Any]] = None


class NearbyFeature(BaseModel):
    feature_type: str
    name: Optional[str] = None
    distance_m: float = Field(..., ge=0.0)
    geometry: Optional[Dict[str, Any]] = None


class GISAnalyzeChangeResponse(BaseModel):
    changed_area_m2: float = Field(..., ge=0.0)
    sensitive_intersections: List[SensitiveIntersection] = Field(default_factory=list)
    overlap_percentages: Dict[str, float] = Field(default_factory=dict)
    nearby_features: List[NearbyFeature] = Field(default_factory=list)
    geojson: Optional[Dict[str, Any]] = None
    layer_versions: Optional[Dict[str, str]] = None
    distances: Optional[Dict[str, float]] = None
