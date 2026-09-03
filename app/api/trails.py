from typing import Any

from fastapi import APIRouter, Query

from app.services.trails import fetch_trails


router = APIRouter(
    prefix="/api/regions/canarias/trails",
    tags=["trails"],
)


@router.get("")
async def get_trails(
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    return await fetch_trails(limit)