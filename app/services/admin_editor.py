from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

import app.data_sources.bootstrap  # noqa: F401
from app.data_sources import get_data_source
from app.data_sources.curation import feature_key
from app.data_sources.store import DATA_ROOT, read_json, write_json_atomic
from app.services.content_editor import content_root
from app.services.events import current_month
from app.utils.islands import normalize_island

EXPLORE_RESOURCES = ("places", "beaches", "natural-pools", "routes", "fauna", "flora")
LIVE_RESOURCES = ("weather", "air-quality", "marine", "tides", "alerts", "seismic", "volcanic", "webcams")


class AdminEditorError(ValueError):
    pass


def admin_data_root() -> Path:
    override = os.environ.get("CANARIAS_EDITOR_DATA_ROOT", "").strip()
    return Path(override) if override else DATA_ROOT


def _island(value: str) -> str:
    normalized = normalize_island(value)
    if normalized is None:
        raise AdminEditorError(f"Unknown island: {value}")
    return normalized


def _key(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


def _slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return value or "item"


def _load_object(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    payload = read_json(path, default) if path.exists() else default
    if not isinstance(payload, dict):
        raise AdminEditorError(f"Expected JSON object in {path}")
    return dict(payload)


def _explore_path(island: str, resource: str, *, curated: bool = False) -> Path:
    if resource not in EXPLORE_RESOURCES:
        raise AdminEditorError(f"Unknown Explore resource: {resource}")
    base = admin_data_root() / ("curated/explore" if curated else "explore")
    return base / resource / f"{_island(island)}.json"


def _feature_identity(feature: dict[str, Any]) -> str:
    return feature_key(feature)


def _flatten_feature(feature: dict[str, Any]) -> dict[str, Any]:
    props = dict(feature.get("properties") or {})
    geometry = dict(feature.get("geometry") or {})
    identity = _feature_identity(feature)
    result = {**props, "_editor_key": _key(identity), "_identity": identity, "_geometry_type": geometry.get("type")}
    coords = geometry.get("coordinates")
    if geometry.get("type") == "Point" and isinstance(coords, list) and len(coords) >= 2:
        result["longitude"], result["latitude"] = coords[0], coords[1]
    return result


def read_explore(island: str, resource: str) -> dict[str, Any]:
    payload = _load_object(_explore_path(island, resource), {"type": "FeatureCollection", "features": []})
    items = [_flatten_feature(f) for f in payload.get("features", []) if isinstance(f, dict)]
    return {
        "island": _island(island),
        "resource": resource,
        "count": len(items),
        "items": items,
        "can_create": resource != "routes",
        "delete_mode": "hide",
    }


def _find_feature(features: list[dict[str, Any]], editor_key: str) -> tuple[int, dict[str, Any]]:
    for index, feature in enumerate(features):
        if isinstance(feature, dict) and _key(_feature_identity(feature)) == editor_key:
            return index, feature
    raise AdminEditorError("Explore item not found")


def update_explore(island: str, resource: str, editor_key: str, item: dict[str, Any]) -> dict[str, Any]:
    path = _explore_path(island, resource)
    payload = _load_object(path, {"type": "FeatureCollection", "features": []})
    features = list(payload.get("features") or [])
    index, feature = _find_feature(features, editor_key)

    props = dict(feature.get("properties") or {})
    protected_identity = {"id", "route_id", "osm_id", "osm_type", "gbif_id"}
    clean = {
        k: v for k, v in item.items()
        if not k.startswith("_") and k not in {"latitude", "longitude"} and k not in protected_identity
    }
    props.update(clean)
    props["editorial_override"] = True

    geometry = dict(feature.get("geometry") or {})
    if geometry.get("type") == "Point":
        coords = list(geometry.get("coordinates") or [])
        if len(coords) >= 2:
            if item.get("longitude") not in (None, ""):
                coords[0] = float(item["longitude"])
            if item.get("latitude") not in (None, ""):
                coords[1] = float(item["latitude"])
            geometry["coordinates"] = coords

    features[index] = {**feature, "geometry": geometry, "properties": props}
    payload["features"] = features
    write_json_atomic(path, payload)
    return _flatten_feature(features[index])


def create_explore(island: str, resource: str, item: dict[str, Any]) -> dict[str, Any]:
    if resource == "routes":
        raise AdminEditorError("Routes need real line geometry and cannot be created here")

    normalized = _island(island)
    name = str(item.get("name") or item.get("common_name") or "").strip()
    if not name:
        raise AdminEditorError("name is required")
    if item.get("latitude") in (None, "") or item.get("longitude") in (None, ""):
        raise AdminEditorError("latitude and longitude are required")

    identifier = f"editor-{resource}-{normalized}-{_slug(str(item.get('slug') or name))}"
    props = {
        k: v for k, v in item.items()
        if not k.startswith("_") and k not in {"latitude", "longitude", "slug"}
    }
    props.update({
        "id": identifier,
        "name": name,
        "island": normalized,
        "source": "canarias-cerca-editorial",
        "cc_curated": True,
        "editorial_override": True,
    })
    feature = {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [float(item["longitude"]), float(item["latitude"])]},
        "properties": props,
    }

    for path in (_explore_path(normalized, resource), _explore_path(normalized, resource, curated=True)):
        payload = _load_object(path, {"type": "FeatureCollection", "source": "Canarias Cerca editorial catalog", "features": []})
        features = list(payload.get("features") or [])
        if not any(isinstance(f, dict) and _feature_identity(f) == _feature_identity(feature) for f in features):
            features.append(feature)
        payload["features"] = features
        payload["available"] = True
        write_json_atomic(path, payload)

    return _flatten_feature(feature)


def hide_explore(island: str, resource: str, editor_key: str) -> dict[str, Any]:
    data = read_explore(island, resource)
    item = next((x for x in data["items"] if x.get("_editor_key") == editor_key), None)
    if item is None:
        raise AdminEditorError("Explore item not found")
    item["hidden"] = True
    return update_explore(island, resource, editor_key, item)


def _calendar_path(island: str, month: str) -> Path:
    if not re.fullmatch(r"20\d{2}-\d{2}", month):
        raise AdminEditorError("month must use YYYY-MM")
    return admin_data_root() / "calendar" / _island(island) / f"{month}.json"


def _record_identity(item: dict[str, Any]) -> str:
    return str(item.get("id") or item.get("url") or item.get("slug") or item.get("title") or "").strip()


def _decorate(item: dict[str, Any]) -> dict[str, Any]:
    return {**item, "_editor_key": _key(_record_identity(item))}


def read_events(island: str, month: str | None = None) -> dict[str, Any]:
    month = month or current_month()
    payload = _load_object(_calendar_path(island, month), {"island": _island(island), "month": month, "items": []})
    items = [_decorate(dict(x)) for x in payload.get("items", []) if isinstance(x, dict)]
    return {**payload, "items": items, "count": len(items)}


def _find_record(items: list[dict[str, Any]], editor_key: str) -> tuple[int, dict[str, Any]]:
    for index, item in enumerate(items):
        if isinstance(item, dict) and _key(_record_identity(item)) == editor_key:
            return index, item
    raise AdminEditorError("Item not found")


def update_event(island: str, month: str, editor_key: str, item: dict[str, Any]) -> dict[str, Any]:
    path = _calendar_path(island, month)
    payload = _load_object(path, {"items": []})
    items = list(payload.get("items") or [])
    index, old = _find_record(items, editor_key)
    clean = {k: v for k, v in item.items() if not k.startswith("_") and k not in {"id", "url", "source", "source_id"}}
    saved = {**old, **clean, "editorial_override": True}
    items[index] = saved
    payload["items"] = items
    write_json_atomic(path, payload)
    return _decorate(saved)


def create_event(island: str, month: str, item: dict[str, Any]) -> dict[str, Any]:
    normalized = _island(island)
    title = str(item.get("title") or item.get("name") or "").strip()
    start_date = str(item.get("start_date") or "").strip()
    if not title or not start_date:
        raise AdminEditorError("title and start_date are required")
    if not start_date.startswith(month):
        raise AdminEditorError("start_date must belong to selected month")

    saved = {
        **{k: v for k, v in item.items() if not k.startswith("_")},
        "id": f"manual:{uuid4().hex}",
        "title": title,
        "island": normalized,
        "source": "Canarias Cerca editorial",
        "source_id": "canarias-cerca-editorial",
        "editorial_override": True,
        "hidden": False,
    }
    saved.setdefault("end_date", start_date)
    saved.setdefault("all_day", True)
    path = _calendar_path(normalized, month)
    payload = _load_object(path, {"island": normalized, "month": month, "items": []})
    items = list(payload.get("items") or [])
    items.append(saved)
    payload["items"] = items
    payload["available"] = True
    write_json_atomic(path, payload)
    return _decorate(saved)


def hide_event(island: str, month: str, editor_key: str) -> dict[str, Any]:
    data = read_events(island, month)
    item = next((x for x in data["items"] if x.get("_editor_key") == editor_key), None)
    if item is None:
        raise AdminEditorError("Event not found")
    item["hidden"] = True
    return update_event(island, month, editor_key, item)


def _news_path() -> Path:
    return admin_data_root() / "news" / "latest.json"


def read_news(island: str | None = None) -> dict[str, Any]:
    payload = _load_object(_news_path(), {"items": []})
    items = []
    for item in payload.get("items", []):
        if not isinstance(item, dict):
            continue
        if island and island != "canarias" and item.get("island") != island:
            continue
        items.append(_decorate(dict(item)))
    return {**payload, "items": items, "count": len(items)}


def update_news(editor_key: str, item: dict[str, Any]) -> dict[str, Any]:
    path = _news_path()
    payload = _load_object(path, {"items": []})
    items = list(payload.get("items") or [])
    index, old = _find_record(items, editor_key)
    clean = {k: v for k, v in item.items() if not k.startswith("_") and k not in {"id", "url", "source"}}
    saved = {**old, **clean, "editorial_override": True}
    items[index] = saved
    payload["items"] = items
    write_json_atomic(path, payload)
    return _decorate(saved)


def hide_news(editor_key: str) -> dict[str, Any]:
    data = read_news()
    item = next((x for x in data["items"] if x.get("_editor_key") == editor_key), None)
    if item is None:
        raise AdminEditorError("News item not found")
    item["hidden"] = True
    return update_news(editor_key, item)


def read_live(island: str, resource: str) -> dict[str, Any]:
    if resource not in LIVE_RESOURCES:
        raise AdminEditorError(f"Unknown Live resource: {resource}")
    params: dict[str, Any] = {"island": _island(island)}
    if resource == "tides":
        params["hours"] = 48
    return {"island": params["island"], "resource": resource, "read_only": True, "payload": get_data_source("live", resource).read(**params)}


def media_inventory(island: str) -> dict[str, Any]:
    normalized = _island(island)
    result: list[dict[str, Any]] = []

    folder = content_root() / normalized
    if folder.exists():
        for path in sorted(folder.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, list):
                continue
            for item in payload:
                if not isinstance(item, dict):
                    continue
                result.append({
                    "area": "guide", "resource": path.stem,
                    "key": item.get("slug") or item.get("id"),
                    "name": item.get("name") or item.get("title") or item.get("slug"),
                    "image_url": item.get("image_url"),
                    "image_credit": item.get("image_credit"),
                    "image_license": item.get("image_license"),
                    "image_origin": item.get("image_origin"),
                    "missing": not bool(item.get("image_url")),
                })

    for resource in ("places", "beaches", "natural-pools", "fauna", "flora"):
        payload = _load_object(_explore_path(normalized, resource), {"features": []})
        for feature in payload.get("features", []):
            if not isinstance(feature, dict):
                continue
            props = feature.get("properties") or {}
            result.append({
                "area": "explore", "resource": resource,
                "key": _key(_feature_identity(feature)),
                "name": props.get("name") or props.get("common_name") or props.get("id"),
                "image_url": props.get("image_url") or props.get("image"),
                "image_credit": props.get("image_credit"),
                "image_license": props.get("image_license"),
                "image_origin": props.get("image_origin"),
                "missing": not bool(props.get("image_url") or props.get("image")),
            })

    missing = sum(1 for item in result if item["missing"])
    return {
        "island": normalized,
        "count": len(result),
        "with_image": len(result) - missing,
        "missing": missing,
        "items": result,
        "read_only": True,
    }
