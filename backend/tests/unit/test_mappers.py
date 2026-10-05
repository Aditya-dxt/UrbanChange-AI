"""
Unit tests for all four mappers.

These tests are pure Python — no DB, no HTTP, no adapters.
They verify:
  - Happy-path mapping
  - Alias resolution (cloud_score, file_path, mask_path)
  - Tolerant reader (extra fields ignored, never raise)
  - Missing required field → MapperError with correct module/stage/field
  - Edge cases (empty lists, null fields, invalid formats)
"""
from __future__ import annotations

import pytest
from datetime import date

from app.errors import MapperError
from app.adapters.mappers.satellite_mapper import map_satellite_fetch, map_satellite_search
from app.adapters.mappers.ml_mapper import map_ml_detect_change, map_ml_request
from app.adapters.mappers.gis_mapper import map_gis_analyze_change
from app.adapters.mappers.intelligence_mapper import (
    map_intelligence_response,
    map_assistant_response,
)


# ══════════════════════════════════════════════════════════════════════════════
# Satellite mapper
# ══════════════════════════════════════════════════════════════════════════════

VALID_SCENE = {
    "scene_id": "S2A_20250414",
    "acquisition_date": "2025-04-14",
    "sensor": "Sentinel-2",
    "cloud_cover": 12.5,
    "crs": "EPSG:4326",
    "resolution": 10.0,
    "image_path": "/data/storage/before.tif",
    "preview_path": "/data/storage/before.png",
    "bounds": [77.1, 28.5, 77.3, 28.7],
}

VALID_FETCH = {
    "success": True,
    "before": VALID_SCENE,
    "after": {**VALID_SCENE, "scene_id": "S2B_20260118", "acquisition_date": "2026-01-18"},
    "intermediate": [],
}


class TestSatelliteMapper:

    def test_fetch_happy_path(self):
        result, raw = map_satellite_fetch(VALID_FETCH)
        assert result.success is True
        assert result.before is not None
        assert result.before.scene_id == "S2A_20250414"
        assert result.before.acquisition_date == date(2025, 4, 14)
        assert result.after is not None
        assert result.after.scene_id == "S2B_20260118"
        assert result.intermediate == []
        assert raw is VALID_FETCH

    def test_fetch_cloud_score_alias(self):
        scene = {**VALID_SCENE}
        del scene["cloud_cover"]
        scene["cloud_score"] = 25.0
        fetch = {**VALID_FETCH, "before": scene}
        result, _ = map_satellite_fetch(fetch)
        assert result.before.cloud_cover == 25.0

    def test_fetch_file_path_alias(self):
        scene = {**VALID_SCENE}
        del scene["image_path"]
        scene["file_path"] = "/data/storage/before_alias.tif"
        fetch = {**VALID_FETCH, "before": scene}
        result, _ = map_satellite_fetch(fetch)
        assert result.before.image_path == "/data/storage/before_alias.tif"

    def test_fetch_no_image_success_false(self):
        raw = {"success": False, "reason": "cloud_cover_too_high"}
        result, _ = map_satellite_fetch(raw)
        assert result.success is False
        assert result.failure_reason == "cloud_cover_too_high"
        assert result.before is None
        assert result.after is None

    def test_fetch_no_image_implicit_success_true_missing_before(self):
        """success field absent but before is missing → MapperError"""
        with pytest.raises(MapperError) as exc:
            map_satellite_fetch({"after": VALID_SCENE})
        assert exc.value.missing_field == "before"
        assert exc.value.module == "satellite"

    def test_fetch_missing_scene_id(self):
        scene = {k: v for k, v in VALID_SCENE.items() if k != "scene_id"}
        fetch = {**VALID_FETCH, "before": scene}
        with pytest.raises(MapperError) as exc:
            map_satellite_fetch(fetch)
        assert exc.value.missing_field == "scene_id"

    def test_fetch_missing_acquisition_date(self):
        scene = {k: v for k, v in VALID_SCENE.items() if k != "acquisition_date"}
        fetch = {**VALID_FETCH, "before": scene}
        with pytest.raises(MapperError) as exc:
            map_satellite_fetch(fetch)
        assert exc.value.missing_field == "acquisition_date"

    def test_fetch_invalid_acquisition_date_format(self):
        scene = {**VALID_SCENE, "acquisition_date": "not-a-date"}
        fetch = {**VALID_FETCH, "before": scene}
        with pytest.raises(MapperError):
            map_satellite_fetch(fetch)

    def test_fetch_extra_fields_ignored(self):
        fetch = {**VALID_FETCH, "totally_unknown_field": "should-be-ignored"}
        result, _ = map_satellite_fetch(fetch)
        assert result.success is True  # No crash

    def test_fetch_with_intermediate(self):
        mid = {**VALID_SCENE, "scene_id": "S2A_mid", "acquisition_date": "2025-08-01"}
        fetch = {**VALID_FETCH, "intermediate": [mid]}
        result, _ = map_satellite_fetch(fetch)
        assert len(result.intermediate) == 1
        assert result.intermediate[0].role == "intermediate"

    def test_fetch_bounds_wrong_length_ignored(self):
        scene = {**VALID_SCENE, "bounds": [1.0, 2.0]}  # invalid — only 2 elements
        fetch = {**VALID_FETCH, "before": scene}
        result, _ = map_satellite_fetch(fetch)
        assert result.before.bounds is None  # ignored gracefully

    def test_search_returns_scenes_list(self):
        raw = {"scenes": [VALID_SCENE], "total": 1}
        scenes, payload = map_satellite_search(raw)
        assert len(scenes) == 1
        assert payload is raw

    def test_search_empty_scenes(self):
        raw = {"scenes": [], "total": 0}
        scenes, _ = map_satellite_search(raw)
        assert scenes == []


