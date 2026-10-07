"""
Pipeline Orchestrator.

Runs the full investigation pipeline:
  1. Satellite  → search + fetch best before/after pair
  2. ML         → detect-change on the pair
  3. GIS        → analyze-change with ML regions + context layers
  4. Intelligence → fingerprint, temporal, evidence, explanation

Stage isolation:
  - Each stage runs in its own try/except.
  - If a stage fails, earlier results are already committed to the DB.
  - Status is set to "partial" + failed_stage is recorded.
  - The frontend still receives all earlier results.

Integration rule:
  - The orchestrator calls ONLY abstract adapter interfaces (never internals).
  - Mappers are the only translation layer.
  - raw_payload is stored alongside every mapped result.

Entry point used by the job runner:
    await run_investigation_pipeline(investigation_id, database_url, settings)
"""
from __future__ import annotations

import logging
import uuid
from datetime import timezone
from pathlib import Path
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.adapters.base import (
    GISAdapter,
    IntelligenceAdapter,
    MLAdapter,
    SatelliteAdapter,
)
from app.adapters.factory import (
    get_gis_adapter,
    get_intelligence_adapter,
    get_ml_adapter,
    get_satellite_adapter,
)
from app.adapters.mappers.gis_mapper import map_gis_analyze_change
from app.adapters.mappers.intelligence_mapper import (
    map_intelligence_response,
)
from app.adapters.mappers.ml_mapper import map_ml_detect_change
from app.adapters.mappers.satellite_mapper import map_satellite_fetch
from app.config import Settings, get_settings
from app.db.models import (
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
from app.errors import AdapterError, MapperError
from app.schemas.internal.gis import GISResultInternal
from app.schemas.internal.intelligence import IntelligenceStageResult
from app.schemas.internal.ml import DetectionInternal
from app.schemas.internal.satellite import ObservationInternal, SatelliteStageResult
from app.services.asset_service import AssetService

log = logging.getLogger(__name__)

# Pipeline stage names (used for progress reporting)
STAGE_SEARCHING    = "searching_catalog"
STAGE_FILTERING    = "quality_filtering"
STAGE_RETRIEVING   = "retrieving_imagery"
STAGE_PREPROCESSING = "preprocessing"
STAGE_DETECTION    = "change_detection"
STAGE_GIS          = "gis_analysis"
STAGE_INTELLIGENCE = "building_evidence"


# ── Orchestrator class ─────────────────────────────────────────────────────────

class PipelineOrchestrator:
    """
    Runs the full investigation pipeline for a single investigation_id.
    Instantiated fresh for each run (not a singleton).
    """

    def __init__(
        self,
        db: AsyncSession,
        settings: Settings,
        satellite: SatelliteAdapter,
        ml: MLAdapter,
        gis: GISAdapter,
        intelligence: IntelligenceAdapter,
        asset_svc: AssetService,
    ) -> None:
        self._db      = db
        self._cfg     = settings
        self._sat     = satellite
        self._ml      = ml
        self._gis     = gis
        self._intel   = intelligence
        self._asset   = asset_svc

    # ── Main entry ─────────────────────────────────────────────────────────────

    async def run(self, investigation_id: UUID) -> None:
        inv = await self._db.get(Investigation, investigation_id)
        if inv is None:
            log.error("orchestrator.run: investigation not found id=%s", investigation_id)
            return

        log.info("orchestrator.run START id=%s", investigation_id)

        try:
            await self._set_status(inv, "running", STAGE_SEARCHING)

            # ── Stage 1–3: Satellite ──────────────────────────────────────────
            sat_result = await self._satellite_stage(inv)
            if sat_result is None:
                return  # failure already persisted

            # ── Stage 4: ML ───────────────────────────────────────────────────
            det_result, det_record = await self._ml_stage(inv, sat_result)
            if det_result is None:
                return

            # ── Stage 5: GIS ──────────────────────────────────────────────────
            gis_result, gis_record = await self._gis_stage(inv, det_result)
            if gis_result is None:
                return

            # ── Stage 6: Intelligence ─────────────────────────────────────────
            await self._intelligence_stage(inv, sat_result, det_result, gis_result)

            # ── Done ──────────────────────────────────────────────────────────
            await self._set_status(inv, "completed", STAGE_INTELLIGENCE)
            log.info("orchestrator.run COMPLETED id=%s", investigation_id)

        except Exception as exc:  # noqa: BLE001
            log.error(
                "orchestrator.run FATAL id=%s error=%s",
                investigation_id, exc, exc_info=True,
            )
            await self._set_status(inv, "failed", failed_stage=inv.stage or "unknown")

    # ── Satellite stage ────────────────────────────────────────────────────────

    async def _satellite_stage(
        self, inv: Investigation
    ) -> Optional[SatelliteStageResult]:
        try:
            # Check if observations were pre-populated (e.g. manual upload)
            existing_obs = (
                await self._db.execute(
                    select(SatelliteObservation).where(SatelliteObservation.investigation_id == inv.id)
                )
            ).scalars().all()
            before_obs = next((o for o in existing_obs if o.role == "before"), None)
            after_obs = next((o for o in existing_obs if o.role == "after"), None)
            if before_obs and after_obs:
                log.info("orchestrator: using pre-populated observations id=%s", inv.id)
                await self._set_stage(inv, STAGE_PREPROCESSING)
                return SatelliteStageResult(
                    success=True,
                    before=ObservationInternal(
                        scene_id=before_obs.scene_id or f"upload-before-{inv.id}",
                        sensor=before_obs.sensor or "manual-upload",
                        acquisition_date=before_obs.acquisition_date,
                        cloud_cover=before_obs.cloud_cover or 0.0,
                        crs=before_obs.crs or "EPSG:4326",
                        resolution=before_obs.resolution or 10.0,
                        image_path=before_obs.image_path,
                        preview_path=before_obs.preview_path,
                        bounds=before_obs.bounds or inv.bbox or [0.0, 0.0, 0.0, 0.0],
                        role="before",
                    ),
                    after=ObservationInternal(
                        scene_id=after_obs.scene_id or f"upload-after-{inv.id}",
                        sensor=after_obs.sensor or "manual-upload",
                        acquisition_date=after_obs.acquisition_date,
                        cloud_cover=after_obs.cloud_cover or 0.0,
                        crs=after_obs.crs or "EPSG:4326",
                        resolution=after_obs.resolution or 10.0,
                        image_path=after_obs.image_path,
                        preview_path=after_obs.preview_path,
                        bounds=after_obs.bounds or inv.bbox or [0.0, 0.0, 0.0, 0.0],
                        role="after",
                    ),
                )

            await self._set_stage(inv, STAGE_SEARCHING)
            bbox = inv.bbox or []
            hist = inv.historical_date.isoformat()
            curr = inv.current_date.isoformat() if inv.current_date else None

            # Search
            search_raw = await self._sat.search(
                bbox=bbox,
                historical_date=hist,
                current_date=curr,
                max_cloud_cover=self._cfg.satellite_max_cloud_cover
                    if hasattr(self._cfg, "satellite_max_cloud_cover") else 30.0,
                max_observations=max(2, self._cfg.temporal_max_observations + 2),
            )
            await self._set_stage(inv, STAGE_FILTERING)

            scenes = search_raw.get("scenes", [])
            if not scenes and not search_raw.get("success", True):
                reason = search_raw.get("reason") or "no_suitable_image"
                log.warning("orchestrator: satellite search returned no scenes reason=%s", reason)
                inv.satellite_failure_reason = reason
                await self._set_status(inv, "partial", failed_stage=STAGE_SEARCHING)
                return None

            # Pick best before/after from scenes (earliest with lowest cloud, latest)
            # The search result already ranks; we pick first & last as before/after
            sorted_scenes = sorted(scenes, key=lambda s: s.get("acquisition_date", ""))
            best_before = sorted_scenes[0] if sorted_scenes else None
            best_after  = sorted_scenes[-1] if len(sorted_scenes) > 1 else None

            if not best_before:
                inv.satellite_failure_reason = "no_suitable_image: search returned empty scenes list"
                await self._set_status(inv, "partial", failed_stage=STAGE_SEARCHING)
                return None

            # Fetch
            await self._set_stage(inv, STAGE_RETRIEVING)
            scene_id = best_before.get("scene_id", "")
            fetch_raw = await self._sat.fetch(scene_id=scene_id, bbox=bbox)

            sat_result, raw_payload = map_satellite_fetch(fetch_raw)

            # No suitable imagery — valid outcome
            if not sat_result.success:
                inv.satellite_failure_reason = sat_result.failure_reason
                await self._set_status(inv, "partial", failed_stage=STAGE_RETRIEVING)
                return None

            await self._set_stage(inv, STAGE_PREPROCESSING)

            # Persist observations
            await self._persist_observations(inv, sat_result, raw_payload)
            await self._db.commit()

            return sat_result

        except (MapperError, AdapterError) as exc:
            log.error("orchestrator: satellite stage error=%s", exc)
            await self._set_status(inv, "partial", failed_stage=STAGE_RETRIEVING)
            return None
        except Exception as exc:  # noqa: BLE001
            log.error("orchestrator: satellite stage unexpected error=%s", exc, exc_info=True)
            await self._set_status(inv, "partial", failed_stage=STAGE_RETRIEVING)
            return None

    async def _persist_observations(
        self,
        inv: Investigation,
        sat_result: SatelliteStageResult,
        raw_payload: dict,
    ) -> None:
        def _make_obs(obs: ObservationInternal) -> SatelliteObservation:
            return SatelliteObservation(
                id=uuid.uuid4(),
                investigation_id=inv.id,
                role=obs.role,
                scene_id=obs.scene_id,
                sensor=obs.sensor,
                acquisition_date=obs.acquisition_date,
                cloud_cover=obs.cloud_cover,
                crs=obs.crs,
                resolution=obs.resolution,
                image_path=obs.image_path,
                preview_path=obs.preview_path,
                bounds=obs.bounds,
                raw_payload=raw_payload,
            )

        if sat_result.before:
            self._db.add(_make_obs(sat_result.before))
        if sat_result.after:
            self._db.add(_make_obs(sat_result.after))
        for obs in sat_result.intermediate:
            self._db.add(_make_obs(obs))

    # ── ML stage ───────────────────────────────────────────────────────────────

    async def _ml_stage(
        self,
        inv: Investigation,
        sat_result: SatelliteStageResult,
    ) -> tuple[Optional[DetectionInternal], Optional[Detection]]:
        try:
            await self._set_stage(inv, STAGE_DETECTION)

            before = sat_result.before
            after  = sat_result.after

            if not before or not after:
                log.warning("orchestrator: ml stage skipped — no before/after pair")
                await self._set_status(inv, "partial", failed_stage=STAGE_DETECTION)
                return None, None

            if not before.image_path or not after.image_path:
                log.warning("orchestrator: ml stage skipped — missing image paths")
                await self._set_status(inv, "partial", failed_stage=STAGE_DETECTION)
                return None, None

            raw = await self._ml.detect_change(
                before_path=before.image_path,
                before_date=before.acquisition_date.isoformat(),
                before_crs=before.crs,
                before_resolution=before.resolution,
                after_path=after.image_path,
                after_date=after.acquisition_date.isoformat(),
                after_crs=after.crs,
                after_resolution=after.resolution,
                sensor=before.sensor,
                investigation_id=str(inv.id),
            )

            det_internal, raw_payload = map_ml_detect_change(raw)

            # Persist detection
            det_record = Detection(
                id=uuid.uuid4(),
                investigation_id=inv.id,
                change_detected=det_internal.change_detected,
                confidence=det_internal.confidence,
                changed_area_pixels=det_internal.changed_area_pixels,
                change_mask_path=det_internal.change_mask_path,
                mask_preview_path=det_internal.mask_preview_path,
                mask_bounds=det_internal.mask_bounds,
                change_regions=det_internal.change_regions,
                model_version=det_internal.model_version,
                preprocessing_version=det_internal.preprocessing_version,
                threshold=det_internal.threshold,
                raw_payload=raw_payload,
            )
            self._db.add(det_record)
            await self._db.flush()  # get det_record.id

            # Persist classification
            if det_internal.classification:
                cls_record = Classification(
                    id=uuid.uuid4(),
                    detection_id=det_record.id,
                    investigation_id=inv.id,
                    label=det_internal.classification.label,
                    confidence=det_internal.classification.confidence,
                    raw_payload={"classification": raw_payload.get("classification")},
                )
                self._db.add(cls_record)

            await self._db.commit()
            return det_internal, det_record

        except (MapperError, AdapterError) as exc:
            log.error("orchestrator: ml stage error=%s", exc)
            await self._set_status(inv, "partial", failed_stage=STAGE_DETECTION)
            return None, None
        except Exception as exc:  # noqa: BLE001
            log.error("orchestrator: ml stage unexpected error=%s", exc, exc_info=True)
            await self._set_status(inv, "partial", failed_stage=STAGE_DETECTION)
            return None, None

    # ── GIS stage ──────────────────────────────────────────────────────────────

    async def _gis_stage(
        self,
        inv: Investigation,
        det_internal: DetectionInternal,
    ) -> tuple[Optional[GISResultInternal], Optional[GISResult]]:
        try:
            await self._set_stage(inv, STAGE_GIS)

            context_layers = list(self._cfg.context_layer_ids)
            raw = await self._gis.analyze_change(
                change_regions=det_internal.change_regions,
                bbox=inv.bbox or [],
                context_layer_ids=context_layers,
                investigation_id=str(inv.id),
            )

            gis_internal, raw_payload = map_gis_analyze_change(raw)

            # Persist GIS result
            gis_record = GISResult(
                id=uuid.uuid4(),
                investigation_id=inv.id,
                changed_area_m2=gis_internal.changed_area_m2,
                overlap_percentages=gis_internal.overlap_percentages,
                distances=gis_internal.distances,
                geojson=gis_internal.geojson,
                layer_versions=gis_internal.layer_versions,
                raw_payload=raw_payload,
            )
            self._db.add(gis_record)
            await self._db.flush()

            # Persist sensitive intersections
            for si in gis_internal.sensitive_intersections:
                self._db.add(SensitiveIntersection(
                    id=uuid.uuid4(),
                    investigation_id=inv.id,
                    gis_result_id=gis_record.id,
                    layer_name=si.layer_name,
                    layer_id=si.layer_id,
                    overlap_pct=si.overlap_pct,
                    raw_payload={"layer_name": si.layer_name, "overlap_pct": si.overlap_pct},
                ))

            # Persist nearby features
            for nf in gis_internal.nearby_features:
                self._db.add(NearbyFeature(
                    id=uuid.uuid4(),
                    investigation_id=inv.id,
                    gis_result_id=gis_record.id,
                    feature_type=nf.feature_type,
                    name=nf.name,
                    distance_m=nf.distance_m,
                    raw_payload={"feature_type": nf.feature_type, "distance_m": nf.distance_m},
                ))

            await self._db.commit()
            return gis_internal, gis_record

        except (MapperError, AdapterError) as exc:
            log.error("orchestrator: gis stage error=%s", exc)
            await self._set_status(inv, "partial", failed_stage=STAGE_GIS)
            return None, None
        except Exception as exc:  # noqa: BLE001
            log.error("orchestrator: gis stage unexpected error=%s", exc, exc_info=True)
            await self._set_status(inv, "partial", failed_stage=STAGE_GIS)
            return None, None

    # ── Intelligence stage ─────────────────────────────────────────────────────

    async def _intelligence_stage(
        self,
        inv: Investigation,
        sat_result: SatelliteStageResult,
        det_internal: DetectionInternal,
        gis_internal: GISResultInternal,
    ) -> None:
        try:
            await self._set_stage(inv, STAGE_INTELLIGENCE)

            # Build payload for the Intelligence module
            obs_list = []
            for obs in [sat_result.before, sat_result.after] + sat_result.intermediate:
                if obs:
                    obs_list.append({
                        "scene_id": obs.scene_id,
                        "role": obs.role,
                        "acquisition_date": obs.acquisition_date.isoformat(),
                        "cloud_cover": obs.cloud_cover,
                        "sensor": obs.sensor,
                    })

            payload = {
                "investigation_id": str(inv.id),
                "bbox": inv.bbox or [],
                "historical_date": inv.historical_date.isoformat(),
                "current_date": (
                    inv.current_date.isoformat() if inv.current_date else None
                ),
                "observations": obs_list,
                "detection": {
                    "change_detected": det_internal.change_detected,
                    "confidence": det_internal.confidence,
                    "changed_area_pixels": det_internal.changed_area_pixels,
                    "model_version": det_internal.model_version,
                    "change_regions": det_internal.change_regions,
                },
                "gis": {
                    "changed_area_m2": gis_internal.changed_area_m2,
                    "sensitive_intersections": [
                        {"layer_name": si.layer_name, "overlap_pct": si.overlap_pct}
                        for si in gis_internal.sensitive_intersections
                    ],
                },
            }

            raw = await self._intel.analyze(payload)
            intel_internal, raw_payload = map_intelligence_response(raw)

            # Persist fingerprint (stores the full raw intelligence response)
            if intel_internal.fingerprint:
                fp = intel_internal.fingerprint
                fp_record = ChangeFingerprint(
                    id=uuid.uuid4(),
                    investigation_id=inv.id,
                    fingerprint_id=fp.fingerprint_id,
                    change_type=fp.change_type,
                    confidence=fp.confidence,
                    changed_area_m2=fp.changed_area_m2,
                    temporal_behavior=fp.temporal_behavior,
                    sensitive_overlap=(
                        {
                            "percentage": fp.sensitive_overlap.percentage,
                            "layers": fp.sensitive_overlap.layers,
                        }
                        if fp.sensitive_overlap else None
                    ),
                    first_observed=fp.first_observed,
                    model_version=fp.model_version,
                    # Store FULL raw intelligence payload for explanation + temporal summary
                    raw_payload=raw_payload,
                )
                self._db.add(fp_record)

            # Persist temporal events
            if intel_internal.temporal_reconstruction:
                for event in intel_internal.temporal_reconstruction.events:
                    self._db.add(TemporalEvent(
                        id=uuid.uuid4(),
                        investigation_id=inv.id,
                        observation_date=event.observation_date,
                        event_type=event.event_type,
                        description=event.description,
                        confidence=event.confidence,
                        area_delta_m2=event.area_delta_m2,
                        raw_payload={
                            "event_type": event.event_type,
                            "observation_date": event.observation_date.isoformat(),
                        },
                    ))

            # Persist evidence items
            for ev_item in intel_internal.evidence:
                self._db.add(Evidence(
                    id=uuid.uuid4(),
                    investigation_id=inv.id,
                    evidence_type=ev_item.evidence_type,
                    source_reference=ev_item.source_reference,
                    extra_metadata=ev_item.metadata,
                    raw_payload={"source_reference": ev_item.source_reference},
                ))

            await self._db.commit()

        except (MapperError, AdapterError) as exc:
            log.error("orchestrator: intelligence stage error=%s", exc)
            await self._set_status(inv, "partial", failed_stage=STAGE_INTELLIGENCE)
        except Exception as exc:  # noqa: BLE001
            log.error(
                "orchestrator: intelligence stage unexpected error=%s",
                exc, exc_info=True,
            )
            await self._set_status(inv, "partial", failed_stage=STAGE_INTELLIGENCE)

    # ── DB helpers ─────────────────────────────────────────────────────────────

    async def _set_status(
        self,
        inv: Investigation,
        status: str,
        stage: Optional[str] = None,
        failed_stage: Optional[str] = None,
    ) -> None:
        from datetime import datetime, timezone
        inv.status = status
        if stage is not None:
            inv.stage = stage
        if failed_stage is not None:
            inv.failed_stage = failed_stage
        inv.updated_at = datetime.now(timezone.utc)
        await self._db.commit()

    async def _set_stage(self, inv: Investigation, stage: str) -> None:
        from datetime import datetime, timezone
        inv.stage = stage
        inv.updated_at = datetime.now(timezone.utc)
        await self._db.commit()
        log.info("orchestrator.stage id=%s stage=%s", inv.id, stage)


# ── Public entry point (called by the job runner) ──────────────────────────────

async def run_investigation_pipeline(
    investigation_id: UUID,
    database_url: str,
    settings: Settings,
) -> None:
    """
    Top-level async function enqueued by the job runner.

    Creates its own DB session (the request session is closed by the time
    the background task runs) and runs the full pipeline.
    """
    engine = create_async_engine(database_url, echo=False)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with SessionLocal() as db:
        try:
            orchestrator = PipelineOrchestrator(
                db=db,
                settings=settings,
                satellite=get_satellite_adapter(settings),
                ml=get_ml_adapter(settings),
                gis=get_gis_adapter(settings),
                intelligence=get_intelligence_adapter(settings),
                asset_svc=AssetService(Path(settings.storage_root)),
            )
            await orchestrator.run(investigation_id)
        finally:
            await engine.dispose()
