from typing import Any

from fastapi import APIRouter

from app.services.air_quality import fetch_air_quality


router = APIRouter(
    prefix="/api/regions/canarias/islands/tenerife/air-quality",
    tags=["air-quality"],
)


@router.get("")
async def get_air_quality() -> dict[str, Any]:
    return await fetch_air_quality()
