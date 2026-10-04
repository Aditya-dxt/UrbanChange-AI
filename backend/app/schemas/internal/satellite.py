"""
Internal schema: Satellite stage results.

These are the backend's canonical, normalised representations of what the
satellite module returned.  Only mappers may translate external→internal.
Nothing outside mappers/ knows the external field names.
"""
from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ObservationInternal(BaseModel):
    """One satellite scene, fully normalised."""
    scene_id: str
    sensor: str
    acquisition_date: date
    cloud_cover: Optional[float] = Field(default=None, ge=0, le=100)
    crs: Optional[str] = None
    resolution: Optional[float] = None     # metres per pixel
    image_path: Optional[str] = None       # absolute or STORAGE_ROOT-relative
    preview_path: Optional[str] = None     # browser-friendly image if available
    bounds: Optional[list[float]] = None   # [west, south, east, north]
    role: str = "before"                   # "before" | "after" | "intermediate"


class SatelliteStageResult(BaseModel):
    """
    The complete result of the satellite stage.
    success=False means no suitable imagery was found; this is a valid
    outcome — never a crash, never a silent date substitution.
    """
    success: bool
    failure_reason: Optional[str] = None   # e.g. "no_suitable_image: cloud cover >30%"
    before: Optional[ObservationInternal] = None
    after: Optional[ObservationInternal] = None
    intermediate: list[ObservationInternal] = Field(default_factory=list)
