from typing import Any

from fastapi import APIRouter, Query

from app.services.tides import fetch_tides


router = APIRouter(prefix="/api/regions/canarias/tides", tags=["tides"])


@router.get("")
async def get_tides(
    latitude: float = Query(...),
    longitude: float = Query(...),
    hours: int = Query(48, ge=12, le=120),
) -> dict[str, Any]:
    return await fetch_tides(latitude, longitude, hours)
