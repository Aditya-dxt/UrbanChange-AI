import pytest
from fastapi.testclient import TestClient
from shapely.geometry import Polygon

from app.main import app
from app.services.geometry import compute_projected_area_m2, estimate_utm_epsg
from app.services.sensitive import SensitiveLayerManager

client = TestClient(app)


def test_projected_area_calculation():
    # Roughly a 0.001 x 0.001 degree box at lat 26.45 (Kanpur)
    # 0.001 deg lat ~= 110.6 m, 0.001 deg lon ~= 99.6 m -> area ~= 11,000 m²
    poly = Polygon([
        [80.350, 26.450],
        [80.351, 26.450],
        [80.351, 26.451],
        [80.350, 26.451],
        [80.350, 26.450],
    ])
    area = compute_projected_area_m2(poly)
    # Must be computed in projected meters (roughly 10,000 - 12,000 m²), never in degrees (~1e-6)
    assert 9000 < area < 13000


def test_hand_checked_overlap_calculation():
    # Sensitive zone ZONE-A is in [80.310, 26.410] to [80.355, 26.455]
    mgr = SensitiveLayerManager(data_dir="gis/data")
    assert len(mgr._layers) > 0

    # Test polygon centered inside ZONE-A
    poly_inside = Polygon([
        [80.320, 26.420],
        [80.330, 26.420],
        [80.330, 26.430],
        [80.320, 26.430],
        [80.320, 26.420],
    ])
    area = compute_projected_area_m2(poly_inside)
    intersections = mgr.analyze_intersections(poly_inside, area)
    assert len(intersections) > 0
    # Since fully inside ZONE-A, overlap should be ~100% (1.0)
    assert intersections[0]["overlap_pct"] > 0.95


def test_gis_analyze_endpoint():
    payload = {
        "change_regions": [
            {
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [80.320, 26.420],
                            [80.330, 26.420],
                            [80.330, 26.430],
                            [80.320, 26.430],
                            [80.320, 26.420],
                        ]
                    ],
                },
                "area_m2": 11000.0,
            }
        ],
        "bbox": [80.30, 26.40, 80.40, 26.50],
        "context_layer_ids": ["sample-env-buffer-01"],
        "investigation_id": "test-inv-001",
    }
    response = client.post("/gis/analyze-change", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["changed_area_m2"] > 0
    assert "sensitive_intersections" in data
    assert "nearby_features" in data
    assert "geojson" in data
