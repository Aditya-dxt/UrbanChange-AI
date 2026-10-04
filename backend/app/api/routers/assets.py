"""
Assets router.

Serves files from STORAGE_ROOT at GET /api/assets/{path}.

Security:
  - Path traversal prevention (resolved path must be inside STORAGE_ROOT)
  - Content-type whitelist (only image/png, image/jpeg, image/tiff,
    application/json, application/geo+json, application/octet-stream)
  - Returns 400 PATH_TRAVERSAL, 404 ASSET_NOT_FOUND, or 415 UNSUPPORTED_MEDIA_TYPE
    on error — never exposes raw filesystem details

No image processing is done here.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.api.deps import SettingsDep
from app.services.asset_service import AssetService

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get(
    "/{file_path:path}",
    summary="Serve a file from STORAGE_ROOT",
    response_class=FileResponse,
)
async def serve_asset(
    file_path: str,
    settings: SettingsDep,
) -> FileResponse:
    """
    Serve a file from STORAGE_ROOT.

    - `file_path` is the path relative to STORAGE_ROOT
      (as it appears after /api/assets/ in the URL).
    - Path traversal attempts return 400.
    - Missing files return 404.
    - Non-whitelisted content types return 415.
    """
    log.debug("assets.serve path=%s", file_path)
    svc = AssetService(Path(settings.storage_root))
    return svc.serve(file_path)
