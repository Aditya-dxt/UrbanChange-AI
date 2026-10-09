"""
Mock GIS Adapter.

Returns realistic fixture data matching the contract in
backend/tests/contracts/gis/response.json.
No spatial computation is performed.
"""
from __future__ import annotations

import logging

from app.adapters.base import GISAdapter

log = logging.getLogger(__name__)


class MockGISAdapter(GISAdapter):
    """Fixture-driven mock for the GIS module (Person 3)."""

    async def analyze_change(
        self,
        change_regions: list[dict],
        bbox: list[float],
        context_layer_ids: list[str],
        investigation_id: str,
    ) -> dict:
        log.debug(
            "MockGISAdapter.analyze_change regions=%d layers=%s investigation=%s",
            len(change_regions), context_layer_ids, investigation_id,
        )

        if bbox and len(bbox) == 4:
            west, south, east, north = bbox
        else:
            west, south, east, north = [80.30, 26.40, 80.40, 26.50]

        return {
            "changed_area_m2": 3842.0,
            "sensitive_intersections": [
                {
                    "layer_name": "protected_forest",
                    "layer_id": "pf_mock_001",
                    "overlap_pct": 64.0,
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [west + 0.05, south + 0.05],
                            [west + 0.08, south + 0.05],
                            [west + 0.08, south + 0.08],
                            [west + 0.05, south + 0.08],
                            [west + 0.05, south + 0.05],
                        ]],
                    },
                }
            ],
            "overlap_percentages": {
                "protected_forest": 64.0,
                "water_bodies": 0.0,
            },
            "nearby_features": [
                {
                    "feature_type": "road",
                    "name": "NH-48 (Mock)",
                    "distance_m": 120.5,
                    "geometry": None,
                }
            ],
            "geojson": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [west + 0.05, south + 0.05],
                                [west + 0.08, south + 0.05],
                                [west + 0.08, south + 0.08],
                                [west + 0.05, south + 0.08],
                                [west + 0.05, south + 0.05],
                            ]],
                        },
                        "properties": {"changed_area_m2": 3842.0},
                    }
                ],
            },
            "layer_versions": {
                "protected_forest": "2024-Q4-mock",
                "water_bodies": "2024-Q4-mock",
            },
            "distances": {
                "road": 120.5,
                "water_body": 450.0,
            },
        }
