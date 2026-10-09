"""
Comprehensive tests for ML Change Detection Service.
Tests model architecture, weights loading, sliding window,
GeoTIFF and PNG inference, and FastAPI HTTP endpoints.
"""
from pathlib import Path
import pytest
import numpy as np
import torch
from fastapi.testclient import TestClient

from ml.app.model import SiameseUNetAttention
from ml.app.predictor import ChangePredictor
from ml.app.main import app

WEIGHTS_PATH = Path("ml/weights/best_siamese_model.pth").resolve()
STORAGE_ROOT = Path("data/storage").resolve()


@pytest.fixture(scope="module")
def predictor():
    assert WEIGHTS_PATH.exists(), f"Weights file missing at {WEIGHTS_PATH}"
    return ChangePredictor(weights_path=WEIGHTS_PATH, device="cpu")


@pytest.fixture(scope="module")
def client(predictor):
    with TestClient(app) as test_client:
        yield test_client


def test_model_instantiation():
    """Verify SiameseUNetAttention architecture and parameter count (~24.87M)."""
    model = SiameseUNetAttention()
    param_count = sum(p.numel() for p in model.parameters())
    assert param_count == 24872157


def test_forward_pass():
    """Verify tensor input/output shapes through encoder and attention decoder."""
    model = SiameseUNetAttention()
    model.eval()
    x1 = torch.randn(1, 3, 256, 256)
    x2 = torch.randn(1, 3, 256, 256)
    with torch.no_grad():
        out = model(x1, x2)
    assert out.shape == (1, 1, 256, 256)


def test_sliding_window_arbitrary_size(predictor):
    """Verify inference on arbitrary dimensions (e.g. 300x400) via sliding window."""
    h, w = 300, 400
    dummy1 = np.random.randn(h, w, 3).astype(np.float32)
    dummy2 = np.random.randn(h, w, 3).astype(np.float32)
    prob_map = predictor.predict_change_prob(dummy1, dummy2)
    assert prob_map.shape == (h, w)
    assert prob_map.min() >= 0.0
    assert prob_map.max() <= 1.0


def test_no_change_on_identical_inputs(predictor):
    """Identical input images should yield zero or negligible change."""
    img_path = Path("sample_data/pairs/pair_01_construction/before.png")
    assert img_path.exists()
    res = predictor.detect(
        before_path=img_path,
        after_path=img_path,
        storage_root=STORAGE_ROOT,
        threshold=0.5,
    )
    assert res.change_detected is False
    assert res.changed_area_pixels == 0
    assert len(res.change_regions) == 0


def test_png_pair_inference(predictor):
    """Test real change detection on known construction pair."""
    b_path = Path("sample_data/pairs/pair_01_construction/before.png")
    a_path = Path("sample_data/pairs/pair_01_construction/after.png")
    res = predictor.detect(
        before_path=b_path,
        after_path=a_path,
        storage_root=STORAGE_ROOT,
        threshold=0.5,
        min_area_m2=50.0,
    )
    assert res.change_detected is True
    assert res.confidence > 0.70
    assert res.changed_area_pixels > 1000
    assert len(res.change_regions) > 0
    assert Path(res.mask_path).exists()
    assert Path(res.preview_path).exists()


def test_no_change_sample_pair(predictor):
    """Test pair_04_no_change evaluates correctly as no change."""
    b_path = Path("sample_data/pairs/pair_04_no_change/before.png")
    a_path = Path("sample_data/pairs/pair_04_no_change/after.png")
    res = predictor.detect(
        before_path=b_path,
        after_path=a_path,
        storage_root=STORAGE_ROOT,
        threshold=0.5,
    )
    assert res.change_detected is False
    assert res.changed_area_pixels == 0


def test_geotiff_pair_inference(predictor):
    """Test 4-band Sentinel-2 GeoTIFF stack with georeferencing."""
    b_path = Path("sample_data/pairs/pair_05_sentinel2_geotiff/before.tif")
    a_path = Path("sample_data/pairs/pair_05_sentinel2_geotiff/after.tif")
    res = predictor.detect(
        before_path=b_path,
        after_path=a_path,
        storage_root=STORAGE_ROOT,
        threshold=0.5,
    )
    assert res.change_detected is True
    assert res.bounds is not None
    assert len(res.bounds) == 4
    assert res.changed_area_m2 is not None and res.changed_area_m2 > 0
    # Coordinates must be valid WGS84
    assert -180.0 <= res.bounds[0] <= 180.0
    assert -90.0 <= res.bounds[1] <= 90.0


def test_health_endpoint(client):
    """GET /ml/health returns 200 with model loaded."""
    resp = client.get("/ml/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["model_loaded"] is True
    assert "model_version" in data


def test_model_info_endpoint(client):
    """GET /ml/model-info returns complete architectural metrics."""
    resp = client.get("/ml/model-info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["parameter_count"] == 24872157
    assert data["val_f1"] == 0.8475
    assert data["test_f1"] == 0.8184
    assert data["status"] == "ready"


def test_detect_change_endpoint_success(client):
    """POST /ml/detect-change processes valid request."""
    b_path = str(Path("sample_data/pairs/pair_01_construction/before.png").resolve())
    a_path = str(Path("sample_data/pairs/pair_01_construction/after.png").resolve())
    payload = {
        "before": {"image_path": b_path, "acquisition_date": "2023-03-10"},
        "after": {"image_path": a_path, "acquisition_date": "2024-02-15"},
        "investigation_id": "test-inv-001",
        "threshold": 0.5,
    }
    resp = client.post("/ml/detect-change", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["change_detected"] is True
    assert data["confidence"] > 0.70
    assert "mask_path" in data
    assert "preview_path" in data
    assert len(data["change_regions"]) > 0


def test_detect_change_missing_image_returns_404(client):
    """POST /ml/detect-change with non-existent path returns 404."""
    payload = {
        "before": {"image_path": "non_existent_before.png", "acquisition_date": "2023-01-01"},
        "after": {"image_path": "non_existent_after.png", "acquisition_date": "2023-02-01"},
    }
    resp = client.post("/ml/detect-change", json=payload)
    assert resp.status_code == 404
