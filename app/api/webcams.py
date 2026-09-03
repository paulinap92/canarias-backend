from typing import Any

from fastapi import APIRouter, Query

from app.services.webcams import fetch_tenerife_webcams
from app.utils.islands import normalize_island


router = APIRouter(
    tags=["webcams"],
)


@router.get("/api/regions/canarias/webcams")
async def get_webcams(
    island: str | None = Query(None),
    limit: int = Query(100, ge=1, le=200),
) -> dict[str, Any]:
    normalized = normalize_island(island)

    if island is not None and normalized != "tenerife":
        return {
            "island": normalized or island,
            "available": False,
            "supported_islands": ["tenerife"],
            "items": [],
        }

    items = await fetch_tenerife_webcams(limit)

    return {
        "island": "tenerife",
        "available": True,
        "supported_islands": ["tenerife"],
        "items": items,
    }


@router.get(
    "/api/regions/canarias/islands/tenerife/webcams"
)
async def get_tenerife_webcams_legacy(
    limit: int = Query(100, ge=1, le=200),
) -> dict[str, Any]:
    return await get_webcams(
        island="tenerife",
        limit=limit,
    )
