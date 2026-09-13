from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any, Callable

from .store import DATA_ROOT

PROTECTED_EDITORIAL_FIELDS = {
    "description",
    "short_description",
    "featured",
    "verified",
    "editorial_tags",
    "why_go",
    "image",
    "image_url",
    "image_credit",
    "image_source_url",
    "access_notes",
    "for_whom",
    "priority",
}


def _norm(value: Any) -> str:
    return " ".join(str(value or "").casefold().strip().split())


def _ascii_norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _norm(value))
    return "".join(ch for ch in text if not unicodedata.combining(ch))


FEATURED_BEACH_NAMES: dict[str, list[str]] = {
    "tenerife": ["las teresitas", "benijo", "el medano", "la tejita", "playa jardin", "el bollullo", "las vistas", "los cristianos", "abama"],
    "gran-canaria": ["las canteras", "maspalomas", "playa del ingles", "amadores", "puerto rico", "guigui", "mogan", "san agustin"],
    "lanzarote": ["famara", "papagayo", "playa dorada", "playa flamingo", "playa chica", "las cucharas", "el reducto", "caleton blanco"],
    "fuerteventura": ["cofete", "corralejo", "sotavento", "matorral", "la concha", "ajuy", "esquinzo", "gran tarajal"],
    "la-palma": ["puerto naos", "tazacorte", "los cancajos", "nogales", "echentive", "charco verde", "bajamar"],
    "la-gomera": ["valle gran rey", "playa de santiago", "san sebastian", "la caleta", "alojera", "playa del ingles", "vueltas"],
    "el-hierro": ["verodal", "timijiraque", "arenas blancas", "tacoron", "la restinga", "charco azul"],
    "la-graciosa": ["las conchas", "la francesa", "la cocina", "el salado", "la laja", "pedro barba"],
}


def _feature_key(feature: dict[str, Any]) -> str:
    p = feature.get("properties") or {}
    for candidate in (
        p.get("id"),
        p.get("route_id"),
        f"osm:{p.get('osm_type')}:{p.get('osm_id')}" if p.get("osm_id") else None,
        f"gbif:{p.get('gbif_id')}" if p.get("gbif_id") else None,
    ):
        if candidate:
            return str(candidate)
    return f"name:{_norm(p.get('name') or p.get('common_name') or p.get('species') or p.get('scientific_name'))}"



def feature_key(feature: dict[str, Any]) -> str:
    """Stable identity used by RAW upserts and published editorial merges."""
    return _feature_key(feature)

def _valid_point(feature: dict[str, Any]) -> bool:
    geometry = feature.get("geometry") or {}
    if geometry.get("type") != "Point":
        return True
    coords = geometry.get("coordinates") or []
    return (
        isinstance(coords, list)
        and len(coords) >= 2
        and isinstance(coords[0], (int, float))
        and isinstance(coords[1], (int, float))
        and -180 <= coords[0] <= 180
        and -90 <= coords[1] <= 90
    )


def _read_curated_catalog(resource: str, island: str | None) -> dict[str, Any] | None:
    if not island:
        return None
    path = DATA_ROOT / "curated" / "explore" / resource / f"{island}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
        return None
    return data


def _merge_editorial_fields(
    selected: list[dict[str, Any]],
    previous: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    previous_features = (previous or {}).get("features") or []
    previous_by_key = {
        _feature_key(feature): feature
        for feature in previous_features
        if isinstance(feature, dict)
    }
    result: list[dict[str, Any]] = []
    for feature in selected:
        feature = dict(feature)
        props = dict(feature.get("properties") or {})
        old = previous_by_key.get(_feature_key(feature))
        if old:
            old_props = old.get("properties") or {}
            for key in PROTECTED_EDITORIAL_FIELDS:
                if old_props.get(key) not in (None, "", [], {}):
                    props[key] = old_props[key]
        props["status"] = "published"
        feature["properties"] = props
        result.append(feature)
    return result


def _geojson(
    source: dict[str, Any],
    features: list[dict[str, Any]],
    *,
    island: str | None,
    raw_count: int | None = None,
    curation: str,
) -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "features": features,
        "available": bool(features),
        "island": island,
        "source": source.get("source"),
        "raw_count": raw_count if raw_count is not None else len(source.get("features") or []),
        "published_count": len(features),
        "curation": curation,
    }


