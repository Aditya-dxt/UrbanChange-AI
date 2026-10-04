"""
Asset Service.

Responsible for:
  1. Resolving module-returned file paths (absolute or STORAGE_ROOT-relative)
     to safe, validated absolute paths.
  2. Converting filesystem paths → /api/assets/<rel_path> URLs for the frontend.
  3. Serving files from STORAGE_ROOT with:
       - Path traversal prevention (resolved path must start with STORAGE_ROOT)
       - Content-type whitelisting
       - 404 on missing files

The frontend never sees raw filesystem paths — only /api/assets/... URLs.
No image processing happens here.
"""
from __future__ import annotations

import logging
import mimetypes
import os
from pathlib import Path
from typing import Optional

from fastapi.responses import FileResponse

from app.errors import AssetNotFoundError, PathTraversalError, UnsupportedMediaTypeError

log = logging.getLogger(__name__)

# Whitelisted content types that may be served
_ALLOWED_TYPES: frozenset[str] = frozenset({
    "image/png",
    "image/jpeg",
    "image/tiff",
    "image/geo+tiff",
    "application/json",
    "application/geo+json",
    "application/octet-stream",  # fallback for GeoTIFF
})

# Extension → content-type overrides (mimetypes module doesn't know geo+json / geo+tiff)
_EXT_OVERRIDES: dict[str, str] = {
    ".tif":     "image/tiff",
    ".tiff":    "image/tiff",
    ".geojson": "application/geo+json",
    ".json":    "application/json",
    ".png":     "image/png",
    ".jpg":     "image/jpeg",
    ".jpeg":    "image/jpeg",
}


class AssetService:
    """
    Manages all file access from STORAGE_ROOT.

    Usage:
        svc = AssetService(Path(settings.storage_root))
        url  = svc.path_to_url("/data/storage/mock/sentinel2/before.tif")
        resp = svc.serve("mock/sentinel2/before.tif")
    """

    def __init__(self, storage_root: Path) -> None:
        self._root = storage_root.resolve()
        log.info("AssetService initialised storage_root=%s", self._root)

    # ── Path resolution ────────────────────────────────────────────────────────

    def resolve(self, path: str) -> Path:
        """
        Resolve any path (absolute or relative) to a safe absolute path.

        Raises:
            PathTraversalError: if resolved path is outside STORAGE_ROOT.
        """
        p = Path(path)
        # Absolute paths that are already inside the root are fine
        if p.is_absolute():
            resolved = p.resolve()
        else:
            resolved = (self._root / p).resolve()

        # Critical: prevent traversal attacks
        try:
            resolved.relative_to(self._root)
        except ValueError:
            raise PathTraversalError(path)

        return resolved

    def relative_path(self, path: str) -> Optional[str]:
        """
        Convert an absolute or relative path to a path relative to STORAGE_ROOT.
        Returns None if path is None or cannot be resolved safely.
        """
        if not path:
            return None
        try:
            resolved = self.resolve(path)
            return str(resolved.relative_to(self._root)).replace("\\", "/")
        except (PathTraversalError, ValueError, OSError):
            log.warning("AssetService.relative_path: cannot resolve path=%s", path)
            return None

    # ── URL generation ─────────────────────────────────────────────────────────

    def path_to_url(self, path: Optional[str]) -> Optional[str]:
        """
        Convert a filesystem path (absolute or relative to STORAGE_ROOT) to a
        /api/assets/<rel_path> URL for the frontend.

        Returns None if path is None, empty, or outside STORAGE_ROOT.
        """
        if not path:
            return None
        rel = self.relative_path(path)
        if rel is None:
            return None
        return f"/api/assets/{rel}"

    def has_preview(self, preview_path: Optional[str]) -> bool:
        """Return True if a browser-friendly preview path is provided and non-empty."""
        return bool(preview_path)

    # ── File serving ───────────────────────────────────────────────────────────

    def _content_type(self, path: Path) -> str:
        ext = path.suffix.lower()
        if ext in _EXT_OVERRIDES:
            return _EXT_OVERRIDES[ext]
        guessed, _ = mimetypes.guess_type(str(path))
        return guessed or "application/octet-stream"

    def serve(self, relative_path: str) -> FileResponse:
        """
        Validate and serve a file from STORAGE_ROOT.

        Args:
            relative_path: path as it appears in the URL (after /api/assets/)

        Returns:
            FileResponse with appropriate content-type header.

        Raises:
            PathTraversalError:       path resolves outside STORAGE_ROOT
            AssetNotFoundError:       file does not exist
            UnsupportedMediaTypeError: content-type not in whitelist
        """
        # Normalise: remove leading slashes so Path doesn't treat it as absolute
        relative_path = relative_path.lstrip("/")

        resolved = self.resolve(relative_path)

        if not resolved.exists() or not resolved.is_file():
            raise AssetNotFoundError(relative_path)

        content_type = self._content_type(resolved)
        if content_type not in _ALLOWED_TYPES:
            raise UnsupportedMediaTypeError(content_type)

        log.debug("AssetService.serve path=%s content_type=%s", resolved, content_type)
        return FileResponse(path=str(resolved), media_type=content_type)
