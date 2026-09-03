from typing import Any

from fastapi import APIRouter, Query

from app.services.news import fetch_news


router = APIRouter(prefix="/api/regions/canarias/news", tags=["news"])


@router.get("")
async def get_news(
    limit: int = Query(20, ge=1, le=50),
) -> list[dict[str, Any]]:
    return await fetch_news(limit)
