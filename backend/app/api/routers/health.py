"""
Health check routers.

GET  /health        – liveness probe (always returns 200 if the process is up)
GET  /health/ready  – readiness probe:
                        • checks DB connectivity
                        • reports adapter mode + reachability for every module
                        • returns 503 if DB is not reachable
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.deps import DBSession, SettingsDep

log = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


# ── GET /health ───────────────────────────────────────────────────────────────

@router.get("/health", summary="Liveness probe")
async def health(settings: SettingsDep) -> dict:
    return {
        "status": "ok",
        "version": settings.api_version,
        "contract_version": settings.contract_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── GET /health/ready ─────────────────────────────────────────────────────────

@router.get("/health/ready", summary="Readiness probe")
async def health_ready(settings: SettingsDep) -> JSONResponse:
    """
    Returns the adapter mode and reachability of every module.

    Reachability check for http adapters: a lightweight HEAD/GET to
    <base_url>/health with a 3-second timeout.  For mock and python
    adapters reachability is always True (in-process).

    The endpoint never raises; it always returns a well-formed body.
    HTTP 503 is returned only when the database itself is not reachable.
    """
    db_ok = await _check_db(settings.database_url)

    modules: dict[str, dict] = {
        "satellite": await _check_module(
            mode=settings.satellite_adapter,
            base_url=settings.satellite_base_url,
        ),
        "ml": await _check_module(
            mode=settings.ml_adapter,
            base_url=settings.ml_base_url,
        ),
        "gis": await _check_module(
            mode=settings.gis_adapter,
            base_url=settings.gis_base_url,
        ),
        "intelligence": await _check_module(
            mode=settings.intelligence_adapter,
            base_url=settings.intelligence_base_url,
        ),
    }

    all_reachable = all(m["reachable"] for m in modules.values())
    ready = db_ok and all_reachable

    body = {
        "ready": ready,
        "db": "ok" if db_ok else "unavailable",
        "database": {"reachable": db_ok},
        "modules": modules,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    status_code = 200 if ready else 503
    return JSONResponse(content=body, status_code=status_code)


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _check_db(database_url: str) -> bool:
    """Attempt a SELECT 1 with a fresh short-lived connection. Never raises."""
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        engine = create_async_engine(database_url, pool_pre_ping=False, echo=False)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("health.db_unreachable error=%s", exc)
        return False


async def _check_module(mode: str, base_url: str) -> dict:
    """
    For mock / python adapters: always reachable (in-process).
    For http adapters: attempt a GET to <base_url>/health with 3 s timeout.
    """
    if mode in ("mock", "python"):
        return {"mode": mode, "reachable": True}

    # http mode – probe the remote service
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{base_url}/health")
            reachable = resp.status_code < 500
    except Exception as exc:  # noqa: BLE001
        log.debug("health.module_unreachable base_url=%s error=%s", base_url, exc)
        reachable = False

    return {"mode": mode, "reachable": reachable, "base_url": base_url}
