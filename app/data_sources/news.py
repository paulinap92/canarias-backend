from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.news import fetch_news_bundle

from .base import DataSource
from .registry import data_source
from .store import DATA_ROOT


def _news_key(item: dict[str, Any]) -> str:
    return str(item.get("url") or item.get("id") or item.get("title") or "").strip()


@data_source("news", "latest")
class NewsSource(DataSource):
    write_strategy = "append"
    def path(self, **params: Any) -> Path:
        return DATA_ROOT / "news" / "latest.json"

    def empty_payload(self, **params: Any) -> dict[str, Any]:
        return {
            "items": [],
            "available": False,
            "status": "not_initialized",
            "updated_at": None,
        }

    async def fetch(self, **params: Any) -> dict[str, Any]:
        return await fetch_news_bundle(int(params.get("refresh_limit") or 200))

    def merge_payload(
        self,
        previous: Any,
        fetched: Any,
        **params: Any,
    ) -> dict[str, Any]:
        previous_items = list(previous.get("items", [])) if isinstance(previous, dict) else []
        fetched_items = list(fetched.get("items", [])) if isinstance(fetched, dict) else []

        merged: dict[str, dict[str, Any]] = {}
        order: list[str] = []
        previous_by_key = {
            _news_key(item): item
            for item in previous_items
            if isinstance(item, dict) and _news_key(item)
        }
        added = 0
        updated = 0
        duplicates = 0

        # Fresh feed comes first. Existing records survive if the RSS window is
        # shorter than our local history. Fresh source fields win, while local
        # enrichment that is absent in the new item is preserved.
        for item in fetched_items:
            if not isinstance(item, dict):
                continue
            key = _news_key(item)
            if not key:
                continue
            old = previous_by_key.get(key)
            if old is None:
                added += 1
                merged[key] = dict(item)
            else:
                duplicates += 1
                combined = {**old, **item}
                if combined != old:
                    updated += 1
                merged[key] = combined
            if key not in order:
                order.append(key)

        for item in previous_items:
            if not isinstance(item, dict):
                continue
            key = _news_key(item)
            if not key:
                continue
            if key not in merged:
                merged[key] = dict(item)
            if key not in order:
                order.append(key)

        items = [merged[key] for key in order[:500]]
        return {
            **(previous if isinstance(previous, dict) else {}),
            **(fetched if isinstance(fetched, dict) else {}),
            "items": items,
            "available": True,
            "refresh_stats": {
                "fetched": len(fetched_items),
                "added": added,
                "updated": updated,
                "duplicates": duplicates,
                "stored": len(items),
            },
        }
