from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

import app.data_sources.bootstrap  # noqa: F401
from app.data_sources import get_data_source
from app.services.events import current_month
from app.services.today import build_today_payload
from app.utils.islands import filter_records_by_island, normalize_island

router = APIRouter(prefix="/api/regions/canarias", tags=["today"])


@router.get("/today")
async def canarias_today(island: str = Query(...)) -> dict[str, Any]:
    normalized = normalize_island(island)
    if normalized is None:
        raise HTTPException(status_code=404, detail="Unknown island")

    # IMPORTANT: read() only. This endpoint never calls refresh() or any
    # external API. It is safe to use as the future LLM context endpoint.
    weather = get_data_source("live", "weather").read(island=normalized)
    alerts = get_data_source("live", "alerts").read(island=normalized)
    events = get_data_source("calendar", "events").read(island=normalized, month=current_month())
    places = get_data_source("explore", "places").read(island=normalized)
    beaches = get_data_source("explore", "beaches").read(island=normalized)
    routes = get_data_source("explore", "routes").read(island=normalized)
    news_payload = get_data_source("news", "latest").read()
    news_items = filter_records_by_island(
        news_payload.get("items", []) if isinstance(news_payload, dict) else [],
        normalized,
        include_regional=True,
    )

    return build_today_payload(
        island=normalized,
        weather=weather,
        alerts=alerts,
        events=events,
        places=places,
        beaches=beaches,
        routes=routes,
        news_items=news_items,
    )
