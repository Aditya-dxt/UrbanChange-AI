"""
Mock Intelligence Adapter.

Returns realistic fixture data matching the contract in
backend/tests/contracts/intelligence/response.json.
No LLM or retrieval logic is involved.
"""
from __future__ import annotations

import logging

from app.adapters.base import IntelligenceAdapter

log = logging.getLogger(__name__)


class MockIntelligenceAdapter(IntelligenceAdapter):
    """Fixture-driven mock for the Intelligence module (Person 6)."""

    async def analyze(self, payload: dict) -> dict:
        investigation_id = payload.get("investigation_id", "unknown")
        log.debug("MockIntelligenceAdapter.analyze investigation=%s", investigation_id)

        hist = payload.get("historical_date", "2025-04-14")
        curr = payload.get("current_date", "2026-01-18")

        return {
            "fingerprint": {
                "fingerprint_id": f"UC-MOCK-{investigation_id[:8].upper()}",
                "change_type": "construction",
                "changed_area_m2": 3842.0,
                "confidence": 0.94,
                "temporal_behavior": "progressive",
                "sensitive_overlap": {
                    "percentage": 64.0,
                    "layers": ["protected_forest"],
                },
                "first_observed": hist,
                "model_version": "siamese-unet-attention-v1",
            },
            "temporal_reconstruction": {
                "events": [
                    {
                        "observation_date": hist,
                        "event_type": "ground_disturbance",
                        "description": "Initial ground disturbance detected (mock)",
                        "confidence": 0.81,
                        "area_delta_m2": 1200.0,
                    },
                    {
                        "observation_date": curr,
                        "event_type": "structure_complete",
                        "description": "Large structure established (mock)",
                        "confidence": 0.94,
                        "area_delta_m2": 2642.0,
                    },
                ],
                "first_persistent_interval": f"{hist}/{curr}",
                "summary": (
                    f"Progressive construction observed from {hist} to {curr}. "
                    "Mock data — replace with real intelligence output."
                ),
            },
            "evidence": [
                {
                    "evidence_type": "satellite_observation",
                    "source_reference": f"scene_id:S2A_before_mock",
                    "metadata": {"acquisition_date": hist, "cloud_cover": 8.3},
                },
                {
                    "evidence_type": "detection",
                    "source_reference": "model:siamese-unet-attention-v1",
                    "metadata": {"confidence": 0.94, "changed_area_pixels": 38420},
                },
                {
                    "evidence_type": "gis_analysis",
                    "source_reference": "layer:protected_forest",
                    "metadata": {"overlap_pct": 64.0},
                },
            ],
            "evidence_graph": {
                "nodes": [
                    "observation_before",
                    "observation_after",
                    "detection",
                    "gis_analysis",
                ],
                "edges": [
                    {"from": "observation_before", "to": "detection"},
                    {"from": "observation_after", "to": "detection"},
                    {"from": "detection", "to": "gis_analysis"},
                ],
            },
            "explanation": {
                "text": (
                    "Significant construction activity was detected between "
                    f"{hist} and {curr}. "
                    "The changed area (3,842 m²) overlaps 64% with a protected "
                    "forest context layer. Model confidence is 94%. "
                    "Human verification is required before drawing legal conclusions. "
                    "(Mock explanation — replace with real intelligence output.)"
                ),
                "evidence_ids": ["ev_mock_001", "ev_mock_002", "ev_mock_003"],
                "status": "requires_human_verification",
            },
        }

    async def ask_assistant(
        self,
        investigation_id: str,
        question: str,
        evidence_ids: list[str],
    ) -> dict:
        log.debug(
            "MockIntelligenceAdapter.ask_assistant investigation=%s question=%s",
            investigation_id, question[:60],
        )
        return {
            "answer": (
                f"[Mock answer] Based on the available evidence for investigation "
                f"{investigation_id[:8]}, the satellite imagery shows significant "
                "construction activity between the two observation dates. "
                "The changed area (≈3,842 m²) intersects a protected context layer "
                "at 64% overlap. This is a mock response — the real Intelligence "
                "module will provide evidence-grounded answers."
            ),
            "evidence_ids": evidence_ids or ["ev_mock_001"],
            "uncertainty_notes": (
                "This is a mock response. All findings require human verification "
                "before any legal or regulatory conclusions are drawn."
            ),
            "status": "requires_human_verification",
        }
