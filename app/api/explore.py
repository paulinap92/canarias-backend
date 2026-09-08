from typing import Any

from fastapi import APIRouter, Query

from app.services.explore import get_explore_items


router = APIRouter(
    prefix="/api/regions/canarias/explore",
    tags=["explore"],
)


@router.get("")
async def get_explore(
    island: str = Query(...),
    limit: int = Query(
        6,
        ge=1,
        le=20,
    ),
    category: str | None = Query(None),
) -> dict[str, Any]:

    return get_explore_items(
        island=island,
        limit=limit,
        category=category,
    )