from typing import Any

from fastapi import APIRouter, Query

from app.services.marine import fetch_marine


router = APIRouter(
    prefix="/api/regions/canarias/marine",
    tags=["marine"],
)


@router.get("")
async def get_marine(
    latitude: float = Query(...),
    longitude: float = Query(...),
) -> dict[str, Any]:
    return await fetch_marine(
        latitude,
        longitude,
    )