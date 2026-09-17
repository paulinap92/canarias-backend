from typing import Any

from fastapi import APIRouter, Query

import app.data_sources.bootstrap  # noqa: F401
from app.data_sources import get_data_source

router = APIRouter(prefix="/api/regions/canarias/trails", tags=["trails"])
source = get_data_source("explore", "routes")


def trim(data: dict[str, Any], limit: int) -> dict[str, Any]:
    return {**data, "features": data.get("features", [])[:limit]} if isinstance(data, dict) else data


@router.get("")
async def get_trails(
    limit: int = Query(100, ge=1, le=500),
    island: str | None = Query(None),
) -> dict[str, Any]:
    return trim(source.read(island=island), limit)


@router.post("")
async def refresh_trails(
    limit: int = Query(500, ge=1, le=500),
    island: str | None = Query(None),
) -> dict[str, Any]:
    return trim(await source.refresh(island=island), limit)
