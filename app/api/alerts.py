from typing import Any

from fastapi import APIRouter, Query

from app.services.alerts import fetch_alerts


router = APIRouter(prefix="/api/regions/canarias/alerts", tags=["alerts"])


@router.get("")
async def get_alerts(
    limit: int = Query(20, ge=1, le=50),
) -> list[dict[str, Any]]:
    return await fetch_alerts(limit)
