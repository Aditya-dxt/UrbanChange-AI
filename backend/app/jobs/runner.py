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
        FastAPI BackgroundTasks handles both sync and async callables natively.
        The framework awaits the coroutine in the running event loop after the
        HTTP response is sent — no asyncio.run() wrapper needed.
        """
        log.debug("InProcessJobRunner: enqueuing %s", func.__name__)
        self._bg.add_task(func, *args, **kwargs)
