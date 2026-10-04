"""
Abstract adapter base classes.

The orchestrator ONLY ever calls these interfaces.
It never imports from mock/, http/, or python_module/.
Switching a module from mock → http requires only a config change
(and at most one mapper file edit).

All methods are async and return the raw response dict from the module.
The orchestrator passes that raw dict to the mapper, which translates it
to the internal schema and returns (internal_model, raw_payload_dict).
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class SatelliteAdapter(ABC):
    """Contract for the satellite module (Person 2)."""

    @abstractmethod
    async def search(
        self,
        bbox: list[float],
        historical_date: str,
        current_date: str | None,
        max_cloud_cover: float,
        max_observations: int,
    ) -> dict:
        """
        Call POST /satellite/search.
        Returns the raw response dict from the module.
        """

    @abstractmethod
    async def fetch(self, scene_id: str, bbox: list[float]) -> dict:
        """
        Call POST /satellite/fetch for a specific scene.
        Returns the raw response dict (before/after pair + intermediates).
        """


class MLAdapter(ABC):
    """Contract for the ML module (Person 1)."""

    @abstractmethod
    async def detect_change(
        self,
        before_path: str,
        before_date: str,
        before_crs: str | None,
        before_resolution: float | None,
        after_path: str,
        after_date: str,
        after_crs: str | None,
        after_resolution: float | None,
        sensor: str,
        investigation_id: str,
    ) -> dict:
        """
        Call POST /ml/detect-change.
        Returns the raw response dict from the module.
        """


class GISAdapter(ABC):
    """Contract for the GIS module (Person 3)."""

    @abstractmethod
    async def analyze_change(
        self,
        change_regions: list[dict],
        bbox: list[float],
        context_layer_ids: list[str],
        investigation_id: str,
    ) -> dict:
        """
        Call POST /gis/analyze-change.
        Returns the raw response dict from the module.
        """


class IntelligenceAdapter(ABC):
    """Contract for the Intelligence module (Person 6)."""

    @abstractmethod
    async def analyze(self, payload: dict) -> dict:
        """
        Call the intelligence analysis function (HTTP or python callable).
        Payload contains all prior-stage results.
        Returns the raw response dict from the module.
        """

    @abstractmethod
    async def ask_assistant(
        self,
        investigation_id: str,
        question: str,
        evidence_ids: list[str],
    ) -> dict:
        """
        Call the investigation assistant.
        Returns the raw response dict.
        """
