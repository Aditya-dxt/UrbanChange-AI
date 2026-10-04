"""HTTP adapter for the GIS module (Person 3)."""
from __future__ import annotations

import logging
from typing import Any

from app.adapters.base import GISAdapter
from app.adapters.http._http import post_with_retry

log = logging.getLogger(__name__)
_MODULE = "gis"


class HttpGISAdapter(GISAdapter):
    """
    Calls the real GIS service over HTTP.
    Endpoint (per contract):
      POST {base_url}/gis/analyze-change
    """

    def __init__(self, base_url: str, timeout: int) -> None:
        self._base_url = base_url
        self._timeout = float(timeout)
        log.info("HttpGISAdapter base_url=%s timeout=%s", base_url, timeout)

    async def analyze_change(
        self,
        change_regions: list[dict[str, Any]],
        bbox: list[float],
        context_layer_ids: list[str],
        investigation_id: str,
    ) -> dict:
        payload = {
            "change_regions": change_regions,
            "bbox": bbox,
            "context_layer_ids": context_layer_ids,
            "investigation_id": investigation_id,
        }
        return await post_with_retry(
            self._base_url, "/gis/analyze-change", payload, _MODULE, "analyze_change", self._timeout
        )
