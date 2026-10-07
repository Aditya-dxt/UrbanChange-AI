from fastapi.testclient import TestClient
from satellite.app.main import app

client = TestClient(app)


def test_satellite_search_contract():
    payload = {
        "bbox": [80.30, 26.40, 80.40, 26.50],
        "historical_date": "2024-01-01",
        "current_date": "2025-01-01",
        "max_cloud_cover": 25.0,
        "max_observations": 5,
    }
    response = client.post("/satellite/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "scenes" in data
    assert len(data["scenes"]) > 0
    scene = data["scenes"][0]
    assert "scene_id" in scene
    assert "acquisition_date" in scene
    assert "sensor" in scene
    assert "cloud_cover" in scene


def test_satellite_fetch_contract():
    payload = {
        "scene_id": "S2B_MSIL2A_TEST001",
        "bbox": [80.30, 26.40, 80.40, 26.50],
    }
    response = client.post("/satellite/fetch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["before"] is not None
    assert data["after"] is not None
    assert "file_path" in data["before"]
    assert "preview_path" in data["before"]
    assert "file_path" in data["after"]
