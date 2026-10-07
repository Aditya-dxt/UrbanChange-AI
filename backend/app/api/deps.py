"""
FastAPI shared dependencies.

Import these in route handlers via Annotated[…, Depends(…)] so they
are injectable and easy to override in tests.
"""
from __future__ import annotations

from typing import Annotated, AsyncGenerator, Optional

from fastapi import Depends, Header
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


# ── Authentication dependency (API Key / Bearer JWT) ──────────────────────────

async def verify_auth(
    settings: SettingsDep,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> Optional[str]:
    import os
    from fastapi import HTTPException as _HTTPException, status as _status

    configured_key = getattr(settings, "api_key", None) or os.getenv("API_KEY")
    require_auth = getattr(settings, "require_auth", False) or (os.getenv("REQUIRE_AUTH", "false").lower() == "true")

    if not require_auth and not configured_key:
        return "anonymous"

    token = x_api_key
    if not token and authorization:
        if authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
        else:
            token = authorization.strip()

    if not token:
        if require_auth:
            raise _HTTPException(
                status_code=_status.HTTP_401_UNAUTHORIZED,
                detail="Missing API authentication credentials.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return "anonymous"

    if configured_key and token != configured_key:
        raise _HTTPException(
            status_code=_status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key or token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token


AuthDep = Annotated[Optional[str], Depends(verify_auth)]

