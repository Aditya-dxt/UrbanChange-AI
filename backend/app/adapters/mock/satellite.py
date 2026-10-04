"""
Mock Satellite Adapter.

Returns realistic fixture data matching the contract in
backend/tests/contracts/satellite/.
No real Copernicus / Sentinel-2 calls are made.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from app.adapters.base import SatelliteAdapter

log = logging.getLogger(__name__)


class MockSatelliteAdapter(SatelliteAdapter):
    """Fixture-driven mock for the satellite module (Person 2)."""

    async def search(
        self,
        bbox: list[float],
        historical_date: str,
        current_date: str | None,
        max_cloud_cover: float,
        max_observations: int,
    ) -> dict:
        log.debug("MockSatelliteAdapter.search bbox=%s historical=%s", bbox, historical_date)

        # Parse dates to build realistic scene IDs
        hist = date.fromisoformat(historical_date)
        curr = date.fromisoformat(current_date) if current_date else date.today()

        west, south, east, north = bbox

        return {
            "success": True,
            "reason": None,
            "scenes": [
                {
                    "scene_id": (
                        f"S2A_MSIL2A_{hist.strftime('%Y%m%d')}T052651"
                        "_N0511_R105_T43RGK_MOCK"
                    ),
                    "acquisition_date": hist.isoformat(),
                    "cloud_cover": 8.3,
                    "sensor": "Sentinel-2",
                    "crs": "EPSG:32643",
                    "resolution": 10.0,
                    "bounds": [west - 0.01, south - 0.01, east + 0.01, north + 0.01],
                },
                {
                    "scene_id": (
                        f"S2B_MSIL2A_{curr.strftime('%Y%m%d')}T052651"
                        "_N0511_R105_T43RGK_MOCK"
                    ),
                    "acquisition_date": curr.isoformat(),
                    "cloud_cover": 4.1,
                    "sensor": "Sentinel-2",
                    "crs": "EPSG:32643",
                    "resolution": 10.0,
                    "bounds": [west - 0.01, south - 0.01, east + 0.01, north + 0.01],
                },
            ],
        }

    async def fetch(self, scene_id: str, bbox: list[float]) -> dict:
        log.debug("MockSatelliteAdapter.fetch scene_id=%s", scene_id)

        # Derive role from scene_id (contains date portion)
        west, south, east, north = bbox
        bounds = [west - 0.01, south - 0.01, east + 0.01, north + 0.01]

        # Build two mock scenes using the scene_id passed in
        # The orchestrator calls fetch once per scene; we return the pair together
        # In the mock we just return a plausible before/after pair
        hist_date = "2025-04-14"
        curr_date = "2026-01-18"

        return {
            "success": True,
            "reason": None,
            "before": {
                "scene_id": f"S2A_MSIL2A_20250414T052651_N0511_R105_T43RGK_MOCK",
                "acquisition_date": hist_date,
                "sensor": "Sentinel-2",
                "image_path": "mock/sentinel2/before.tif",
                "preview_path": "mock/sentinel2/before_preview.png",
                "cloud_cover": 8.3,
                "crs": "EPSG:32643",
                "resolution": 10.0,
                "bounds": bounds,
            },
            "after": {
                "scene_id": f"S2B_MSIL2A_20260118T052651_N0511_R105_T43RGK_MOCK",
                "acquisition_date": curr_date,
                "sensor": "Sentinel-2",
                "image_path": "mock/sentinel2/after.tif",
                "preview_path": "mock/sentinel2/after_preview.png",
                "cloud_cover": 4.1,
                "crs": "EPSG:32643",
                "resolution": 10.0,
                "bounds": bounds,
            },
            "intermediate": [],
        }
