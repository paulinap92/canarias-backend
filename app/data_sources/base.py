from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .store import read_json, update_source_state, utc_now, write_json_atomic

logger = logging.getLogger("uvicorn.error")


class DataSource(ABC):
    allow_empty: bool = False
    # Persistence semantics are explicit so the temporary JSON layer mirrors
    # the future SQL behaviour: Live replaces current snapshots, curated
    # catalogs upsert, News appends/deduplicates.
    write_strategy: str = "replace"

    def __init__(self, section: str, resource: str) -> None:
        self.section = section
        self.resource = resource

    def key(self, **params: Any) -> str:
        island = params.get("island")
        month = params.get("month")
        suffix = ":".join(str(x) for x in (island, month) if x)
        return f"{self.section}:{self.resource}" + (f":{suffix}" if suffix else "")

    @abstractmethod
    def path(self, **params: Any) -> Path:
        raise NotImplementedError

    @abstractmethod
    def empty_payload(self, **params: Any) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def fetch(self, **params: Any) -> Any:
        raise NotImplementedError

    def count(self, payload: Any) -> int | None:
        if isinstance(payload, list):
            return len(payload)
        if isinstance(payload, dict):
            for key in ("features", "items", "data", "points"):
                value = payload.get(key)
                if isinstance(value, list):
                    return len(value)
        return None

    def decorate(self, payload: Any, *, status: str = "ok") -> Any:
        if isinstance(payload, dict):
            result = dict(payload)
            result["status"] = status
            result["updated_at"] = utc_now()
            return result
        return payload

    def merge_payload(
        self,
        previous: Any,
        fetched: Any,
        **params: Any,
    ) -> Any:
        """Return the payload that should be persisted after refresh.

        Live/current-state sources keep the default replace behaviour.
        Append/upsert sources (News, Calendar, later curated Explore) override
        this hook so a refresh cannot silently erase already stored records.
        """
        return fetched

    def is_valid(self, payload: Any) -> bool:
        if payload is None:
            return False
        count = self.count(payload)
        if count == 0 and not self.allow_empty:
            return False
        return True

    def read(self, **params: Any) -> Any:
        path = self.path(**params)
        payload = read_json(path, self.empty_payload(**params)) if path.exists() else self.empty_payload(**params)
        logger.info(
            "[DATA GET] %s status=%s count=%s file=%s",
            self.key(**params),
            payload.get("status") if isinstance(payload, dict) else "ok",
            self.count(payload),
            path,
        )
        return payload

    async def refresh(self, **params: Any) -> Any:
        path = self.path(**params)
        previous = read_json(path, self.empty_payload(**params)) if path.exists() else self.empty_payload(**params)
        key = self.key(**params)

        logger.info("[DATA REFRESH START] %s -> %s", key, path)
        try:
            fetched = await self.fetch(**params)
            if not self.is_valid(fetched):
                raise ValueError("refreshed payload is empty or invalid")

            merged = self.merge_payload(previous, fetched, **params)
            fresh = self.decorate(merged, status="ok")
            if not self.is_valid(fresh):
                raise ValueError("merged payload is empty or invalid")

            write_json_atomic(path, fresh)
            count = self.count(fresh)
            update_source_state(key, success=True, count=count)
            stats = fresh.get("refresh_stats") if isinstance(fresh, dict) else None
            logger.info(
                "[DATA REFRESH OK] %s strategy=%s count=%s updated_at=%s stats=%s",
                key,
                self.write_strategy,
                count,
                fresh.get("updated_at") if isinstance(fresh, dict) else None,
                stats,
            )
            return fresh
        except Exception as exc:
            update_source_state(key, success=False, error=str(exc))
            keeping_previous = path.exists()
            logger.exception(
                "[DATA REFRESH FAIL] %s keeping_previous=%s error=%s",
                key,
                keeping_previous,
                exc,
            )

            if keeping_previous:
                if isinstance(previous, dict):
                    stale = dict(previous)
                    stale["status"] = "stale"
                    stale["refresh_error"] = str(exc)
                    return stale
                return previous

            empty = self.empty_payload(**params)
            if isinstance(empty, dict):
                empty = dict(empty)
                empty["status"] = "error"
                empty["refresh_error"] = str(exc)
            return empty


class IslandGeoJSONSource(DataSource):
    def path(self, **params: Any) -> Path:
        from .store import DATA_ROOT
        island = str(params.get("island") or "canarias")
        return DATA_ROOT / self.section / self.resource / f"{island}.json"

    def empty_payload(self, **params: Any) -> dict[str, Any]:
        return {
            "type": "FeatureCollection",
            "features": [],
            "available": False,
            "status": "not_initialized",
            "updated_at": None,
        }
