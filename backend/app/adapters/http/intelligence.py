"""HTTP adapter for the Intelligence module (Person 6)."""
from __future__ import annotations

import logging

from app.adapters.base import IntelligenceAdapter
from app.adapters.http._http import post_with_retry

log = logging.getLogger(__name__)
_MODULE = "intelligence"


class HttpIntelligenceAdapter(IntelligenceAdapter):
    """
    Calls the real Intelligence service over HTTP.
    Endpoints (interface not yet fully fixed — assumed based on contract):
      POST {base_url}/intelligence/analyze
      POST {base_url}/intelligence/assistant
    If Person 6 changes the path, update ONLY the path strings below.
    """

    def __init__(self, base_url: str, timeout: int) -> None:
        self._base_url = base_url
        self._timeout = float(timeout)
        log.info("HttpIntelligenceAdapter base_url=%s timeout=%s", base_url, timeout)

    async def analyze(self, payload: dict) -> dict:
        return await post_with_retry(
            self._base_url, "/intelligence/analyze", payload, _MODULE, "analyze", self._timeout
        )

    async def ask_assistant(
        self,
        investigation_id: str,
        question: str,
        evidence_ids: list[str],
    ) -> dict:
        payload = {
            "investigation_id": investigation_id,
            "question": question,
            "evidence_ids": evidence_ids,
        }
        return await post_with_retry(
            self._base_url, "/intelligence/assistant", payload, _MODULE, "assistant", self._timeout
        )
