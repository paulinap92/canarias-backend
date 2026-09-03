from typing import Any

from fastapi import APIRouter

from app.services.volcanic import fetch_volcanic_activity


router = APIRouter(prefix="/api/regions/canarias/volcanic", tags=["volcanic"])


@router.get("")
async def get_volcanic_activity() -> dict[str, Any]:
    return await fetch_volcanic_activity()
