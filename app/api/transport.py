from typing import Any

from fastapi import APIRouter, Query

import app.data_sources.bootstrap  # noqa: F401
from app.data_sources import get_data_source
from app.services.transport import get_airports, get_transport_overview


router = APIRouter(
    prefix="/api/regions/canarias",
    tags=["transport"],
)


@router.get("/transport/airports")
async def airports(
    island: str | None = Query(None),
) -> list[dict[str, Any]]:
    return get_airports(island)


@router.get("/transport/overview")
async def transport_overview(
    island: str = Query(...),
) -> dict[str, Any]:
    return get_transport_overview(island)


@router.get("/islands/tenerife/transport/stops")
async def tenerife_stops(
    limit: int = Query(500, ge=1, le=5000),
) -> dict[str, Any]:
    source = get_data_source("transport", "titsa-stops")
    payload = source.read(limit=limit)
    if isinstance(payload, dict) and isinstance(payload.get("features"), list):
        result = dict(payload)
        result["features"] = payload["features"][:limit]
        return result
    return payload


@router.post("/islands/tenerife/transport/stops")
async def refresh_tenerife_stops(
    limit: int = Query(5000, ge=1, le=5000),
) -> dict[str, Any]:
    source = get_data_source("transport", "titsa-stops")
    return await source.refresh(limit=limit)


@router.get("/islands/tenerife/transport/routes")
async def tenerife_routes(
    limit: int = Query(250, ge=1, le=1000),
) -> dict[str, Any]:
    source = get_data_source("transport", "titsa-routes")
    payload = source.read(limit=limit)
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        result = dict(payload)
        result["items"] = payload["items"][:limit]
        return result
    return payload


@router.post("/islands/tenerife/transport/routes")
async def refresh_tenerife_routes(
    limit: int = Query(1000, ge=1, le=1000),
) -> dict[str, Any]:
    source = get_data_source("transport", "titsa-routes")
    return await source.refresh(limit=limit)
