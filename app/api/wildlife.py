from typing import Any

from fastapi import APIRouter, Query

from app.services.wildlife import fetch_wildlife
from app.utils.islands import filter_feature_collection_by_island


router = APIRouter(
    prefix="/api/regions/canarias/wildlife",
    tags=["wildlife"],
)


@router.get("")
async def get_wildlife(
    limit: int = Query(50, ge=1, le=300),
    island: str | None = Query(None),
) -> dict[str, Any]:
    data = await fetch_wildlife(
        limit=300 if island else limit,
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
    filtered["source"] = data.get("source", "gbif")

    return filtered
