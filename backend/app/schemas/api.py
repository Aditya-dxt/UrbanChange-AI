"""
API schema: Frontend-facing response models (consumed by Person 5).

These are the ONLY models the frontend should depend on.
Field names here are frozen; changes require a CONTRACT_VERSION bump.

GeoJSON convention: [longitude, latitude] everywhere.
Asset URLs are always /api/assets/<path> — never raw filesystem paths.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    """Uniform error shape for ALL error responses."""
    code: str
    message: str
    reason: Optional[str] = None
    request_id: str


# ---------------------------------------------------------------------------
# Observations
# ---------------------------------------------------------------------------

class ObservationOut(BaseModel):
    """One satellite scene as presented to the frontend."""
    scene_id: str
    sensor: str
    acquisition_date: date
    cloud_cover: Optional[float] = None
    crs: Optional[str] = None
    resolution: Optional[float] = None
    image_url: Optional[str] = None       # /api/assets/… URL
    preview_url: Optional[str] = None     # /api/assets/… URL or null
    preview_available: bool = False
    # Map overlay bounds [west, south, east, north]
    bounds: Optional[list[float]] = None
    role: str = "before"                  # "before" | "after" | "intermediate"


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

class ClassificationOut(BaseModel):
    label: str
    confidence: float


class DetectionOut(BaseModel):
    change_detected: bool
    confidence: float
    changed_area_pixels: int
    change_mask_url: Optional[str] = None       # /api/assets/… URL or null
    mask_preview_url: Optional[str] = None      # /api/assets/… URL or null
    mask_preview_available: bool = False
    bounds: Optional[list[float]] = None        # [west, south, east, north] or null
    change_regions: list[dict[str, Any]] = Field(default_factory=list)
    classification: Optional[ClassificationOut] = None
    model_version: str


# ---------------------------------------------------------------------------
# GIS
# ---------------------------------------------------------------------------

class SensitiveIntersectionOut(BaseModel):
    layer_name: str
    overlap_pct: float
    geometry: Optional[dict[str, Any]] = None


class NearbyFeatureOut(BaseModel):
    feature_type: str
    name: Optional[str] = None
    distance_m: float


class GISOut(BaseModel):
    changed_area_m2: float
    sensitive_intersections: list[SensitiveIntersectionOut] = Field(
        default_factory=list
    )
    overlap_percentages: dict[str, float] = Field(default_factory=dict)
    nearby_features: list[NearbyFeatureOut] = Field(default_factory=list)
    distances: Optional[dict[str, float]] = None
    geojson: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Intelligence
# ---------------------------------------------------------------------------

class FingerprintOut(BaseModel):
    fingerprint_id: str
    change_type: str
    changed_area_m2: Optional[float] = None
    confidence: Optional[float] = None
    temporal_behavior: Optional[str] = None
    sensitive_overlap: Optional[dict[str, Any]] = None
    first_observed: Optional[date] = None
    model_version: Optional[str] = None


class TemporalEventOut(BaseModel):
    observation_date: date
    event_type: str
    description: Optional[str] = None
    confidence: Optional[float] = None
    area_delta_m2: Optional[float] = None


class TemporalReconstructionOut(BaseModel):
    events: list[TemporalEventOut] = Field(default_factory=list)
    first_persistent_interval: Optional[str] = None
    summary: Optional[str] = None


class EvidenceOut(BaseModel):
    id: UUID
    evidence_type: str
    source_reference: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExplanationOut(BaseModel):
    text: str
    evidence_ids: list[str] = Field(default_factory=list)
    # Always pass through from Intelligence — never assert legality
    status: str = "requires_human_verification"


# ---------------------------------------------------------------------------
# Investigation (main response)
# ---------------------------------------------------------------------------

class InvestigationCreateRequest(BaseModel):
    """POST /api/investigations body."""
    bbox: list[float] = Field(
        ...,
        description="[west, south, east, north] WGS-84",
        min_length=4,
        max_length=4,
    )
    historical_date: date
    current_date: Optional[date] = None

    @field_validator("bbox")
    @classmethod
    def _validate_bbox(cls, v: list[float]) -> list[float]:
        if len(v) != 4:
            raise ValueError("bbox must have exactly 4 elements: [west, south, east, north]")
        west, south, east, north = v
        if not (-180 <= west <= 180 and -180 <= east <= 180):
            raise ValueError("bbox longitude values must be in [-180, 180]")
        if not (-90 <= south <= 90 and -90 <= north <= 90):
            raise ValueError("bbox latitude values must be in [-90, 90]")
        if south >= north:
            raise ValueError("bbox south must be less than north")
        if west > east:
            raise ValueError("bbox west must be less than or equal to east")
        return v


class InvestigationCreateResponse(BaseModel):
    """Response to POST /api/investigations."""
    id: UUID
    status: str


class InvestigationResponse(BaseModel):
    """
    Full investigation response — GET /api/investigations/{id}.
    Fields may be null if their stage has not completed or failed.
    """
    id: UUID
    status: str   # pending | running | completed | partial | failed
    stage: Optional[str] = None           # current/last pipeline stage
    failed_stage: Optional[str] = None    # set when status = partial | failed

    bbox: list[float]
    historical_date: date
    current_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    observations: list[ObservationOut] = Field(default_factory=list)
    detection: Optional[DetectionOut] = None
    gis: Optional[GISOut] = None
    fingerprint: Optional[FingerprintOut] = None
    temporal_reconstruction: Optional[TemporalReconstructionOut] = None
    evidence: list[EvidenceOut] = Field(default_factory=list)
    explanation: Optional[ExplanationOut] = None

    # Satellite failure reason (when satellite stage found no suitable image)
    satellite_failure_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------

class TimelineOut(BaseModel):
    """GET /api/investigations/{id}/timeline"""
    investigation_id: UUID
    events: list[TemporalEventOut] = Field(default_factory=list)
    observations: list[ObservationOut] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Assistant
# ---------------------------------------------------------------------------

class AssistantAskRequest(BaseModel):
    """POST /api/investigations/{id}/assistant body."""
    question: str


class AssistantMessageOut(BaseModel):
    """Response to the assistant endpoint."""
    id: UUID
    investigation_id: UUID
    role: str = "assistant"
    answer: str
    evidence_ids: list[str] = Field(default_factory=list)
    uncertainty_notes: Optional[str] = None
    status: str = "requires_human_verification"
    created_at: datetime
