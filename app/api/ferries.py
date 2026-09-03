from typing import Any

from fastapi import APIRouter, Query

from app.services.ferries import get_ferry_routes


router = APIRouter(
    prefix="/api/regions/canarias/ferries",
    tags=["ferries"],
)


@router.get("/routes")
async def get_routes(
    island: str | None = Query(None),
) -> dict[str, Any]:
    return get_ferry_routes(island)
