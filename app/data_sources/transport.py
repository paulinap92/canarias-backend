from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.transport import fetch_titsa_routes, fetch_titsa_stops

from .base import DataSource
from .registry import data_source
from .store import DATA_ROOT


@data_source("transport", "titsa-stops")
class TitsaStopsSource(DataSource):
    """Persisted TITSA stop snapshot.

    GETs read the saved JSON only. A manual POST refresh may download the
    current GTFS ZIP; a future scheduler can call the same refresh method.
    """

    write_strategy = "replace"

    def path(self, **params: Any) -> Path:
        return DATA_ROOT / "transport" / "titsa" / "stops.json"

    def empty_payload(self, **params: Any) -> dict[str, Any]:
        return {
            "type": "FeatureCollection",
            "features": [],
            "available": False,
            "status": "not_initialized",
            "updated_at": None,
            "source": "TITSA GTFS",
        }

    async def fetch(self, **params: Any) -> dict[str, Any]:
        payload = await fetch_titsa_stops(limit=int(params.get("limit") or 5000))
        return {
            **payload,
            "available": True,
            "source": "TITSA GTFS",
        }


@data_source("transport", "titsa-routes")
class TitsaRoutesSource(DataSource):
    write_strategy = "replace"

    def path(self, **params: Any) -> Path:
        return DATA_ROOT / "transport" / "titsa" / "routes.json"

    def empty_payload(self, **params: Any) -> dict[str, Any]:
        return {
            "items": [],
            "available": False,
            "status": "not_initialized",
            "updated_at": None,
            "source": "TITSA GTFS",
        }

    async def fetch(self, **params: Any) -> dict[str, Any]:
        items = await fetch_titsa_routes(limit=int(params.get("limit") or 1000))
        return {
            "items": items,
            "available": True,
            "source": "TITSA GTFS",
        }
