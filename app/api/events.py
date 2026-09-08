from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Query

from app.services.events import (
    current_month,
    fetch_tenerife_events,
)
from app.utils.islands import normalize_island


router = APIRouter(
    tags=["events"],
)


def _unsupported(
    island: str,
) -> dict[str, Any]:
    return {
        "island": island,
        "available": False,
        "supported_islands": [
            "tenerife"
        ],
        "calendar_ready": True,
        "items": [],
    }


@router.get(
    "/api/regions/canarias/events"
)
async def get_events(
    island: str | None = Query(None),
    month: str | None = Query(
        None,
        pattern=r"^\d{4}-\d{2}$",
    ),
    category: str | None = Query(None),
    limit: int = Query(
        100,
        ge=1,
        le=200,
    ),
) -> dict[str, Any]:
    normalized = normalize_island(
        island
    )

    if (
        island is not None
        and normalized != "tenerife"
    ):
        return _unsupported(
            normalized or island
        )

    selected_month = (
        month or current_month()
    )

    items = await fetch_tenerife_events(
        limit=200,
        month=selected_month,
    )

    if category:
        items = [
            item
            for item in items
            if item.get(
                "category"
            )
            == category
        ]

    items = items[:limit]

    return {
        "island": "tenerife",
        "available": True,
        "supported_islands": [
            "tenerife"
        ],
        "calendar_ready": True,
        "month": selected_month,
        "category": category,
        "count": len(items),
        "items": items,
    }


@router.get(
    "/api/regions/canarias/events/calendar"
)
async def get_events_calendar(
    island: str | None = Query(None),
    month: str | None = Query(
        None,
        pattern=r"^\d{4}-\d{2}$",
    ),
    category: str | None = Query(None),
) -> dict[str, Any]:
    data = await get_events(
        island=island,
        month=month,
        category=category,
        limit=200,
    )

    if not data["available"]:
        return {
            **data,
            "days": {},
        }

    days: dict[
        str,
        list[dict[str, Any]],
    ] = defaultdict(list)

    for item in data["items"]:
        days[
            item["start_date"]
        ].append(item)

    return {
        "island": data["island"],
        "available": True,
        "supported_islands": [
            "tenerife"
        ],
        "calendar_ready": True,
        "month": data["month"],
        "category": category,
        "events_count": len(
            data["items"]
        ),
        "days_with_events": len(
            days
        ),
        "days": dict(days),
    }


@router.get(
    "/api/regions/canarias/islands/"
    "tenerife/events"
)
async def get_tenerife_events_legacy(
    limit: int = Query(
        30,
        ge=1,
        le=100,
    ),
) -> dict[str, Any]:
    return await get_events(
        island="tenerife",
        limit=limit,
    )
