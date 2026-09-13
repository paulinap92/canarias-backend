from typing import Any

from fastapi import APIRouter, Query

import app.data_sources.bootstrap  # noqa: F401
from app.data_sources import get_data_source


router = APIRouter(
    prefix="/api/regions/canarias/marine",
    tags=["marine"],
)
source = get_data_source("live", "marine")


@router.get("")
async def get_marine(
    island: str | None = Query(None),
) -> dict[str, Any]:
    """Compatibility alias for the persisted multi-point marine snapshot."""
    return source.read(island=island)


@router.post("")
async def refresh_marine(
    island: str | None = Query(None),
) -> dict[str, Any]:
    return await source.refresh(island=island)
