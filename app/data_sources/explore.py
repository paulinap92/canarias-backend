from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.services.beaches import fetch_beaches
from app.services.flora import fetch_flora
from app.services.places import fetch_places
from app.services.natural_pools import fetch_natural_pools
from app.services.trails import fetch_trails
from app.services.wildlife import fetch_wildlife
from app.services.explore_collections import (
    fetch_official_directory,
    fetch_terrain_features,
)
from app.utils.islands import filter_feature_collection_by_island, normalize_island

from .base import IslandGeoJSONSource
from .curation_v2 import curate_explore, feature_key
from .registry import data_source
from .store import DATA_ROOT, read_json, update_source_state, utc_now, write_json_atomic

logger = logging.getLogger("uvicorn.error")


def merge_feature_collections(previous: dict[str, Any], fetched: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
    """Upsert RAW candidates without deleting records missing from one refresh.

    Fresh source geometry/properties win for the same stable id. Candidates that
    temporarily disappear remain available for audit/curation until an explicit
    cleanup rule removes them.
    """
    previous_features = [f for f in previous.get("features", []) if isinstance(f, dict)]
    fetched_features = [f for f in fetched.get("features", []) if isinstance(f, dict)]

    merged: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for feature in previous_features:
        key = feature_key(feature)
        if not key or key in merged:
            continue
        merged[key] = dict(feature)
        order.append(key)

    added = 0
    updated = 0
    unchanged = 0
    for feature in fetched_features:
        key = feature_key(feature)
        if not key:
            continue
        old = merged.get(key)
        if old is None:
            added += 1
            merged[key] = dict(feature)
            order.append(key)
            continue

        old_props = dict(old.get("properties") or {})
        new_props = dict(feature.get("properties") or {})
        combined = {**old, **feature, "properties": {**old_props, **new_props}}
        if combined != old:
            updated += 1
        else:
            unchanged += 1
        merged[key] = combined

    result = {
        **previous,
        **fetched,
        "type": "FeatureCollection",
        "features": [merged[key] for key in order],
        "available": bool(order),
    }
    stats = {
        "previous": len(previous_features),
        "fetched": len(fetched_features),
        "added": added,
        "updated": updated,
        "unchanged": unchanged,
        "kept_missing_from_refresh": max(0, len(previous_features) - updated - unchanged),
        "stored_raw": len(order),
    }
    result["refresh_stats"] = stats
    return result, stats


class CuratedExploreSource(IslandGeoJSONSource):
    write_strategy = "merge"

    """Explore source with a hard RAW -> CURATION -> PUBLISHED boundary.

    GET never exposes raw external imports. POST refreshes candidates into
    data/raw/explore/... and then publishes only the curated/quality-gated view
    into data/explore/....
    """

    def raw_path(self, **params: Any) -> Path:
        island = normalize_island(params.get("island")) or "canarias"
        return DATA_ROOT / "raw" / "explore" / self.resource / f"{island}.json"

    def _curated_read(self, payload: dict[str, Any], **params: Any) -> dict[str, Any]:
        island = normalize_island(params.get("island"))
        return curate_explore(self.resource, payload, island=island, previous=payload)

    def read(self, **params: Any) -> Any:
        path = self.path(**params)
        payload = read_json(path, self.empty_payload(**params)) if path.exists() else self.empty_payload(**params)

        curated = self._curated_read(payload, **params)
        curated.setdefault("status", payload.get("status", "ok") if isinstance(payload, dict) else "ok")
        curated.setdefault("updated_at", payload.get("updated_at") if isinstance(payload, dict) else None)
        migrated = not bool(isinstance(payload, dict) and payload.get("curation"))

        logger.info(
            "[DATA GET] %s published=%s stored=%s migrated_legacy=%s file=%s",
            self.key(**params),
            self.count(curated),
            self.count(payload),
            migrated,
            path,
        )
        return curated

    async def refresh(self, **params: Any) -> Any:
        published_path = self.path(**params)
        raw_path = self.raw_path(**params)
        previous = read_json(published_path, self.empty_payload(**params)) if published_path.exists() else self.empty_payload(**params)
        key = self.key(**params)
        island = normalize_island(params.get("island"))

        logger.info("[DATA REFRESH START] %s raw=%s published=%s", key, raw_path, published_path)
        try:
            fetched = await self.fetch(**params)
            if not self.is_valid(fetched):
                raise ValueError("refreshed raw payload is empty or invalid")

            previous_raw = (
                read_json(raw_path, self.empty_payload(**params))
                if raw_path.exists()
                else self.empty_payload(**params)
            )
            raw_snapshot, raw_stats = merge_feature_collections(previous_raw, fetched)
            raw_snapshot["status"] = "raw"
            raw_snapshot["updated_at"] = utc_now()
            write_json_atomic(raw_path, raw_snapshot)

            curated = curate_explore(self.resource, raw_snapshot, island=island, previous=previous)
            curated["refresh_stats"] = {
                **raw_stats,
                "published": self.count(curated) or 0,
            }
            fresh = self.decorate(curated, status="ok")
            if (
                not self.allow_empty
                and self.resource not in {"fauna", "flora"}
                and not self.is_valid(fresh)
            ):
                raise ValueError("curation produced no publishable records")

            write_json_atomic(published_path, fresh)
            count = self.count(fresh)
            update_source_state(key, success=True, count=count)
            logger.info(
                "[DATA REFRESH OK] %s strategy=%s fetched=%s raw_stored=%s published=%s updated_at=%s",
                key,
                self.write_strategy,
                self.count(fetched),
                raw_stats.get("stored_raw"),
                count,
                fresh.get("updated_at"),
            )
            return fresh
        except Exception as exc:
            update_source_state(key, success=False, error=str(exc))
            logger.exception("[DATA REFRESH FAIL] %s keeping_previous=%s error=%s", key, published_path.exists(), exc)
            return self.read(**params)


@data_source("explore", "places")
class PlacesSource(CuratedExploreSource):
    async def fetch(self, **params: Any) -> dict[str, Any]:
        island = params.get("island")
        data = await fetch_places(limit=500, island=island)
        result = filter_feature_collection_by_island(data, island)
        result["available"] = True
        result["source"] = data.get("source", "overpass")
        return result


@data_source("explore", "beaches")
class BeachesSource(CuratedExploreSource):
    async def fetch(self, **params: Any) -> dict[str, Any]:
        island = params.get("island")
        data = await fetch_beaches(limit=500, island=island)
        result = filter_feature_collection_by_island(data, island)
        result["available"] = True
        result["source"] = data.get("source", "overpass")
        return result


@data_source("explore", "routes")
class RoutesSource(CuratedExploreSource):
    async def fetch(self, **params: Any) -> dict[str, Any]:
        island = params.get("island")
        data = await fetch_trails(limit=500, island=island)
        result = filter_feature_collection_by_island(data, island) if island else data
        result["available"] = True
        return result


@data_source("explore", "fauna")
class FaunaSource(CuratedExploreSource):
    async def fetch(self, **params: Any) -> dict[str, Any]:
        island = params.get("island")
        data = await fetch_wildlife(limit=500, island=island)
        result = filter_feature_collection_by_island(data, island)
        result["available"] = True
        result["source"] = "GBIF candidates"
        return result


@data_source("explore", "flora")
class FloraSource(CuratedExploreSource):
    async def fetch(self, **params: Any) -> dict[str, Any]:
        island = params.get("island")
        data = await fetch_flora(limit=300, island=island)
        result = filter_feature_collection_by_island(data, island)
        result["available"] = True
        result["source"] = "GBIF candidates"
        return result



@data_source("explore", "natural-pools")
class NaturalPoolsSource(CuratedExploreSource):
    async def fetch(self, **params: Any) -> dict[str, Any]:
        island = params.get("island")
        data = await fetch_natural_pools(limit=200, island=island)
        result = filter_feature_collection_by_island(data, island)
        result["available"] = True
        result["source"] = data.get("source", "Hola Islas Canarias")
        result["source_url"] = data.get("source_url")
        result["official_discovered"] = data.get("official_discovered", 0)
        result["mapped_count"] = data.get("mapped_count", 0)
        result["unmapped_count"] = data.get("unmapped_count", 0)
        result["unmapped_items"] = data.get("unmapped_items", [])
        return result



class _OfficialDirectorySource(CuratedExploreSource):
    allow_empty = True

    async def fetch(self, **params: Any) -> dict[str, Any]:
        island = params.get("island")
        data = await fetch_official_directory(
            self.resource,
            island=island,
            limit=200,
        )
        result = filter_feature_collection_by_island(data, island)
        result["available"] = True
        for key in (
            "source",
            "source_url",
            "official_discovered",
            "mapped_count",
            "unmapped_count",
            "unmapped_items",
        ):
            if key in data:
                result[key] = data[key]
        return result


@data_source("explore", "marinas")
class MarinasSource(_OfficialDirectorySource):
    pass


@data_source("explore", "food-producers")
class FoodProducersSource(_OfficialDirectorySource):
    pass


@data_source("explore", "markets")
class MarketsSource(_OfficialDirectorySource):
    pass


@data_source("explore", "stargazing")
class StargazingSource(_OfficialDirectorySource):
    pass


@data_source("explore", "surf-spots")
class SurfSpotsSource(_OfficialDirectorySource):
    pass


@data_source("explore", "natural-spaces")
class NaturalSpacesSource(_OfficialDirectorySource):
    pass


@data_source("explore", "museums-visits")
class MuseumsVisitsSource(_OfficialDirectorySource):
    pass


@data_source("explore", "leisure-centers")
class LeisureCentersSource(_OfficialDirectorySource):
    pass


@data_source("explore", "diving-spots")
class DivingSpotsSource(_OfficialDirectorySource):
    pass


class _TerrainPointSource(CuratedExploreSource):
    allow_empty = True

    async def fetch(self, **params: Any) -> dict[str, Any]:
        island = params.get("island")
        data = await fetch_terrain_features(
            self.resource,
            island=island,
            limit=50,
        )
        result = filter_feature_collection_by_island(data, island)
        result["available"] = True
        for key in ("source", "reference_source", "reference_url"):
            if key in data:
                result[key] = data[key]
        return result


@data_source("explore", "volcanoes")
class VolcanoesSource(_TerrainPointSource):
    pass


@data_source("explore", "summits")
class SummitsSource(_TerrainPointSource):
    pass
