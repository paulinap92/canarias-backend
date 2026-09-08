from typing import Any
from fastapi import APIRouter, Query
from app.services.alerts import fetch_active_alerts

router = APIRouter(
    prefix="/api/regions/canarias/alerts",
    tags=["alerts"],
)

@router.get("")
async def get_alerts(
    island: str | None = Query(None),
) -> list[dict[str, Any]]:
    return await fetch_active_alerts(island)
