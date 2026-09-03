from typing import Any

from fastapi import APIRouter, Query

from app.services.events import fetch_tenerife_events
from app.utils.islands import normalize_island


router = APIRouter(
    tags=["events"],
)


@router.get("/api/regions/canarias/events")
async def get_events(
    island: str | None = Query(None),
    limit: int = Query(30, ge=1, le=100),
) -> dict[str, Any]:
    normalized = normalize_island(island)

    if island is not None and normalized != "tenerife":
        return {
            "island": normalized or island,
            "available": False,
            "supported_islands": ["tenerife"],
            "items": [],
        }

    items = await fetch_tenerife_events(limit)

    return {
        "island": "tenerife",
        "available": True,
        "supported_islands": ["tenerife"],
        "items": items,
    }


@router.get(
    "/api/regions/canarias/islands/tenerife/events"
)
async def get_tenerife_events_legacy(
    limit: int = Query(30, ge=1, le=100),
) -> dict[str, Any]:
    return await get_events(
        island="tenerife",
        limit=limit,
    )
