from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    investigation_id: Optional[str] = None
    change_polygon: Optional[Dict[str, Any]] = None
    area_m2: Optional[float] = None
    change_area_sqm: Optional[float] = None
    change_type: Optional[str] = None
    classification: Optional[str] = None
    confidence: Optional[float] = None
    confidence_score: Optional[float] = None
    overlap_percent: Optional[float] = None
    timeline: Optional[List[Dict[str, Any]]] = None
    zoning: Optional[Dict[str, Any]] = None

    def resolved_area(self) -> float:
        if self.area_m2 is not None:
            return float(self.area_m2)
        if self.change_area_sqm is not None:
            return float(self.change_area_sqm)
        return 15200.0

    def resolved_change_type(self) -> str:
        return self.change_type or self.classification or "construction"

    def resolved_confidence(self) -> float:
        if self.confidence is not None:
            return float(self.confidence)
        if self.confidence_score is not None:
            return float(self.confidence_score)
        return 0.88

    def resolved_overlap_pct(self) -> float:
        if self.overlap_percent is not None:
            return float(self.overlap_percent)
        if self.zoning and isinstance(self.zoning, dict):
            return float(self.zoning.get("overlap_pct", 0.0))
        return 0.0


class FingerprintSensitiveOverlap(BaseModel):
    percentage: Optional[float] = None
    layers: List[str] = Field(default_factory=list)


class FingerprintOut(BaseModel):
    fingerprint_id: str
    change_type: str
    changed_area_m2: Optional[float] = None
    confidence: Optional[float] = None
    temporal_behavior: Optional[str] = None
    sensitive_overlap: Optional[FingerprintSensitiveOverlap] = None
    first_observed: Optional[date] = None
    model_version: Optional[str] = "UC-Intelligence-v1.4"


class TemporalEvent(BaseModel):
    observation_date: date
    event_type: str
    description: Optional[str] = None
    confidence: Optional[float] = None
    area_delta_m2: Optional[float] = None


class TemporalReconstructionOut(BaseModel):
    events: List[TemporalEvent] = Field(default_factory=list)
    first_persistent_interval: Optional[str] = None
    summary: Optional[str] = None


class EvidenceItem(BaseModel):
    evidence_type: str
    source_reference: str
    metadata: Optional[Dict[str, Any]] = None


class ExplanationOut(BaseModel):
    text: str
    evidence_ids: List[str] = Field(default_factory=list)
    status: str = "requires_human_verification"


class IntelligenceResponse(BaseModel):
    fingerprint: FingerprintOut
    temporal_reconstruction: Optional[TemporalReconstructionOut] = None
    evidence: List[EvidenceItem] = Field(default_factory=list)
    explanation: ExplanationOut
    evidence_graph: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    question: str
    evidence_ids: List[str] = Field(default_factory=list)
    investigation_id: Optional[str] = None
    evidence_graph: Optional[Dict[str, Any]] = None
    fingerprint: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    answer: str
    evidence_ids: List[str] = Field(default_factory=list)
    uncertainty_notes: Optional[str] = None
    status: str = "requires_human_verification"
