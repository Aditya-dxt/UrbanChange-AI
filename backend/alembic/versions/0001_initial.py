"""Create PostGIS extension and all initial tables.

Revision ID: 0001
Revises: 
Create Date: 2026-10-04
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
import geoalchemy2
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── PostGIS extension ────────────────────────────────────────────────────
    # Requires SUPERUSER or CREATE privilege on the database.
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # ── investigations ────────────────────────────────────────────────────────
    op.create_table(
        "investigations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "aoi",
            geoalchemy2.types.Geometry(geometry_type="POLYGON", srid=4326),
            nullable=True,
        ),
        sa.Column(
            "bbox",
            postgresql.ARRAY(sa.Float()),
            nullable=True,
            comment="[west, south, east, north] in WGS-84",
        ),
        sa.Column("historical_date", sa.Date(), nullable=False),
        sa.Column("current_date", sa.Date(), nullable=True),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="pending",
            comment="pending|running|completed|partial|failed",
        ),
        sa.Column("stage", sa.String(64), nullable=True),
        sa.Column("failed_stage", sa.String(64), nullable=True),
        sa.Column("satellite_failure_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_investigations_status", "investigations", ["status"])

    # ── satellite_observations ────────────────────────────────────────────────
    op.create_table(
        "satellite_observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "investigation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investigations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(16),
            nullable=False,
            server_default="before",
            comment="before|after|intermediate",
        ),
        sa.Column("scene_id", sa.String(256), nullable=False),
        sa.Column("sensor", sa.String(64), nullable=False, server_default="Sentinel-2"),
        sa.Column("acquisition_date", sa.Date(), nullable=False),
        sa.Column("cloud_cover", sa.Float(), nullable=True),
        sa.Column("crs", sa.String(32), nullable=True),
        sa.Column("resolution", sa.Float(), nullable=True),
        sa.Column("image_path", sa.Text(), nullable=True),
        sa.Column("preview_path", sa.Text(), nullable=True),
        sa.Column(
            "bounds",
            postgresql.ARRAY(sa.Float()),
            nullable=True,
            comment="[west, south, east, north]",
        ),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_satellite_observations_investigation_id",
        "satellite_observations",
        ["investigation_id"],
    )

    # ── detections ────────────────────────────────────────────────────────────
    op.create_table(
        "detections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "investigation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investigations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("change_detected", sa.Boolean(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("changed_area_pixels", sa.Integer(), nullable=False),
        sa.Column("change_mask_path", sa.Text(), nullable=True),
        sa.Column("mask_preview_path", sa.Text(), nullable=True),
        sa.Column("mask_bounds", postgresql.JSONB(), nullable=True),
        sa.Column("change_regions", postgresql.JSONB(), nullable=True),
        sa.Column("model_version", sa.String(128), nullable=False),
        sa.Column("preprocessing_version", sa.String(64), nullable=True),
        sa.Column("threshold", sa.Float(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_detections_investigation_id", "detections", ["investigation_id"]
    )

    # ── classifications ───────────────────────────────────────────────────────
    op.create_table(
        "classifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "detection_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("detections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "investigation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investigations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.String(64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
    )
    op.create_index(
        "ix_classifications_detection_id", "classifications", ["detection_id"]
    )
    op.create_index(
        "ix_classifications_investigation_id",
        "classifications",
        ["investigation_id"],
    )

    # ── gis_results ───────────────────────────────────────────────────────────
    op.create_table(
        "gis_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "investigation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investigations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("changed_area_m2", sa.Float(), nullable=False),
        sa.Column("overlap_percentages", postgresql.JSONB(), nullable=True),
        sa.Column("distances", postgresql.JSONB(), nullable=True),
        sa.Column("geojson", postgresql.JSONB(), nullable=True),
        sa.Column("layer_versions", postgresql.JSONB(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_gis_results_investigation_id", "gis_results", ["investigation_id"]
    )

    # ── sensitive_intersections ───────────────────────────────────────────────
    op.create_table(
        "sensitive_intersections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "investigation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investigations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "gis_result_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("gis_results.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("layer_name", sa.String(128), nullable=False),
        sa.Column("layer_id", sa.String(128), nullable=True),
        sa.Column("overlap_pct", sa.Float(), nullable=False),
        sa.Column(
            "geometry",
            geoalchemy2.types.Geometry(geometry_type="GEOMETRY", srid=4326),
            nullable=True,
        ),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
    )
    op.create_index(
        "ix_sensitive_intersections_investigation_id",
        "sensitive_intersections",
        ["investigation_id"],
    )
    op.create_index(
        "ix_sensitive_intersections_gis_result_id",
        "sensitive_intersections",
        ["gis_result_id"],
    )

    # ── nearby_features ───────────────────────────────────────────────────────
    op.create_table(
        "nearby_features",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "investigation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investigations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "gis_result_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("gis_results.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("feature_type", sa.String(64), nullable=False),
        sa.Column("name", sa.String(256), nullable=True),
        sa.Column("distance_m", sa.Float(), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
    )
    op.create_index(
        "ix_nearby_features_investigation_id",
        "nearby_features",
        ["investigation_id"],
    )

    # ── change_fingerprints ───────────────────────────────────────────────────
    op.create_table(
        "change_fingerprints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "investigation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investigations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fingerprint_id", sa.String(64), nullable=False),
        sa.Column("change_type", sa.String(64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("changed_area_m2", sa.Float(), nullable=True),
        sa.Column("temporal_behavior", sa.String(64), nullable=True),
        sa.Column("sensitive_overlap", postgresql.JSONB(), nullable=True),
        sa.Column("first_observed", sa.Date(), nullable=True),
        sa.Column("model_version", sa.String(128), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_change_fingerprints_investigation_id",
        "change_fingerprints",
        ["investigation_id"],
    )
    op.create_index(
        "ix_change_fingerprints_fingerprint_id",
        "change_fingerprints",
        ["fingerprint_id"],
        unique=True,
    )

    # ── temporal_events ───────────────────────────────────────────────────────
    op.create_table(
        "temporal_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "investigation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investigations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("observation_date", sa.Date(), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("area_delta_m2", sa.Float(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
    )
    op.create_index(
        "ix_temporal_events_investigation_id",
        "temporal_events",
        ["investigation_id"],
    )

    # ── evidence ──────────────────────────────────────────────────────────────
    op.create_table(
        "evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "investigation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investigations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("evidence_type", sa.String(64), nullable=False),
        sa.Column("source_reference", sa.String(256), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
    )
    op.create_index(
        "ix_evidence_investigation_id", "evidence", ["investigation_id"]
    )

    # ── assistant_messages ────────────────────────────────────────────────────
    op.create_table(
        "assistant_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "investigation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investigations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(16),
            nullable=False,
            comment="user|assistant",
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "evidence_ids",
            postgresql.JSONB(),
            nullable=True,
            comment="JSON array of evidence ID strings",
        ),
        sa.Column("uncertainty_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_assistant_messages_investigation_id",
        "assistant_messages",
        ["investigation_id"],
    )


def downgrade() -> None:
    # Drop in reverse FK dependency order
    op.drop_table("assistant_messages")
    op.drop_table("evidence")
    op.drop_table("temporal_events")
    op.drop_table("change_fingerprints")
    op.drop_table("nearby_features")
    op.drop_table("sensitive_intersections")
    op.drop_table("gis_results")
    op.drop_table("classifications")
    op.drop_table("detections")
    op.drop_table("satellite_observations")
    op.drop_table("investigations")
    op.execute("DROP EXTENSION IF EXISTS postgis")
