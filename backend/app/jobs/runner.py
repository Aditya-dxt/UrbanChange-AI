"""
JobRunner abstraction.

The orchestrator calls job_runner.enqueue(coro_func, *args) and never
knows whether it's running in-process (FastAPI BackgroundTasks) or in
a Celery / RQ worker.

To swap to Celery: implement CeleryJobRunner(JobRunner) and return it
from get_job_runner() — nothing else changes.
"""
from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Coroutine

from fastapi import BackgroundTasks

log = logging.getLogger(__name__)


class JobRunner(ABC):
    """Abstract job runner interface."""

    @abstractmethod
    def enqueue(
        self,
        func: Callable[..., Coroutine[Any, Any, None]],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Enqueue an async function to run in the background."""


class InProcessJobRunner(JobRunner):
    """
    Runs jobs via FastAPI BackgroundTasks (in-process, after response is sent).

    Suitable for development and MVP. Replace with CeleryJobRunner for
    production-scale workloads.
    """

    def __init__(self, background_tasks: BackgroundTasks) -> None:
        self._bg = background_tasks

    def enqueue(
        self,
        func: Callable[..., Coroutine[Any, Any, None]],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Wraps the async coroutine in a sync wrapper that asyncio.run()s it,
        because BackgroundTasks expects sync callables.
        """
        def _sync_wrapper() -> None:
            try:
                asyncio.run(func(*args, **kwargs))
            except Exception as exc:  # noqa: BLE001
                log.error("InProcessJobRunner: job failed func=%s error=%s", func.__name__, exc, exc_info=True)

        log.debug("InProcessJobRunner: enqueuing %s", func.__name__)
        self._bg.add_task(_sync_wrapper)
