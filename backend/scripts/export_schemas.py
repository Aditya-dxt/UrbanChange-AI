#!/usr/bin/env python
"""
Export all external + api Pydantic schemas to JSON Schema files in /shared/schemas.

Run from backend/:
    python scripts/export_schemas.py

Output:
    shared/schemas/external/satellite_search_response.json
    shared/schemas/external/satellite_fetch_response.json
    shared/schemas/external/ml_detect_change_response.json
    shared/schemas/external/gis_analyze_change_response.json
    shared/schemas/external/intelligence_response.json
    shared/schemas/external/assistant_response.json
    shared/schemas/api/investigation_response.json
    shared/schemas/api/error_response.json
    shared/schemas/api/assistant_message_out.json
    (etc.)

These files are the team's source of truth during parallel development.
Teammates in /ml, /satellite, /gis, /intelligence can validate their
outputs against these JSON Schemas without importing Python code.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure the backend/ root is on sys.path when running as a script.
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))
REPO_ROOT = BACKEND_ROOT.parent
SHARED_DIR = REPO_ROOT / "shared" / "schemas"


def export(model, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    schema = model.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    out_path.write_text(json.dumps(schema, indent=2))
    print(f"  Exported: {out_path.relative_to(REPO_ROOT)}")


def main() -> None:
    print("Exporting schemas to /shared/schemas …\n")

    # ── External schemas ──────────────────────────────────────────────────
    from app.schemas.external.satellite import (
        SatelliteSearchResponse,
        SatelliteFetchResponse,
    )
    from app.schemas.external.ml import MLDetectChangeResponse
    from app.schemas.external.gis import GISAnalyzeChangeResponse
    from app.schemas.external.intelligence import (
        IntelligenceResponse,
        AssistantResponse,
    )

    ext = SHARED_DIR / "external"
    export(SatelliteSearchResponse,    ext / "satellite_search_response.json")
    export(SatelliteFetchResponse,     ext / "satellite_fetch_response.json")
    export(MLDetectChangeResponse,     ext / "ml_detect_change_response.json")
    export(GISAnalyzeChangeResponse,   ext / "gis_analyze_change_response.json")
    export(IntelligenceResponse,       ext / "intelligence_response.json")
    export(AssistantResponse,          ext / "assistant_response.json")

    # ── API (frontend-facing) schemas ─────────────────────────────────────
    from app.schemas.api import (
        InvestigationResponse,
        InvestigationCreateResponse,
        TimelineOut,
        AssistantMessageOut,
        ErrorResponse,
    )

    api = SHARED_DIR / "api"
    export(InvestigationResponse,       api / "investigation_response.json")
    export(InvestigationCreateResponse, api / "investigation_create_response.json")
    export(TimelineOut,                 api / "timeline_out.json")
    export(AssistantMessageOut,         api / "assistant_message_out.json")
    export(ErrorResponse,               api / "error_response.json")

    print(f"\nDone. JSON Schema files written to {SHARED_DIR.relative_to(REPO_ROOT)}/")


if __name__ == "__main__":
    main()
