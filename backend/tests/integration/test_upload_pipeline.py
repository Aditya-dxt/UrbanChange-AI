"""
Integration tests for manual two-image upload flow and orchestrator pipeline.
"""
from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.models import Investigation, SatelliteObservation
from app.schemas.internal.satellite import ObservationInternal, SatelliteStageResult
from app.schemas.internal.ml import DetectionInternal, ClassificationInternal
from app.services.orchestrator import PipelineOrchestrator
from app.services.asset_service import AssetService
from app.config import get_settings


@pytest.fixture
def sample_pair_paths():
    b = Path("sample_data/pairs/pair_01_construction/before.png").resolve()
    a = Path("sample_data/pairs/pair_01_construction/after.png").resolve()
    assert b.exists()
    assert a.exists()
    return b, a


@pytest.mark.anyio
async def test_upload_endpoint_creates_investigation(app_no_db, mock_db_session, sample_pair_paths):
    """Test POST /api/investigations/upload accepts two images and returns 201 Created."""
    b_path, a_path = sample_pair_paths
    inv_id = uuid.uuid4()

    mock_db_session.commit = AsyncMock()

    async with AsyncClient(transport=ASGITransport(app=app_no_db), base_url="http://test") as client:
        with open(b_path, "rb") as fb, open(a_path, "rb") as fa:
            files = {
                "before": ("before.png", fb, "image/png"),
                "after": ("after.png", fa, "image/png"),
            }
            data = {
                "historical_date": "2023-03-10",
                "current_date": "2024-02-15",
                "bbox": "[80.32, 26.42, 80.36, 26.46]",
            }
            resp = await client.post("/api/investigations/upload", files=files, data=data)

    assert resp.status_code == 201
    res_json = resp.json()
    assert "id" in res_json
    assert res_json["status"] == "pending"


@pytest.mark.anyio
async def test_orchestrator_handles_non_georeferenced_upload():
    """Verify orchestrator gracefully skips GIS zoning for non-georeferenced upload."""
    settings = get_settings()
    inv_id = uuid.uuid4()

    inv = Investigation(
        id=inv_id,
        bbox=[80.32, 26.42, 80.36, 26.46],
        historical_date=date(2023, 3, 10),
        current_date=date(2024, 2, 15),
        status="running",
        stage=None,
    )

    db = AsyncMock()
    db.get = AsyncMock(return_value=inv)
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()

    # Pre-existing observations from upload
    obs_b = SatelliteObservation(
        id=uuid.uuid4(),
        investigation_id=inv_id,
        role="before",
        scene_id=f"upload-before-{inv_id}",
        sensor="manual-upload",
        acquisition_date=date(2023, 3, 10),
        cloud_cover=0.0,
        crs=None,
        resolution=0.5,
        image_path="/storage/before.png",
        bounds=None,
    )
    obs_a = SatelliteObservation(
        id=uuid.uuid4(),
        investigation_id=inv_id,
        role="after",
        scene_id=f"upload-after-{inv_id}",
        sensor="manual-upload",
        acquisition_date=date(2024, 2, 15),
        cloud_cover=0.0,
        crs=None,
        resolution=0.5,
        image_path="/storage/after.png",
        bounds=None,
    )

    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=[obs_b, obs_a])
    db.execute.return_value.scalars = MagicMock(return_value=scalars_mock)

    # Mock ML Adapter returning non-georeferenced mask
    mock_ml = AsyncMock()
    mock_ml.detect_change = AsyncMock(return_value={
        "change_detected": True,
        "confidence": 0.92,
        "changed_area_pixels": 2500,
        "mask_path": "/data/storage/masks/mask_test.png",
        "preview_path": "/data/storage/previews/preview_test.png",
        "bounds": None,  # Non-georeferenced
        "change_regions": [
            {
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0.1, 0.1], [0.5, 0.1], [0.5, 0.5], [0.1, 0.5], [0.1, 0.1]]],
                },
                "area_pixels": 2500,
                "confidence": 0.92,
                "label": "construction",
            }
        ],
        "classification": {"label": "construction", "confidence": 0.92},
        "model_version": "SatQuery-Siamese-UNet-v1.0",
        "threshold": 0.5,
    })

    mock_sat = AsyncMock()
    mock_gis = AsyncMock()
    mock_intel = AsyncMock()
    mock_intel.analyze = AsyncMock(return_value={
        "summary": "Construction detected from uploaded pair.",
        "fingerprint": {
            "fingerprint_id": "FP-UPLOAD-001",
            "change_type": "construction",
            "changed_area_m2": 625.0,
            "confidence": 0.92,
            "temporal_behavior": "persistent",
            "temporal_class": "persistent",
        },
        "timeline": [],
        "evidence_graph": {"nodes": [], "edges": []},
        "evidence_items": [],
        "explanation": "Uploaded optical pair shows new construction footprint.",
    })

    orchestrator = PipelineOrchestrator(
        db=db,
        settings=settings,
        satellite=mock_sat,
        ml=mock_ml,
        gis=mock_gis,
        intelligence=mock_intel,
        asset_svc=AssetService(Path("data/storage")),
    )

    await orchestrator.run(inv_id)

    # GIS analyze_change should NOT have been called because input is non-georeferenced
    assert mock_gis.analyze_change.call_count == 0
    # Intelligence stage was reached and completed
    assert mock_intel.analyze.call_count == 1
    assert inv.status == "completed"
