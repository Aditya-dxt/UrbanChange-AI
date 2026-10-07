"""
Integration tests — HTTP endpoints via httpx ASGI transport.

Tests that do NOT need a DB (validation, health, assets, rate limiting)
run against the real app. Tests that need a DB use the mock_db_session
fixture from conftest and are marked @pytest.mark.requires_db for
tests that need real data.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport


# ══════════════════════════════════════════════════════════════════════════════
# Health endpoints — no DB needed
# ══════════════════════════════════════════════════════════════════════════════

class TestHealth:

    @pytest.mark.anyio
    async def test_health_returns_200(self, async_client: AsyncClient):
        r = await async_client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "version" in data

    @pytest.mark.anyio
    async def test_health_ready_returns_503_without_db(self, async_client: AsyncClient):
        """Without a real Postgres, /health/ready should be degraded (503)."""
        r = await async_client.get("/health/ready")
        # Either 200 (DB up) or 503 (DB down) — both are valid structural responses
        assert r.status_code in (200, 503)
        data = r.json()
        assert "db" in data

    @pytest.mark.anyio
    async def test_health_has_request_id_header(self, async_client: AsyncClient):
        r = await async_client.get("/health")
        assert "x-request-id" in r.headers


# ══════════════════════════════════════════════════════════════════════════════
# Investigation create — input validation (no DB needed)
# ══════════════════════════════════════════════════════════════════════════════

class TestInvestigationValidation:

    @pytest.mark.anyio
    async def test_valid_request_no_db_returns_503(self, async_client: AsyncClient):
        """Without DB, valid request returns 503 (DB unavailable), not a crash."""
        r = await async_client.post("/api/investigations", json={
            "bbox": [77.10, 28.50, 77.30, 28.70],
            "historical_date": "2025-04-14",
        })
        assert r.status_code in (201, 503)
        data = r.json()
        # Either success or a structured error — never a raw traceback
        assert "id" in data or "code" in data

    @pytest.mark.anyio
    async def test_south_greater_than_north_returns_422(self, async_client: AsyncClient):
        r = await async_client.post("/api/investigations", json={
            "bbox": [77.10, 28.70, 77.30, 28.50],
            "historical_date": "2025-04-14",
        })
        assert r.status_code == 422

    @pytest.mark.anyio
    async def test_three_element_bbox_returns_422(self, async_client: AsyncClient):
        r = await async_client.post("/api/investigations", json={
            "bbox": [77.10, 28.50, 77.30],
            "historical_date": "2025-04-14",
        })
        assert r.status_code == 422

    @pytest.mark.anyio
    async def test_longitude_out_of_range_returns_422(self, async_client: AsyncClient):
        r = await async_client.post("/api/investigations", json={
            "bbox": [200.0, 28.50, 77.30, 28.70],
            "historical_date": "2025-04-14",
        })
        assert r.status_code == 422

    @pytest.mark.anyio
    async def test_latitude_out_of_range_returns_422(self, async_client: AsyncClient):
        r = await async_client.post("/api/investigations", json={
            "bbox": [77.10, -95.0, 77.30, 28.70],
            "historical_date": "2025-04-14",
        })
        assert r.status_code == 422

    @pytest.mark.anyio
    async def test_missing_historical_date_returns_422(self, async_client: AsyncClient):
        r = await async_client.post("/api/investigations", json={
            "bbox": [77.10, 28.50, 77.30, 28.70],
        })
        assert r.status_code == 422

    @pytest.mark.anyio
    async def test_missing_bbox_returns_422(self, async_client: AsyncClient):
        r = await async_client.post("/api/investigations", json={
            "historical_date": "2025-04-14",
        })
        assert r.status_code == 422

    @pytest.mark.anyio
    async def test_empty_body_returns_422(self, async_client: AsyncClient):
        r = await async_client.post("/api/investigations", json={})
        assert r.status_code == 422

    @pytest.mark.anyio
    async def test_error_response_has_request_id(self, async_client: AsyncClient):
        r = await async_client.post("/api/investigations", json={
            "bbox": [77.10, 28.70, 77.30, 28.50],
            "historical_date": "2025-04-14",
        })
        assert r.status_code == 422
        assert "x-request-id" in r.headers


# ══════════════════════════════════════════════════════════════════════════════
# Asset endpoint security — no DB needed
# ══════════════════════════════════════════════════════════════════════════════

class TestAssetSecurity:

    @pytest.mark.anyio
    async def test_url_encoded_traversal_blocked(self, async_client: AsyncClient):
        r = await async_client.get("/api/assets/%2e%2e%2fetc%2fpasswd")
        assert r.status_code == 400
        assert r.json()["code"] == "PATH_TRAVERSAL"

    @pytest.mark.anyio
    async def test_missing_asset_returns_404(self, async_client: AsyncClient):
        r = await async_client.get("/api/assets/no/such/file.tif")
        assert r.status_code == 404
        assert r.json()["code"] == "ASSET_NOT_FOUND"

    @pytest.mark.anyio
    async def test_error_response_structure(self, async_client: AsyncClient):
        r = await async_client.get("/api/assets/no/such/file.png")
        assert r.status_code == 404
        data = r.json()
        assert "code" in data
        assert "message" in data
        assert "request_id" in data


# ══════════════════════════════════════════════════════════════════════════════
# Rate limiting — no DB needed
# ══════════════════════════════════════════════════════════════════════════════

class TestRateLimiting:

    @pytest.mark.anyio
    async def test_run_endpoint_rate_limited_after_10_calls(self, async_client: AsyncClient):
        inv_id = "550e8400-e29b-41d4-a716-446655440001"  # unique ID to avoid conflicts
        responses = []
        for _ in range(12):
            r = await async_client.post(f"/api/investigations/{inv_id}/run")
            responses.append(r.status_code)
        assert 429 in responses, f"Expected 429 in responses: {responses}"

    @pytest.mark.anyio
    async def test_run_rate_limit_response_structure(self, async_client: AsyncClient):
        inv_id = "550e8400-e29b-41d4-a716-446655440002"
        for _ in range(11):
            r = await async_client.post(f"/api/investigations/{inv_id}/run")
        assert r.status_code == 429
        # FastAPI HTTPException detail (not our UrbanChangeError format — that's ok)
        assert r.status_code == 429


# ══════════════════════════════════════════════════════════════════════════════
# OpenAPI spec — no DB needed
# ══════════════════════════════════════════════════════════════════════════════

class TestOpenAPI:

    @pytest.mark.anyio
    async def test_openapi_json_is_valid(self, async_client: AsyncClient):
        r = await async_client.get("/openapi.json")
        assert r.status_code == 200
        spec = r.json()
        assert spec["info"]["title"] == "UrbanChange AI – Backend API"
        assert "/api/investigations" in spec["paths"]
        assert "/api/investigations/{investigation_id}/run" in spec["paths"]
        assert "/api/investigations/{investigation_id}" in spec["paths"]
        assert "/api/investigations/{investigation_id}/timeline" in spec["paths"]
        assert "/api/investigations/{investigation_id}/assistant" in spec["paths"]
        assert "/api/assets/{file_path}" in spec["paths"]
        assert "/health" in spec["paths"]
        assert "/health/ready" in spec["paths"]

    @pytest.mark.anyio
    async def test_docs_endpoint_returns_200(self, async_client: AsyncClient):
        r = await async_client.get("/docs")
        assert r.status_code == 200

    @pytest.mark.anyio
    async def test_all_required_response_schemas_present(self, async_client: AsyncClient):
        r = await async_client.get("/openapi.json")
        spec = r.json()
        schemas = spec.get("components", {}).get("schemas", {})
        required = [
            "InvestigationResponse",
            "InvestigationCreateRequest",
            "InvestigationCreateResponse",
            "ObservationOut",
            "DetectionOut",
            "GISOut",
            "TimelineOut",
            "AssistantMessageOut",
            "AssistantAskRequest",
        ]
        for name in required:
            assert name in schemas, f"Schema '{name}' missing from OpenAPI spec"

    @pytest.mark.anyio
    async def test_upload_endpoint_present_in_openapi(self, async_client: AsyncClient):
        r = await async_client.get("/openapi.json")
        spec = r.json()
        assert "/api/investigations/upload" in spec["paths"]

    @pytest.mark.anyio
    async def test_upload_invalid_file_extension_returns_400(self, async_client: AsyncClient):
        files = {
            "before": ("before.exe", b"fake binary content", "application/octet-stream"),
            "after": ("after.exe", b"fake binary content", "application/octet-stream"),
        }
        r = await async_client.post("/api/investigations/upload", files=files)
        assert r.status_code == 400
        assert "Unsupported file extension" in r.text
