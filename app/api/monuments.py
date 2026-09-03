from typing import Any

from fastapi import APIRouter, Query

from app.services.monuments import load_monuments
from app.utils.islands import filter_records_by_island


router = APIRouter(
    prefix="/api/regions/canarias/monuments",
    tags=["monuments"],
)


@router.get("")
async def get_monuments(
    island: str | None = Query(None),
) -> list[dict[str, Any]]:
    monuments = load_monuments()

    return filter_records_by_island(
        monuments,
        island,
    )
