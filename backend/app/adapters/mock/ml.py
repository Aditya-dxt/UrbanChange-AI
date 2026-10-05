"""
Mock ML Adapter.

Returns realistic fixture data matching the contract in
backend/tests/contracts/ml/response.json.
No model inference is performed.
"""
from __future__ import annotations

import logging

from app.adapters.base import MLAdapter

log = logging.getLogger(__name__)


class MockMLAdapter(MLAdapter):
    """Fixture-driven mock for the ML module (Person 1)."""

    async def detect_change(
        self,
        before_path: str = "",
        before_date: str = "",
        before_crs: str | None = None,
        before_resolution: float | None = None,
        after_path: str = "",
        after_date: str = "",
        after_crs: str | None = None,
        after_resolution: float | None = None,
        sensor: str = "Sentinel-2",
        investigation_id: str = "",
        *,
        before_image_path: str | None = None,
        before_acquisition_date: str | None = None,
        after_image_path: str | None = None,
        after_acquisition_date: str | None = None,
    ) -> dict:
        b_path = before_image_path or before_path
        b_date = before_acquisition_date or before_date
        a_path = after_image_path or after_path
        a_date = after_acquisition_date or after_date
        log.debug(
            "MockMLAdapter.detect_change before_path=%s before_date=%s after_path=%s after_date=%s investigation=%s",
            b_path, b_date, a_path, a_date, investigation_id,
        )

        return {
            "change_detected": True,
            "confidence": 0.94,
            "changed_area_pixels": 38420,
            "change_mask_path": "mock/outputs/masks/change_mask.tif",
            "mask_preview_path": "mock/outputs/masks/change_mask_preview.png",
            "mask_bounds": [77.15, 28.55, 77.18, 28.58],
            "change_regions": [
                {
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [77.15, 28.55],
                            [77.18, 28.55],
                            [77.18, 28.58],
                            [77.15, 28.58],
                            [77.15, 28.55],
                        ]],
                    },
                    "area_pixels": 38420,
                    "confidence": 0.94,
                    "label": "construction",
                }
            ],
            "classification": {
                "label": "construction",
                "confidence": 0.91,
            },
            "model_version": "siamese-unet-attention-v1",
            "preprocessing_version": "v1.0",
            "threshold": 0.5,
        }
