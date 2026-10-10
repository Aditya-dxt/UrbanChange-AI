import logging
import math
from datetime import date, datetime, timedelta
from typing import Any, List, Optional, Tuple, Union
import urllib.request
import urllib.error
import json
import time

log = logging.getLogger(__name__)


def compute_bbox_area_km2(bbox: List[float]) -> float:
    """Calculate approximate ellipsoidal/spherical area of WGS84 bbox in km²."""
    west, south, east, north = bbox
    # Earth radius in km
    r = 6371.0
    lat1 = math.radians(south)
    lat2 = math.radians(north)
    lon1 = math.radians(west)
    lon2 = math.radians(east)
    area = (r ** 2) * abs(lon2 - lon1) * abs(math.sin(lat2) - math.sin(lat1))
    return float(area)


class SentinelCatalog:
    """
    STAC Catalog search service using Earth Search AWS (sentinel-2-l2a).
    Handles date windows, rank ordering by AOI cloud / date proximity / season,
    and validation.
    """

    def __init__(
        self,
        stac_url: str = "https://earth-search.aws.element84.com/v1",
        collection: str = "sentinel-2-l2a",
    ):
        self.stac_url = stac_url.rstrip("/")
        self.collection = collection

    def _query_stac(
        self,
        bbox: List[float],
        start_dt: datetime,
        end_dt: datetime,
        max_cloud: float = 100.0,
        limit: int = 50,
        retries: int = 3,
        timeout: int = 20,
    ) -> List[dict]:
        """Perform a robust STAC POST /search with retries."""
        url = f"{self.stac_url}/search"
        payload = {
            "collections": [self.collection],
            "bbox": bbox,
            "datetime": f"{start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')}/{end_dt.strftime('%Y-%m-%dT%H:%M:%SZ')}",
            "query": {
                "eo:cloud_cover": {"lte": float(max_cloud)},
            },
            "limit": limit,
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json", "User-Agent": "UrbanChangeAI/1.0"}

        last_err = None
        for attempt in range(retries):
            try:
                req = urllib.request.Request(url, data=body, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data.get("features", [])
            except Exception as e:
                last_err = e
                log.warning("STAC query attempt %d/%d failed: %s", attempt + 1, retries, e)
                time.sleep(1.0 * (attempt + 1))

        log.error("All STAC query retries failed: %s", last_err)
        return []

    def search_scenes(
        self,
        bbox: List[float],
        target_date: date,
        window_days: int = 30,
        max_cloud: float = 20.0,
        is_latest_rule: bool = False,
    ) -> List[dict]:
        """
        Search STAC for scenes within window around target date.
        If is_latest_rule is True, searches from (target_date - window_days) up to target_date (or today).
        """
        if is_latest_rule:
            start_date = target_date - timedelta(days=window_days)
            end_date = target_date
        else:
            start_date = target_date - timedelta(days=window_days)
            end_date = target_date + timedelta(days=window_days)

        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        features = self._query_stac(
            bbox=bbox,
            start_dt=start_dt,
            end_dt=end_dt,
            max_cloud=max_cloud,
            limit=50,
        )
        return features

    @staticmethod
    def extract_scene_date(item: dict) -> date:
        dt_str = item.get("properties", {}).get("datetime", "")
        if dt_str:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).date()
        return date.today()

    @staticmethod
    def extract_scene_cloud(item: dict) -> float:
        return float(item.get("properties", {}).get("eo:cloud_cover", 0.0))

    @classmethod
    def rank_candidates(
        cls,
        items: List[dict],
        target_date: date,
        reference_season_date: Optional[date] = None,
        is_latest_rule: bool = False,
        aoi_clouds: Optional[dict[str, float]] = None,
    ) -> List[dict]:
        """
        Rank candidates by:
        (a) AOI cloud cover (or scene cloud cover fallback)
        (b) Date proximity to target_date
        (c) Seasonal proximity (day-of-year distance) to reference_season_date if provided.
        """
        if not items:
            return []

        aoi_clouds = aoi_clouds or {}

        def sort_key(item: dict):
            item_id = item.get("id", "")
            d = cls.extract_scene_date(item)
            cloud = aoi_clouds.get(item_id, cls.extract_scene_cloud(item))

            if is_latest_rule:
                # Latest date preferred (must be <= target_date if possible)
                date_penalty = -d.toordinal()
            else:
                date_penalty = abs((d - target_date).days)

            # Season difference (distance in day-of-year mod 365)
            season_penalty = 0
            if reference_season_date:
                doy1 = d.timetuple().tm_yday
                doy2 = reference_season_date.timetuple().tm_yday
                diff = abs(doy1 - doy2)
                season_penalty = min(diff, 365 - diff)

            return (
                cloud,           # (a) Cloud fraction first
                date_penalty,    # (b) Date proximity / latest
                season_penalty,  # (c) Same season preference
            )

        return sorted(items, key=sort_key)