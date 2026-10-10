"""HTTP adapter for the ML module (Person 1)."""
from __future__ import annotations

import logging
from typing import Optional

from app.adapters.base import MLAdapter
from app.adapters.http._http import post_with_retry

log = logging.getLogger(__name__)
_MODULE = "ml"


class HttpMLAdapter(MLAdapter):
    """
    Calls the real ML service over HTTP.
    Endpoint (per contract):
      POST {base_url}/ml/detect-change
    """

    def __init__(self, base_url: str, timeout: int) -> None:
        self._base_url = base_url
        self._timeout = float(timeout)
        log.info("HttpMLAdapter base_url=%s timeout=%s", base_url, timeout)

    @staticmethod
    def _resolve_image_path(p: str) -> str:
        if not p:
            return p
        if p.startswith("/"):
            return p
        # If relative path in shared storage, qualify with /data/storage/
        if p.startswith("satellite/") or p.startswith("uploads/"):
            return f"/data/storage/{p}"
        from pathlib import Path
        if Path(f"/data/storage/{p}").exists():
            return f"/data/storage/{p}"
        return p

    async def detect_change(
        self,
        before_path: str,
        before_date: str,
        before_crs: Optional[str],
        before_resolution: Optional[float],
        after_path: str,
        after_date: str,
        after_crs: Optional[str],
        after_resolution: Optional[float],
        sensor: str,
        investigation_id: str,
    ) -> dict:
        payload = {
            "before": {
                "image_path": self._resolve_image_path(before_path),
                "acquisition_date": before_date,
                "crs": before_crs,
                "resolution": before_resolution,
            },
            "after": {
                "image_path": self._resolve_image_path(after_path),
                "acquisition_date": after_date,
                "crs": after_crs,
                "resolution": after_resolution,
            },
            "sensor": sensor,
            "investigation_id": investigation_id,
        }
        return await post_with_retry(
            self._base_url, "/ml/detect-change", payload, _MODULE, "detect_change", self._timeout
        )
