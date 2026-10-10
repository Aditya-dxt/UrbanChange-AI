import logging
from datetime import date
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.models.schemas import (
    FetchedScene,
    SatelliteFetchRequest,
    SatelliteFetchResponse,
    SatelliteSearchRequest,
    SatelliteSearchResponse,
    SceneCandidate,
)
from app.services.acquisition import AcquisitionSelector
from app.services.catalog import SentinelCatalog, compute_bbox_area_km2
from app.services.windowed_service import WindowedSentinelService

log = logging.getLogger(__name__)

router = APIRouter(
    prefix="/satellite",
    tags=["Satellite"],
)

catalog = SentinelCatalog(
    stac_url=settings.stac_url,
    collection=settings.stac_collection,
)
windowed_svc = WindowedSentinelService(storage_root=settings.storage_root)

# In-memory scene metadata cache so fetch can retrieve STAC items found by search
_STAC_ITEM_CACHE: dict[str, dict] = {}
_STAC_PAIRS_BY_SCENE_ID: dict[str, tuple[dict, dict]] = {}
_LAST_SEARCH_PAIR_BY_BBOX: dict[tuple, tuple[dict, dict]] = {}


def _validate_request_params(bbox: list[float], h_date: date, c_date: Optional[date] = None):
    # Check bbox order
    if len(bbox) != 4:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Bbox must have exactly 4 coordinates [west, south, east, north].",
        )
    west, south, east, north = bbox
    if west >= east or south >= north:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid bounding box coordinates: west ({west}) must be < east ({east}) and south ({south}) < north ({north}).",
        )

    # Check minimum area
    area_km2 = compute_bbox_area_km2(bbox)
    if area_km2 < settings.min_aoi_km2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"AOI area ({area_km2:.3f} km²) is smaller than minimum required {settings.min_aoi_km2} km².",
        )

    # Check date ordering
    if c_date and h_date > c_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Historical date ({h_date}) cannot be after current date ({c_date}).",
        )


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

    # Validation
    _validate_request_params(bbox_list, h_date, c_date)

    max_cloud = (
        request.max_cloud_cover
        if request.max_cloud_cover is not None
        else (request.max_cloud_percentage if request.max_cloud_percentage is not None else settings.max_cloud_cover)
    )
    window_days = request.date_window_days or settings.date_window_days

    # 1. Search catalog around historical date
    before_items = catalog.search_scenes(
        bbox=bbox_list,
        target_date=h_date,
        window_days=window_days,
        max_cloud=max_cloud,
        is_latest_rule=False,
    )

    # 2. Search catalog up to current date
    after_items = catalog.search_scenes(
        bbox=bbox_list,
        target_date=c_date,
        window_days=window_days,
        max_cloud=max_cloud,
        is_latest_rule=True,
    )

    if not before_items and not after_items:
        reason = f"no_suitable_image: no Sentinel-2 scene under {max_cloud}% cloud within +/-{window_days} days of {h_date} and {c_date}"
        return SatelliteSearchResponse(
            success=False,
            reason=reason,
            scenes=[],
            message=reason,
        )

    # Store items in in-memory cache for subsequent fetch calls
    for it in before_items + after_items:
        _STAC_ITEM_CACHE[it.get("id")] = it

    # Rank before scenes: date proximity + SCL cloud fraction
    # First, compute AOI cloud fraction for top candidates using SCL
    aoi_clouds_before = {}
    for item in before_items[:10]:
        aoi_clouds_before[item.get("id")] = windowed_svc.compute_aoi_cloud_fraction(item, bbox_list)

    ranked_before = catalog.rank_candidates(
        before_items,
        target_date=h_date,
        reference_season_date=c_date,
        is_latest_rule=False,
        aoi_clouds=aoi_clouds_before,
    )

    # Filter out scenes where AOI cloud exceeds max_cloud
    valid_before = [
        it for it in ranked_before
        if aoi_clouds_before.get(it.get("id"), SentinelCatalog.extract_scene_cloud(it)) <= max_cloud
    ]

    aoi_clouds_after = {}
    for item in after_items[:10]:
        aoi_clouds_after[item.get("id")] = windowed_svc.compute_aoi_cloud_fraction(item, bbox_list)

    ref_season = SentinelCatalog.extract_scene_date(valid_before[0]) if valid_before else h_date
    ranked_after = catalog.rank_candidates(
        after_items,
        target_date=c_date,
        reference_season_date=ref_season,
        is_latest_rule=True,
        aoi_clouds=aoi_clouds_after,
    )

    valid_after = [
        it for it in ranked_after
        if aoi_clouds_after.get(it.get("id"), SentinelCatalog.extract_scene_cloud(it)) <= max_cloud
    ]

    if not valid_before:
        reason = f"no_suitable_image: no Sentinel-2 scene under {max_cloud}% cloud within +/-{window_days} days of {h_date}"
        return SatelliteSearchResponse(
            success=False,
            reason=reason,
            scenes=[],
            message=reason,
        )

    if not valid_after:
        reason = f"no_suitable_image: no Sentinel-2 scene under {max_cloud}% cloud within +/-{window_days} days of {c_date}"
        return SatelliteSearchResponse(
            success=False,
            reason=reason,
            scenes=[],
            message=reason,
        )

    candidates: list[SceneCandidate] = []
    # Add historical candidates
    for item in valid_before[:request.max_observations or 5]:
        c_cloud = aoi_clouds_before.get(item.get("id"))
        candidates.append(AcquisitionSelector.to_scene_candidate(item, bounds=bbox_list, aoi_cloud=c_cloud))

    # Add current candidates
    for item in valid_after[:request.max_observations or 5]:
        c_cloud = aoi_clouds_after.get(item.get("id"))
        candidates.append(AcquisitionSelector.to_scene_candidate(item, bounds=bbox_list, aoi_cloud=c_cloud))

    # Deduplicate by scene_id
    seen = set()
    deduped = []
    for c in candidates:
        if c.scene_id not in seen:
            seen.add(c.scene_id)
            deduped.append(c)

    best_before_obs = AcquisitionSelector.to_observation(valid_before[0]) if valid_before else None
    best_after_obs = AcquisitionSelector.to_observation(valid_after[0]) if valid_after else None

    # Cache best pair for both scene_ids and bbox
    if valid_before and valid_after:
        pair = (valid_before[0], valid_after[0])
        bbox_key = tuple(round(x, 4) for x in bbox_list)
        _LAST_SEARCH_PAIR_BY_BBOX[bbox_key] = pair
        if valid_before[0].get("id"):
            _STAC_PAIRS_BY_SCENE_ID[valid_before[0]["id"]] = pair
        if valid_after[0].get("id"):
            _STAC_PAIRS_BY_SCENE_ID[valid_after[0]["id"]] = pair

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
    bbox = request.bbox
    if len(bbox) != 4:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Bbox must have exactly 4 coordinates [west, south, east, north].",
        )

    _validate_request_params(bbox, date.today())

    # Resolve before and after STAC items
    before_item = None
    after_item = None

    # Case 1: scene_id provided (e.g. called from orchestrator or check_modules)
    if request.before_scene_id and request.before_scene_id in _STAC_ITEM_CACHE:
        before_item = _STAC_ITEM_CACHE[request.before_scene_id]
    if request.after_scene_id and request.after_scene_id in _STAC_ITEM_CACHE:
        after_item = _STAC_ITEM_CACHE[request.after_scene_id]

    if not before_item and request.scene_id:
        if request.scene_id in _STAC_PAIRS_BY_SCENE_ID:
            before_item, after_item = _STAC_PAIRS_BY_SCENE_ID[request.scene_id]
        elif request.scene_id in _STAC_ITEM_CACHE:
            before_item = _STAC_ITEM_CACHE[request.scene_id]

    # If pair still incomplete, check if recently searched for this bbox
    if not before_item or not after_item:
        bbox_key = tuple(round(x, 4) for x in bbox)
        if bbox_key in _LAST_SEARCH_PAIR_BY_BBOX:
            b_pair, a_pair = _LAST_SEARCH_PAIR_BY_BBOX[bbox_key]
            if not before_item:
                before_item = b_pair
            if not after_item:
                after_item = a_pair

    # Case 2: If items not in memory cache (or direct fetch without search), query STAC directly
    if not before_item or not after_item:
        h_date = (
            request.historical_date
            if isinstance(request.historical_date, date)
            else (date.fromisoformat(str(request.historical_date)) if request.historical_date else date(2025, 1, 5))
        )
        c_date = (
            request.current_date
            if isinstance(request.current_date, date)
            else (date.fromisoformat(str(request.current_date)) if request.current_date else date.today())
        )

        b_items = catalog.search_scenes(bbox=bbox, target_date=h_date, window_days=settings.date_window_days, max_cloud=settings.max_cloud_cover)
        a_items = catalog.search_scenes(bbox=bbox, target_date=c_date, window_days=settings.date_window_days, max_cloud=settings.max_cloud_cover, is_latest_rule=True)

        if not before_item and b_items:
            before_item = b_items[0]
        if not after_item and a_items:
            after_item = a_items[0]

    if not before_item or not after_item:
        reason = "no_suitable_image: unable to find or resolve matching before and after Sentinel-2 scenes"
        return SatelliteFetchResponse(success=False, reason=reason)

    try:
        (
            before_tif,
            before_png,
            after_tif,
            after_png,
            crs_str,
            bounds,
        ) = windowed_svc.fetch_and_align_pair(before_item, after_item, bbox)

        storage_root_path = Path(settings.storage_root).resolve()

        def rel_path(p: Path) -> str:
            try:
                return str(p.resolve().relative_to(storage_root_path)).replace("\\", "/")
            except Exception:
                return str(p).replace("\\", "/")

        b_rel_tif = rel_path(before_tif)
        b_rel_png = rel_path(before_png)
        a_rel_tif = rel_path(after_tif)
        a_rel_png = rel_path(after_png)

        b_date = SentinelCatalog.extract_scene_date(before_item)
        a_date = SentinelCatalog.extract_scene_date(after_item)
        b_cloud = windowed_svc.compute_aoi_cloud_fraction(before_item, bbox)
        a_cloud = windowed_svc.compute_aoi_cloud_fraction(after_item, bbox)

        before_scene = FetchedScene(
            scene_id=before_item.get("id"),
            acquisition_date=b_date.isoformat(),
            sensor="Sentinel-2",
            image_path=b_rel_tif,
            file_path=b_rel_tif,
            preview_path=b_rel_png,
            cloud_cover=round(b_cloud, 2),
            cloud_score=round(b_cloud, 2),
            crs=crs_str,
            resolution=10.0,
            bounds=bounds,
        )

        after_scene = FetchedScene(
            scene_id=after_item.get("id"),
            acquisition_date=a_date.isoformat(),
            sensor="Sentinel-2",
            image_path=a_rel_tif,
            file_path=a_rel_tif,
            preview_path=a_rel_png,
            cloud_cover=round(a_cloud, 2),
            cloud_score=round(a_cloud, 2),
            crs=crs_str,
            resolution=10.0,
            bounds=bounds,
        )

        return SatelliteFetchResponse(
            success=True,
            before=before_scene,
            after=after_scene,
            intermediate=[],
        )
    except Exception as exc:
        log.error("satellite.fetch error: %s", exc, exc_info=True)
        return SatelliteFetchResponse(
            success=False,
            reason=f"Failed to fetch and align satellite imagery: {exc}",
        )