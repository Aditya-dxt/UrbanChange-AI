"""
Request-ID middleware.

Reads X-Request-ID from the incoming request (if present) or generates
a new UUID4.  The ID is:
  1. Stored in request.state.request_id
  2. Written into the logging context variable (so all log records carry it)
  3. Echoed back as X-Request-ID in the response

This must be mounted BEFORE all routers so the ID is available during
dependency injection and error handlers.
"""
from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.logging import request_id_ctx


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Inject a unique request ID into every request/response cycle."""

    HEADER = "X-Request-ID"

    async def dispatch(self, request: Request, call_next: object) -> Response:
        # Prefer client-supplied ID so distributed traces are correlated.
        req_id = request.headers.get(self.HEADER) or str(uuid.uuid4())

        # Make available on the request state.
        request.state.request_id = req_id

        # Set the context variable so loggers pick it up automatically.
        token = request_id_ctx.set(req_id)

        try:
            response: Response = await call_next(request)  # type: ignore[arg-type]
        finally:
            request_id_ctx.reset(token)

        response.headers[self.HEADER] = req_id
        return response
