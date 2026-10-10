from datetime import date
from typing import Any, Optional
from app.models.schemas import SceneCandidate, SatelliteObservation
from app.services.catalog import SentinelCatalog


class AcquisitionSelector:

    @staticmethod
    def to_scene_candidate(item: Any, bounds: Optional[list[float]] = None, aoi_cloud: Optional[float] = None) -> SceneCandidate:
        if isinstance(item, dict):
            item_id = item.get("id", "S2_UNKNOWN")
            props = item.get("properties", {})
            acq_date = SentinelCatalog.extract_scene_date(item)
            scene_cloud = SentinelCatalog.extract_scene_cloud(item)
            cloud = aoi_cloud if aoi_cloud is not None else scene_cloud
            b = item.get("bbox", bounds)
            crs_proj = props.get("proj:epsg")
            crs_str = f"EPSG:{crs_proj}" if crs_proj else "EPSG:32644"
        else:
            item_id = getattr(item, "id", "S2_UNKNOWN")
            props = getattr(item, "properties", {})
            dt = getattr(item, "datetime", date.today())
            acq_date = dt.date() if hasattr(dt, "date") else dt
            cloud = props.get("eo:cloud_cover", 5.0) if aoi_cloud is None else aoi_cloud
            b = getattr(item, "bbox", bounds)
            crs_str = "EPSG:32644"

        return SceneCandidate(
            scene_id=item_id,
            acquisition_date=acq_date.isoformat(),
            cloud_cover=round(float(cloud), 2) if cloud is not None else None,
            sensor="Sentinel-2",
            crs=crs_str,
            resolution=10.0,
            bounds=b,
        )

    @staticmethod
    def to_observation(item: Any) -> SatelliteObservation:
        if isinstance(item, dict):
            item_id = item.get("id", "S2_UNKNOWN")
            acq_date = SentinelCatalog.extract_scene_date(item)
            cloud = SentinelCatalog.extract_scene_cloud(item)
        else:
            item_id = getattr(item, "id", "S2_UNKNOWN")
            dt = getattr(item, "datetime", date.today())
            acq_date = dt.date() if hasattr(dt, "date") else dt
            props = getattr(item, "properties", {})
            cloud = props.get("eo:cloud_cover", 5.0)

        return SatelliteObservation(
            item_id=item_id,
            acquisition_date=acq_date,
            sensor="Sentinel-2",
            cloud_percentage=float(cloud) if cloud is not None else 5.0,
            crs="EPSG:32644",
            resolution_m=10.0,
            image_reference=None,
        )