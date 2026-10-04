"""
Adapter factory.

Reads SATELLITE_ADAPTER / ML_ADAPTER / GIS_ADAPTER / INTELLIGENCE_ADAPTER
from config and returns the correct concrete adapter instance.

This is the ONLY place in the codebase that knows which adapter class
corresponds to which mode. Everything else uses the abstract base.

Phase 4: mock adapters fully implemented.
Phase 7: http + python_module adapters will be added here.
"""
from __future__ import annotations

import logging

from app.adapters.base import (
    GISAdapter,
    IntelligenceAdapter,
    MLAdapter,
    SatelliteAdapter,
)
from app.config import Settings

log = logging.getLogger(__name__)


def get_satellite_adapter(settings: Settings) -> SatelliteAdapter:
    mode = settings.satellite_adapter
    log.info("satellite adapter mode=%s", mode)
    if mode == "mock":
        from app.adapters.mock.satellite import MockSatelliteAdapter
        return MockSatelliteAdapter()
    if mode == "http":
        from app.adapters.http.satellite import HttpSatelliteAdapter  # Phase 7
        return HttpSatelliteAdapter(
            base_url=settings.satellite_base_url,
            timeout=settings.satellite_timeout_seconds,
        )
    raise ValueError(f"Unknown SATELLITE_ADAPTER mode: {mode!r}")


def get_ml_adapter(settings: Settings) -> MLAdapter:
    mode = settings.ml_adapter
    log.info("ml adapter mode=%s", mode)
    if mode == "mock":
        from app.adapters.mock.ml import MockMLAdapter
        return MockMLAdapter()
    if mode == "http":
        from app.adapters.http.ml import HttpMLAdapter  # Phase 7
        return HttpMLAdapter(
            base_url=settings.ml_base_url,
            timeout=settings.ml_timeout_seconds,
        )
    raise ValueError(f"Unknown ML_ADAPTER mode: {mode!r}")


def get_gis_adapter(settings: Settings) -> GISAdapter:
    mode = settings.gis_adapter
    log.info("gis adapter mode=%s", mode)
    if mode == "mock":
        from app.adapters.mock.gis import MockGISAdapter
        return MockGISAdapter()
    if mode == "http":
        from app.adapters.http.gis import HttpGISAdapter  # Phase 7
        return HttpGISAdapter(
            base_url=settings.gis_base_url,
            timeout=settings.gis_timeout_seconds,
        )
    raise ValueError(f"Unknown GIS_ADAPTER mode: {mode!r}")


def get_intelligence_adapter(settings: Settings) -> IntelligenceAdapter:
    mode = settings.intelligence_adapter
    log.info("intelligence adapter mode=%s", mode)
    if mode == "mock":
        from app.adapters.mock.intelligence import MockIntelligenceAdapter
        return MockIntelligenceAdapter()
    if mode == "http":
        from app.adapters.http.intelligence import HttpIntelligenceAdapter  # Phase 7
        return HttpIntelligenceAdapter(
            base_url=settings.intelligence_base_url,
            timeout=settings.intelligence_timeout_seconds,
        )
    if mode == "python":
        from app.adapters.python_module.intelligence import PythonModuleIntelligenceAdapter
        return PythonModuleIntelligenceAdapter(
            entrypoint=settings.intelligence_python_entrypoint
        )
    raise ValueError(f"Unknown INTELLIGENCE_ADAPTER mode: {mode!r}")
