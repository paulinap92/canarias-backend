from typing import Any

from fastapi import APIRouter, Query

from app.services.beaches import fetch_beaches
from app.utils.islands import filter_feature_collection_by_island


router = APIRouter(
    prefix="/api/regions/canarias/beaches",
    tags=["beaches"],
)


@router.get("")
async def get_beaches(
    limit: int = Query(100, ge=1, le=500),
    island: str | None = Query(None),
) -> dict[str, Any]:
    data = await fetch_beaches(
        limit=500 if island else limit,
        island=island,
    )

    if data.get("available") is False:
        return data

    filtered = filter_feature_collection_by_island(
        data,
        island,
    )

    if island:
        filtered["features"] = filtered.get(
            "features",
            [],
        )[:limit]

    filtered["available"] = True
    filtered["source"] = data.get("source", "overpass")

    return filtered
