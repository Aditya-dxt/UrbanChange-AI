"""
Investigations router.

Implements ALL investigation endpoints consumed by the frontend (Person 5):
  POST /api/investigations           → create (pending)
  POST /api/investigations/{id}/run  → enqueue pipeline (202)
  GET  /api/investigations/{id}      → full result
  GET  /api/investigations/{id}/timeline
  POST /api/investigations/{id}/assistant

Rate limiting: a simple in-memory per-IP counter on /run.
In production, replace with a Redis-backed limiter.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import json
import shutil
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse

from app.adapters.factory import get_intelligence_adapter
from app.adapters.mappers.intelligence_mapper import map_assistant_response
from app.api.deps import AuthDep, DBSession, SettingsDep
from app.errors import InvestigationNotFoundError
from app.schemas.api import (
    AssistantAskRequest,
    AssistantMessageOut,
    InvestigationCreateRequest,
    InvestigationCreateResponse,
    InvestigationResponse,
    TimelineOut,
)
from app.services.asset_service import AssetService
from app.services.investigation_service import InvestigationService
from app.services.orchestrator import run_investigation_pipeline
from app.jobs.runner import InProcessJobRunner

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/investigations", tags=["investigations"])


# ── Simple in-memory rate limiter for /run ────────────────────────────────────
# Key: client IP, Value: list of call datetimes in the current minute window
_run_call_log: dict[str, list[datetime]] = defaultdict(list)
_upload_call_log: dict[str, list[datetime]] = defaultdict(list)


def _check_run_rate_limit(client_ip: str, limit_per_minute: int) -> bool:
    """Return True if the request is within the rate limit, False if exceeded."""
    now = datetime.now(timezone.utc)
    cutoff = now.timestamp() - 60
    calls = [t for t in _run_call_log[client_ip] if t.timestamp() > cutoff]
    if len(calls) >= limit_per_minute:
        _run_call_log[client_ip] = calls
        return False
    calls.append(now)
    _run_call_log[client_ip] = calls
    return True


def _check_upload_rate_limit(client_ip: str, limit_per_minute: int) -> bool:
    """Rate limit check specifically for /upload endpoint."""
    now = datetime.now(timezone.utc)
    cutoff = now.timestamp() - 60
    calls = [t for t in _upload_call_log[client_ip] if t.timestamp() > cutoff]
    if len(calls) >= limit_per_minute:
        _upload_call_log[client_ip] = calls
        return False
    calls.append(now)
    _upload_call_log[client_ip] = calls
    return True


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ── POST /api/investigations ──────────────────────────────────────────────────

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=InvestigationCreateResponse,
    summary="Create a new investigation",
)
async def create_investigation(
    body: InvestigationCreateRequest,
    db: DBSession,
    settings: SettingsDep,
) -> InvestigationCreateResponse:
    """
    Create a new investigation record (status = pending).
    Returns the investigation ID. Call /run to start the pipeline.
    """
    svc = InvestigationService(db, AssetService(Path(settings.storage_root)))
    return await svc.create(
        bbox=body.bbox,
        historical_date=body.historical_date,
        current_date=body.current_date,
    )


# ── POST /api/investigations/upload ───────────────────────────────────────────

@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
    response_model=InvestigationCreateResponse,
    summary="Create a new investigation from uploaded before/after images",
)
async def upload_investigation(
    request: Request,
    before: UploadFile = File(...),
    after: UploadFile = File(...),
    bbox: Optional[str] = Form(None),
    historical_date: Optional[str] = Form(None),
    current_date: Optional[str] = Form(None),
    db: DBSession = None,
    settings: SettingsDep = None,
    auth: AuthDep = None,
) -> InvestigationCreateResponse:
    """
    Create a new investigation directly from an uploaded before/after pair
    (GeoTIFF, PNG, JPEG). Reuses the orchestrator pipeline starting at the ML stage.
    """
    # Rate limit check
    limit = settings.run_rate_limit_per_minute
    if not _check_upload_rate_limit(_client_ip(request), limit):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: max {limit} upload calls per minute per IP.",
        )

    allowed_exts = {".tif", ".tiff", ".png", ".jpg", ".jpeg"}
    before_ext = Path(before.filename or "before.tif").suffix.lower()
    after_ext = Path(after.filename or "after.tif").suffix.lower()

    if before_ext not in allowed_exts or after_ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file extension. Allowed formats: GeoTIFF (.tif, .tiff), PNG (.png), JPEG (.jpg, .jpeg).",
        )

    # Resolve and validate bounding box
    parsed_bbox = [80.30, 26.40, 80.40, 26.50]
    if bbox:
        try:
            val = json.loads(bbox) if bbox.strip().startswith("[") else [float(x.strip()) for x in bbox.split(",")]
            if len(val) == 4:
                w, s, e, n = [float(x) for x in val]
                if not (-180 <= w <= 180 and -180 <= e <= 180 and -90 <= s <= 90 and -90 <= n <= 90):
                    raise ValueError("Coordinates out of range")
                if s >= n or w > e:
                    raise ValueError("Invalid bounding box ordering")
                parsed_bbox = [w, s, e, n]
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid bbox parameter: {e}",
            )

    # Resolve dates
    from datetime import date
    h_date = date(2024, 1, 1)
    if historical_date:
        try:
            h_date = date.fromisoformat(historical_date)
        except Exception:
            pass

    c_date = date(2025, 1, 1)
    if current_date:
        try:
            c_date = date.fromisoformat(current_date)
        except Exception:
            pass

    # Save uploaded files into storage root with size limits (max 50 MB)
    MAX_FILE_BYTES = 50 * 1024 * 1024
    upload_id = uuid.uuid4()
    target_dir = Path(settings.storage_root) / "uploads" / str(upload_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    before_path = target_dir / f"before{before_ext}"
    after_path = target_dir / f"after{after_ext}"

    # Read and validate size
    b_bytes = await before.read()
    a_bytes = await after.read()
    if len(b_bytes) > MAX_FILE_BYTES or len(a_bytes) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Uploaded file exceeds maximum allowed size of {MAX_FILE_BYTES // (1024*1024)} MB.",
        )

    with open(before_path, "wb") as f_out:
        f_out.write(b_bytes)
    with open(after_path, "wb") as f_out:
        f_out.write(a_bytes)

    svc = InvestigationService(db, AssetService(Path(settings.storage_root)))
    return await svc.create_with_observations(
        bbox=parsed_bbox,
        historical_date=h_date,
        current_date=c_date,
        before_path=str(before_path),
        after_path=str(after_path),
    )


# ── POST /api/investigations/{id}/run ─────────────────────────────────────────

@router.post(
    "/{investigation_id}/run",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start the detection pipeline for an investigation",
)
async def run_investigation(
    investigation_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    settings: SettingsDep,
    # NOTE: db is NOT a dependency here so rate limit fires first
) -> JSONResponse:
    """
    Enqueue the full satellite → ML → GIS → Intelligence pipeline.
    Returns 202 immediately; poll GET /{id} for progress.
    Rate limit checked BEFORE any DB call.
    """
    # ── Rate limit (no DB needed) ─────────────────────────────────────────────
    limit = settings.run_rate_limit_per_minute
    if not _check_run_rate_limit(_client_ip(request), limit):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: max {limit} /run calls per minute per IP.",
        )

    # ── DB validation ─────────────────────────────────────────────────────────
    from app.db.session import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as db:
            svc = InvestigationService(db, AssetService(Path(settings.storage_root)))
            inv = await svc.get_or_404(investigation_id)

            if inv.status in ("running", "completed"):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Investigation is already {inv.status}. Cannot re-run.",
                )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"code": "DB_UNAVAILABLE", "reason": type(exc).__name__}) from exc

    # ── Enqueue ───────────────────────────────────────────────────────────────
    job_runner = InProcessJobRunner(background_tasks)
    job_runner.enqueue(
        run_investigation_pipeline,
        investigation_id,
        settings.database_url,
        settings,
    )

    log.info("investigation.run_enqueued id=%s", investigation_id)
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"id": str(investigation_id), "status": "running"},
    )


# ── GET /api/investigations/{id} ──────────────────────────────────────────────

@router.get(
    "/{investigation_id}",
    response_model=InvestigationResponse,
    summary="Get full investigation result",
)
async def get_investigation(
    investigation_id: UUID,
    db: DBSession,
    settings: SettingsDep,
) -> InvestigationResponse:
    """
    Returns the full investigation result.
    Fields are null until their pipeline stage completes.
    Poll this endpoint for progress (check the `stage` field).
    """
    svc = InvestigationService(db, AssetService(Path(settings.storage_root)))
    return await svc.get_response(investigation_id)


# ── GET /api/investigations/{id}/timeline ─────────────────────────────────────

@router.get(
    "/{investigation_id}/timeline",
    response_model=TimelineOut,
    summary="Get temporal reconstruction timeline",
)
async def get_timeline(
    investigation_id: UUID,
    db: DBSession,
    settings: SettingsDep,
) -> TimelineOut:
    """
    Returns the temporal event list and satellite observations for the timeline view.
    """
    svc = InvestigationService(db, AssetService(Path(settings.storage_root)))
    return await svc.get_timeline(investigation_id)


# ── POST /api/investigations/{id}/assistant ───────────────────────────────────

@router.post(
    "/{investigation_id}/assistant",
    response_model=AssistantMessageOut,
    summary="Ask the Investigation Assistant a question",
)
async def ask_assistant(
    investigation_id: UUID,
    body: AssistantAskRequest,
    db: DBSession,
    settings: SettingsDep,
) -> AssistantMessageOut:
    """
    Delegates the question to the Intelligence adapter and persists the
    message. Always returns status=requires_human_verification.
    """
    svc = InvestigationService(db, AssetService(Path(settings.storage_root)))

    # Ensure investigation exists
    await svc.get_or_404(investigation_id)

    # Load evidence IDs for context (from the investigation's evidence records)
    inv_response = await svc.get_response(investigation_id)
    evidence_ids = [str(ev.id) for ev in inv_response.evidence]

    # Call intelligence adapter
    intel = get_intelligence_adapter(settings)
    raw = await intel.ask_assistant(
        investigation_id=str(investigation_id),
        question=body.question,
        evidence_ids=evidence_ids,
    )

    # Map response
    mapped = map_assistant_response(raw)

    # Persist the assistant message
    msg = await svc.save_assistant_message(
        investigation_id=investigation_id,
        role="assistant",
        content=mapped["answer"],
        evidence_ids=mapped.get("evidence_ids", []),
        uncertainty_notes=mapped.get("uncertainty_notes"),
    )

    return await svc.get_assistant_message_out(msg)
