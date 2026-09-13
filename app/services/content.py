from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.utils.islands import normalize_island


ROOT = Path(__file__).resolve().parents[2]

CONTENT_ROOT = ROOT / "data" / "guide" / "content"

VALID_SECTIONS = {
    "explore",
    "food",
    "culture",
    "music",
    "fiestas",
    "products",
    "stories",
    "crafts",
    "heritage",
    "history",
    "climate",
    "historical-weather",
    "geology",
    "nature",
    "experiences",
}


def _content_file(
    island: str,
    section: str,
) -> Path:
    return (
        CONTENT_ROOT
        / island
        / f"{section}.json"
    )


def get_content(
    island: str,
    section: str,
    *,
    limit: int = 50,
    featured_only: bool = False,
) -> dict[str, Any]:

    normalized_island = normalize_island(
        island
    )

    if normalized_island is None:
        return {
            "island": island,
            "section": section,
            "available": False,
            "reason": "invalid_island",
            "items": [],
        }

    if section not in VALID_SECTIONS:
        return {
            "island": normalized_island,
            "section": section,
            "available": False,
            "reason": "invalid_section",
            "items": [],
        }

    path = _content_file(
        normalized_island,
        section,
    )

    if not path.exists():
        return {
            "island": normalized_island,
            "section": section,
            "available": False,
            "reason": "content_not_created_yet",
            "items": [],
        }

    items = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if featured_only:
        items = [
            item
            for item in items
            if item.get("featured") is True
        ]

    items.sort(
        key=lambda item: (
            item.get("order", 9999),
            item.get("name")
            or item.get("title")
            or "",
        )
    )

    items = items[:limit]

    return {
        "island": normalized_island,
        "section": section,
        "available": True,
        "count": len(items),
        "items": items,
    }


def get_content_item(
    island: str,
    section: str,
    slug: str,
) -> dict[str, Any] | None:

    data = get_content(
        island=island,
        section=section,
        limit=1000,
    )

    for item in data["items"]:

        if item.get("slug") == slug:
            return item

    return None