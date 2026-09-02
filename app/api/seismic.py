from typing import Any

from fastapi import APIRouter

from app.services.seismic import fetch_canary_earthquakes


router = APIRouter(
    prefix="/api/regions/canarias/seismic",
    tags=["seismic"],
)


@router.get("")
async def get_canary_earthquakes() -> dict[str, Any]:
    return await fetch_canary_earthquakes()