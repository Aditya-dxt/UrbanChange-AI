#!/usr/bin/env python
"""
check_modules.py — Integration readiness checker.

Calls each module that is configured as `http` (or `python` for Intelligence)
with its example contract request, validates the response, and maps it through
the mapper. Prints a PASS/FAIL table per module.

Usage (from backend/ directory):
    python scripts/check_modules.py

Exit codes:
    0 — all checked modules PASS
    1 — at least one module FAIL
    2 — configuration or import error

Set adapter modes in .env or environment:
    SATELLITE_ADAPTER=http  SATELLITE_BASE_URL=http://...
    ML_ADAPTER=http         ML_BASE_URL=http://...
    GIS_ADAPTER=http        GIS_BASE_URL=http://...
    INTELLIGENCE_ADAPTER=http  INTELLIGENCE_BASE_URL=http://...
"""
from __future__ import annotations

import asyncio
import json
import sys
import textwrap
import traceback
from pathlib import Path
from typing import Optional

# -- Ensure backend/ is on sys.path --------------------------------------------
_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.config import get_settings
from app.adapters.factory import (
    get_satellite_adapter,
    get_ml_adapter,
    get_gis_adapter,
    get_intelligence_adapter,
)
from app.adapters.mappers.satellite_mapper import map_satellite_fetch, map_satellite_search
from app.adapters.mappers.ml_mapper import map_ml_detect_change
from app.adapters.mappers.gis_mapper import map_gis_analyze_change
from app.adapters.mappers.intelligence_mapper import map_intelligence_response, map_assistant_response

_CONTRACTS = _BACKEND / "tests" / "contracts"


# -- ANSI colours --------------------------------------------------------------
_GREEN  = "\033[32m"
_RED    = "\033[31m"
_YELLOW = "\033[33m"
_BOLD   = "\033[1m"
_RESET  = "\033[0m"


def _ok(msg: str = "PASS") -> str:
    return f"{_GREEN}{_BOLD}{msg}{_RESET}"


def _fail(msg: str = "FAIL") -> str:
    return f"{_RED}{_BOLD}{msg}{_RESET}"


def _skip(msg: str = "SKIPPED") -> str:
    return f"{_YELLOW}{msg}{_RESET}"


# -- Contract fixture loader ----------------------------------------------------

MODULE_FIXTURES: dict[str, dict[str, str]] = {
    "satellite": {
        "search_request": "search_request.json",
        "search_response": "search_response.json",
        "fetch_request": "fetch_request.json",
        "fetch_response": "fetch_response.json",
    },
    "ml": {
        "request": "request.json",
        "response": "response.json",
    },
    "gis": {
        "request": "request.json",
        "response": "response.json",
    },
    "intelligence": {
        "request": "request.json",
        "response": "response.json",
    },
}


def _verify_all_fixtures() -> None:
    """Verify that every required fixture file exists before running checks."""
    missing = []
    for module, files in MODULE_FIXTURES.items():
        for role, filename in files.items():
            path = _CONTRACTS / module / filename
            if not path.exists():
                missing.append(f"{module}/{filename}")
    if missing:
        raise FileNotFoundError(f"Missing required contract fixture files: {', '.join(missing)}")


def _load_fixture(module: str, filename: str) -> dict:
    path = _CONTRACTS / module / filename
    if not path.exists():
        raise FileNotFoundError(f"Contract fixture not found: {path}")
    with open(path) as f:
        return json.load(f)


# -- Per-module checks ----------------------------------------------------------

async def check_satellite(settings) -> tuple[str, str, Optional[str]]:
    """Returns (module, status, detail)."""
    mode = settings.satellite_adapter
    if mode == "mock":
        return "satellite", "mock", None

    try:
        adapter = get_satellite_adapter(settings)

        # Load example fetch response from contract fixture
        fetch_fixture = _load_fixture("satellite", "fetch_response.json")

        # Call search
        search_req = _load_fixture("satellite", MODULE_FIXTURES["satellite"]["search_request"])
        raw_search = await adapter.search(
            bbox=search_req["bbox"],
            historical_date=search_req["historical_date"],
            current_date=search_req.get("current_date"),
            max_cloud_cover=search_req.get("max_cloud_cover", 30.0),
            max_observations=search_req.get("max_observations", 5),
        )
        _, _ = map_satellite_search(raw_search)

        # Call fetch
        fetch_req = _load_fixture("satellite", MODULE_FIXTURES["satellite"]["fetch_request"])
        raw_fetch = await adapter.fetch(
            scene_id=fetch_req["scene_id"],
            bbox=fetch_req["bbox"],
        )
        result, raw_payload = map_satellite_fetch(raw_fetch)

        return "satellite", "pass", f"success={result.success} before={result.before and result.before.scene_id[:20]}"

    except Exception as exc:  # noqa: BLE001
        return "satellite", "fail", _format_error(exc)


