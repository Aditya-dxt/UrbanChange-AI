"""
Internal schema: ML stage results.

Canonical backend representation after mapping from MLDetectChangeResponse.
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ClassificationInternal(BaseModel):
    """Change classification for a detection."""
    label: str
    confidence: float = Field(ge=0, le=1)


class DetectionInternal(BaseModel):
    """Fully normalised ML detection result."""
    change_detected: bool
    confidence: float = Field(ge=0, le=1)
    changed_area_pixels: int = Field(ge=0)
    change_mask_path: Optional[str] = None
    mask_preview_path: Optional[str] = None
    mask_bounds: Optional[list[float]] = None
    change_regions: list[dict[str, Any]] = Field(default_factory=list)
    classification: Optional[ClassificationInternal] = None
    model_version: str
    preprocessing_version: Optional[str] = None
    threshold: Optional[float] = Field(default=None, ge=0, le=1)
