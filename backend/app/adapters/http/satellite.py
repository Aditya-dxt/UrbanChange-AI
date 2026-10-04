"""HTTP adapter for the Satellite module (Person 2)."""
from __future__ import annotations

import logging
from typing import Optional

from app.adapters.base import SatelliteAdapter
from app.adapters.http._http import post_with_retry

log = logging.getLogger(__name__)
_MODULE = "satellite"


class HttpSatelliteAdapter(SatelliteAdapter):
    """
    Calls the real Satellite service over HTTP.
    Endpoints (per contract):
      POST {base_url}/satellite/search
      POST {base_url}/satellite/fetch
    """

    def __init__(self, base_url: str, timeout: int) -> None:
        self._base_url = base_url
        self._timeout = float(timeout)
        log.info("HttpSatelliteAdapter base_url=%s timeout=%s", base_url, timeout)

    async def search(
        self,
        bbox: list[float],
        historical_date: str,
        current_date: Optional[str],
        max_cloud_cover: float,
        max_observations: int,
    ) -> dict:
        payload = {
            "bbox": bbox,
            "historical_date": historical_date,
            "current_date": current_date,
            "max_cloud_cover": max_cloud_cover,
            "max_observations": max_observations,
        }
        return await post_with_retry(
            self._base_url, "/satellite/search", payload, _MODULE, "search", self._timeout
        )

    async def fetch(self, scene_id: str, bbox: list[float]) -> dict:
        payload = {"scene_id": scene_id, "bbox": bbox}
        return await post_with_retry(
            self._base_url, "/satellite/fetch", payload, _MODULE, "fetch", self._timeout
        )
