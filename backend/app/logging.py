"""
Structured logging configuration.

Sets up stdlib logging with a JSON formatter in production and a
human-readable colorized formatter in development.  A `request_id`
context variable is threaded through every log record emitted inside
a request lifecycle.

Usage:
    from app.logging import configure_logging, get_logger
    configure_logging(log_level="INFO", env="development")
    log = get_logger(__name__)
    log.info("investigation.created", investigation_id=str(inv_id))
"""
from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import Any

# Context variable shared across the request lifecycle.
# Set by RequestIDMiddleware; read by every logger call.
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class _RequestIDFilter(logging.Filter):
    """Inject request_id into every LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        record.request_id = request_id_ctx.get("-")
        return True


class _JSONFormatter(logging.Formatter):
    """
    Single-line JSON log formatter.
    Produces:  {"level":"INFO","logger":"app.main","request_id":"…","message":"…","…extra…"}
    """

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        import json
        import traceback

        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = traceback.format_exception(*record.exc_info)
        # Carry through any extra keyword args passed to the logger call.
        for key, val in record.__dict__.items():
            if key not in _STDLIB_RECORD_KEYS and not key.startswith("_"):
                payload[key] = val
        return json.dumps(payload, default=str)


# Keys that belong to the stdlib LogRecord and should not be re-emitted.
_STDLIB_RECORD_KEYS = frozenset(
    {
        "name", "msg", "args", "levelname", "levelno", "pathname",
        "filename", "module", "exc_info", "exc_text", "stack_info",
        "lineno", "funcName", "created", "msecs", "relativeCreated",
        "thread", "threadName", "processName", "process", "message",
        "taskName", "request_id",
    }
)


def configure_logging(log_level: str = "INFO", env: str = "development") -> None:
    """
    Call once at application startup.
    - development → colored, human-readable output via stdlib
    - staging / production → JSON output
    """
    root = logging.getLogger()
    root.setLevel(log_level)

    # Remove any existing handlers (e.g. added by uvicorn).
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_RequestIDFilter())

    if env == "development":
        fmt = (
            "%(asctime)s  %(levelname)-8s  [%(request_id)s]  %(name)s  %(message)s"
        )
        handler.setFormatter(logging.Formatter(fmt, datefmt="%H:%M:%S"))
    else:
        handler.setFormatter(_JSONFormatter())

    root.addHandler(handler)

    # Silence noisy third-party libraries.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a stdlib logger with the request-ID filter pre-attached."""
    log = logging.getLogger(name)
    # Idempotent: only add the filter once.
    if not any(isinstance(f, _RequestIDFilter) for f in log.filters):
        log.addFilter(_RequestIDFilter())
    return log
