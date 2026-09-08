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
    # Query Overpass with the selected island bbox instead of
    # downloading the whole archipelago and filtering afterwards.
    data = await fetch_places(
        limit=limit,
        island=island,
    )

    if data.get("available") is False:
        return data

    filtered = filter_feature_collection_by_island(
        data,
        island,
    )

    filtered["available"] = True
    filtered["source"] = data.get("source", "overpass")

    return filtered
