from datetime import date
from typing import Any, List, Optional, Union
from pydantic import BaseModel, Field, field_validator


class BoundingBox(BaseModel):
    min_lon: float = Field(..., ge=-180, le=180)
    min_lat: float = Field(..., ge=-90, le=90)
    max_lon: float = Field(..., ge=-180, le=180)
    max_lat: float = Field(..., ge=-90, le=90)


class SceneCandidate(BaseModel):
    scene_id: str
    acquisition_date: date
    cloud_cover: Optional[float] = None
    sensor: str = "Sentinel-2"
    crs: Optional[str] = "EPSG:32644"
    resolution: Optional[float] = 10.0
    bounds: Optional[List[float]] = None


class SatelliteSearchRequest(BaseModel):
    bbox: Union[List[float], BoundingBox, dict]
    historical_date: Union[date, str]
    current_date: Optional[Union[date, str]] = None
    max_cloud_cover: Optional[float] = None
    max_cloud_percentage: Optional[float] = None
    max_observations: Optional[int] = 10
    date_window_days: Optional[int] = 30

    def parsed_bbox_list(self) -> List[float]:
        if isinstance(self.bbox, list) and len(self.bbox) == 4:
            return [float(x) for x in self.bbox]
        if isinstance(self.bbox, BoundingBox):
            return [self.bbox.min_lon, self.bbox.min_lat, self.bbox.max_lon, self.bbox.max_lat]
        if isinstance(self.bbox, dict):
            if "min_lon" in self.bbox:
                return [
                    float(self.bbox["min_lon"]),
                    float(self.bbox["min_lat"]),
                    float(self.bbox["max_lon"]),
                    float(self.bbox["max_lat"]),
                ]
            if "west" in self.bbox:
                return [
                    float(self.bbox["west"]),
                    float(self.bbox["south"]),
                    float(self.bbox["east"]),
                    float(self.bbox["north"]),
                ]
        return [80.30, 26.40, 80.40, 26.50]


class SatelliteObservation(BaseModel):
    item_id: str
    acquisition_date: date
    sensor: str = "Sentinel-2"
    cloud_percentage: Optional[float] = None
    crs: Optional[str] = None
    resolution_m: Optional[float] = None
    image_reference: Optional[str] = None


class SatelliteSearchResponse(BaseModel):
    scenes: List[SceneCandidate] = Field(default_factory=list)
    success: bool = True
    reason: Optional[str] = None
    before: Optional[SatelliteObservation] = None
    after: Optional[SatelliteObservation] = None
    message: Optional[str] = None


class SatelliteFetchRequest(BaseModel):
    scene_id: str
    bbox: List[float]


class FetchedScene(BaseModel):
    scene_id: str
    acquisition_date: date
    sensor: str = "Sentinel-2"
    file_path: Optional[str] = None
    preview_path: Optional[str] = None
    cloud_score: Optional[float] = None
    crs: Optional[str] = "EPSG:32644"
    resolution: Optional[float] = 10.0
    bounds: Optional[List[float]] = None


class SatelliteFetchResponse(BaseModel):
    before: Optional[FetchedScene] = None
    after: Optional[FetchedScene] = None
    intermediate: List[FetchedScene] = Field(default_factory=list)
    success: bool = True
    reason: Optional[str] = None