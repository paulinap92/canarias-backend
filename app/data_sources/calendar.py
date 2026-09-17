from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.services.events import (
    EVENT_SOURCES,
    current_month,
    fetch_island_events,
    parse_event_dates,
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
    "lanzarote": "https://turismolanzarote.com/agenda-de-eventos/",
    "la-graciosa": "https://www.visitlagraciosa.com/calendario-de-eventos/",
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


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _event_key(item: dict[str, Any]) -> str:
    return str(
        item.get("id")
        or item.get("url")
        or f"{item.get('title', '')}|{item.get('start_date') or item.get('start_at') or ''}"
    ).strip()


def _fallback_listing_events(
    html: str,
    *,
    base_url: str,
    source: str,
    source_id: str,
    island: str,
    month: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Parse looser official agenda cards when their markup is not heading-first."""
    soup = BeautifulSoup(html, "html.parser")
    reference_year = int(month[:4])
    items: list[dict[str, Any]] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = urljoin(base_url, anchor.get("href", ""))
        anchor_text = _clean(anchor.get_text(" ", strip=True))
        if not href.startswith("http") or not anchor_text:
            continue

        block = (
            anchor.find_parent(["article", "li", "section"])
            or anchor.find_parent("div")
            or anchor
        )
        context = _clean(block.get_text(" ", strip=True))
        start_date, end_date, schedule_text = parse_event_dates(
            context,
            reference_year=reference_year,
        )
        if start_date is None:
            continue
        if not (
            start_date.startswith(month)
            or (end_date or "").startswith(month)
        ):
            continue

        heading = block.find(["h1", "h2", "h3", "h4", "h5"]) if block is not anchor else None
        title = _clean(heading.get_text(" ", strip=True)) if heading is not None else anchor_text
        if len(title) < 3:
            continue

        key = href.rstrip("/") or f"{source_id}:{title.casefold()}:{start_date}"
        if key in seen:
            continue

        summary = context
        if schedule_text:
            summary = summary.replace(schedule_text, " ", 1)
        summary = _clean(summary.replace(title, " ", 1))

        items.append({
            "id": key,
            "title": title[:250],
            "start_date": start_date,
            "end_date": end_date or start_date,
            "schedule_text": schedule_text,
            "start_at": None,
            "end_at": None,
            "all_day": True,
            "category": "other",
            "location_name": None,
            "latitude": None,
            "longitude": None,
            "summary": summary[:500] or None,
            "image_url": None,
            "url": href,
            "island": island,
            "source": source,
            "source_id": source_id,
        })
        seen.add(key)
        if len(items) >= limit:
            break

    items.sort(key=lambda item: (item["start_date"], item["title"]))
    return items


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
        if not items:
            items = _fallback_listing_events(
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
