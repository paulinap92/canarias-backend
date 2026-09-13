from __future__ import annotations

from typing import Any

from app.services.alerts import fetch_active_alerts
from app.services.open_meteo_live import (
    fetch_air_quality_points,
    fetch_marine_points,
    fetch_tide_points,
    fetch_weather_points,
)
from app.services.seismic import IGN_URL, fetch_canary_earthquakes
from app.services.volcanic import fetch_volcanic_activity
from app.services.webcams import fetch_tenerife_webcams
from app.utils.islands import filter_feature_collection_by_island, normalize_island

from .base import DataSource
from .registry import data_source
from .store import DATA_ROOT, read_json


class IslandSnapshotSource(DataSource):
    def path(self, **params: Any):
        island = normalize_island(params.get("island")) or "canarias"
        return DATA_ROOT / "live" / self.resource / f"{island}.json"


@data_source("live", "weather")
class WeatherSource(IslandSnapshotSource):
    def empty_payload(self, **params: Any):
        island = normalize_island(params.get("island"))
        return {
            "source": "Open-Meteo",
            "source_type": "model",
            "island": island,
            "points_count": 0,
            "points": [],
            "available": False,
            "status": "not_initialized",
            "updated_at": None,
        }

    async def fetch(self, **params: Any):
        result = await fetch_weather_points(params.get("island"))
        result["available"] = True
        return result


@data_source("live", "air-quality")
class AirQualitySource(IslandSnapshotSource):
    def empty_payload(self, **params: Any):
        island = normalize_island(params.get("island"))
        return {
            "source": "Open-Meteo / CAMS",
            "source_type": "model",
            "island": island,
            "points_count": 0,
            "points": [],
            "available": False,
            "status": "not_initialized",
            "updated_at": None,
        }

    async def fetch(self, **params: Any):
        result = await fetch_air_quality_points(params.get("island"))
        result["available"] = True
        return result


@data_source("live", "tides")
class TidesSource(IslandSnapshotSource):
    def empty_payload(self, **params: Any):
        island = normalize_island(params.get("island"))
        hours = int(params.get("hours") or 48)
        return {
            "source": "Open-Meteo Marine",
            "source_type": "model",
            "island": island,
            "hours": hours,
            "points_count": 0,
            "points": [],
            "available": False,
            "status": "not_initialized",
            "updated_at": None,
        }

    async def fetch(self, **params: Any):
        result = await fetch_tide_points(params.get("island"), int(params.get("hours") or 48))
        result["available"] = True
        return result


@data_source("live", "alerts")
class AlertsSource(IslandSnapshotSource):
    allow_empty = True

    def empty_payload(self, **params: Any):
        island = normalize_island(params.get("island"))
        return {
            "island": island,
            "items": [],
            "available": False,
            "status": "not_initialized",
            "updated_at": None,
        }

    async def fetch(self, **params: Any):
        return {
            "island": normalize_island(params.get("island")),
            "items": await fetch_active_alerts(params.get("island")),
            "available": True,
        }


@data_source("live", "seismic")
class SeismicSource(IslandSnapshotSource):
    allow_empty = True

    def empty_payload(self, **params: Any):
        return {
            "type": "FeatureCollection",
            "features": [],
            "available": False,
            "status": "not_initialized",
            "updated_at": None,
            "window_days": 10,
            "source": "IGN",
            "source_url": IGN_URL,
        }

    def read(self, **params: Any):
        payload = super().read(**params)
        if isinstance(payload, dict):
            payload.setdefault("window_days", 10)
            payload.setdefault("source", "IGN")
            payload.setdefault("source_url", IGN_URL)
        return payload

    async def fetch(self, **params: Any):
        island = params.get("island")
        data = filter_feature_collection_by_island(await fetch_canary_earthquakes(), island)
        data["available"] = True
        data["window_days"] = 10
        data["source"] = "IGN"
        data["source_url"] = IGN_URL
        return data


@data_source("live", "marine")
class MarineSource(IslandSnapshotSource):
    def empty_payload(self, **params: Any):
        island = normalize_island(params.get("island"))
        return {
            "source": "Open-Meteo Marine",
            "source_type": "model",
            "island": island,
            "points_count": 0,
            "points": [],
            "available": False,
            "status": "not_initialized",
            "updated_at": None,
        }

    async def fetch(self, **params: Any):
        result = await fetch_marine_points(params.get("island"))
        result["available"] = True
        return result


@data_source("live", "webcams")
class WebcamsSource(IslandSnapshotSource):
    def empty_payload(self, **params: Any):
        island = normalize_island(params.get("island")) or "tenerife"
        return {
            "island": island,
            "items": [],
            "available": False,
            "status": "not_initialized",
            "updated_at": None,
        }

    async def fetch(self, **params: Any):
        island = normalize_island(params.get("island")) or "tenerife"
        if island != "tenerife":
            raise RuntimeError("Webcam importer currently supports Tenerife only")
        return {
            "island": island,
            "items": await fetch_tenerife_webcams(100),
            "available": True,
        }


@data_source("live", "volcanic")
class VolcanicSource(IslandSnapshotSource):
    allow_empty = True

    def path(self, **params: Any):
        # IGN volcanic reports are archipelago-wide. Keep one canonical snapshot
        # so a refresh from Tenerife/Gran Canaria updates the same data read by UI.
        return DATA_ROOT / "live" / self.resource / "canarias.json"

    def empty_payload(self, **params: Any):
        return {
            "island": "canarias",
            "reports": [],
            "reports_count": 0,
            "available": False,
            "status": "not_initialized",
            "updated_at": None,
            "source": "IGN",
        }

    def read(self, **params: Any):
        canonical = self.path(**params)
        if canonical.exists():
            return super().read(**params)

        # Migration bridge: older local builds wrote one volcanic snapshot per
        # island. Reuse any meaningful old snapshot until the first global
        # refresh creates canarias.json.
        folder = DATA_ROOT / "live" / self.resource
        for candidate in sorted(folder.glob("*.json")) if folder.exists() else []:
            payload = read_json(candidate, {})
            if not isinstance(payload, dict):
                continue
            if payload.get("title") or payload.get("reports"):
                migrated = dict(payload)
                if not migrated.get("reports") and migrated.get("title"):
                    migrated["reports"] = [{
                        key: migrated.get(key)
                        for key in (
                            "period", "title", "summary", "earthquakes_total",
                            "max_magnitude", "significant_deformation_detected",
                            "source", "source_url"
                        )
                    }]
                migrated["reports_count"] = len(migrated.get("reports") or [])
                migrated["island"] = "canarias"
                return migrated

        return super().read(**params)

    async def fetch(self, **params: Any):
        result = await fetch_volcanic_activity()
        if isinstance(result, dict):
            result.setdefault("available", True)
            result.setdefault("island", "canarias")
        return result