# ══════════════════════════════════════════════════════════════════════════════
# ML mapper
# ══════════════════════════════════════════════════════════════════════════════

VALID_ML_POLYGON = {
    "type": "Polygon",
    "coordinates": [[[77.15, 28.55], [77.18, 28.55], [77.18, 28.58], [77.15, 28.58], [77.15, 28.55]]],
}

VALID_ML = {
    "change_detected": True,
    "confidence": 0.94,
    "changed_area_pixels": 15420,
    "change_mask_path": "/data/storage/mask.tif",
    "mask_preview_path": "/data/storage/mask_preview.png",
    "mask_bounds": [77.15, 28.55, 77.18, 28.58],
    "change_regions": [{"type": "Feature", "geometry": VALID_ML_POLYGON}],
    "classification": {"label": "construction", "confidence": 0.87},
    "model_version": "urbanchange-v1.2.0",
    "preprocessing_version": "preproc-v0.3",
    "threshold": 0.5,
}


class TestMLMapper:

    def test_happy_path(self):
        det, raw = map_ml_detect_change(VALID_ML)
        assert det.change_detected is True
        assert det.confidence == pytest.approx(0.94)
        assert det.changed_area_pixels == 15420
        assert det.change_mask_path == "/data/storage/mask.tif"
        assert det.mask_preview_path == "/data/storage/mask_preview.png"
        assert det.mask_bounds == [77.15, 28.55, 77.18, 28.58]
        assert len(det.change_regions) == 1
        assert det.classification is not None
        assert det.classification.label == "construction"
        assert det.model_version == "urbanchange-v1.2.0"
        assert raw is VALID_ML

    def test_mask_path_alias(self):
        ml = {**VALID_ML}
        del ml["change_mask_path"]
        ml["mask_path"] = "/data/storage/alias_mask.tif"
        det, _ = map_ml_detect_change(ml)
        assert det.change_mask_path == "/data/storage/alias_mask.tif"

    def test_mask_preview_and_bounds_aliases(self):
        ml = {**VALID_ML}
        del ml["mask_preview_path"]
        del ml["mask_bounds"]
        ml["preview_path"] = "/data/storage/alias_preview.png"
        ml["bounds"] = [77.10, 28.50, 77.30, 28.70]
        det, _ = map_ml_detect_change(ml)
        assert det.mask_preview_path == "/data/storage/alias_preview.png"
        assert det.mask_bounds == [77.10, 28.50, 77.30, 28.70]

    def test_mask_preview_absent_defaults_to_none(self):
        ml = {**VALID_ML}
        del ml["mask_preview_path"]
        del ml["mask_bounds"]
        det, _ = map_ml_detect_change(ml)
        assert det.mask_preview_path is None
        assert det.mask_bounds is None

    def test_mask_bounds_invalid_ignored(self):
        # 3 elements instead of 4
        ml = {**VALID_ML, "mask_bounds": [77.15, 28.55, 77.18]}
        det, _ = map_ml_detect_change(ml)
        assert det.mask_bounds is None

        # Coordinates out of range
        ml = {**VALID_ML, "mask_bounds": [200.0, 28.55, 77.18, 28.58]}
        det, _ = map_ml_detect_change(ml)
        assert det.mask_bounds is None

    def test_map_ml_request_canonical(self):
        req = {
            "before": {"image_path": "before.tif", "acquisition_date": "2025-04-14"},
            "after": {"image_path": "after.tif", "acquisition_date": "2026-01-18"},
        }
        mapped = map_ml_request(req)
        assert mapped["before"]["image_path"] == "before.tif"
        assert mapped["before"]["acquisition_date"] == "2025-04-14"
        assert mapped["after"]["image_path"] == "after.tif"
        assert mapped["after"]["acquisition_date"] == "2026-01-18"

    def test_map_ml_request_aliases(self):
        req = {
            "before": {"path": "before.tif", "date": "2025-04-14"},
            "after": {"path": "after.tif", "date": "2026-01-18"},
        }
        mapped = map_ml_request(req)
        assert mapped["before"]["image_path"] == "before.tif"
        assert mapped["before"]["acquisition_date"] == "2025-04-14"
        assert "path" not in mapped["before"]
        assert "date" not in mapped["before"]
        assert mapped["after"]["image_path"] == "after.tif"
        assert mapped["after"]["acquisition_date"] == "2026-01-18"

    def test_change_regions_missing_geometry_raises(self):
        ml = {**VALID_ML, "change_regions": [{"area_pixels": 100}]}
        with pytest.raises(MapperError) as exc:
            map_ml_detect_change(ml)
        assert exc.value.module == "ml"
        assert "change_regions[].geometry" in exc.value.missing_field

    def test_change_regions_geometry_not_polygon_raises(self):
        ml = {
            **VALID_ML,
            "change_regions": [
                {"geometry": {"type": "Point", "coordinates": [77.15, 28.55]}}
            ],
        }
        with pytest.raises(MapperError) as exc:
            map_ml_detect_change(ml)
        assert exc.value.module == "ml"
        assert "change_regions[].geometry" in exc.value.missing_field

    def test_change_regions_geometry_empty_coordinates_raises(self):
        ml = {
            **VALID_ML,
            "change_regions": [
                {"geometry": {"type": "Polygon", "coordinates": []}}
            ],
        }
        with pytest.raises(MapperError) as exc:
            map_ml_detect_change(ml)
        assert exc.value.module == "ml"
        assert "change_regions[].geometry" in exc.value.missing_field

    def test_change_regions_geometry_ring_too_few_points_raises(self):
        ml = {
            **VALID_ML,
            "change_regions": [
                {
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[77.15, 28.55], [77.18, 28.55], [77.15, 28.55]]],
                    }
                }
            ],
        }
        with pytest.raises(MapperError) as exc:
            map_ml_detect_change(ml)
        assert exc.value.module == "ml"
        assert "change_regions[].geometry" in exc.value.missing_field

    def test_change_regions_geometry_longitude_out_of_range_raises(self):
        ml = {
            **VALID_ML,
            "change_regions": [
                {
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[200.0, 28.55], [77.18, 28.55], [77.18, 28.58], [200.0, 28.55]]],
                    }
                }
            ],
        }
        with pytest.raises(MapperError) as exc:
            map_ml_detect_change(ml)
        assert exc.value.module == "ml"
        assert "change_regions[].geometry" in exc.value.missing_field

    def test_change_regions_geometry_latitude_out_of_range_raises(self):
        ml = {
            **VALID_ML,
            "change_regions": [
                {
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[77.15, 95.0], [77.18, 95.0], [77.18, 28.58], [77.15, 95.0]]],
                    }
                }
            ],
        }
        with pytest.raises(MapperError) as exc:
            map_ml_detect_change(ml)
        assert exc.value.module == "ml"
        assert "change_regions[].geometry" in exc.value.missing_field

    def test_no_change_detected(self):
        ml = {**VALID_ML, "change_detected": False, "confidence": 0.12}
        det, _ = map_ml_detect_change(ml)
        assert det.change_detected is False

    def test_missing_change_detected(self):
        ml = {k: v for k, v in VALID_ML.items() if k != "change_detected"}
        with pytest.raises(MapperError) as exc:
            map_ml_detect_change(ml)
        assert exc.value.missing_field == "change_detected"
        assert exc.value.module == "ml"

    def test_missing_confidence(self):
        ml = {k: v for k, v in VALID_ML.items() if k != "confidence"}
        with pytest.raises(MapperError) as exc:
            map_ml_detect_change(ml)
        assert exc.value.missing_field == "confidence"

    def test_missing_changed_area_pixels(self):
        ml = {k: v for k, v in VALID_ML.items() if k != "changed_area_pixels"}
        with pytest.raises(MapperError) as exc:
            map_ml_detect_change(ml)
        assert exc.value.missing_field == "changed_area_pixels"

    def test_missing_model_version(self):
        ml = {k: v for k, v in VALID_ML.items() if k != "model_version"}
        with pytest.raises(MapperError) as exc:
            map_ml_detect_change(ml)
        assert exc.value.missing_field == "model_version"

    def test_no_classification(self):
        ml = {k: v for k, v in VALID_ML.items() if k != "classification"}
        det, _ = map_ml_detect_change(ml)
        assert det.classification is None

    def test_classification_missing_label_skipped(self):
        ml = {**VALID_ML, "classification": {"confidence": 0.9}}
        det, _ = map_ml_detect_change(ml)
        assert det.classification is None

    def test_invalid_change_regions_type(self):
        ml = {**VALID_ML, "change_regions": "not-a-list"}
        det, _ = map_ml_detect_change(ml)
        assert det.change_regions == []

    def test_extra_fields_ignored(self):
        ml = {**VALID_ML, "future_field_from_person1": "value"}
        det, _ = map_ml_detect_change(ml)
        assert det.model_version == "urbanchange-v1.2.0"


