"""
Intelligence mapper.

The ONLY place that translates external Intelligence field names → internal schema.

Integration-first rules:
  - Unknown fields logged at DEBUG
  - fingerprint.fingerprint_id and fingerprint.change_type required
  - All other fields optional (Intelligence interface is not yet fixed)
  - Returns (IntelligenceStageResult, raw_payload_dict)
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Optional

from app.errors import MapperError
from app.schemas.internal.intelligence import (
    EvidenceInternal,
    ExplanationInternal,
    FingerprintInternal,
    FingerprintSensitiveOverlapInternal,
    IntelligenceStageResult,
    TemporalEventInternal,
    TemporalReconstructionInternal,
)

log = logging.getLogger(__name__)

_KNOWN_KEYS = frozenset({
    "fingerprint", "temporal_reconstruction", "evidence",
    "evidence_graph", "explanation",
})


def _log_extra(raw: dict, context: str, known: frozenset) -> None:
    extra = set(raw.keys()) - known
    if extra:
        log.debug("intelligence_mapper[%s]: ignoring unknown fields %s", context, extra)


# ── Fingerprint ────────────────────────────────────────────────────────────────

_FP_KNOWN = frozenset({
    "fingerprint_id", "change_type", "changed_area_m2", "confidence",
    "temporal_behavior", "sensitive_overlap", "first_observed", "model_version",
})


def _map_fingerprint(raw: dict) -> FingerprintInternal:
    _log_extra(raw, "fingerprint", _FP_KNOWN)

    if not raw.get("fingerprint_id"):
        raise MapperError("intelligence", "fingerprint", "fingerprint_id")
    if not raw.get("change_type"):
        raise MapperError("intelligence", "fingerprint", "change_type")

    overlap_raw = raw.get("sensitive_overlap")
    overlap = None
    if isinstance(overlap_raw, dict):
        overlap = FingerprintSensitiveOverlapInternal(
            percentage=overlap_raw.get("percentage"),
            layers=overlap_raw.get("layers", []),
        )

    first_obs = None
    if raw.get("first_observed"):
        try:
            first_obs = date.fromisoformat(str(raw["first_observed"]))
        except ValueError:
            log.warning("intelligence_mapper: invalid first_observed format — ignoring")

    return FingerprintInternal(
        fingerprint_id=raw["fingerprint_id"],
        change_type=raw["change_type"],
        changed_area_m2=float(raw["changed_area_m2"]) if raw.get("changed_area_m2") is not None else None,
        confidence=float(raw["confidence"]) if raw.get("confidence") is not None else None,
        temporal_behavior=raw.get("temporal_behavior"),
        sensitive_overlap=overlap,
        first_observed=first_obs,
        model_version=raw.get("model_version"),
    )


# ── Temporal reconstruction ────────────────────────────────────────────────────

_TR_KNOWN = frozenset({"events", "first_persistent_interval", "summary"})
_EV_KNOWN = frozenset({
    "observation_date", "event_type", "description", "confidence", "area_delta_m2",
})


def _map_temporal_event(raw: dict, idx: int) -> Optional[TemporalEventInternal]:
    _log_extra(raw, f"temporal_event[{idx}]", _EV_KNOWN)
    if not raw.get("observation_date"):
        log.warning("intelligence_mapper: temporal_event[%d] missing observation_date — skipping", idx)
        return None
    if not raw.get("event_type"):
        log.warning("intelligence_mapper: temporal_event[%d] missing event_type — skipping", idx)
        return None
    try:
        obs_date = date.fromisoformat(str(raw["observation_date"]))
    except ValueError:
        log.warning("intelligence_mapper: temporal_event[%d] invalid observation_date — skipping", idx)
        return None
    return TemporalEventInternal(
        observation_date=obs_date,
        event_type=raw["event_type"],
        description=raw.get("description"),
        confidence=float(raw["confidence"]) if raw.get("confidence") is not None else None,
        area_delta_m2=float(raw["area_delta_m2"]) if raw.get("area_delta_m2") is not None else None,
    )


def _map_temporal_reconstruction(raw: dict) -> TemporalReconstructionInternal:
    _log_extra(raw, "temporal_reconstruction", _TR_KNOWN)
    events = [
        mapped
        for i, item in enumerate(raw.get("events", []))
        if isinstance(item, dict) and (mapped := _map_temporal_event(item, i)) is not None
    ]
    return TemporalReconstructionInternal(
        events=events,
        first_persistent_interval=raw.get("first_persistent_interval"),
        summary=raw.get("summary"),
    )


# ── Evidence ───────────────────────────────────────────────────────────────────

_EVIDENCE_KNOWN = frozenset({"evidence_type", "source_reference", "metadata"})


def _map_evidence_item(raw: dict, idx: int) -> Optional[EvidenceInternal]:
    _log_extra(raw, f"evidence[{idx}]", _EVIDENCE_KNOWN)
    if not raw.get("evidence_type"):
        log.warning("intelligence_mapper: evidence[%d] missing evidence_type — skipping", idx)
        return None
    if not raw.get("source_reference"):
        log.warning("intelligence_mapper: evidence[%d] missing source_reference — skipping", idx)
        return None
    meta = raw.get("metadata", {})
    if not isinstance(meta, dict):
        meta = {}
    return EvidenceInternal(
        evidence_type=raw["evidence_type"],
        source_reference=raw["source_reference"],
        metadata=meta,
    )


# ── Explanation ────────────────────────────────────────────────────────────────

_EXPL_KNOWN = frozenset({"text", "evidence_ids", "status"})


def _map_explanation(raw: dict) -> Optional[ExplanationInternal]:
    _log_extra(raw, "explanation", _EXPL_KNOWN)
    if not raw.get("text"):
        log.warning("intelligence_mapper: explanation missing text — skipping")
        return None
    return ExplanationInternal(
        text=raw["text"],
        evidence_ids=raw.get("evidence_ids", []),
        status=raw.get("status", "requires_human_verification"),
    )


# ── Public API ─────────────────────────────────────────────────────────────────

def map_intelligence_response(raw: dict) -> tuple[IntelligenceStageResult, dict]:
    """
    Map raw Intelligence module response → (IntelligenceStageResult, raw_payload_dict).
    Raises MapperError if fingerprint.fingerprint_id or fingerprint.change_type absent.
    All other fields are optional.
    """
    log.debug("intelligence_mapper: raw keys=%s", list(raw.keys()))
    _log_extra(raw, "root", _KNOWN_KEYS)

    # Fingerprint — only required if present; but if present, must have required fields
    fingerprint = None
    fp_raw = raw.get("fingerprint")
    if fp_raw:
        fingerprint = _map_fingerprint(fp_raw)

    # Temporal reconstruction
    tr_raw = raw.get("temporal_reconstruction")
    temporal = _map_temporal_reconstruction(tr_raw) if tr_raw else None

    # Evidence list
    evidence = [
        mapped
        for i, item in enumerate(raw.get("evidence", []))
        if isinstance(item, dict) and (mapped := _map_evidence_item(item, i)) is not None
    ]

    # Explanation
    expl_raw = raw.get("explanation")
    explanation = _map_explanation(expl_raw) if expl_raw else None

    return (
        IntelligenceStageResult(
            fingerprint=fingerprint,
            temporal_reconstruction=temporal,
            evidence=evidence,
            explanation=explanation,
        ),
        raw,
    )


def map_assistant_response(raw: dict) -> dict:
    """
    Map raw assistant response.
    Returns a plain dict (no internal model needed — stored directly).
    Raises MapperError if 'answer' field is absent.
    """
    if not raw.get("answer"):
        raise MapperError("intelligence", "assistant", "answer")
    return {
        "answer": raw["answer"],
        "evidence_ids": raw.get("evidence_ids", []),
        "uncertainty_notes": raw.get("uncertainty_notes"),
        "status": raw.get("status", "requires_human_verification"),
    }
