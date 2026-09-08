from typing import Any
from fastapi import APIRouter, Query
from app.services.open_meteo_live import (
    fetch_air_quality_points,
    fetch_tide_points,
    fetch_weather_points,
)

router = APIRouter(prefix="/api/regions/canarias/live", tags=["live"])

@router.get("/weather")
async def live_weather(island: str | None = Query(None)) -> dict[str, Any]:
    return await fetch_weather_points(island)

@router.get("/air-quality")
async def live_air_quality(island: str | None = Query(None)) -> dict[str, Any]:
    return await fetch_air_quality_points(island)

@router.get("/tides")
async def live_tides(
    island: str | None = Query(None),
    hours: int = Query(48, ge=12, le=96),
) -> dict[str, Any]:
    return await fetch_tide_points(island, hours)
