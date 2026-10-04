"""
Unit tests for AssetService.

No DB, no HTTP — pure filesystem + path logic.
"""
from __future__ import annotations

import pytest
from pathlib import Path

from app.services.asset_service import AssetService
from app.errors import AssetNotFoundError, PathTraversalError, UnsupportedMediaTypeError


@pytest.fixture
def svc(tmp_path: Path) -> AssetService:
    return AssetService(tmp_path)


class TestPathToUrl:

    def test_relative_path(self, svc, tmp_path):
        (tmp_path / "scene.tif").write_bytes(b"")
        url = svc.path_to_url("scene.tif")
        assert url == "/api/assets/scene.tif"

    def test_nested_relative_path(self, svc, tmp_path):
        (tmp_path / "mock").mkdir()
        (tmp_path / "mock" / "sentinel2.tif").write_bytes(b"")
        url = svc.path_to_url("mock/sentinel2.tif")
        assert url == "/api/assets/mock/sentinel2.tif"

    def test_absolute_path_inside_root(self, svc, tmp_path):
        (tmp_path / "file.png").write_bytes(b"")
        url = svc.path_to_url(str(tmp_path / "file.png"))
        assert url == "/api/assets/file.png"

    def test_none_returns_none(self, svc):
        assert svc.path_to_url(None) is None

    def test_empty_string_returns_none(self, svc):
        assert svc.path_to_url("") is None

    def test_traversal_path_returns_none(self, svc):
        # path_to_url should return None (not raise) for traversal paths
        result = svc.path_to_url("../etc/passwd")
        assert result is None


class TestTraversalPrevention:

    def test_dotdot_blocked(self, svc):
        with pytest.raises(PathTraversalError):
            svc.resolve("../etc/passwd")

    def test_dotdot_in_subdir_blocked(self, svc):
        with pytest.raises(PathTraversalError):
            svc.resolve("subdir/../../etc/passwd")

    def test_absolute_outside_root_blocked(self, svc, tmp_path):
        with pytest.raises(PathTraversalError):
            svc.resolve("/etc/passwd")

    def test_valid_relative_resolves(self, svc, tmp_path):
        (tmp_path / "valid.tif").write_bytes(b"")
        resolved = svc.resolve("valid.tif")
        assert resolved == (tmp_path / "valid.tif").resolve()

    def test_valid_absolute_inside_root_resolves(self, svc, tmp_path):
        f = tmp_path / "valid.png"
        f.write_bytes(b"")
        resolved = svc.resolve(str(f))
        assert resolved == f.resolve()


class TestServe:

    def test_serve_png(self, svc, tmp_path):
        (tmp_path / "image.png").write_bytes(b"\x89PNG")
        from fastapi.responses import FileResponse
        resp = svc.serve("image.png")
        assert isinstance(resp, FileResponse)
        assert resp.media_type == "image/png"

    def test_serve_tif(self, svc, tmp_path):
        (tmp_path / "scene.tif").write_bytes(b"GeoTIFF")
        resp = svc.serve("scene.tif")
        assert resp.media_type == "image/tiff"

    def test_serve_geojson(self, svc, tmp_path):
        (tmp_path / "result.geojson").write_bytes(b"{}")
        resp = svc.serve("result.geojson")
        assert resp.media_type == "application/geo+json"

    def test_serve_missing_file(self, svc):
        with pytest.raises(AssetNotFoundError):
            svc.serve("nonexistent.png")

    def test_serve_disallowed_type(self, svc, tmp_path):
        (tmp_path / "script.sh").write_bytes(b"#!/bin/bash")
        with pytest.raises(UnsupportedMediaTypeError):
            svc.serve("script.sh")

    def test_serve_traversal_blocked(self, svc):
        with pytest.raises(PathTraversalError):
            svc.serve("../etc/passwd")

    def test_serve_leading_slash_stripped(self, svc, tmp_path):
        (tmp_path / "img.png").write_bytes(b"")
        resp = svc.serve("/img.png")  # leading slash should be stripped
        from fastapi.responses import FileResponse
        assert isinstance(resp, FileResponse)


class TestHasPreview:

    def test_has_preview_true(self, svc):
        assert svc.has_preview("/some/path.png") is True

    def test_has_preview_none(self, svc):
        assert svc.has_preview(None) is False

    def test_has_preview_empty(self, svc):
        assert svc.has_preview("") is False
