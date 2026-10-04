"""
External schema: Satellite module (Person 2)

What POST /satellite/search and POST /satellite/fetch must return.

Fields marked  # ASSUMED  were inferred from the README / project context
and have not been confirmed by Person 2. See docs/API_CONTRACTS.md
"Fields needing confirmation" table.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

class _TolerantBase(BaseModel):
    """Accept and silently drop unknown fields (tolerant reader pattern)."""
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


# ---------------------------------------------------------------------------
# POST /satellite/search
# ---------------------------------------------------------------------------

class SatelliteSearchRequest(BaseModel):
    """Body sent BY the backend TO the satellite service."""
    bbox: list[float] = Field(..., description="[west, south, east, north] WGS-84")
    historical_date: date
    current_date: Optional[date] = None
    max_cloud_cover: float = Field(default=30.0, ge=0, le=100)
    max_observations: int = Field(default=2, ge=2)  # 2 for MVP; > 2 for temporal

    @field_validator("bbox")
    @classmethod
    def _validate_bbox(cls, v: list[float]) -> list[float]:
        if len(v) != 4:
            raise ValueError("bbox must have exactly 4 elements [west,south,east,north]")
        west, south, east, north = v
        if not (-180 <= west <= 180 and -180 <= east <= 180):
            raise ValueError("bbox longitude out of range [-180, 180]")
        if not (-90 <= south <= 90 and -90 <= north <= 90):
            raise ValueError("bbox latitude out of range [-90, 90]")
        if south >= north:
            raise ValueError("bbox south must be less than north")
        return v


class SceneCandidate(_TolerantBase):
    """A single candidate scene returned by the catalog search."""
    scene_id: str
    acquisition_date: date
    # ASSUMED: confirm alias with Person 2 (cloud_cover vs cloud_score)
    cloud_cover: Optional[float] = Field(
        default=None,
        alias="cloud_score",        # accept either name
        validation_alias="cloud_cover",
        ge=0, le=100,
    )
    sensor: str = "Sentinel-2"      # ASSUMED: default sensor name
    crs: Optional[str] = None       # e.g. "EPSG:32644"
    resolution: Optional[float] = None  # metres per pixel, e.g. 10.0
    # Bounding box of the scene [west, south, east, north]
    bounds: Optional[list[float]] = None  # ASSUMED: confirm field name

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    @field_validator("cloud_cover", mode="before")
    @classmethod
    def _coerce_cloud(cls, v: Any) -> Any:
        return v  # raw value; alias handling is done in mapper


class SatelliteSearchResponse(_TolerantBase):
    """Response from POST /satellite/search."""
    scenes: list[SceneCandidate] = Field(default_factory=list)
    # When no suitable image exists, success=False and reason is set.
    success: bool = True
    reason: Optional[str] = None   # e.g. "no_suitable_image: excessive cloud cover"


# ---------------------------------------------------------------------------
# POST /satellite/fetch
# ---------------------------------------------------------------------------

class SatelliteFetchRequest(BaseModel):
    """Body sent BY the backend TO the satellite fetch endpoint."""
    scene_id: str
    bbox: list[float] = Field(..., description="[west, south, east, north]")


class FetchedScene(_TolerantBase):
    """A fully retrieved scene with file paths."""
    scene_id: str
    acquisition_date: date
    sensor: str
    # ASSUMED: confirm field name (image_path vs file_path vs tif_path)
    image_path: Optional[str] = Field(default=None, alias="file_path")
    # ASSUMED: optional browser-friendly preview
    preview_path: Optional[str] = None
    cloud_cover: Optional[float] = Field(
        default=None, alias="cloud_score", ge=0, le=100
    )
    crs: Optional[str] = None
    resolution: Optional[float] = None
    bounds: Optional[list[float]] = None  # ASSUMED: [west, south, east, north]

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class SatelliteFetchResponse(_TolerantBase):
    """Response from POST /satellite/fetch — a before/after pair + extras."""
    before: Optional[FetchedScene] = None
    after: Optional[FetchedScene] = None
    # Extra intermediate observations for temporal reconstruction (MVP: empty)
    intermediate: list[FetchedScene] = Field(default_factory=list)
    success: bool = True
    reason: Optional[str] = None
