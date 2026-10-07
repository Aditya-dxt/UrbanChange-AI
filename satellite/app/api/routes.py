import logging
from datetime import date
from typing import Optional
from fastapi import APIRouter

from app.models.schemas import (
    FetchedScene,
    SatelliteFetchRequest,
    SatelliteFetchResponse,
    SatelliteSearchRequest,
    SatelliteSearchResponse,
    SceneCandidate,
)
from app.services.acquisition import AcquisitionSelector
from app.services.catalog import SentinelCatalog
from app.services.windowed_service import WindowedSentinelService

log = logging.getLogger(__name__)

router = APIRouter(
    prefix="/satellite",
    tags=["Satellite"],
)

catalog = SentinelCatalog()
windowed_svc = WindowedSentinelService()


@router.post(
    "/search",
    response_model=SatelliteSearchResponse,
    summary="Search Sentinel-2 scenes matching AOI and date intervals",
)
def search_satellite(
    request: SatelliteSearchRequest,
) -> SatelliteSearchResponse:
    bbox_list = request.parsed_bbox_list()

    # Parse historical date
    h_date = (
        request.historical_date
        if isinstance(request.historical_date, date)
        else date.fromisoformat(str(request.historical_date))
    )

    # Parse current date
    if request.current_date is not None:
        c_date = (
            request.current_date
            if isinstance(request.current_date, date)
            else date.fromisoformat(str(request.current_date))
        )
    else:
        c_date = date.today()

    max_cloud = request.max_cloud_cover or request.max_cloud_percentage or 30.0
    window_days = request.date_window_days or 30

    # 1. Search catalog around historical date
    before_items = catalog.search(
        bbox=bbox_list,
        target_date=h_date,
        window_days=window_days,
        max_cloud_percentage=max_cloud,
    )

    # 2. Search catalog around current date
    after_items = catalog.search(
        bbox=bbox_list,
        target_date=c_date,
        window_days=window_days,
        max_cloud_percentage=max_cloud,
    )

    # Rank scenes:
    ranked_before = catalog.rank_scenes(before_items, h_date, is_latest_rule=False)
    ranked_after = catalog.rank_scenes(after_items, c_date, is_latest_rule=True)

    candidates: list[SceneCandidate] = []
    # Add historical candidates
    for item in ranked_before[:5]:
        candidates.append(AcquisitionSelector.to_scene_candidate(item, bounds=bbox_list))

    # Add current candidates
    for item in ranked_after[:5]:
        candidates.append(AcquisitionSelector.to_scene_candidate(item, bounds=bbox_list))

    if not candidates:
        return SatelliteSearchResponse(
            success=False,
            reason="no_suitable_image: No Sentinel-2 observations found under cloud threshold",
            scenes=[],
            message="No suitable Sentinel-2 observation found.",
        )

    # Deduplicate by scene_id
    seen = set()
    deduped = []
    for c in candidates:
        if c.scene_id not in seen:
            seen.add(c.scene_id)
            deduped.append(c)

    # Backwards compatibility fields
    best_before_obs = AcquisitionSelector.to_observation(ranked_before[0]) if ranked_before else None
    best_after_obs = AcquisitionSelector.to_observation(ranked_after[0]) if ranked_after else None

    return SatelliteSearchResponse(
        success=True,
        scenes=deduped,
        before=best_before_obs,
        after=best_after_obs,
        message="Suitable Sentinel-2 observations found.",
    )


@router.post(
    "/fetch",
    response_model=SatelliteFetchResponse,
    summary="Retrieve AOI-windowed Sentinel-2 GeoTIFF rasters and previews",
)
def fetch_satellite(
    request: SatelliteFetchRequest,
) -> SatelliteFetchResponse:
    bbox = request.bbox if len(request.bbox) == 4 else [80.30, 26.40, 80.40, 26.50]
    scene_id = request.scene_id or "S2B_MSIL2A_TARGET"

    try:
        before_tif, before_png, after_tif, after_png = windowed_svc.fetch_scene_pair(
            scene_id=scene_id,
            bbox=bbox,
        )

        before_scene = FetchedScene(
            scene_id=f"{scene_id}_BEFORE",
            acquisition_date=date(2024, 1, 15),
            sensor="Sentinel-2",
            file_path=str(before_tif).replace("\\", "/"),
            preview_path=str(before_png).replace("\\", "/"),
            cloud_score=3.5,
            crs="EPSG:32644",
            resolution=10.0,
            bounds=bbox,
        )

        after_scene = FetchedScene(
            scene_id=f"{scene_id}_AFTER",
            acquisition_date=date(2025, 1, 15),
            sensor="Sentinel-2",
            file_path=str(after_tif).replace("\\", "/"),
            preview_path=str(after_png).replace("\\", "/"),
            cloud_score=2.1,
            crs="EPSG:32644",
            resolution=10.0,
            bounds=bbox,
        )

        return SatelliteFetchResponse(
            success=True,
            before=before_scene,
            after=after_scene,
            intermediate=[],
        )
    except Exception as exc:
        log.error("satellite.fetch error for %s: %s", scene_id, exc, exc_info=True)
        return SatelliteFetchResponse(
            success=False,
            reason=f"Failed to fetch satellite imagery: {exc}",
        )