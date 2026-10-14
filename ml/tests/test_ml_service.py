"""
Comprehensive tests for ML Change Detection Service.
Tests model architecture, weights loading, sliding window,
GeoTIFF and PNG inference, FastAPI HTTP endpoints, multi-task heads,
dual resolution profiles, and vehicle perception.
"""
from pathlib import Path
import pytest
import numpy as np
import torch
from fastapi.testclient import TestClient

import sys

try:
    from app.model import SiameseUNetAttention
    from app.model_v2 import MultiTaskSiameseChangeNet, NUM_SEMANTIC_CLASSES
    from app.predictor import ChangePredictor
    from app.vehicles import VehicleDetectorService
    from app.schemas import MLDetectChangeResponse, VehiclesResult
    from app.main import app
except ImportError:
    from ml.app.model import SiameseUNetAttention
    from ml.app.model_v2 import MultiTaskSiameseChangeNet, NUM_SEMANTIC_CLASSES
    from ml.app.predictor import ChangePredictor
    from ml.app.vehicles import VehicleDetectorService
    from ml.app.schemas import MLDetectChangeResponse, VehiclesResult
    from ml.app.main import app

WEIGHTS_PATH = Path("weights/best_siamese_model.pth").resolve()
if not WEIGHTS_PATH.exists():
    WEIGHTS_PATH = Path("ml/weights/best_siamese_model.pth").resolve()

STORAGE_ROOT = Path("data/storage").resolve()


@pytest.fixture(scope="module")
def predictor():
    assert WEIGHTS_PATH.exists(), f"Weights file missing at {WEIGHTS_PATH}"
    return ChangePredictor(weights_path=WEIGHTS_PATH, device="cpu", engine="legacy")


@pytest.fixture(scope="module")
def predictor_v2():
    return ChangePredictor(weights_path=WEIGHTS_PATH, device="cpu", engine="v2")


@pytest.fixture(scope="module")
def client(predictor):
    with TestClient(app) as test_client:
        yield test_client


def test_model_instantiation():
    """Verify SiameseUNetAttention architecture and parameter count (~24.87M)."""
    model = SiameseUNetAttention()
    param_count = sum(p.numel() for p in model.parameters())
    assert param_count == 24872157


def test_multitask_model_instantiation():
    """Verify MultiTaskSiameseChangeNet parameter count (~34.59M) and heads."""
    model = MultiTaskSiameseChangeNet()
    param_count = sum(p.numel() for p in model.parameters())
    assert param_count > 30000000

    x1 = torch.randn(1, 3, 256, 256)
    x2 = torch.randn(1, 3, 256, 256)
    with torch.no_grad():
        change, s1, s2 = model(x1, x2)
    assert change.shape == (1, 1, 256, 256)
    assert s1.shape == (1, NUM_SEMANTIC_CLASSES, 256, 256)
    assert s2.shape == (1, NUM_SEMANTIC_CLASSES, 256, 256)


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
    prob_map, _, _ = predictor.predict_change_prob(dummy1, dummy2, profile="hires")
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
    assert res.profile_used == "hires"
    assert res.vehicles is not None
    assert res.vehicles.supported is True


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
    assert -180.0 <= res.bounds[0] <= 180.0
    assert -90.0 <= res.bounds[1] <= 90.0
    # Sentinel-2 should flag vehicle detection as unsupported
    assert res.profile_used == "sentinel2"
    assert res.vehicles is not None
    assert res.vehicles.supported is False
    assert res.vehicles.reason == "Vehicles are not resolvable at this ground resolution"


def test_vehicle_detector_resolution_rules():
    """Verify vehicle detection supports <= 0.5m and rejects > 0.5m."""
    svc = VehicleDetectorService(device="cpu")
    dummy = np.random.rand(256, 256, 3).astype(np.float32)

    # 1. High-resolution drone/aerial (0.2m)
    res_hires = svc.analyze_pair(dummy, dummy, pixel_size_m=0.2)
    assert res_hires["supported"] is True
    assert res_hires["reason"] is None
    assert isinstance(res_hires["before_count"], int)

    # 2. Sentinel-2 satellite (10m)
    res_s2 = svc.analyze_pair(dummy, dummy, pixel_size_m=10.0)
    assert res_s2["supported"] is False
    assert res_s2["reason"] == "Vehicles are not resolvable at this ground resolution"
    assert res_s2["before_count"] == 0
    assert res_s2["after_count"] == 0


def test_alias_synchronization_in_response():
    """Verify that both mask_path/change_mask_path and bounds/mask_bounds serialize properly."""
    resp = MLDetectChangeResponse(
        change_detected=True,
        confidence=0.9,
        changed_area_pixels=100,
        mask_path="/path/mask.png",
        preview_path="/path/preview.png",
        bounds=[77.1, 28.5, 77.2, 28.6],
        model_version="test-v1",
    )
    assert resp.change_mask_path == "/path/mask.png"
    assert resp.mask_preview_path == "/path/preview.png"
    assert resp.mask_bounds == [77.1, 28.5, 77.2, 28.6]


def test_missing_weights_fallback():
    """Verify that missing weights trigger a graceful fallback to legacy model without crashing."""
    bogus_path = Path("ml/weights/non_existent_weights.pth")
    # Initializing predictor should safely fallback to existing legacy weights
    pred = ChangePredictor(weights_path=bogus_path, device="cpu", engine="legacy")
    assert pred.legacy_model is not None


def test_health_endpoint(client):
    """GET /ml/health returns 200 with model loaded and active engine."""
    resp = client.get("/ml/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["model_loaded"] is True
    assert "model_version" in data
    assert "engine" in data
    assert "profiles_available" in data


def test_model_info_endpoint(client):
    """GET /ml/model-info returns complete architectural metrics and profile catalog."""
    resp = client.get("/ml/model-info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["parameter_count"] == 24872157
    assert data["val_f1"] == 0.8475
    assert data["test_f1"] == 0.8184
    assert data["status"] == "ready"
    assert "profiles" in data
    assert data["vehicles_enabled"] is True


def test_detect_change_endpoint_success(client):
    """POST /ml/detect-change processes valid request and conforms to external schema."""
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
    assert "vehicles" in data
    assert data["vehicles"]["supported"] is True


def test_detect_change_missing_image_returns_404(client):
    """POST /ml/detect-change with non-existent path returns 404."""
    payload = {
        "before": {"image_path": "non_existent_before.png", "acquisition_date": "2023-01-01"},
        "after": {"image_path": "non_existent_after.png", "acquisition_date": "2023-02-01"},
    }
    resp = client.post("/ml/detect-change", json=payload)
    assert resp.status_code == 404
