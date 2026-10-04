"""
External schema: Intelligence module (Person 6)

Interface is NOT fixed — may be HTTP or a Python module callable.
The backend treats both the same after the adapter layer.

Fields marked  # ASSUMED  are highly inferred; Person 6 must confirm.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class _TolerantBase(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


# ---------------------------------------------------------------------------
# Intelligence  – Request
# ---------------------------------------------------------------------------

class IntelligenceRequest(BaseModel):
    """
    Payload sent to the Intelligence module.
    Carries all prior-stage results so Intelligence can build its outputs.
    """
    investigation_id: str
    bbox: list[float]
    historical_date: str    # ISO date
    current_date: str       # ISO date
    observations: list[dict[str, Any]]     # mapped satellite observations
    detection: Optional[dict[str, Any]] = None   # mapped ML result
    gis: Optional[dict[str, Any]] = None         # mapped GIS result


# ---------------------------------------------------------------------------
# Intelligence  – Outputs
# ---------------------------------------------------------------------------

class FingerprintSensitiveOverlap(_TolerantBase):
    """Sensitive-zone overlap summary inside the fingerprint."""
    percentage: Optional[float] = Field(default=None, ge=0, le=100)
    layers: list[str] = Field(default_factory=list)


class FingerprintOut(_TolerantBase):
    """Change Fingerprint (README §6 – Change Fingerprint)."""
    # ASSUMED: fingerprint_id format e.g. "UC-2026-A91F"
    fingerprint_id: str
    change_type: str
    changed_area_m2: Optional[float] = Field(default=None, ge=0)
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    temporal_behavior: Optional[str] = None      # e.g. "progressive"
    sensitive_overlap: Optional[FingerprintSensitiveOverlap] = None
    first_observed: Optional[date] = None
    model_version: Optional[str] = None


class TemporalEvent(_TolerantBase):
    """One step in the temporal reconstruction timeline."""
    observation_date: date
    event_type: str           # e.g. "ground_disturbance", "structure_appears"
    description: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    area_delta_m2: Optional[float] = None   # ASSUMED: area change at this step


class TemporalReconstructionOut(_TolerantBase):
    """Temporal reconstruction (README §7)."""
    events: list[TemporalEvent] = Field(default_factory=list)
    # ASSUMED: ISO date string of when the change first became persistent
    first_persistent_interval: Optional[str] = None
    summary: Optional[str] = None


class EvidenceItem(_TolerantBase):
    """One item in the evidence graph."""
    evidence_type: str           # e.g. "satellite_observation", "detection"
    source_reference: str        # e.g. "scene_id:S2A_…" or "detection:uuid"
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict)


class ExplanationOut(_TolerantBase):
    """Explanation text with evidence references."""
    text: str
    evidence_ids: list[str] = Field(default_factory=list)
    # ASSUMED: verification status
    status: str = "requires_human_verification"


class IntelligenceResponse(_TolerantBase):
    """Full response from the Intelligence module (README §Intelligence→Backend)."""
    fingerprint: Optional[FingerprintOut] = None
    temporal_reconstruction: Optional[TemporalReconstructionOut] = None
    evidence: list[EvidenceItem] = Field(default_factory=list)
    explanation: Optional[ExplanationOut] = None
    # ASSUMED: raw evidence graph structure for future use
    evidence_graph: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Assistant  – Request / Response
# ---------------------------------------------------------------------------

class AssistantRequest(BaseModel):
    """Body for asking the Investigation Assistant a question."""
    investigation_id: str
    question: str
    # ASSUMED: pass evidence IDs as context to ground the answer
    evidence_ids: list[str] = Field(default_factory=list)


class AssistantResponse(_TolerantBase):
    """Response from the Investigation Assistant."""
    answer: str
    evidence_ids: list[str] = Field(default_factory=list)
    uncertainty_notes: Optional[str] = None
    # ASSUMED: always echoed so the frontend can flag unverified answers
    status: str = "requires_human_verification"
