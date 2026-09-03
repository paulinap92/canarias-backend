from typing import Any

from fastapi import APIRouter

from app.services.monuments import load_monuments


router = APIRouter(
    prefix="/api/regions/canarias/monuments",
    tags=["monuments"],
)


@router.get("")
async def get_monuments() -> list[dict[str, Any]]:
    return load_monuments()