from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from app.services.events import (
    EVENT_SOURCES,
    current_month,
    fetch_island_events,
    parse_generic_events,
)
from app.utils.islands import normalize_island

from .base import DataSource
from .registry import data_source
from .store import DATA_ROOT


CALENDAR_URL_OVERRIDES: dict[str, str] = {
    "fuerteventura": "https://www.visitfuerteventura.com/eventos/",
    "la-palma": "https://visitlapalma.es/eventos/",
    "la-gomera": "https://lagomera.travel/eventos/",
    "el-hierro": "https://elhierro.travel/eventos/",
    "lanzarote": "https://www.holaislascanarias.com/eventos/lanzarote/",
    "la-graciosa": "https://www.holaislascanarias.com/eventos/la-graciosa/",
}

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.7",
    "Cache-Control": "no-cache",
}


def _event_key(item: dict[str, Any]) -> str:
    return str(
        item.get("id")
        or item.get("url")
        or f"{item.get('title', '')}|{item.get('start_date') or item.get('start_at') or ''}"
    ).strip()


@data_source("calendar", "events")
class CalendarSource(DataSource):
    write_strategy = "merge"
    allow_empty = True

    def path(self, **params: Any) -> Path:
        island = normalize_island(params.get("island")) or "tenerife"
        month = params.get("month") or current_month()
        return DATA_ROOT / "calendar" / island / f"{month}.json"

    def empty_payload(self, **params: Any) -> dict[str, Any]:
        island = normalize_island(params.get("island")) or "tenerife"
        month = params.get("month") or current_month()
        return {
            "island": island,
            "month": month,
            "items": [],
            "available": False,
            "calendar_ready": True,
            "status": "not_initialized",
            "updated_at": None,
        }

    async def fetch(self, **params: Any) -> dict[str, Any]:
        island = normalize_island(params.get("island"))
        if island is None:
            raise ValueError("Unknown island")
        month = params.get("month") or current_month()
        limit = int(params.get("refresh_limit") or 200)

        # Keep Tenerife's dedicated parser. For the other official tourism
        # agendas use browser-like headers: several CDNs reject the old bot-like
        # User-Agent even though the public page is available in a browser.
        if island == "tenerife":
            return await fetch_island_events(island, limit=limit, month=month)

        config = dict(EVENT_SOURCES[island])
        config["url"] = CALENDAR_URL_OVERRIDES.get(island, config["url"])

        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers=BROWSER_HEADERS,
        ) as client:
            response = await client.get(config["url"])
            response.raise_for_status()

        items = parse_generic_events(
            response.text,
            base_url=config["url"],
            source=config["source"],
            source_id=config["id"],
            island=island,
            month=month,
            limit=limit,
        )
        return {
            "island": island,
            "month": month,
            "items": items,
            "available": True,
            "source": config["source"],
            "source_url": config["url"],
            "source_id": config["id"],
            "calendar_ready": True,
        }

    def merge_payload(self, previous: Any, fetched: Any, **params: Any) -> dict[str, Any]:
        previous_items = list(previous.get("items", [])) if isinstance(previous, dict) else []
        fetched_items = list(fetched.get("items", [])) if isinstance(fetched, dict) else []

        merged: dict[str, dict[str, Any]] = {}
        order: list[str] = []
        for item in previous_items:
            if not isinstance(item, dict):
                continue
            key = _event_key(item)
            if not key:
                continue
            merged[key] = dict(item)
            order.append(key)

        added = 0
        updated = 0
        for item in fetched_items:
            if not isinstance(item, dict):
                continue
            key = _event_key(item)
            if not key:
                continue
            if key not in merged:
                added += 1
                order.append(key)
                merged[key] = dict(item)
            else:
                old = merged[key]
                combined = {**old, **item}
                if combined != old:
                    updated += 1
                merged[key] = combined

        items = [merged[key] for key in order]
        items.sort(
            key=lambda item: (
                str(item.get("start_date") or "9999-99-99"),
                str(item.get("title") or ""),
            )
        )
        return {
            **(previous if isinstance(previous, dict) else {}),
            **(fetched if isinstance(fetched, dict) else {}),
            "items": items,
            "available": True,
            "refresh_stats": {
                "fetched": len(fetched_items),
                "added": added,
                "updated": updated,
                "kept_from_previous": max(0, len(previous_items) - updated),
                "stored": len(items),
            },
        }
