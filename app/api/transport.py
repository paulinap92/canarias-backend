from typing import Any

from fastapi import APIRouter, Query

from app.services.transport import (
    fetch_titsa_routes,
    fetch_titsa_stops,
    get_airports,
)


router = APIRouter(
    prefix="/api/regions/canarias",
    tags=["transport"],
)


@router.get("/transport/airports")
async def airports(
    island: str | None = Query(None),
) -> list[dict[str, Any]]:
    return get_airports(island)


@router.get(
    "/islands/tenerife/transport/stops"
)
async def tenerife_stops(
    limit: int = Query(500, ge=1, le=5000),
) -> dict[str, Any]:
    return await fetch_titsa_stops(limit)


@router.get(
    "/islands/tenerife/transport/routes"
)
async def tenerife_routes(
    limit: int = Query(250, ge=1, le=1000),
) -> list[dict[str, Any]]:
    return await fetch_titsa_routes(limit)
