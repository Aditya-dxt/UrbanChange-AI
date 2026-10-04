"""
pytest configuration and shared fixtures.
Full fixtures (DB, async client, adapter overrides) added in Phase 8.
"""
from __future__ import annotations

import pytest


# ── Async test mode ────────────────────────────────────────────────────────────
# All async tests use anyio as the backend.
pytest_plugins = ("anyio",)
