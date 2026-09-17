from typing import Any

from fastapi import APIRouter, Query

import app.data_sources.bootstrap  # noqa: F401
from app.data_sources import get_data_source
from app.utils.islands import filter_records_by_island

router = APIRouter(prefix="/api/regions/canarias/news", tags=["news"])
source = get_data_source("news", "latest")


def items(payload: dict[str, Any], island: str | None, limit: int) -> list[dict[str, Any]]:
    # Island view means island-specific news only. Regional/archipelago-wide
    # items belong to the Canarias-wide view, not duplicated under every island.
    return filter_records_by_island(
        payload.get("items", []),
        island,
        include_regional=False,
    )[:limit]


@router.get("")
async def get_news(
    limit: int = Query(20, ge=1, le=200),
    island: str | None = Query(None),
) -> list[dict[str, Any]]:
    return items(source.read(), island, limit)


@router.post("")
async def refresh_news(
    limit: int = Query(20, ge=1, le=200),
    island: str | None = Query(None),
) -> list[dict[str, Any]]:
    return items(await source.refresh(refresh_limit=200), island, limit)
