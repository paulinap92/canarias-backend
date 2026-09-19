from typing import Any

from fastapi import APIRouter, HTTPException, Query

import app.data_sources.bootstrap  # noqa: F401
from app.data_sources import get_data_source


RESOURCES = {
    "marinas",
    "food-producers",
    "volcanoes",
    "summits",
    "diving-spots",
    "leisure-centers",
    "museums-visits",
    "natural-spaces",
    "surf-spots",
    "stargazing",
    "markets",
}

router = APIRouter(
    prefix="/api/regions/canarias/explore-collections",
    tags=["explore-collections"],
)


def _source(resource: str):
    if resource not in RESOURCES:
        raise HTTPException(status_code=404, detail="Unknown Explore collection")
    return get_data_source("explore", resource)


def _trim(payload: dict[str, Any], limit: int) -> dict[str, Any]:
    return {
        **payload,
        "features": list(payload.get("features") or [])[:limit],
    }


@router.get("/{resource}")
async def get_collection(
    resource: str,
    island: str = Query(...),
    limit: int = Query(100, ge=1, le=300),
) -> dict[str, Any]:
    return _trim(_source(resource).read(island=island), limit)


@router.post("/{resource}")
async def refresh_collection(
    resource: str,
    island: str = Query(...),
    limit: int = Query(200, ge=1, le=300),
) -> dict[str, Any]:
    return _trim(await _source(resource).refresh(island=island), limit)
