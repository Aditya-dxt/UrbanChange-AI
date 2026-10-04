"""
FastAPI application factory.

Entry point: uvicorn app.main:app --reload

Startup sequence
  1. Configure structured logging
  2. Add RequestIDMiddleware (first – so all subsequent code has a request ID)
  3. Add CORSMiddleware
  4. Register exception handlers
  5. Include routers
  6. Lifespan: verify DB connection on startup
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.errors import (
    UrbanChangeError,
    http_exception_handler,
    urban_change_error_handler,
    validation_error_handler,
)
from app.logging import configure_logging, get_logger
from app.middleware.request_id import RequestIDMiddleware

# ── Bootstrap logging immediately (before any other module logs) ─────────────
_settings = get_settings()
configure_logging(log_level=_settings.log_level, env=_settings.app_env)
log = get_logger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup / shutdown lifecycle."""
    log.info("urbanchange_ai.startup env=%s version=%s", _settings.app_env, _settings.api_version)

    # Verify DB is reachable on startup (non-fatal warning if not – the
    # /health/ready endpoint will report the actual state).
    try:
        from sqlalchemy import text
        from app.db.session import async_engine

        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        log.info("db.connected")
    except Exception as exc:  # noqa: BLE001
        log.warning("db.connection_failed_at_startup error=%s", exc)

    yield  # ← application runs here

    log.info("urbanchange_ai.shutdown")
    from app.db.session import async_engine
    await async_engine.dispose()


# ── Application factory ────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="UrbanChange AI – Backend API",
        description=(
            "Explainable satellite change-detection and urban investigation platform. "
            "All mock adapters are active by default; switch each module via env vars."
        ),
        version=settings.api_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── Middleware (order matters: request-ID must be first) ──────────────────
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # ── Exception handlers ────────────────────────────────────────────────────
    app.add_exception_handler(UrbanChangeError, urban_change_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]

    # Catch-all: any unhandled exception (e.g. DB connection refused) → 500 JSON
    from fastapi import Request as _Request
    from fastapi.responses import JSONResponse as _JSONResponse

    async def _generic_error_handler(request: _Request, exc: Exception) -> _JSONResponse:
        request_id = getattr(request.state, "request_id", "-")
        log.error("unhandled_exception request_id=%s error=%s", request_id, exc, exc_info=True)
        return _JSONResponse(
            status_code=500,
            content={
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred.",
                "reason": type(exc).__name__,
                "request_id": request_id,
            },
        )

    app.add_exception_handler(Exception, _generic_error_handler)  # type: ignore[arg-type]

    # ── Routers ───────────────────────────────────────────────────────────────
    from app.api.routers.health import router as health_router
    from app.api.routers.investigations import router as investigations_router
    from app.api.routers.assets import router as assets_router

    app.include_router(health_router)
    app.include_router(investigations_router)
    app.include_router(assets_router)

    return app


app = create_app()
