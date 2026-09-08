from __future__ import annotations

from typing import Any

from app.services.content import CONTENT_ROOT, get_content


def _supported_islands() -> list[str]:
    if not CONTENT_ROOT.exists():
        return []

    return sorted(
        path.name
        for path in CONTENT_ROOT.iterdir()
        if path.is_dir()
        and (path / "explore.json").exists()
    )


def get_explore_items(
    island: str,
    *,
    limit: int = 6,
    category: str | None = None,
) -> dict[str, Any]:
    data = get_content(
        island=island,
        section="explore",
        limit=100,
    )

    supported_islands = _supported_islands()

    if not data["available"]:
        return {
            "island": data["island"],
            "available": False,
            "supported_islands": supported_islands,
            "count": 0,
            "items": [],
        }

    items = data["items"]

    if category:
        items = [
            item
            for item in items
            if item.get("category") == category
        ]

    items = items[:limit]

    return {
        "island": data["island"],
        "available": True,
        "supported_islands": supported_islands,
        "count": len(items),
        "items": items,
    }
