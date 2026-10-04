"""
Python-module adapter for the Intelligence module.

Used when INTELLIGENCE_ADAPTER=python.
Loads INTELLIGENCE_PYTHON_ENTRYPOINT="package.module:function" via importlib
and calls it directly (no HTTP). Useful when intelligence code lives in the
same Python environment as the backend.

The entrypoint function must accept a dict and return a dict matching
the IntelligenceResponse contract.
"""
from __future__ import annotations

import importlib
import logging
from typing import Any, Callable

from app.adapters.base import IntelligenceAdapter

log = logging.getLogger(__name__)


def _load_entrypoint(entrypoint: str) -> Callable[[dict], dict]:
    """
    Load a callable from "package.module:function" notation.
    Raises ImportError with a clear message if not found.
    """
    if not entrypoint or ":" not in entrypoint:
        raise ImportError(
            f"INTELLIGENCE_PYTHON_ENTRYPOINT must be 'package.module:function', "
            f"got: {entrypoint!r}"
        )
    module_path, func_name = entrypoint.rsplit(":", 1)
    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as exc:
        raise ImportError(
            f"Cannot import intelligence module '{module_path}': {exc}. "
            "Make sure the intelligence package is installed in the same virtualenv."
        ) from exc
    func = getattr(module, func_name, None)
    if func is None:
        raise ImportError(
            f"Function '{func_name}' not found in module '{module_path}'."
        )
    log.info("intelligence python_module loaded entrypoint=%s", entrypoint)
    return func


class PythonModuleIntelligenceAdapter(IntelligenceAdapter):
    """
    Calls the intelligence module as a Python function in-process.
    The function receives the full payload dict and returns a dict
    matching the IntelligenceResponse contract.
    """

    def __init__(self, entrypoint: str) -> None:
        self._entrypoint = entrypoint
        self._analyze_fn: Callable[[dict], dict] | None = None
        self._assistant_fn: Callable[[dict], dict] | None = None

    def _get_analyze_fn(self) -> Callable[[dict], dict]:
        if self._analyze_fn is None:
            self._analyze_fn = _load_entrypoint(self._entrypoint)
        return self._analyze_fn

    async def analyze(self, payload: dict) -> dict:
        """Call the python entrypoint function synchronously (no async support assumed)."""
        log.debug(
            "PythonModuleIntelligenceAdapter.analyze investigation=%s",
            payload.get("investigation_id", "unknown"),
        )
        fn = self._get_analyze_fn()
        # If Person 6 provides an async function, await it; otherwise call directly
        import asyncio, inspect
        if inspect.iscoroutinefunction(fn):
            return await fn(payload)
        return fn(payload)

    async def ask_assistant(
        self,
        investigation_id: str,
        question: str,
        evidence_ids: list[str],
    ) -> dict:
        """
        Look for an optional 'ask_assistant' function in the same module.
        Falls back to a stub response if not found.
        """
        module_path = self._entrypoint.rsplit(":", 1)[0]
        try:
            module = importlib.import_module(module_path)
            fn = getattr(module, "ask_assistant", None)
        except Exception:
            fn = None

        if fn is None:
            log.warning(
                "intelligence python_module: no ask_assistant function found in %s — "
                "returning stub response",
                module_path,
            )
            return {
                "answer": "Assistant not implemented in the intelligence Python module yet.",
                "evidence_ids": [],
                "uncertainty_notes": "ask_assistant function not found in entrypoint module.",
                "status": "requires_human_verification",
            }

        payload = {
            "investigation_id": investigation_id,
            "question": question,
            "evidence_ids": evidence_ids,
        }
        import inspect
        if inspect.iscoroutinefunction(fn):
            return await fn(payload)
        return fn(payload)
