from typing import Any

from fastapi import APIRouter, Query

from app.services.seismic import fetch_canary_earthquakes
from app.utils.islands import filter_feature_collection_by_island


router = APIRouter(
    prefix="/api/regions/canarias/seismic",
    tags=["seismic"],
)


@router.get("")
async def get_canary_earthquakes(
    island: str | None = Query(None),
) -> dict[str, Any]:
    data = await fetch_canary_earthquakes()

    return filter_feature_collection_by_island(
        data,
        island,
    )
