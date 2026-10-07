from datetime import date
from typing import Any, Optional
from app.models.schemas import SceneCandidate, SatelliteObservation


class AcquisitionSelector:

    @staticmethod
    def to_scene_candidate(item: Any, bounds: Optional[list[float]] = None) -> SceneCandidate:
        if isinstance(item, dict):
            item_id = item.get("id", "S2B_MSIL2A_UNKNOWN")
            dt = item.get("datetime")
            acq_date = dt.date() if hasattr(dt, "date") else (dt if isinstance(dt, date) else date.today())
            cloud = item.get("properties", {}).get("eo:cloud_cover", 5.0)
            b = item.get("bounds", bounds)
        else:
            item_id = getattr(item, "id", "S2B_MSIL2A_UNKNOWN")
            dt = getattr(item, "datetime", date.today())
            acq_date = dt.date() if hasattr(dt, "date") else dt
            props = getattr(item, "properties", {})
            cloud = props.get("eo:cloud_cover", 5.0)
            b = getattr(item, "bounds", bounds)

        return SceneCandidate(
            scene_id=item_id,
            acquisition_date=acq_date,
            cloud_cover=float(cloud) if cloud is not None else 5.0,
            sensor="Sentinel-2",
            crs="EPSG:32644",
            resolution=10.0,
            bounds=b or [80.30, 26.40, 80.40, 26.50],
        )

    @staticmethod
    def to_observation(item: Any) -> SatelliteObservation:
        if isinstance(item, dict):
            item_id = item.get("id", "S2B_MSIL2A_UNKNOWN")
            dt = item.get("datetime")
            acq_date = dt.date() if hasattr(dt, "date") else (dt if isinstance(dt, date) else date.today())
            cloud = item.get("properties", {}).get("eo:cloud_cover", 5.0)
        else:
            item_id = getattr(item, "id", "S2B_MSIL2A_UNKNOWN")
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