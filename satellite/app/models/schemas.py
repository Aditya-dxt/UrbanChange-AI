from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    min_lon: float = Field(..., ge=-180, le=180)
    min_lat: float = Field(..., ge=-90, le=90)
    max_lon: float = Field(..., ge=-180, le=180)
    max_lat: float = Field(..., ge=-90, le=90)


class SatelliteSearchRequest(BaseModel):
    bbox: BoundingBox

    historical_date: date
    current_date: date

    max_cloud_percentage: float = Field(
        default=20.0,
        ge=0,
        le=100
    )

    date_window_days: int = Field(
        default=30,
        ge=0
    )


class SatelliteObservation(BaseModel):
    item_id: str

    acquisition_date: date

    sensor: str = "Sentinel-2"

    cloud_percentage: Optional[float] = None

    crs: Optional[str] = None

    resolution_m: Optional[float] = None

    image_reference: Optional[str] = None


class SatelliteSearchResponse(BaseModel):
    before: Optional[SatelliteObservation] = None
    after: Optional[SatelliteObservation] = None

    message: Optional[str] = None