async def check_ml(settings) -> tuple[str, str, Optional[str]]:
    mode = settings.ml_adapter
    if mode == "mock":
        return "ml", "mock", None

    try:
        adapter = get_ml_adapter(settings)
        req = _load_fixture("ml", MODULE_FIXTURES["ml"]["request"])
        before_cfg = req["before"]
        after_cfg = req["after"]
        raw = await adapter.detect_change(
            before_path=before_cfg.get("image_path") or before_cfg.get("path"),
            before_date=before_cfg.get("acquisition_date") or before_cfg.get("date"),
            before_crs=before_cfg.get("crs"),
            before_resolution=before_cfg.get("resolution"),
            after_path=after_cfg.get("image_path") or after_cfg.get("path"),
            after_date=after_cfg.get("acquisition_date") or after_cfg.get("date"),
            after_crs=after_cfg.get("crs"),
            after_resolution=after_cfg.get("resolution"),
            sensor=req.get("sensor", "Sentinel-2"),
            investigation_id=req.get("investigation_id", "check-test"),
        )
        det, _ = map_ml_detect_change(raw)
        return "ml", "pass", f"change_detected={det.change_detected} confidence={det.confidence:.2f} model={det.model_version}"

    except Exception as exc:  # noqa: BLE001
        return "ml", "fail", _format_error(exc)


async def check_gis(settings) -> tuple[str, str, Optional[str]]:
    mode = settings.gis_adapter
    if mode == "mock":
        return "gis", "mock", None

    try:
        adapter = get_gis_adapter(settings)
        req = _load_fixture("gis", MODULE_FIXTURES["gis"]["request"])
        raw = await adapter.analyze_change(
            change_regions=req.get("change_regions", []),
            bbox=req["bbox"],
            context_layer_ids=req.get("context_layer_ids", []),
            investigation_id=req.get("investigation_id", "check-test"),
        )
        result, _ = map_gis_analyze_change(raw)
        return "gis", "pass", f"changed_area_m2={result.changed_area_m2} intersections={len(result.sensitive_intersections)}"

    except Exception as exc:  # noqa: BLE001
        return "gis", "fail", _format_error(exc)


async def check_intelligence(settings) -> tuple[str, str, Optional[str]]:
    mode = settings.intelligence_adapter
    if mode == "mock":
        return "intelligence", "mock", None

    try:
        adapter = get_intelligence_adapter(settings)
        req = _load_fixture("intelligence", MODULE_FIXTURES["intelligence"]["request"])
        raw = await adapter.analyze(req)
        result, _ = map_intelligence_response(raw)
        fp_id = result.fingerprint.fingerprint_id if result.fingerprint else "none"
        return "intelligence", "pass", f"fingerprint_id={fp_id} evidence={len(result.evidence)}"

    except Exception as exc:  # noqa: BLE001
        return "intelligence", "fail", _format_error(exc)


async def check_intelligence_assistant(settings) -> tuple[str, str, Optional[str]]:
    """Sub-check for the assistant endpoint."""
    mode = settings.intelligence_adapter
    if mode == "mock":
        return "intelligence/assistant", "mock", None

    try:
        adapter = get_intelligence_adapter(settings)
        raw = await adapter.ask_assistant(
            investigation_id="check-test",
            question="What changed in this area?",
            evidence_ids=[],
        )
        mapped = map_assistant_response(raw)
        status = mapped.get("status", "?")
        return "intelligence/assistant", "pass", f"answer_len={len(mapped.get('answer',''))} status={status}"

    except Exception as exc:  # noqa: BLE001
        return "intelligence/assistant", "fail", _format_error(exc)


def _format_error(exc: Exception) -> str:
    tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
    last_lines = "".join(tb[-3:]).strip()
    return f"{type(exc).__name__}: {exc}\n{textwrap.indent(last_lines, '    ')}"


# -- Main ----------------------------------------------------------------------

async def run_all() -> int:
    settings = get_settings()

    print()
    print(f"{_BOLD}UrbanChange AI — Module Integration Checker{_RESET}")
    print(f"CONTRACT_VERSION: {settings.contract_version}")
    print()

    # Verify all contract fixture example files are present on disk
    _verify_all_fixtures()

    checks = await asyncio.gather(
        check_satellite(settings),
        check_ml(settings),
        check_gis(settings),
        check_intelligence(settings),
        check_intelligence_assistant(settings),
        return_exceptions=True,
    )

    # -- Print table -----------------------------------------------------------
    width = 24
    print(f"{'MODULE':<{width}}  {'MODE':<10}  {'RESULT':<8}  DETAIL")
    print("-" * 90)

    any_fail = False
    for check in checks:
        if isinstance(check, Exception):
            print(f"{'<internal error>':<{width}}  {'?':<10}  {_fail():<8}  {check}")
            any_fail = True
            continue

        module, status, detail = check
        if status == "pass":
            badge = _ok("PASS")
        elif status == "mock":
            badge = _skip("MOCK")
        else:
            badge = _fail("FAIL")
            any_fail = True

        mode_label = getattr(settings, f"{module.split('/')[0]}_adapter", "?")
        print(f"{module:<{width}}  {mode_label:<10}  {badge:<20}  {detail or ''}")

        if status == "fail" and detail:
            # Print error detail indented
            for line in detail.splitlines()[1:]:
                print(f"  {_RED}{line}{_RESET}")

    print()
    if any_fail:
        print(f"{_fail('Some modules FAILED.')} Fix the issues above before integration day.")
        return 1
    else:
        print(f"{_ok('All checked modules PASS.')} Ready for integration.")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(run_all())
    sys.exit(exit_code)
