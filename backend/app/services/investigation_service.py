"""
Investigation Service.

Handles all DB operations for investigations:
  - Create / read / update status & stage
  - Load all related records and build the frontend-facing InvestigationResponse
  - Timeline query

This service owns the translation from DB models → API response models.
It uses AssetService to convert filesystem paths → /api/assets/ URLs.
No business logic lives here — only DB + response building.
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone
from typing import Optional
from uuid import UUID

from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AssistantMessage,
    ChangeFingerprint,
    Classification,
    Detection,
    Evidence,
    GISResult,
    Investigation,
    NearbyFeature,
    SatelliteObservation,
    SensitiveIntersection,
    TemporalEvent,
)
from app.errors import InvestigationNotFoundError
from app.schemas.api import (
    AssistantMessageOut,
    ClassificationOut,
    DetectionOut,
    EvidenceOut,
    ExplanationOut,
    FingerprintOut,
    GISOut,
    InvestigationCreateResponse,
    InvestigationResponse,
    NearbyFeatureOut,
    ObservationOut,
    SensitiveIntersectionOut,
    TemporalEventOut,
    TemporalReconstructionOut,
    TimelineOut,
)
from app.services.asset_service import AssetService

log = logging.getLogger(__name__)


def _bbox_to_wkt(bbox: list[float]) -> str:
    west, south, east, north = bbox
    return (
        f"POLYGON(({west} {south}, {east} {south}, {east} {north}, "
        f"{west} {north}, {west} {south}))"
    )


class InvestigationService:
    def __init__(self, db: AsyncSession, asset_svc: AssetService) -> None:
        self._db = db
        self._asset = asset_svc

    # ── Create ─────────────────────────────────────────────────────────────────

    async def create(
        self,
        bbox: list[float],
        historical_date: date,
        current_date: Optional[date],
    ) -> InvestigationCreateResponse:
        aoi = WKTElement(_bbox_to_wkt(bbox), srid=4326)
        inv = Investigation(
            id=uuid.uuid4(),
            aoi=aoi,
            bbox=bbox,
            historical_date=historical_date,
            current_date=current_date,
            status="pending",
        )
        self._db.add(inv)
        await self._db.commit()
        await self._db.refresh(inv)
        log.info("investigation.created id=%s", inv.id)
        return InvestigationCreateResponse(id=inv.id, status=inv.status)

    async def create_with_observations(
        self,
        bbox: list[float],
        historical_date: date,
        current_date: date,
        before_path: str,
        after_path: str,
        before_preview: Optional[str] = None,
        after_preview: Optional[str] = None,
    ) -> InvestigationCreateResponse:
        aoi = WKTElement(_bbox_to_wkt(bbox), srid=4326)
        inv_id = uuid.uuid4()
        inv = Investigation(
            id=inv_id,
            aoi=aoi,
            bbox=bbox,
            historical_date=historical_date,
            current_date=current_date,
            status="pending",
        )
        self._db.add(inv)

        obs_before = SatelliteObservation(
            id=uuid.uuid4(),
            investigation_id=inv_id,
            role="before",
            scene_id=f"upload-before-{inv_id}",
            sensor="manual-upload",
            acquisition_date=historical_date,
            image_path=before_path,
            preview_path=before_preview or before_path,
            bounds=bbox,
            raw_payload={"source": "manual_upload", "role": "before"},
        )
        obs_after = SatelliteObservation(
            id=uuid.uuid4(),
            investigation_id=inv_id,
            role="after",
            scene_id=f"upload-after-{inv_id}",
            sensor="manual-upload",
            acquisition_date=current_date,
            image_path=after_path,
            preview_path=after_preview or after_path,
            bounds=bbox,
            raw_payload={"source": "manual_upload", "role": "after"},
        )
        self._db.add(obs_before)
        self._db.add(obs_after)
        await self._db.commit()
        await self._db.refresh(inv)
        log.info("investigation.created_with_upload id=%s", inv.id)
        return InvestigationCreateResponse(id=inv.id, status=inv.status)

    # ── Read ───────────────────────────────────────────────────────────────────

    async def get_or_404(self, investigation_id: UUID) -> Investigation:
        inv = await self._db.get(Investigation, investigation_id)
        if inv is None:
            raise InvestigationNotFoundError(str(investigation_id))
        return inv

    # ── Status / stage mutations ───────────────────────────────────────────────

    async def set_status(
        self,
        inv: Investigation,
        status: str,
        stage: Optional[str] = None,
        failed_stage: Optional[str] = None,
    ) -> None:
        inv.status = status
        if stage is not None:
            inv.stage = stage
        if failed_stage is not None:
            inv.failed_stage = failed_stage
        inv.updated_at = datetime.now(timezone.utc)
        await self._db.commit()
        log.info(
            "investigation.status_updated id=%s status=%s stage=%s",
            inv.id, status, stage,
        )

    async def set_stage(self, inv: Investigation, stage: str) -> None:
        inv.stage = stage
        inv.updated_at = datetime.now(timezone.utc)
        await self._db.commit()

    async def set_satellite_failure(self, inv: Investigation, reason: str) -> None:
        inv.satellite_failure_reason = reason
        inv.updated_at = datetime.now(timezone.utc)
        await self._db.commit()

    # ── Full response builder ──────────────────────────────────────────────────

    async def get_response(self, investigation_id: UUID) -> InvestigationResponse:
        inv = await self.get_or_404(investigation_id)

        observations = await self._load_observations(investigation_id)
        detection    = await self._load_detection(investigation_id)
        gis          = await self._load_gis(investigation_id)
        fingerprint  = await self._load_fingerprint(investigation_id)
        temporal     = await self._load_temporal_reconstruction(investigation_id)
        evidence     = await self._load_evidence(investigation_id)
        explanation  = await self._load_explanation(investigation_id)

        return InvestigationResponse(
            id=inv.id,
            status=inv.status,
            stage=inv.stage,
            failed_stage=inv.failed_stage,
            bbox=inv.bbox or [],
            historical_date=inv.historical_date,
            current_date=inv.current_date,
            created_at=inv.created_at,
            updated_at=inv.updated_at,
            observations=observations,
            detection=detection,
            gis=gis,
            fingerprint=fingerprint,
            temporal_reconstruction=temporal,
            evidence=evidence,
            explanation=explanation,
            satellite_failure_reason=inv.satellite_failure_reason,
        )

    # ── Timeline ───────────────────────────────────────────────────────────────

    async def get_timeline(self, investigation_id: UUID) -> TimelineOut:
        await self.get_or_404(investigation_id)
        events       = await self._load_temporal_events_raw(investigation_id)
        observations = await self._load_observations(investigation_id)
        return TimelineOut(
            investigation_id=investigation_id,
            events=events,
            observations=observations,
        )

    # ── Private loaders ────────────────────────────────────────────────────────

    async def _load_observations(
        self, investigation_id: UUID
    ) -> list[ObservationOut]:
        result = await self._db.execute(
            select(SatelliteObservation)
            .where(SatelliteObservation.investigation_id == investigation_id)
            .order_by(SatelliteObservation.acquisition_date)
        )
        rows = result.scalars().all()
        out = []
        for obs in rows:
            preview_url = self._asset.path_to_url(obs.preview_path)
            out.append(ObservationOut(
                scene_id=obs.scene_id,
                sensor=obs.sensor,
                acquisition_date=obs.acquisition_date,
                cloud_cover=obs.cloud_cover,
                crs=obs.crs,
                resolution=obs.resolution,
                image_url=self._asset.path_to_url(obs.image_path),
                preview_url=preview_url,
                preview_available=bool(preview_url),
                bounds=obs.bounds,
                role=obs.role,
            ))
        return out

    async def _load_detection(
        self, investigation_id: UUID
    ) -> Optional[DetectionOut]:
        result = await self._db.execute(
            select(Detection)
            .where(Detection.investigation_id == investigation_id)
            .limit(1)
        )
        det = result.scalars().first()
        if det is None:
            return None

        # Load classification
        cls_result = await self._db.execute(
            select(Classification)
            .where(Classification.detection_id == det.id)
            .limit(1)
        )
        cls = cls_result.scalars().first()

        preview_path = getattr(det, "mask_preview_path", None)
        mask_preview_url = self._asset.path_to_url(preview_path) if preview_path else None

        return DetectionOut(
            change_detected=det.change_detected,
            confidence=det.confidence,
            changed_area_pixels=det.changed_area_pixels,
            change_mask_url=self._asset.path_to_url(det.change_mask_path),
            mask_preview_url=mask_preview_url,
            mask_preview_available=bool(mask_preview_url),
            bounds=getattr(det, "mask_bounds", None),
            change_regions=det.change_regions or [],
            classification=(
                ClassificationOut(label=cls.label, confidence=cls.confidence)
                if cls else None
            ),
            model_version=det.model_version,
        )

    async def _load_gis(
        self, investigation_id: UUID
    ) -> Optional[GISOut]:
        result = await self._db.execute(
            select(GISResult)
            .where(GISResult.investigation_id == investigation_id)
            .limit(1)
        )
        gis = result.scalars().first()
        if gis is None:
            return None

        # Sensitive intersections
        si_result = await self._db.execute(
            select(SensitiveIntersection)
            .where(SensitiveIntersection.gis_result_id == gis.id)
        )
        intersections = [
            SensitiveIntersectionOut(
                layer_name=si.layer_name,
                overlap_pct=si.overlap_pct,
                geometry=si.geometry if not hasattr(si.geometry, 'desc') else None,
            )
            for si in si_result.scalars().all()
        ]

        # Nearby features
        nf_result = await self._db.execute(
            select(NearbyFeature)
            .where(NearbyFeature.gis_result_id == gis.id)
        )
        nearby = [
            NearbyFeatureOut(
                feature_type=nf.feature_type,
                name=nf.name,
                distance_m=nf.distance_m,
            )
            for nf in nf_result.scalars().all()
        ]

        return GISOut(
            changed_area_m2=gis.changed_area_m2,
            sensitive_intersections=intersections,
            overlap_percentages=gis.overlap_percentages or {},
            nearby_features=nearby,
            distances=gis.distances,
            geojson=gis.geojson,
        )

    async def _load_fingerprint(
        self, investigation_id: UUID
    ) -> Optional[FingerprintOut]:
        result = await self._db.execute(
            select(ChangeFingerprint)
            .where(ChangeFingerprint.investigation_id == investigation_id)
            .limit(1)
        )
        fp = result.scalars().first()
        if fp is None:
            return None
        return FingerprintOut(
            fingerprint_id=fp.fingerprint_id,
            change_type=fp.change_type,
            changed_area_m2=fp.changed_area_m2,
            confidence=fp.confidence,
            temporal_behavior=fp.temporal_behavior,
            sensitive_overlap=fp.sensitive_overlap,
            first_observed=fp.first_observed,
            model_version=fp.model_version,
        )

    async def _load_temporal_events_raw(
        self, investigation_id: UUID
    ) -> list[TemporalEventOut]:
        result = await self._db.execute(
            select(TemporalEvent)
            .where(TemporalEvent.investigation_id == investigation_id)
            .order_by(TemporalEvent.observation_date)
        )
        return [
            TemporalEventOut(
                observation_date=te.observation_date,
                event_type=te.event_type,
                description=te.description,
                confidence=te.confidence,
                area_delta_m2=te.area_delta_m2,
            )
            for te in result.scalars().all()
        ]

    async def _load_temporal_reconstruction(
        self, investigation_id: UUID
    ) -> Optional[TemporalReconstructionOut]:
        # Get temporal events
        events = await self._load_temporal_events_raw(investigation_id)
        if not events:
            return None

        # Get summary from fingerprint
        fp_result = await self._db.execute(
            select(ChangeFingerprint)
            .where(ChangeFingerprint.investigation_id == investigation_id)
            .limit(1)
        )
        fp = fp_result.scalars().first()

        return TemporalReconstructionOut(
            events=events,
            first_persistent_interval=(
                fp.raw_payload.get("temporal_reconstruction", {}).get("first_persistent_interval")
                if fp and fp.raw_payload else None
            ),
            summary=(
                fp.raw_payload.get("temporal_reconstruction", {}).get("summary")
                if fp and fp.raw_payload else None
            ),
        )

    async def _load_evidence(
        self, investigation_id: UUID
    ) -> list[EvidenceOut]:
        result = await self._db.execute(
            select(Evidence)
            .where(Evidence.investigation_id == investigation_id)
        )
        return [
            EvidenceOut(
                id=ev.id,
                evidence_type=ev.evidence_type,
                source_reference=ev.source_reference,
                metadata=ev.extra_metadata or {},
            )
            for ev in result.scalars().all()
        ]

    async def _load_explanation(
        self, investigation_id: UUID
    ) -> Optional[ExplanationOut]:
        # Explanation is stored in the fingerprint's raw_payload
        result = await self._db.execute(
            select(ChangeFingerprint)
            .where(ChangeFingerprint.investigation_id == investigation_id)
            .limit(1)
        )
        fp = result.scalars().first()
        if not fp or not fp.raw_payload:
            return None
        expl = fp.raw_payload.get("explanation")
        if not expl or not expl.get("text"):
            return None
        return ExplanationOut(
            text=expl["text"],
            evidence_ids=expl.get("evidence_ids", []),
            status=expl.get("status", "requires_human_verification"),
        )

    # ── Assistant messages ─────────────────────────────────────────────────────

    async def save_assistant_message(
        self,
        investigation_id: UUID,
        role: str,
        content: str,
        evidence_ids: list[str],
        uncertainty_notes: Optional[str],
    ) -> AssistantMessage:
        msg = AssistantMessage(
            id=uuid.uuid4(),
            investigation_id=investigation_id,
            role=role,
            content=content,
            evidence_ids=evidence_ids,
            uncertainty_notes=uncertainty_notes,
        )
        self._db.add(msg)
        await self._db.commit()
        await self._db.refresh(msg)
        return msg

    async def get_assistant_message_out(
        self, msg: AssistantMessage
    ) -> AssistantMessageOut:
        return AssistantMessageOut(
            id=msg.id,
            investigation_id=msg.investigation_id,
            role=msg.role,
            answer=msg.content,
            evidence_ids=msg.evidence_ids or [],
            uncertainty_notes=msg.uncertainty_notes,
            status="requires_human_verification",
            created_at=msg.created_at,
        )
