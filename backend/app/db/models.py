"""
SQLAlchemy 2.x ORM models for UrbanChange AI.

All tables use:
  - UUID primary keys (server-generated)
  - raw_payload JSONB on every module-result table (for traceability)
  - created_at / updated_at with timezone
  - GeoAlchemy2 geometry columns (SRID 4326, lon/lat)

Relationships are declared but lazy-loaded by default to keep async safe.
No GIS math or area calculations happen here.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from geoalchemy2 import Geometry
from sqlalchemy import (
    ARRAY,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Investigation  (root record)
# ---------------------------------------------------------------------------

class Investigation(Base):
    """
    Root record for every change-detection investigation.
    AOI stored as PostGIS Polygon (SRID 4326).
    bbox stored as a plain float array for fast retrieval without PostGIS math.
    """
    __tablename__ = "investigations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )

    # Area of Interest – PostGIS polygon (lon/lat, SRID 4326)
    aoi: Mapped[object] = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326), nullable=True
    )
    # Bounding box as [west, south, east, north] for quick reads
    bbox: Mapped[list[float] | None] = mapped_column(ARRAY(Float), nullable=True)

    historical_date: Mapped[object] = mapped_column(Date, nullable=False)
    current_date: Mapped[object | None] = mapped_column(Date, nullable=True)

    # Status machine: pending → running → completed | partial | failed
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", index=True
    )
    # Current / last pipeline stage name
    stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Set when status = partial | failed
    failed_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Optional: reason when satellite found no suitable imagery
    satellite_failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now,
        onupdate=_now, server_default=func.now()
    )

    # ── Relationships ──────────────────────────────────────────────────────
    observations: Mapped[list["SatelliteObservation"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan"
    )
    detections: Mapped[list["Detection"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan"
    )
    gis_results: Mapped[list["GISResult"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan"
    )
    fingerprints: Mapped[list["ChangeFingerprint"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan"
    )
    temporal_events: Mapped[list["TemporalEvent"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan"
    )
    evidence: Mapped[list["Evidence"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan"
    )
    assistant_messages: Mapped[list["AssistantMessage"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Satellite Observations
# ---------------------------------------------------------------------------

class SatelliteObservation(Base):
    """
    One retrieved satellite scene linked to an investigation.
    role = before | after | intermediate
    Both image_path and preview_path are relative to STORAGE_ROOT.
    """
    __tablename__ = "satellite_observations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(
        String(16), nullable=False, default="before"
    )  # before | after | intermediate

    scene_id: Mapped[str] = mapped_column(String(256), nullable=False)
    sensor: Mapped[str] = mapped_column(String(64), nullable=False, default="Sentinel-2")
    acquisition_date: Mapped[object] = mapped_column(Date, nullable=False)
    cloud_cover: Mapped[float | None] = mapped_column(Float, nullable=True)
    crs: Mapped[str | None] = mapped_column(String(32), nullable=True)
    resolution: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Filesystem paths (relative to STORAGE_ROOT)
    image_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    preview_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Scene bounding box [west, south, east, north]
    bounds: Mapped[list[float] | None] = mapped_column(ARRAY(Float), nullable=True)

    # Raw module response for this scene (traceability)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, server_default=func.now()
    )

    investigation: Mapped["Investigation"] = relationship(back_populates="observations")


# ---------------------------------------------------------------------------
# Detections  (ML output)
# ---------------------------------------------------------------------------

class Detection(Base):
    """ML change-detection result for a before/after pair."""
    __tablename__ = "detections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    change_detected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    changed_area_pixels: Mapped[int] = mapped_column(Integer, nullable=False)
    change_mask_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    # GeoJSON feature list stored as JSONB
    change_regions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    model_version: Mapped[str] = mapped_column(String(128), nullable=False)
    preprocessing_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)

    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, server_default=func.now()
    )

    investigation: Mapped["Investigation"] = relationship(back_populates="detections")
    classifications: Mapped[list["Classification"]] = relationship(
        back_populates="detection", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Classifications  (ML change category)
# ---------------------------------------------------------------------------

class Classification(Base):
    """Change classification label + confidence for a detection."""
    __tablename__ = "classifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    detection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("detections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    label: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    detection: Mapped["Detection"] = relationship(back_populates="classifications")


# ---------------------------------------------------------------------------
# GIS Results
# ---------------------------------------------------------------------------

class GISResult(Base):
    """GIS spatial analysis result for an investigation."""
    __tablename__ = "gis_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    changed_area_m2: Mapped[float] = mapped_column(Float, nullable=False)
    # dict: layer_name → overlap_pct
    overlap_percentages: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # dict: feature_type → nearest distance metres
    distances: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # GeoJSON FeatureCollection
    geojson: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # dict: layer_name → version string
    layer_versions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, server_default=func.now()
    )

    investigation: Mapped["Investigation"] = relationship(back_populates="gis_results")
    sensitive_intersections: Mapped[list["SensitiveIntersection"]] = relationship(
        back_populates="gis_result", cascade="all, delete-orphan"
    )
    nearby_features: Mapped[list["NearbyFeature"]] = relationship(
        back_populates="gis_result", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Sensitive Intersections
# ---------------------------------------------------------------------------

class SensitiveIntersection(Base):
    """One geographic layer that overlaps the change region."""
    __tablename__ = "sensitive_intersections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gis_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gis_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    layer_name: Mapped[str] = mapped_column(String(128), nullable=False)
    layer_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    overlap_pct: Mapped[float] = mapped_column(Float, nullable=False)
    # PostGIS geometry of the intersection area
    geometry: Mapped[object | None] = mapped_column(
        Geometry(geometry_type="GEOMETRY", srid=4326), nullable=True
    )

    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    gis_result: Mapped["GISResult"] = relationship(
        back_populates="sensitive_intersections"
    )


# ---------------------------------------------------------------------------
# Nearby Features
# ---------------------------------------------------------------------------

class NearbyFeature(Base):
    """A notable geographic feature near (but not necessarily overlapping) the change."""
    __tablename__ = "nearby_features"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gis_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gis_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    feature_type: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    distance_m: Mapped[float] = mapped_column(Float, nullable=False)

    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    gis_result: Mapped["GISResult"] = relationship(back_populates="nearby_features")


# ---------------------------------------------------------------------------
# Change Fingerprints  (Intelligence output)
# ---------------------------------------------------------------------------

class ChangeFingerprint(Base):
    """Structured change fingerprint generated by the Intelligence module."""
    __tablename__ = "change_fingerprints"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    fingerprint_id: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    change_type: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    changed_area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    temporal_behavior: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # JSONB: { "percentage": float, "layers": [str] }
    sensitive_overlap: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    first_observed: Mapped[object | None] = mapped_column(Date, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(128), nullable=True)

    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, server_default=func.now()
    )

    investigation: Mapped["Investigation"] = relationship(back_populates="fingerprints")


# ---------------------------------------------------------------------------
# Temporal Events
# ---------------------------------------------------------------------------

class TemporalEvent(Base):
    """One step in the temporal reconstruction timeline."""
    __tablename__ = "temporal_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    observation_date: Mapped[object] = mapped_column(Date, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    area_delta_m2: Mapped[float | None] = mapped_column(Float, nullable=True)

    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    investigation: Mapped["Investigation"] = relationship(back_populates="temporal_events")


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------

class Evidence(Base):
    """One item in the evidence graph — traceable to a source record."""
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    evidence_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(256), nullable=False)
    # Named extra_metadata because 'metadata' is reserved by SQLAlchemy's DeclarativeBase
    extra_metadata: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    investigation: Mapped["Investigation"] = relationship(back_populates="evidence")


# ---------------------------------------------------------------------------
# Assistant Messages
# ---------------------------------------------------------------------------

class AssistantMessage(Base):
    """Chat message for the AI Investigation Assistant."""
    __tablename__ = "assistant_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Stored as JSONB array of evidence ID strings
    evidence_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    uncertainty_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, server_default=func.now()
    )

    investigation: Mapped["Investigation"] = relationship(
        back_populates="assistant_messages"
    )
