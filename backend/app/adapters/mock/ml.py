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
        before_path: str,
        before_date: str,
        before_crs: str | None,
        before_resolution: float | None,
        after_path: str,
        after_date: str,
        after_crs: str | None,
        after_resolution: float | None,
        sensor: str,
        investigation_id: str,
    ) -> dict:
        log.debug(
            "MockMLAdapter.detect_change before=%s after=%s investigation=%s",
            before_path, after_path, investigation_id,
        )

        return {
            "change_detected": True,
            "confidence": 0.94,
            "changed_area_pixels": 38420,
            "change_mask_path": "mock/outputs/masks/change_mask.tif",
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
