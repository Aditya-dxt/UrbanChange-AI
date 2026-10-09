"""
Pydantic schemas for the ML microservice.
Conforms strictly to shared/schemas/external/ml_detect_request.json
and shared/schemas/external/ml_detect_change_response.json.
"""
from __future__ import annotations

from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class MLImagePair(BaseModel):
    """Single image descriptor sent to the ML service."""
    image_path: str
    acquisition_date: str
    sensor: str = "Sentinel-2"
    crs: Optional[str] = None
    resolution: Optional[float] = None
    # Optional pixel size in meters for non-georeferenced images
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


class ClassificationResult(BaseModel):
    """Top-level change classification for the whole scene."""
    label: str
    confidence: float = Field(ge=0.0, le=1.0)


class MLDetectChangeResponse(BaseModel):
    """Response matching shared/schemas/external/ml_detect_change_response.json."""
    model_config = ConfigDict(populate_by_name=True)

    change_detected: bool
    confidence: float = Field(ge=0.0, le=1.0)
    changed_area_pixels: int = Field(ge=0)
    changed_area_m2: Optional[float] = None
    mask_path: Optional[str] = None
    preview_path: Optional[str] = None
    bounds: Optional[List[float]] = None
    change_regions: List[ChangeRegion] = Field(default_factory=list)
    classification: Optional[ClassificationResult] = None
    model_version: str
    preprocessing_version: Optional[str] = "v1.0-imagenet-norm-sliding-window"
    threshold: Optional[float] = Field(default=0.5, ge=0.0, le=1.0)


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    device: str
    model_version: str


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
