from typing import Any

from fastapi import APIRouter, Query

from app.services.places import fetch_places
from app.utils.islands import filter_feature_collection_by_island


router = APIRouter(
    prefix="/api/regions/canarias/places",
    tags=["places"],
)


@router.get("")
async def get_places(
    limit: int = Query(100, ge=1, le=500),
    island: str | None = Query(None),
) -> dict[str, Any]:
    data = await fetch_places(
        500 if island else limit
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
