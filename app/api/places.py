from typing import Any

from fastapi import APIRouter, Query

from app.services.places import fetch_places


router = APIRouter(
    prefix="/api/regions/canarias/places",
    tags=["places"],
)


@router.get("")
async def get_places(
    limit: int = Query(
        100,
        ge=1,
        le=500,
    ),
) -> dict[str, Any]:
    return await fetch_places(limit)