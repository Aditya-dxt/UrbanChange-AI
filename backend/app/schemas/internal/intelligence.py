"""
Internal schema: Intelligence stage results.

Canonical backend representation after mapping from IntelligenceResponse.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, Field


class FingerprintSensitiveOverlapInternal(BaseModel):
    percentage: Optional[float] = Field(default=None, ge=0, le=100)
    layers: list[str] = Field(default_factory=list)


class FingerprintInternal(BaseModel):
    fingerprint_id: str
    change_type: str
    changed_area_m2: Optional[float] = Field(default=None, ge=0)
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    temporal_behavior: Optional[str] = None
    sensitive_overlap: Optional[FingerprintSensitiveOverlapInternal] = None
    first_observed: Optional[date] = None
    model_version: Optional[str] = None


class TemporalEventInternal(BaseModel):
    observation_date: date
    event_type: str
    description: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    area_delta_m2: Optional[float] = None


class TemporalReconstructionInternal(BaseModel):
    events: list[TemporalEventInternal] = Field(default_factory=list)
    first_persistent_interval: Optional[str] = None
    summary: Optional[str] = None


class EvidenceInternal(BaseModel):
    evidence_type: str
    source_reference: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExplanationInternal(BaseModel):
    text: str
    evidence_ids: list[str] = Field(default_factory=list)
    status: str = "requires_human_verification"


class IntelligenceStageResult(BaseModel):
    """Complete normalised result from the Intelligence stage."""
    fingerprint: Optional[FingerprintInternal] = None
    temporal_reconstruction: Optional[TemporalReconstructionInternal] = None
    evidence: list[EvidenceInternal] = Field(default_factory=list)
    explanation: Optional[ExplanationInternal] = None
