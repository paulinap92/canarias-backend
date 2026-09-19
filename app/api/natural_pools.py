from typing import Any

from fastapi import APIRouter, Query

import app.data_sources.bootstrap  # noqa: F401
from app.data_sources import get_data_source


router = APIRouter(
    prefix="/api/regions/canarias/natural-pools",
    tags=["natural-pools"],
)
source = get_data_source("explore", "natural-pools")


def trim(data: dict[str, Any], limit: int) -> dict[str, Any]:
    if not isinstance(data, dict):
        return data
    return {
        **data,
        "features": data.get("features", [])[:limit],
    }


@router.get("")
async def get_natural_pools(
    limit: int = Query(100, ge=1, le=300),
    island: str | None = Query(None),
) -> dict[str, Any]:
    return trim(source.read(island=island), limit)


@router.post("")
async def refresh_natural_pools(
    limit: int = Query(200, ge=1, le=300),
    island: str | None = Query(None),
) -> dict[str, Any]:
    return trim(await source.refresh(island=island), limit)
