from typing import Any

from fastapi import APIRouter, Query

from app.services.news import fetch_news
from app.utils.islands import filter_records_by_island


router = APIRouter(
    prefix="/api/regions/canarias/news",
    tags=["news"],
)


@router.get("")
async def get_news(
    limit: int = Query(
        20,
        ge=1,
        le=50,
    ),
    island: str | None = Query(None),
) -> list[dict[str, Any]]:
    items = await fetch_news(limit)

    # Gobierno de Canarias items are regional (island=None),
    # therefore they remain visible for every selected island.
    # Future Cabildo items can have island="tenerife", etc.,
    # and this filter will stop cross-island leakage.
    return filter_records_by_island(
        items,
        island,
        include_regional=True,
    )
