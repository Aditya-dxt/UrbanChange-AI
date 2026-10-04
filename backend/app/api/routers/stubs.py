"""
Stub router placeholders for investigations and assets.
Full implementation arrives in Phase 5 and 6.
These stubs exist so main.py compiles and /docs is reachable immediately.
"""
from __future__ import annotations

from fastapi import APIRouter

# ── Investigations ────────────────────────────────────────────────────────────
investigations_router = APIRouter(
    prefix="/api/investigations",
    tags=["investigations"],
)


@investigations_router.get("", summary="[stub] List investigations")
async def list_investigations_stub() -> dict:
    return {"detail": "Investigations router – full implementation in Phase 5/6."}


# ── Assets ────────────────────────────────────────────────────────────────────
assets_router = APIRouter(
    prefix="/api/assets",
    tags=["assets"],
)


@assets_router.get("/{path:path}", summary="[stub] Serve asset")
async def serve_asset_stub(path: str) -> dict:
    return {"detail": "Asset router – full implementation in Phase 5/6.", "path": path}
