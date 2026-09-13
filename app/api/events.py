from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Query

import app.data_sources.bootstrap  # noqa: F401
from app.data_sources import get_data_source
from app.services.events import EVENT_SOURCES, current_month
from app.utils.islands import normalize_island

router = APIRouter(tags=["events"])
source = get_data_source("calendar", "events")


def _invalid(island: str) -> dict[str, Any]:
    return {
        "island": island,
        "available": False,
        "calendar_ready": False,
        "supported_islands": sorted(EVENT_SOURCES),
        "items": [],
        "status": "unsupported",
    }


def _filtered(payload: dict[str, Any], category: str | None, limit: int) -> dict[str, Any]:
    values = list(payload.get("items", []))
    if category:
        values = [item for item in values if item.get("category") == category]
    visible = values[:limit]
    return {**payload, "items": visible, "count": len(visible), "category": category}


@router.get("/api/regions/canarias/events")
async def get_events(
    island: str | None = Query(None),
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    category: str | None = Query(None),
    limit: int = Query(100, ge=1, le=200),
) -> dict[str, Any]:
    normalized = normalize_island(island) if island is not None else "tenerife"
    if normalized is None:
        return _invalid(island or "")
    return _filtered(source.read(island=normalized, month=month or current_month()), category, limit)


@router.post("/api/regions/canarias/events")
async def refresh_events(
    island: str | None = Query(None),
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    category: str | None = Query(None),
    limit: int = Query(100, ge=1, le=200),
) -> dict[str, Any]:
    normalized = normalize_island(island) if island is not None else "tenerife"
    if normalized is None:
        return _invalid(island or "")
    payload = await source.refresh(island=normalized, month=month or current_month(), refresh_limit=200)
    return _filtered(payload, category, limit)


@router.get("/api/regions/canarias/events/calendar")
async def get_events_calendar(
    island: str | None = Query(None),
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    category: str | None = Query(None),
) -> dict[str, Any]:
    data = await get_events(island=island, month=month, category=category, limit=200)
    days: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in data.get("items", []):
        if item.get("start_date"):
            days[item["start_date"]].append(item)
    return {
        **data,
        "events_count": len(data.get("items", [])),
        "days_with_events": len(days),
        "days": dict(days),
    }


@router.get("/api/regions/canarias/islands/tenerife/events")
async def legacy(limit: int = Query(30, ge=1, le=100)) -> dict[str, Any]:
    return await get_events(island="tenerife", limit=limit)
