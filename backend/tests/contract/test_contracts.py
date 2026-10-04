"""
Contract tests.

Verify that:
  1. Every JSON fixture in tests/contracts/<module>/ validates against the
     external Pydantic schema for that module.
  2. Every mock adapter output validates against the same external schema.
  3. Every validated payload maps cleanly through the mapper to the
     internal schema without errors.

These tests are the gate that BOTH the backend AND each module owner can run
to confirm the contract is honoured.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

CONTRACTS_DIR = Path(__file__).parent.parent / "contracts"


# ── Helpers ────────────────────────────────────────────────────────────────────

def load(module: str, filename: str) -> dict:
    path = CONTRACTS_DIR / module / filename
    with open(path) as f:
        return json.load(f)


# ══════════════════════════════════════════════════════════════════════════════
# Satellite contract
# ══════════════════════════════════════════════════════════════════════════════

class TestSatelliteContract:

    def test_search_response_fixture_maps(self):
        raw = load("satellite", "search_response.json")
        from app.adapters.mappers.satellite_mapper import map_satellite_search
        scenes, payload = map_satellite_search(raw)
        assert isinstance(scenes, list)

    def test_fetch_response_fixture_maps(self):
        raw = load("satellite", "fetch_response.json")
        from app.adapters.mappers.satellite_mapper import map_satellite_fetch
        result, payload = map_satellite_fetch(raw)
        assert result.success is True
        assert result.before is not None
        assert result.after is not None

    @pytest.mark.anyio
    async def test_mock_satellite_output_maps(self):
        from app.adapters.mock.satellite import MockSatelliteAdapter
        from app.adapters.mappers.satellite_mapper import map_satellite_fetch
        adapter = MockSatelliteAdapter()
        raw = await adapter.fetch("mock-scene-id", [77.1, 28.5, 77.3, 28.7])
        result, _ = map_satellite_fetch(raw)
        assert result.success is True
        assert result.before is not None
        assert result.after is not None

    @pytest.mark.anyio
    async def test_mock_satellite_search_output_maps(self):
        from app.adapters.mock.satellite import MockSatelliteAdapter
        from app.adapters.mappers.satellite_mapper import map_satellite_search
        adapter = MockSatelliteAdapter()
        raw = await adapter.search([77.1, 28.5, 77.3, 28.7], "2025-04-14", None, 30.0, 5)
        scenes, _ = map_satellite_search(raw)
        assert isinstance(scenes, list)
        assert len(scenes) >= 0


# ══════════════════════════════════════════════════════════════════════════════
# ML contract
# ══════════════════════════════════════════════════════════════════════════════

class TestMLContract:

    def test_detect_response_fixture_maps(self):
        raw = load("ml", "response.json")
        from app.adapters.mappers.ml_mapper import map_ml_detect_change
        det, _ = map_ml_detect_change(raw)
        assert det.change_detected is not None
        assert det.confidence >= 0.0
        assert det.model_version

    @pytest.mark.anyio
    async def test_mock_ml_output_maps(self):
        from app.adapters.mock.ml import MockMLAdapter
        from app.adapters.mappers.ml_mapper import map_ml_detect_change
        adapter = MockMLAdapter()
        raw = await adapter.detect_change(
            "/data/before.tif", "2025-04-14", "EPSG:4326", 10.0,
            "/data/after.tif", "2026-01-18", "EPSG:4326", 10.0,
            "Sentinel-2", "test-inv-id"
        )
        det, _ = map_ml_detect_change(raw)
        assert det.change_detected is True
        assert 0.0 <= det.confidence <= 1.0
        assert det.model_version
        assert det.changed_area_pixels > 0


# ══════════════════════════════════════════════════════════════════════════════
# GIS contract
# ══════════════════════════════════════════════════════════════════════════════

class TestGISContract:

    def test_analyze_response_fixture_maps(self):
        raw = load("gis", "response.json")
        from app.adapters.mappers.gis_mapper import map_gis_analyze_change
        result, _ = map_gis_analyze_change(raw)
        assert result.changed_area_m2 >= 0.0

    @pytest.mark.anyio
    async def test_mock_gis_output_maps(self):
        from app.adapters.mock.gis import MockGISAdapter
        from app.adapters.mappers.gis_mapper import map_gis_analyze_change
        adapter = MockGISAdapter()
        regions = [{"type": "Feature", "geometry": {"type": "Polygon", "coordinates": []}}]
        raw = await adapter.analyze_change(regions, [77.1, 28.5, 77.3, 28.7], ["protected_forest"], "test-inv-id")
        result, _ = map_gis_analyze_change(raw)
        assert result.changed_area_m2 > 0


# ══════════════════════════════════════════════════════════════════════════════
# Intelligence contract
# ══════════════════════════════════════════════════════════════════════════════

class TestIntelligenceContract:

    def test_analyze_response_fixture_maps(self):
        raw = load("intelligence", "response.json")
        from app.adapters.mappers.intelligence_mapper import map_intelligence_response
        result, _ = map_intelligence_response(raw)
        assert result.fingerprint is not None
        assert result.fingerprint.fingerprint_id
        assert result.fingerprint.change_type

    @pytest.mark.anyio
    async def test_assistant_response_maps(self):
        """Use mock adapter output directly — no separate fixture file needed."""
        from app.adapters.mock.intelligence import MockIntelligenceAdapter
        from app.adapters.mappers.intelligence_mapper import map_assistant_response
        adapter = MockIntelligenceAdapter()
        raw = await adapter.ask_assistant("contract-test", "What changed?", [])
        mapped = map_assistant_response(raw)
        assert mapped["answer"]
        assert mapped["status"] == "requires_human_verification"

    @pytest.mark.anyio
    async def test_mock_intelligence_analyze_maps(self):
        from app.adapters.mock.intelligence import MockIntelligenceAdapter
        from app.adapters.mappers.intelligence_mapper import map_intelligence_response
        adapter = MockIntelligenceAdapter()
        raw = await adapter.analyze({"investigation_id": "contract-test", "historical_date": "2025-04-14"})
        result, _ = map_intelligence_response(raw)
        assert result.fingerprint is not None
        assert result.explanation is not None
        assert result.explanation.status == "requires_human_verification"

    @pytest.mark.anyio
    async def test_mock_intelligence_assistant_maps(self):
        from app.adapters.mock.intelligence import MockIntelligenceAdapter
        from app.adapters.mappers.intelligence_mapper import map_assistant_response
        adapter = MockIntelligenceAdapter()
        raw = await adapter.ask_assistant("contract-test", "What changed?", [])
        mapped = map_assistant_response(raw)
        assert mapped["answer"]


# ══════════════════════════════════════════════════════════════════════════════
# Frontend API contract
# ══════════════════════════════════════════════════════════════════════════════

class TestAPISchemas:

    def test_investigation_create_request_valid_bbox(self):
        from app.schemas.api import InvestigationCreateRequest
        from datetime import date
        req = InvestigationCreateRequest(
            bbox=[77.1, 28.5, 77.3, 28.7],
            historical_date=date(2025, 4, 14),
        )
        assert req.bbox == [77.1, 28.5, 77.3, 28.7]

    def test_investigation_create_request_bad_bbox_south_gt_north(self):
        from app.schemas.api import InvestigationCreateRequest
        from pydantic import ValidationError
        from datetime import date
        with pytest.raises(ValidationError):
            InvestigationCreateRequest(
                bbox=[77.1, 28.7, 77.3, 28.5],  # south > north
                historical_date=date(2025, 4, 14),
            )

    def test_investigation_create_request_bad_bbox_lon_range(self):
        from app.schemas.api import InvestigationCreateRequest
        from pydantic import ValidationError
        from datetime import date
        with pytest.raises(ValidationError):
            InvestigationCreateRequest(
                bbox=[200.0, 28.5, 77.3, 28.7],  # lon out of range
                historical_date=date(2025, 4, 14),
            )

    def test_investigation_create_request_bad_bbox_3_elements(self):
        from app.schemas.api import InvestigationCreateRequest
        from pydantic import ValidationError
        from datetime import date
        with pytest.raises(ValidationError):
            InvestigationCreateRequest(
                bbox=[77.1, 28.5, 77.3],  # only 3 elements
                historical_date=date(2025, 4, 14),
            )
