from __future__ import annotations

import hmac
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query, Request
from fastapi.responses import FileResponse

from app.services.content import VALID_SECTIONS
from app.services.content_editor import (
    ContentEditorError,
    create_item,
    delete_item,
    read_items,
    update_item,
)
from app.utils.islands import VALID_ISLANDS


router = APIRouter(tags=["content-editor"])
EDITOR_DIR = Path(__file__).resolve().parents[1] / "editor"


def _enabled() -> bool:
    return os.environ.get("CANARIAS_CONTENT_EDITOR", "0").strip().casefold() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _require_editor(request: Request) -> None:
    if not _enabled():
        raise HTTPException(status_code=404, detail="Not found")

    host = request.client.host if request.client else ""
    if host in {"127.0.0.1", "::1", "localhost"}:
        return

    expected = os.environ.get("CANARIAS_CONTENT_EDITOR_TOKEN", "")
    if not expected:
        raise HTTPException(
            status_code=403,
            detail="Remote editor access is disabled",
        )

    authorization = request.headers.get("authorization", "")
    supplied = authorization.removeprefix("Bearer ").strip()
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Invalid editor token")


def _editor_file(request: Request, filename: str) -> FileResponse:
    _require_editor(request)
    path = EDITOR_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(path)


@router.get("/editor", include_in_schema=False)
async def editor_page(request: Request) -> FileResponse:
    return _editor_file(request, "index.html")


@router.get("/editor/editor.css", include_in_schema=False)
async def editor_css(request: Request) -> FileResponse:
    return _editor_file(request, "editor.css")


@router.get("/editor/editor.js", include_in_schema=False)
async def editor_js(request: Request) -> FileResponse:
    return _editor_file(request, "editor.js")


@router.get("/api/editor/options")
async def editor_options(request: Request) -> dict[str, Any]:
    _require_editor(request)
    r2_keys = (
        "R2_ACCOUNT_ID",
        "R2_BUCKET",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_PUBLIC_BASE_URL",
    )
    return {
        "islands": list(VALID_ISLANDS),
        "sections": sorted(VALID_SECTIONS),
        "media_upload_enabled": all(os.environ.get(key) for key in r2_keys),
    }


@router.get("/api/editor/content")
async def editor_content(
    request: Request,
    island: str = Query(...),
    section: str = Query(...),
) -> dict[str, Any]:
    _require_editor(request)
    try:
        items = read_items(island, section)
    except ContentEditorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "island": island,
        "section": section,
        "count": len(items),
        "items": items,
    }


@router.post("/api/editor/content", status_code=201)
async def editor_create(
    request: Request,
    island: str = Query(...),
    section: str = Query(...),
    item: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    _require_editor(request)
    try:
        saved = create_item(island, section, item)
    except ContentEditorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"saved": saved}


@router.put("/api/editor/content/{slug}")
async def editor_update(
    slug: str,
    request: Request,
    island: str = Query(...),
    section: str = Query(...),
    item: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    _require_editor(request)
    try:
        saved = update_item(island, section, slug, item)
    except ContentEditorError as exc:
        status = 404 if "not found" in str(exc) else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    return {"saved": saved}


@router.delete("/api/editor/content/{slug}", status_code=204)
async def editor_delete(
    slug: str,
    request: Request,
    island: str = Query(...),
    section: str = Query(...),
) -> None:
    _require_editor(request)
    try:
        delete_item(island, section, slug)
    except ContentEditorError as exc:
        status = 404 if "not found" in str(exc) else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc
