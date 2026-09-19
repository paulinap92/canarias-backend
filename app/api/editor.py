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
from app.services.admin_editor import (
    AdminEditorError,
    EXPLORE_RESOURCES,
    LIVE_RESOURCES,
    create_event,
    create_explore,
    hide_event,
    hide_explore,
    hide_news,
    media_inventory,
    read_events,
    read_explore,
    read_live,
    read_news,
    update_event,
    update_explore,
    update_news,
)
from app.services.events import current_month
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
        "explore_resources": list(EXPLORE_RESOURCES),
        "live_resources": list(LIVE_RESOURCES),
        "current_month": current_month(),
        "areas": ["guide", "explore", "calendar", "news", "live", "media"],
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


@router.get("/api/editor/explore")
async def editor_explore(request: Request, island: str = Query(...), resource: str = Query(...)) -> dict[str, Any]:
    _require_editor(request)
    try:
        return read_explore(island, resource)
    except AdminEditorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.post("/api/editor/explore", status_code=201)
async def editor_explore_create(request: Request, island: str = Query(...), resource: str = Query(...), item: dict[str, Any] = Body(...)) -> dict[str, Any]:
    _require_editor(request)
    try:
        return {"saved": create_explore(island, resource, item)}
    except AdminEditorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.put("/api/editor/explore/{editor_key}")
async def editor_explore_update(editor_key: str, request: Request, island: str = Query(...), resource: str = Query(...), item: dict[str, Any] = Body(...)) -> dict[str, Any]:
    _require_editor(request)
    try:
        return {"saved": update_explore(island, resource, editor_key, item)}
    except AdminEditorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.delete("/api/editor/explore/{editor_key}")
async def editor_explore_hide(editor_key: str, request: Request, island: str = Query(...), resource: str = Query(...)) -> dict[str, Any]:
    _require_editor(request)
    try:
        return {"saved": hide_explore(island, resource, editor_key)}
    except AdminEditorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.get("/api/editor/events")
async def editor_events(request: Request, island: str = Query(...), month: str = Query(..., pattern=r"^\d{4}-\d{2}$")) -> dict[str, Any]:
    _require_editor(request)
    try:
        return read_events(island, month)
    except AdminEditorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.post("/api/editor/events", status_code=201)
async def editor_event_create(request: Request, island: str = Query(...), month: str = Query(..., pattern=r"^\d{4}-\d{2}$"), item: dict[str, Any] = Body(...)) -> dict[str, Any]:
    _require_editor(request)
    try:
        return {"saved": create_event(island, month, item)}
    except AdminEditorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.put("/api/editor/events/{editor_key}")
async def editor_event_update(editor_key: str, request: Request, island: str = Query(...), month: str = Query(..., pattern=r"^\d{4}-\d{2}$"), item: dict[str, Any] = Body(...)) -> dict[str, Any]:
    _require_editor(request)
    try:
        return {"saved": update_event(island, month, editor_key, item)}
    except AdminEditorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.delete("/api/editor/events/{editor_key}")
async def editor_event_hide(editor_key: str, request: Request, island: str = Query(...), month: str = Query(..., pattern=r"^\d{4}-\d{2}$")) -> dict[str, Any]:
    _require_editor(request)
    try:
        return {"saved": hide_event(island, month, editor_key)}
    except AdminEditorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.get("/api/editor/news")
async def editor_news(request: Request, island: str | None = Query(None)) -> dict[str, Any]:
    _require_editor(request)
    return read_news(island)

@router.put("/api/editor/news/{editor_key}")
async def editor_news_update(editor_key: str, request: Request, item: dict[str, Any] = Body(...)) -> dict[str, Any]:
    _require_editor(request)
    try:
        return {"saved": update_news(editor_key, item)}
    except AdminEditorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.delete("/api/editor/news/{editor_key}")
async def editor_news_hide(editor_key: str, request: Request) -> dict[str, Any]:
    _require_editor(request)
    try:
        return {"saved": hide_news(editor_key)}
    except AdminEditorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.get("/api/editor/live")
async def editor_live(request: Request, island: str = Query(...), resource: str = Query(...)) -> dict[str, Any]:
    _require_editor(request)
    try:
        return read_live(island, resource)
    except (AdminEditorError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.get("/api/editor/media")
async def editor_media(request: Request, island: str = Query(...)) -> dict[str, Any]:
    _require_editor(request)
    try:
        return media_inventory(island)
    except AdminEditorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