# ══════════════════════════════════════════════════════════════════════════════
# GIS mapper
# ══════════════════════════════════════════════════════════════════════════════

VALID_GIS = {
    "changed_area_m2": 38420.5,
    "sensitive_intersections": [
        {"layer_name": "protected_forest", "layer_id": "LYR-001", "overlap_pct": 64.2}
    ],
    "overlap_percentages": {"protected_forest": 64.2},
    "nearby_features": [
        {"feature_type": "road", "name": "NH-48", "distance_m": 120.5}
    ],
    "geojson": {"type": "FeatureCollection", "features": []},
    "layer_versions": {"protected_forest": "2026-01"},
    "distances": {"nearest_road": 120.5},
}


class TestGISMapper:

    def test_happy_path(self):
        result, raw = map_gis_analyze_change(VALID_GIS)
        assert result.changed_area_m2 == pytest.approx(38420.5)
        assert len(result.sensitive_intersections) == 1
        assert result.sensitive_intersections[0].layer_name == "protected_forest"
        assert result.sensitive_intersections[0].overlap_pct == pytest.approx(64.2)
        assert len(result.nearby_features) == 1
        assert result.nearby_features[0].feature_type == "road"
        assert raw is VALID_GIS

    def test_missing_changed_area_m2(self):
        gis = {k: v for k, v in VALID_GIS.items() if k != "changed_area_m2"}
        with pytest.raises(MapperError) as exc:
            map_gis_analyze_change(gis)
        assert exc.value.missing_field == "changed_area_m2"
        assert exc.value.module == "gis"

    def test_empty_intersections(self):
        gis = {**VALID_GIS, "sensitive_intersections": []}
        result, _ = map_gis_analyze_change(gis)
        assert result.sensitive_intersections == []

    def test_malformed_intersection_skipped(self):
        bad = {"layer_name": "protected_forest"}  # missing overlap_pct
        gis = {**VALID_GIS, "sensitive_intersections": [bad]}
        result, _ = map_gis_analyze_change(gis)
        assert result.sensitive_intersections == []  # skipped, not crashed

    def test_malformed_nearby_skipped(self):
        bad = {"feature_type": "road"}  # missing distance_m
        gis = {**VALID_GIS, "nearby_features": [bad]}
        result, _ = map_gis_analyze_change(gis)
        assert result.nearby_features == []

    def test_invalid_overlap_percentages_type(self):
        gis = {**VALID_GIS, "overlap_percentages": "not-a-dict"}
        result, _ = map_gis_analyze_change(gis)
        assert result.overlap_percentages == {}

    def test_extra_fields_ignored(self):
        gis = {**VALID_GIS, "future_gis_field": "value"}
        result, _ = map_gis_analyze_change(gis)
        assert result.changed_area_m2 == pytest.approx(38420.5)

    def test_zero_area(self):
        gis = {**VALID_GIS, "changed_area_m2": 0.0}
        result, _ = map_gis_analyze_change(gis)
        assert result.changed_area_m2 == 0.0


# ══════════════════════════════════════════════════════════════════════════════
# Intelligence mapper
# ══════════════════════════════════════════════════════════════════════════════

VALID_INTEL = {
    "fingerprint": {
        "fingerprint_id": "UC-TEST-001",
        "change_type": "construction",
        "changed_area_m2": 38420.5,
        "confidence": 0.91,
        "temporal_behavior": "rapid_growth",
        "sensitive_overlap": {"percentage": 64.2, "layers": ["protected_forest"]},
        "first_observed": "2025-06-01",
        "model_version": "intel-v0.1",
    },
    "temporal_reconstruction": {
        "events": [
            {
                "observation_date": "2025-06-01",
                "event_type": "initial_clearing",
                "description": "Initial forest clearing detected",
                "confidence": 0.88,
                "area_delta_m2": 15000.0,
            }
        ],
        "first_persistent_interval": "2025-06-01/2026-01-18",
        "summary": "Rapid construction activity",
    },
    "evidence": [
        {
            "evidence_type": "satellite_observation",
            "source_reference": "S2A_20250414",
            "metadata": {"cloud_cover": 12.5},
        }
    ],
    "explanation": {
        "text": "Construction detected. Human verification required.",
        "evidence_ids": ["ev-001"],
        "status": "requires_human_verification",
    },
}


