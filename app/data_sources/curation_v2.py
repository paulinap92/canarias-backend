from __future__ import annotations

import re
from typing import Any

from .curation import curate_explore as _legacy_curate_explore
from .curation import feature_key

_GENERIC_ROUTE_RE = re.compile(
    r"^(?:tramo|etapa|segmento|seccion|sección|stage|section)\s*[-_. ]*\d+[a-z]?$",
    re.IGNORECASE,
)


def _valid_point(feature: dict[str, Any]) -> bool:
    geometry = feature.get("geometry") or {}
    coords = geometry.get("coordinates") or []
    return (
        geometry.get("type") == "Point"
        and isinstance(coords, list)
        and len(coords) >= 2
        and isinstance(coords[0], (int, float))
        and isinstance(coords[1], (int, float))
        and -180 <= coords[0] <= 180
        and -90 <= coords[1] <= 90
    )


def _route_name(properties: dict[str, Any]) -> str:
    return str(properties.get("name") or "").strip()


def _useful_route(feature: dict[str, Any]) -> bool:
    geometry = feature.get("geometry") or {}
    if geometry.get("type") not in {"LineString", "MultiLineString"}:
        return False
    properties = feature.get("properties") or {}
    name = _route_name(properties)
    if not name or _GENERIC_ROUTE_RE.fullmatch(name):
        return False
    # Keep named OSM route relations and genuinely descriptive trail records.
    return bool(
        properties.get("ref")
        or properties.get("network")
        or properties.get("route_id")
        or properties.get("osm_id")
        or len(name) >= 8
    )


def _curate_all_routes(
    raw: dict[str, Any],
    *,
    island: str | None,
    previous: dict[str, Any] | None,
) -> dict[str, Any]:
    previous_by_key = {
        feature_key(item): item
        for item in (previous or {}).get("features", [])
        if isinstance(item, dict)
    }
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for feature in raw.get("features", []):
        if not isinstance(feature, dict) or not _useful_route(feature):
            continue
        key = feature_key(feature)
        if not key or key in seen:
            continue
        seen.add(key)
        item = dict(feature)
        props = dict(item.get("properties") or {})
        old_props = (previous_by_key.get(key) or {}).get("properties") or {}
        for field in (
            "description", "short_description", "featured", "verified",
            "editorial_tags", "why_go", "image", "image_url",
            "image_credit", "image_source_url", "access_notes", "for_whom",
            "priority", "name", "category", "difficulty", "duration",
            "hidden", "editorial_override", "image_license",
            "image_license_url", "image_origin",
        ):
            if old_props.get(field) not in (None, "", [], {}):
                props[field] = old_props[field]
        props["status"] = "published"
        item["properties"] = props
        if not props.get("hidden"):
            selected.append(item)

    selected.sort(
        key=lambda item: (
            0 if (item.get("properties") or {}).get("featured") else 1,
            int((item.get("properties") or {}).get("priority") or 9999),
            _route_name(item.get("properties") or {}).casefold(),
        )
    )
    return {
        "type": "FeatureCollection",
        "features": selected,
        "available": bool(selected),
        "island": island,
        "source": raw.get("source"),
        "raw_count": len(raw.get("features") or []),
        "published_count": len(selected),
        "curation": "quality-gate:routes-v2-all-complete-routes",
    }


def _curate_biodiversity(
    resource: str,
    raw: dict[str, Any],
    *,
    island: str | None,
    previous: dict[str, Any] | None,
) -> dict[str, Any]:
    base = _legacy_curate_explore(resource, raw, island=island, previous=previous)
    selected = [item for item in base.get("features", []) if isinstance(item, dict)]
    seen = {feature_key(item) for item in selected}

    # Curated species stay first. GBIF occurrence points extend the map instead
    # of replacing editorial content. Keep a bounded catalogue to avoid noise.
    max_items = 80 if resource == "fauna" else 60
    for feature in raw.get("features", []):
        if len(selected) >= max_items:
            break
        if not isinstance(feature, dict) or not _valid_point(feature):
            continue
        props = dict(feature.get("properties") or {})
        scientific_name = str(props.get("scientific_name") or props.get("species") or "").strip()
        if not scientific_name:
            continue
        if resource == "fauna" and str(props.get("kingdom") or "").casefold() == "plantae":
            continue
        key = feature_key(feature)
        if not key or key in seen:
            continue
        seen.add(key)
        props.setdefault("name", scientific_name)
        props.setdefault("source", "GBIF")
        props["status"] = "published"
        selected.append({**feature, "properties": props})

    return {
        **base,
        "features": selected,
        "available": bool(selected),
        "raw_count": len(raw.get("features") or []),
        "published_count": len(selected),
        "curation": f"curated-plus-gbif:{resource}-v2",
    }


def curate_explore(
    resource: str,
    raw: dict[str, Any],
    *,
    island: str | None,
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if resource == "routes":
        return _curate_all_routes(raw, island=island, previous=previous)
    if resource in {"fauna", "flora"}:
        return _curate_biodiversity(resource, raw, island=island, previous=previous)
    return _legacy_curate_explore(resource, raw, island=island, previous=previous)


__all__ = ["curate_explore", "feature_key"]
