"""
Shared HTTP retry/request utilities for all HTTP adapters.

Provides _post_with_retry() — a thin httpx wrapper that:
  - Retries on 5xx and network errors (exponential backoff, max 2 retries)
  - Raises AdapterError with module, stage, and detail on final failure
  - Raises AdapterError immediately on 4xx (no retry)
  - Returns raw parsed JSON dict on success
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.errors import AdapterError

log = logging.getLogger(__name__)

_MAX_RETRIES = 2
_BACKOFF_BASE = 1.0   # seconds; doubles each retry


async def post_with_retry(
    base_url: str,
    path: str,
    payload: dict[str, Any],
    module: str,
    stage: str,
    timeout: float,
) -> dict[str, Any]:
    """
    POST `payload` to `base_url + path` as JSON.
    Retries up to _MAX_RETRIES times on 5xx / network errors.
    Raises AdapterError on non-2xx or exhausted retries.
    Returns the parsed JSON dict.
    """
    url = f"{base_url.rstrip('/')}{path}"
    last_exc: Exception | None = None

    for attempt in range(_MAX_RETRIES + 1):
        if attempt > 0:
            wait = _BACKOFF_BASE * (2 ** (attempt - 1))
            log.warning(
                "http_adapter.retry module=%s stage=%s attempt=%d wait=%.1fs",
                module, stage, attempt, wait,
            )
            await asyncio.sleep(wait)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                log.debug("http_adapter.post module=%s url=%s attempt=%d", module, url, attempt)
                r = await client.post(url, json=payload)

            if 200 <= r.status_code < 300:
                log.debug("http_adapter.ok module=%s status=%d", module, r.status_code)
                return r.json()

            if r.status_code >= 500:
                # Server error — retry
                detail = f"HTTP {r.status_code}: {r.text[:300]}"
                log.warning("http_adapter.server_error module=%s stage=%s detail=%s", module, stage, detail)
                last_exc = AdapterError(module, stage, detail)
                continue   # retry

            # 4xx — client error, no retry
            raise AdapterError(
                module, stage,
                f"HTTP {r.status_code}: {r.text[:300]}"
            )

        except AdapterError:
            raise
        except httpx.TimeoutException as exc:
            detail = f"Timeout after {timeout}s: {exc}"
            log.warning("http_adapter.timeout module=%s stage=%s detail=%s", module, stage, detail)
            last_exc = AdapterError(module, stage, detail)
        except httpx.RequestError as exc:
            detail = f"Request error: {exc}"
            log.warning("http_adapter.request_error module=%s stage=%s detail=%s", module, stage, detail)
            last_exc = AdapterError(module, stage, detail)

    # All retries exhausted
    raise last_exc or AdapterError(module, stage, "Unknown error after retries")
