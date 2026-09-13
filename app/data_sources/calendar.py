from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.events import current_month, fetch_island_events
from app.utils.islands import normalize_island

from .base import DataSource
from .registry import data_source
from .store import DATA_ROOT


def _event_key(item: dict[str, Any]) -> str:
    return str(
        item.get("id")
        or item.get("url")
        or f"{item.get('title', '')}|{item.get('start_date') or item.get('start_at') or ''}"
    ).strip()


@data_source("calendar", "events")
class CalendarSource(DataSource):
    write_strategy = "merge"
    # An official agenda can legitimately have no matching events for one month.
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
        return await fetch_island_events(island, limit=int(params.get("refresh_limit") or 200), month=month)

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
        items.sort(key=lambda item: (str(item.get("start_date") or "9999-99-99"), str(item.get("title") or "")))
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
