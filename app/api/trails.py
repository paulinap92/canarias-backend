from typing import Any

from fastapi import APIRouter, Query

from app.services.trails import fetch_trails
from app.utils.islands import filter_feature_collection_by_island


router = APIRouter(
    prefix="/api/regions/canarias/trails",
    tags=["trails"],
)


@router.get("")
async def get_trails(
    limit: int = Query(50, ge=1, le=200),
    island: str | None = Query(None),
) -> dict[str, Any]:
    data = await fetch_trails(
        200 if island else limit
    )

    filtered = filter_feature_collection_by_island(
        data,
        island,
    )

    if island:
        filtered["features"] = filtered.get(
            "features",
            [],
        )[:limit]

    return filtered
