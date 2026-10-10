import pytest
import numpy as np
from datetime import date
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.services.catalog import SentinelCatalog, compute_bbox_area_km2
from app.services.windowed_service import WindowedSentinelService, compute_cache_key

client = TestClient(app)


def test_scene_selection_ranking():
    """Verify ranking by AOI cloud, date proximity, and seasonal similarity."""
    target_date = date(2025, 4, 15)
    season_ref = date(2026, 4, 15)

    candidates = [
        {
            "id": "scene_cloudy",
            "properties": {"datetime": "2025-04-15T05:00:00Z", "eo:cloud_cover": 25.0},
        },
        {
            "id": "scene_clean_near",
            "properties": {"datetime": "2025-04-14T05:00:00Z", "eo:cloud_cover": 2.0},
        },
        {
            "id": "scene_clean_far",
            "properties": {"datetime": "2025-04-01T05:00:00Z", "eo:cloud_cover": 2.0},
        },
    ]

    aoi_clouds = {
        "scene_cloudy": 25.0,
        "scene_clean_near": 2.0,
        "scene_clean_far": 2.0,
    }

    ranked = SentinelCatalog.rank_candidates(
        candidates,
        target_date=target_date,
        reference_season_date=season_ref,
        aoi_clouds=aoi_clouds,
    )

    # Clean near scene should rank ahead of clean far scene, and cloudy scene should be last
    assert ranked[0]["id"] == "scene_clean_near"
    assert ranked[1]["id"] == "scene_clean_far"
    assert ranked[2]["id"] == "scene_cloudy"


def test_aoi_cloud_computation():
    """Verify SCL classes [3, 8, 9, 10] correctly compute cloud/shadow fraction."""
    svc = WindowedSentinelService()
    # Mock item with SCL
    item = {
        "id": "test_scene",
        "assets": {"scl": {"href": "https://example.com/scl.tif"}},
        "properties": {"eo:cloud_cover": 50.0},
    }

    # Simulate SCL array: 100 pixels, 20 of which are in [3, 8, 9, 10]
    fake_scl = np.zeros((10, 10), dtype=np.uint8)
    fake_scl[0, :5] = 3   # shadow
    fake_scl[1, :5] = 8   # medium cloud
    fake_scl[2, :5] = 9   # high cloud
    fake_scl[3, :5] = 10  # cirrus
    # 20 out of 100 pixels = 20% cloud

    with patch("rasterio.open") as mock_rasterio:
        mock_src = MagicMock()
        mock_src.crs = "EPSG:32644"
        mock_src.read.return_value = fake_scl
        mock_rasterio.return_value.__enter__.return_value = mock_src
        with patch("rasterio.warp.transform_bounds", return_value=(0, 0, 100, 100)):
            with patch("rasterio.windows.from_bounds", return_value=MagicMock()):
                fraction = svc.compute_aoi_cloud_fraction(item, [80.30, 26.40, 80.31, 26.41])
                assert fraction == pytest.approx(20.0, 0.1)


def test_window_alignment():
    """Verify cache key computation and deterministic alignment parameters."""
    bbox = [80.305, 26.435, 80.315, 26.445]
    key1 = compute_cache_key(["scene_A", "scene_B"], bbox)
    key2 = compute_cache_key(["scene_A", "scene_B"], bbox)
    key3 = compute_cache_key(["scene_A", "scene_C"], bbox)

    assert key1 == key2
    assert key1 != key3
    assert len(key1) == 16


def test_minimum_aoi_rejection():
    """Verify that an AOI < 0.25 km² is rejected with HTTP 422."""
    tiny_bbox = [80.3000, 26.4000, 80.3001, 26.4001]
    area = compute_bbox_area_km2(tiny_bbox)
    assert area < 0.25

    response = client.post(
        "/satellite/search",
        json={
            "bbox": tiny_bbox,
            "historical_date": "2025-01-05",
            "current_date": "2026-10-10",
        },
    )
    assert response.status_code == 422
    data = response.json()
    assert "smaller than minimum required" in str(data.get("detail", ""))


def test_no_suitable_scene_reason():
    """Verify explicit reason when no scenes are found under cloud threshold."""
    with patch.object(SentinelCatalog, "search_scenes", return_value=[]):
        response = client.post(
            "/satellite/search",
            json={
                "bbox": [80.30, 26.40, 80.40, 26.50],
                "historical_date": "2025-01-05",
                "current_date": "2026-10-10",
                "max_cloud_cover": 5.0,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "no_suitable_image" in data["reason"]
        assert len(data["scenes"]) == 0
