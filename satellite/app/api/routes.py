from fastapi import APIRouter

from app.models.schemas import (
    SatelliteSearchRequest,
    SatelliteSearchResponse,
)
from app.services.catalog import SentinelCatalog
from app.services.acquisition import AcquisitionSelector


router = APIRouter(
    prefix="/satellite",
    tags=["Satellite"],
)


catalog = SentinelCatalog()


@router.post(
    "/search",
    response_model=SatelliteSearchResponse,
)
def search_satellite(
    request: SatelliteSearchRequest,
):
    bbox = {
        "min_lon": request.bbox.min_lon,
        "min_lat": request.bbox.min_lat,
        "max_lon": request.bbox.max_lon,
        "max_lat": request.bbox.max_lat,
    }

    # Search independently around the historical date
    before_items = catalog.search(
        bbox=bbox,
        target_date=request.historical_date,
        window_days=request.date_window_days,
        max_cloud_percentage=request.max_cloud_percentage,
    )

    # Search independently around the current date
    after_items = catalog.search(
        bbox=bbox,
        target_date=request.current_date,
        window_days=request.date_window_days,
        max_cloud_percentage=request.max_cloud_percentage,
    )

    before, after = AcquisitionSelector.select_pair(
        before_items=before_items,
        after_items=after_items,
        historical_date=request.historical_date,
        current_date=request.current_date,
    )

    # No BEFORE image
    if before is None:
        return SatelliteSearchResponse(
            message="No suitable BEFORE Sentinel-2 observation found."
        )

    # No AFTER image
    if after is None:
        return SatelliteSearchResponse(
            before=AcquisitionSelector.to_observation(before),
            message="No suitable AFTER Sentinel-2 observation found.",
        )

    return SatelliteSearchResponse(
        before=AcquisitionSelector.to_observation(before),
        after=AcquisitionSelector.to_observation(after),
        message="Suitable BEFORE and AFTER observations found.",
    )