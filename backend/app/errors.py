"""
Centralised error handling.

All errors returned by the API conform to the contract shape:
    {
        "code":       str,         # machine-readable error code
        "message":    str,         # human-readable description
        "reason":     str | null,  # optional detail / cause
        "request_id": str          # echoed from X-Request-ID
    }

HTTPException raised inside route handlers is converted to this shape.
RequestValidationError (Pydantic) is also normalised here.
"""
from __future__ import annotations

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger(__name__)


# ── Custom application exceptions ────────────────────────────────────────────

class UrbanChangeError(Exception):
    """Base class for all application-level errors."""

    def __init__(
        self,
        code: str,
        message: str,
        reason: str | None = None,
        status_code: int = 500,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.reason = reason
        self.status_code = status_code


class MapperError(UrbanChangeError):
    """
    Raised when a module mapper cannot translate an external payload to
    the internal schema because a required field is absent.
    """

    def __init__(self, module: str, stage: str, missing_field: str) -> None:
        super().__init__(
            code="MAPPER_ERROR",
            message=(
                f"Module '{module}' returned an invalid payload at stage "
                f"'{stage}': required field '{missing_field}' is absent."
            ),
            reason=f"missing_field={missing_field!r}",
            status_code=502,
        )
        self.module = module
        self.stage = stage
        self.missing_field = missing_field


class AdapterError(UrbanChangeError):
    """Raised when a module adapter call fails (network, timeout, non-2xx)."""

    def __init__(self, module: str, stage: str, detail: str) -> None:
        super().__init__(
            code="ADAPTER_ERROR",
            message=f"Module '{module}' call failed at stage '{stage}': {detail}",
            reason=detail,
            status_code=502,
        )
        self.module = module
        self.stage = stage


class InvestigationNotFoundError(UrbanChangeError):
    def __init__(self, investigation_id: str) -> None:
        super().__init__(
            code="INVESTIGATION_NOT_FOUND",
            message=f"Investigation '{investigation_id}' does not exist.",
            status_code=404,
        )


class AssetNotFoundError(UrbanChangeError):
    def __init__(self, path: str) -> None:
        super().__init__(
            code="ASSET_NOT_FOUND",
            message=f"Asset '{path}' does not exist or is not accessible.",
            status_code=404,
        )


class PathTraversalError(UrbanChangeError):
    def __init__(self, path: str = "") -> None:
        super().__init__(
            code="PATH_TRAVERSAL",
            message=(
                f"Requested path '{path}' is outside the storage root."
                if path else "Requested path is outside the storage root."
            ),
            status_code=400,
        )


class UnsupportedMediaTypeError(UrbanChangeError):
    def __init__(self, content_type: str) -> None:
        super().__init__(
            code="UNSUPPORTED_MEDIA_TYPE",
            message=f"Content type '{content_type}' is not allowed.",
            status_code=415,
        )


# ── Helper ────────────────────────────────────────────────────────────────────

def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def _error_body(
    code: str,
    message: str,
    reason: str | None,
    request_id: str,
) -> dict[str, object]:
    return {
        "code": code,
        "message": message,
        "reason": reason,
        "request_id": request_id,
    }


# ── Exception handlers (registered in main.py) ────────────────────────────────

async def urban_change_error_handler(
    request: Request, exc: UrbanChangeError
) -> JSONResponse:
    log.warning(
        "application_error code=%s message=%s status=%s",
        exc.code, exc.message, exc.status_code,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.code, exc.message, exc.reason, _request_id(request)),
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    log.warning("http_exception status=%s detail=%s", exc.status_code, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(
            code=f"HTTP_{exc.status_code}",
            message=str(exc.detail),
            reason=None,
            request_id=_request_id(request),
        ),
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    # Flatten Pydantic errors into a readable reason string.
    reasons = "; ".join(
        f"{'.'.join(str(l) for l in e['loc'])}: {e['msg']}"
        for e in exc.errors()
    )
    log.warning("validation_error reason=%s", reasons)
    return JSONResponse(
        status_code=422,
        content=_error_body(
            code="VALIDATION_ERROR",
            message="Request body or parameters failed validation.",
            reason=reasons,
            request_id=_request_id(request),
        ),
    )
