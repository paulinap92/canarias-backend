from typing import Any

from fastapi import APIRouter, Query

from app.services.ports import get_ports


router = APIRouter(
    prefix="/api/regions/canarias/ports",
    tags=["ports"],
)


@router.get("")
async def get_ports_api(
    island: str | None = Query(None),
) -> dict[str, Any]:
    return get_ports(island)
