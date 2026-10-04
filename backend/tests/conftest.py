"""
pytest configuration and shared fixtures for the UrbanChange AI backend.

Test categories:
  unit/        — pure Python, no DB, no HTTP, no adapters
  contract/    — validate JSON fixtures against external schemas + mappers
  integration/ — HTTP endpoints via httpx ASGI transport; DB session mocked

Marks:
  @pytest.mark.requires_db  — skipped unless INTEGRATION_TEST_DB_URL is set
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

# anyio provides the async backend for all async tests
pytest_plugins = ("anyio",)

# ── Paths ──────────────────────────────────────────────────────────────────────
TESTS_DIR = Path(__file__).parent
CONTRACTS_DIR = TESTS_DIR / "contracts"
BACKEND_DIR = TESTS_DIR.parent


# ── Markers ────────────────────────────────────────────────────────────────────

def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "requires_db: mark test as requiring a real PostgreSQL+PostGIS instance "
        "(skipped unless INTEGRATION_TEST_DB_URL env var is set)",
    )


def pytest_collection_modifyitems(config, items):
    import os
    if not os.environ.get("INTEGRATION_TEST_DB_URL"):
        skip_db = pytest.mark.skip(reason="INTEGRATION_TEST_DB_URL not set")
        for item in items:
            if "requires_db" in item.keywords:
                item.add_marker(skip_db)


# ── Contract fixture loader ────────────────────────────────────────────────────

def load_fixture(module: str, filename: str) -> dict:
    """Load a JSON fixture from tests/contracts/<module>/<filename>."""
    path = CONTRACTS_DIR / module / filename
    with open(path) as f:
        return json.load(f)


# ── Temporary storage root ────────────────────────────────────────────────────

@pytest.fixture
def tmp_storage(tmp_path: Path) -> Path:
    """A temporary directory acting as STORAGE_ROOT for AssetService tests."""
    return tmp_path


# ── App + HTTP client fixtures ────────────────────────────────────────────────

@pytest.fixture
def app():
    """Return the FastAPI app (no DB session override — use for non-DB endpoints)."""
    from app.main import app as _app
    return _app


@pytest.fixture
def mock_db_session():
    """Return a MagicMock that quacks like an AsyncSession."""
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def app_no_db(mock_db_session):
    """
    Return the FastAPI app with the DB dependency overridden by mock_db_session.
    Use this for endpoint tests that would otherwise fail with DB-unavailable.
    """
    from app.main import app as _app
    from app.api.deps import db_session_dep

    async def _override() -> AsyncGenerator:
        yield mock_db_session

    _app.dependency_overrides[db_session_dep] = _override
    yield _app
    _app.dependency_overrides.pop(db_session_dep, None)


@pytest.fixture
async def async_client(app):
    """Async httpx client pointing at the real app (no DB override)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
async def async_client_no_db(app_no_db):
    """Async httpx client with DB dependency mocked out."""
    async with AsyncClient(transport=ASGITransport(app=app_no_db), base_url="http://test") as client:
        yield client
