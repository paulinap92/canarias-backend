from typing import Any

from fastapi import APIRouter, Query

from app.services.wildlife import fetch_wildlife


router = APIRouter(
    prefix="/api/regions/canarias/wildlife",
    tags=["wildlife"],
)


@router.get("")
async def get_wildlife(
    limit: int = Query(50, ge=1, le=300),
) -> dict[str, Any]:
    return await fetch_wildlife(limit)