def curate_places(
    raw: dict[str, Any],
    *,
    island: str | None,
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    features = [
        f for f in (raw.get("features") or [])
        if isinstance(f, dict)
        and _valid_point(f)
        and _norm((f.get("properties") or {}).get("name"))
    ]

    # Editorial catalog is authoritative for the first places shown to the
    # user. OSM/imported candidates can extend categories, but they cannot
    # displace a hand-curated Teide/Anaga/Masca-style selection.
    catalog = _read_curated_catalog("places", island)
    curated_features = [
        f for f in ((catalog or {}).get("features") or [])
        if isinstance(f, dict) and _valid_point(f)
    ]

    allowed = {
        "viewpoint", "museum", "attraction", "park", "zoo", "theme_park", "aquarium",
        "town", "village", "heritage",
    }
    features = [f for f in features if (f.get("properties") or {}).get("category") in allowed]

    # Put curated records first and dedupe imported records against them.
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for feature in [*curated_features, *features]:
        key = _feature_key(feature)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(feature)

    quotas = {
        "town": 6,
        "village": 7,
        "viewpoint": 10,
        "museum": 8,
        "heritage": 10,
        "park": 8,
        "zoo": 2,
        "theme_park": 3,
        "aquarium": 2,
        "attraction": 8,
    }

    def score(feature: dict[str, Any]) -> tuple[int, int, str]:
        p = feature.get("properties") or {}
        points = 0
        if p.get("featured") is True: points += 1000
        if p.get("cc_curated"): points += 500
        if p.get("source") in {"curated_explore", "curated_monuments"}: points += 250
        if p.get("wikipedia"): points += 20
        if p.get("wikidata"): points += 12
        if p.get("description"): points += 8
        if p.get("website"): points += 4
        if p.get("name"): points += 1
        priority = int(p.get("priority") or 9999)
        return points, -priority, _norm(p.get("name"))

    grouped: dict[str, list[dict[str, Any]]] = {}
    for feature in candidates:
        category = str((feature.get("properties") or {}).get("category") or "other")
        grouped.setdefault(category, []).append(feature)

    selected: list[dict[str, Any]] = []
    selected_keys: set[str] = set()

    # Always keep curated catalog records. These are the editorial backbone.
    for feature in curated_features:
        key = _feature_key(feature)
        if key in selected_keys:
            continue
        selected_keys.add(key)
        selected.append(feature)

    # Then add a controlled amount of useful imported candidates per category.
    for category, quota in quotas.items():
        group = sorted(grouped.get(category, []), key=lambda f: (-score(f)[0], -score(f)[1], score(f)[2]))
        added = 0
        for feature in group:
            key = _feature_key(feature)
            if key in selected_keys:
                continue
            selected_keys.add(key)
            selected.append(feature)
            added += 1
            if added >= quota:
                break

    selected = _merge_editorial_fields(selected, previous)
    return _geojson(raw, selected, island=island, curation="quality-gate:places-v2-editorial-first")


def _tri_state(value: Any, yes_values: set[str], no_values: set[str]) -> str:
    norm = _norm(value)
    if not norm:
        return "unknown"
    if norm in yes_values:
        return "yes"
    if norm in no_values:
        return "no"
    return "unknown"


def curate_beaches(
    raw: dict[str, Any],
    *,
    island: str | None,
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selected: list[dict[str, Any]] = []
    seen_names: set[str] = set()

    # Editorial beach catalogs are allowed to seed the product view even before
    # a developer runs the external importer. Imported beaches can extend the
    # catalog under "Todas", but cannot displace the hand-picked island set.
    catalog = _read_curated_catalog("beaches", island)
    source_features = [
        *[f for f in ((catalog or {}).get("features") or []) if isinstance(f, dict)],
        *[f for f in (raw.get("features") or []) if isinstance(f, dict)],
    ]

    for feature in source_features:
        if not _valid_point(feature):
            continue
        p = dict(feature.get("properties") or {})
        name = _norm(p.get("name"))
        if not name or name in seen_names:
            continue
        seen_names.add(name)
        p["accessibility_status"] = _tri_state(
            p.get("wheelchair"), {"yes", "limited", "designated"}, {"no"}
        )
        p["lifeguard_status"] = _tri_state(
            p.get("lifeguard") or p.get("supervised"),
            {"yes", "designated", "supervised"},
            {"no"},
        )
        p["nudism_status"] = _tri_state(
            p.get("nudism"), {"yes", "designated"}, {"no"}
        )
        featured_names = FEATURED_BEACH_NAMES.get(island or "", [])
        normalized_name = _ascii_norm(p.get("name"))
        matches = [candidate for candidate in featured_names if candidate in normalized_name or normalized_name in candidate]
        if matches and p.get("featured") is not False:
            p["featured"] = True
            p.setdefault("priority", featured_names.index(matches[0]) + 1)
        p["status"] = "published"
        selected.append({**feature, "properties": p})

    # Keep all named beaches available under "Todas", but default product UX
    # shows a featured subset. This prevents incomplete amenity tags from
    # pretending to be authoritative classifications.
    selected = _merge_editorial_fields(selected, previous)
    result = _geojson(raw, selected, island=island, curation="quality-gate:beaches-v2-editorial-first")
    if catalog is not None:
        result["catalog_source"] = catalog.get("source", "canarias-cerca-editorial")
    total = max(1, len(selected))
    result["coverage"] = {
        "accessibility": sum((f.get("properties") or {}).get("accessibility_status") != "unknown" for f in selected) / total,
        "lifeguard": sum((f.get("properties") or {}).get("lifeguard_status") != "unknown" for f in selected) / total,
        "nudism": sum((f.get("properties") or {}).get("nudism_status") != "unknown" for f in selected) / total,
    }
    return result


def curate_routes(
    raw: dict[str, Any],
    *,
    island: str | None,
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for feature in raw.get("features") or []:
        if not isinstance(feature, dict):
            continue
        if (feature.get("geometry") or {}).get("type") not in {"LineString", "MultiLineString"}:
            continue
        p = feature.get("properties") or {}
        if not _norm(p.get("name")):
            continue
        candidates.append(feature)

    def score(feature: dict[str, Any]) -> tuple[int, str]:
        p = feature.get("properties") or {}
        points = 0
        if p.get("description"): points += 8
        if p.get("distance") or p.get("distance_km") is not None: points += 6
        if p.get("duration"): points += 4
        if p.get("difficulty"): points += 4
        if p.get("ref"): points += 5
        if p.get("network") in {"rwn", "nwn", "iwn"}: points += 4
        if p.get("website"): points += 3
        if _norm(p.get("roundtrip")) == "yes": points += 2
        return points, _norm(p.get("name"))

    candidates.sort(key=lambda f: (-score(f)[0], score(f)[1]))
    selected = _merge_editorial_fields(candidates[:8], previous)
    return _geojson(raw, selected, island=island, curation="quality-gate:routes-v1")


def curate_catalog_resource(
    raw: dict[str, Any],
    *,
    resource: str,
    island: str | None,
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    catalog = _read_curated_catalog(resource, island)
    if catalog is None:
        # Do not expose arbitrary biodiversity occurrence records as product UX.
        return _geojson(raw, [], island=island, curation=f"curated-catalog:{resource}-v1")
    selected = _merge_editorial_fields(
        [f for f in catalog.get("features") or [] if isinstance(f, dict) and _valid_point(f)],
        previous,
    )
    result = _geojson(raw, selected, island=island, curation=f"curated-catalog:{resource}-v1")
    result["catalog_source"] = catalog.get("source", "canarias-cerca-editorial")
    result["status"] = "curated"
    return result


CURATORS: dict[str, Callable[..., dict[str, Any]]] = {
    "places": curate_places,
    "beaches": curate_beaches,
    "routes": curate_routes,
}


def curate_explore(
    resource: str,
    raw: dict[str, Any],
    *,
    island: str | None,
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if resource in {"fauna", "flora"}:
        return curate_catalog_resource(raw, resource=resource, island=island, previous=previous)
    curator = CURATORS.get(resource)
    if curator is None:
        return raw
    return curator(raw, island=island, previous=previous)
