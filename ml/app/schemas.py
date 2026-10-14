"""
Pydantic schemas for the ML microservice.
Conforms strictly to shared/schemas/external/ml_detect_request.json
and shared/schemas/external/ml_detect_change_response.json.

Includes optional, non-breaking backward-compatible extensions for:
- vehicles detection
- resolution profile info
- land-cover semantic summary
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class MLImagePair(BaseModel):
    """Single image descriptor sent to the ML service."""
    image_path: str
    acquisition_date: str
    sensor: str = "Sentinel-2"
    crs: Optional[str] = None
    resolution: Optional[float] = None
    pixel_size_m: Optional[float] = None


class MLDetectRequest(BaseModel):
    """Body sent BY the backend TO the ML service."""
    before: MLImagePair
    after: MLImagePair
    sensor: str = "Sentinel-2"
    investigation_id: Optional[str] = None
    threshold: Optional[float] = Field(default=0.5, ge=0.0, le=1.0)
    min_area_m2: Optional[float] = Field(default=50.0, ge=0.0)


class ChangeRegion(BaseModel):
    """A single spatially-localised change region."""
    geometry: Optional[dict[str, Any]] = None
    area_pixels: Optional[int] = None
    area_m2: Optional[float] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    label: Optional[str] = None
    class_detail: Optional[dict[str, Any]] = None


class ClassificationResult(BaseModel):
    """Top-level change classification for the whole scene."""
    label: str
    confidence: float = Field(ge=0.0, le=1.0)


class VehicleDetection(BaseModel):
    box: List[int]
    cls: str = Field(alias="class")
    score: float


class VehiclesResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    supported: bool
    reason: Optional[str] = None
    before_count: int = 0
    after_count: int = 0
    detections_before: List[Dict[str, Any]] = Field(default_factory=list)
    detections_after: List[Dict[str, Any]] = Field(default_factory=list)


class MLDetectChangeResponse(BaseModel):
    """Response matching shared/schemas/external/ml_detect_change_response.json."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    change_detected: bool
    confidence: float = Field(ge=0.0, le=1.0)
    changed_area_pixels: int = Field(ge=0)
    changed_area_m2: Optional[float] = None

    # Aliases supported for both mask_path and change_mask_path
    mask_path: Optional[str] = None
    change_mask_path: Optional[str] = None

    # Aliases supported for both preview_path and mask_preview_path
    preview_path: Optional[str] = None
    mask_preview_path: Optional[str] = None

    # Aliases supported for both bounds and mask_bounds
    bounds: Optional[List[float]] = None
    mask_bounds: Optional[List[float]] = None

    change_regions: List[ChangeRegion] = Field(default_factory=list)
    classification: Optional[ClassificationResult] = None
    model_version: str
    preprocessing_version: Optional[str] = "v1.0-imagenet-norm-sliding-window"
    threshold: Optional[float] = Field(default=0.5, ge=0.0, le=1.0)

    # Optional additions (Person 1 -> Person 4 non-breaking contract additions)
    profile_used: Optional[str] = None
    thresholds_used: Optional[Dict[str, Any]] = None
    semantic_summary: Optional[Dict[str, Any]] = None
    vehicles: Optional[VehiclesResult] = None

    @model_validator(mode="after")
    def sync_aliases(self) -> MLDetectChangeResponse:
        # Sync mask_path and change_mask_path
        if self.mask_path and not self.change_mask_path:
            self.change_mask_path = self.mask_path
        elif self.change_mask_path and not self.mask_path:
            self.mask_path = self.change_mask_path

        # Sync preview_path and mask_preview_path
        if self.preview_path and not self.mask_preview_path:
            self.mask_preview_path = self.preview_path
        elif self.mask_preview_path and not self.preview_path:
            self.preview_path = self.mask_preview_path

        # Sync bounds and mask_bounds
        if self.bounds and not self.mask_bounds:
            self.mask_bounds = self.bounds
        elif self.mask_bounds and not self.bounds:
            self.bounds = self.mask_bounds

        return self


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    device: str
    model_version: str
    engine: Optional[str] = "legacy"
    profiles_available: Optional[List[str]] = Field(default_factory=lambda: ["hires", "sentinel2"])
    vehicles_supported: Optional[bool] = True


class ModelInfoResponse(BaseModel):
    model_version: str
    architecture: str
    device: str
    threshold: float
    parameter_count: int
    val_f1: float
    test_f1: float
    status: str
    input_resolution_trained_m: float
    supported_formats: List[str]
    supported_classes: List[str]
    engine: Optional[str] = "legacy"
    profiles: Optional[Dict[str, Any]] = None
    vehicles_enabled: Optional[bool] = True
