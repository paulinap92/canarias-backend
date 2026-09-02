import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter


router = APIRouter(
    prefix="/api/regions/canarias/cities",
    tags=["cities"],
)


DATA_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "cities.json"
)


@router.get("")
async def get_cities() -> list[dict[str, Any]]:
    with DATA_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)