from typing import Any

from fastapi import APIRouter, Query

from app.services.beaches import fetch_beaches


router = APIRouter(prefix="/api/regions/canarias/beaches", tags=["beaches"])


@router.get("")
async def get_beaches(
    limit: int = Query(100, ge=1, le=500),
) -> dict[str, Any]:
    return await fetch_beaches(limit)
