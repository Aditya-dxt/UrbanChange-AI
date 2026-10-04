"""
FastAPI shared dependencies.

Import these in route handlers via Annotated[…, Depends(…)] so they
are injectable and easy to override in tests.
"""
from __future__ import annotations

from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.session import get_async_session


# ── Settings dependency ────────────────────────────────────────────────────────

def settings_dep() -> Settings:
    return get_settings()


SettingsDep = Annotated[Settings, Depends(settings_dep)]


# ── Database session dependency ────────────────────────────────────────────────

async def db_session_dep() -> AsyncGenerator[AsyncSession, None]:
    from fastapi import HTTPException as _HTTPException
    from fastapi.exceptions import RequestValidationError as _RVE
    try:
        async for session in get_async_session():
            yield session
    except (_HTTPException, _RVE):
        raise  # re-raise FastAPI HTTP / validation errors as-is
    except Exception as exc:
        # Convert DB-level errors (ConnectionRefusedError, OperationalError…) → 503
        raise _HTTPException(
            status_code=503,
            detail={
                "code": "DB_UNAVAILABLE",
                "message": "Database is unavailable.",
                "reason": type(exc).__name__,
            },
        ) from exc


DBSession = Annotated[AsyncSession, Depends(db_session_dep)]