class TestIntelligenceMapper:

    def test_happy_path(self):
        result, raw = map_intelligence_response(VALID_INTEL)
        assert result.fingerprint is not None
        assert result.fingerprint.fingerprint_id == "UC-TEST-001"
        assert result.fingerprint.change_type == "construction"
        assert result.fingerprint.sensitive_overlap is not None
        assert result.fingerprint.sensitive_overlap.percentage == pytest.approx(64.2)
        assert result.fingerprint.first_observed == date(2025, 6, 1)
        assert result.temporal_reconstruction is not None
        assert len(result.temporal_reconstruction.events) == 1
        assert result.temporal_reconstruction.events[0].event_type == "initial_clearing"
        assert len(result.evidence) == 1
        assert result.explanation is not None
        assert "Construction" in result.explanation.text
        assert raw is VALID_INTEL

    def test_missing_fingerprint_id(self):
        fp = {k: v for k, v in VALID_INTEL["fingerprint"].items() if k != "fingerprint_id"}
        intel = {**VALID_INTEL, "fingerprint": fp}
        with pytest.raises(MapperError) as exc:
            map_intelligence_response(intel)
        assert exc.value.missing_field == "fingerprint_id"
        assert exc.value.module == "intelligence"

    def test_missing_change_type(self):
        fp = {k: v for k, v in VALID_INTEL["fingerprint"].items() if k != "change_type"}
        intel = {**VALID_INTEL, "fingerprint": fp}
        with pytest.raises(MapperError) as exc:
            map_intelligence_response(intel)
        assert exc.value.missing_field == "change_type"

    def test_no_fingerprint(self):
        intel = {k: v for k, v in VALID_INTEL.items() if k != "fingerprint"}
        result, _ = map_intelligence_response(intel)
        assert result.fingerprint is None  # optional

    def test_malformed_temporal_event_skipped(self):
        bad_event = {"event_type": "clearing"}  # missing observation_date
        intel = {
            **VALID_INTEL,
            "temporal_reconstruction": {"events": [bad_event]},
        }
        result, _ = map_intelligence_response(intel)
        assert result.temporal_reconstruction.events == []

    def test_malformed_evidence_item_skipped(self):
        bad_ev = {"evidence_type": "satellite_observation"}  # missing source_reference
        intel = {**VALID_INTEL, "evidence": [bad_ev]}
        result, _ = map_intelligence_response(intel)
        assert result.evidence == []

    def test_explanation_missing_text_skipped(self):
        intel = {**VALID_INTEL, "explanation": {"evidence_ids": ["x"]}}
        result, _ = map_intelligence_response(intel)
        assert result.explanation is None

    def test_extra_fields_ignored(self):
        intel = {**VALID_INTEL, "future_intel_field": "value"}
        result, _ = map_intelligence_response(intel)
        assert result.fingerprint.fingerprint_id == "UC-TEST-001"

    def test_invalid_first_observed_format_ignored(self):
        fp = {**VALID_INTEL["fingerprint"], "first_observed": "not-a-date"}
        intel = {**VALID_INTEL, "fingerprint": fp}
        result, _ = map_intelligence_response(intel)
        assert result.fingerprint.first_observed is None


class TestAssistantMapper:

    def test_happy_path(self):
        raw = {"answer": "Significant deforestation detected.", "evidence_ids": ["ev-1"], "uncertainty_notes": "Low confidence"}
        mapped = map_assistant_response(raw)
        assert mapped["answer"] == "Significant deforestation detected."
        assert mapped["evidence_ids"] == ["ev-1"]
        assert mapped["uncertainty_notes"] == "Low confidence"
        assert mapped["status"] == "requires_human_verification"

    def test_missing_answer(self):
        with pytest.raises(MapperError) as exc:
            map_assistant_response({"evidence_ids": []})
        assert exc.value.missing_field == "answer"
        assert exc.value.module == "intelligence"

    def test_default_evidence_ids(self):
        raw = {"answer": "Some answer"}
        mapped = map_assistant_response(raw)
        assert mapped["evidence_ids"] == []

    def test_custom_status_passed_through(self):
        raw = {"answer": "Answer", "status": "verified"}
        mapped = map_assistant_response(raw)
        assert mapped["status"] == "verified"
