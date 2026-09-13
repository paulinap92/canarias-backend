from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import httpx

from app.utils.islands import normalize_island, overpass_bbox


OVERPASS_URLS = [
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
MONUMENTS_FILE = DATA_DIR / "monuments.json"
CONTENT_DIR = DATA_DIR / "guide" / "content"


def _build_overpass_query(island: str | None) -> str:
    bbox = overpass_bbox(island)
    return f"""
[out:json][timeout:25];
(
  nwr["tourism"="viewpoint"]({bbox});
  nwr["tourism"="museum"]({bbox});
  nwr["tourism"="zoo"]({bbox});
  nwr["tourism"="theme_park"]({bbox});
  nwr["tourism"="aquarium"]({bbox});

  /* Generic tourism=attraction is extremely noisy in OSM (for example
     individual animals and shows inside Loro Parque). Keep only attractions
     with a strong notability signal instead of dumping every internal POI. */
  nwr["tourism"="attraction"]["wikidata"]({bbox});
  nwr["tourism"="attraction"]["wikipedia"]({bbox});

  /* Pueblos/localities: include hamlets too. Many Canary settlements are
     mapped as village/hamlet rather than town. */
  nwr["place"~"^(town|village|hamlet)$"]({bbox});

  /* Heritage now belongs inside Lugares instead of a separate top-level
     Monumentos layer. Keep the query deliberately narrow to avoid another
     noisy OSM dump. */
  nwr["historic"~"^(castle|fort|archaeological_site|monument|city_gate|ruins)$"]({bbox});
  nwr["man_made"="lighthouse"]({bbox});
);
out center geom tags;
"""


def _representative_coordinates(element: dict[str, Any]) -> tuple[float, float] | None:
    """Return a marker on the actual OSM geometry when geometry is available."""
    latitude = element.get("lat")
    longitude = element.get("lon")
    if latitude is not None and longitude is not None:
        return float(longitude), float(latitude)

    geometry = element.get("geometry") or []
    points = [
        (float(point["lon"]), float(point["lat"]))
        for point in geometry
        if point.get("lon") is not None and point.get("lat") is not None
    ]
    if points:
        mean_lon = sum(lon for lon, _ in points) / len(points)
        mean_lat = sum(lat for _, lat in points) / len(points)
        return min(
            points,
            key=lambda p: (p[0] - mean_lon) ** 2 + (p[1] - mean_lat) ** 2,
        )

    center = element.get("center") or {}
    latitude = center.get("lat")
    longitude = center.get("lon")
    if latitude is None or longitude is None:
        return None
    return float(longitude), float(latitude)


def get_category(tags: dict[str, Any]) -> str:
    tourism = tags.get("tourism")
    if tourism == "viewpoint":
        return "viewpoint"
    if tourism == "museum":
        return "museum"
    if tourism == "zoo":
        return "zoo"
    if tourism == "theme_park":
        return "theme_park"
    if tourism == "aquarium":
        return "aquarium"
    if tourism == "attraction":
        return "attraction"

    place = tags.get("place")
    if place == "town":
        return "town"
    if place in {"village", "hamlet"}:
        return "village"

    historic = tags.get("historic")
    if historic in {
        "castle",
        "fort",
        "archaeological_site",
        "monument",
        "city_gate",
        "ruins",
    }:
        return "heritage"

    if tags.get("man_made") == "lighthouse":
        return "heritage"

    return "other"


def _heritage_type(tags: dict[str, Any]) -> str | None:
    if tags.get("historic"):
        return str(tags["historic"])
    if tags.get("man_made") == "lighthouse":
        return "lighthouse"
    return None


async def fetch_overpass_data(island: str | None = None) -> dict[str, Any]:
    query = _build_overpass_query(island)
    body = "data=" + quote_plus(query)
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Canarias-Cerca/1.0",
    }

    async with httpx.AsyncClient(timeout=35.0, follow_redirects=True) as client:
        last_error: Exception | None = None
        for url in OVERPASS_URLS:
            try:
                response = await client.post(url, content=body, headers=headers)
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if "json" not in content_type.lower():
                    continue
                return response.json()
            except (httpx.HTTPError, ValueError) as error:
                last_error = error

    raise RuntimeError(f"All Overpass servers failed: {last_error}")


def _balanced_limit(features: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    """Keep every category discoverable when a global API limit is applied."""
    if len(features) <= limit:
        return features

    groups: dict[str, list[dict[str, Any]]] = {}
    for feature in features:
        category = str(feature.get("properties", {}).get("category") or "other")
        groups.setdefault(category, []).append(feature)

    category_order = [
        "town",
        "village",
        "heritage",
        "viewpoint",
        "museum",
        "zoo",
        "theme_park",
        "aquarium",
        "attraction",
    ]
    reserve = max(8, min(40, limit // max(1, len(category_order) * 2)))
    selected: list[dict[str, Any]] = []
    selected_ids: set[tuple[Any, Any]] = set()

    def add(feature: dict[str, Any]) -> None:
        props = feature.get("properties", {})
        key = (
            props.get("osm_type") or props.get("source"),
            props.get("osm_id") or props.get("id") or props.get("name"),
        )
        if key in selected_ids or len(selected) >= limit:
            return
        selected_ids.add(key)
        selected.append(feature)

    for category in category_order:
        for feature in groups.get(category, [])[:reserve]:
            add(feature)

    for feature in features:
        add(feature)
        if len(selected) >= limit:
            break

    return selected


def _normalise_name(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _load_curated_heritage(island: str | None) -> list[dict[str, Any]]:
    if not MONUMENTS_FILE.exists():
        return []

    try:
        records = json.loads(MONUMENTS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    result: list[dict[str, Any]] = []
    for record in records:
        record_island = normalize_island(record.get("island"))
        if island and record_island != island:
            continue
        latitude = record.get("latitude")
        longitude = record.get("longitude")
        if latitude is None or longitude is None:
            continue
        result.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(longitude), float(latitude)],
            },
            "properties": {
                "id": record.get("id"),
                "name": record.get("name"),
                "category": "heritage",
                "heritage_type": record.get("category") or "historic",
                "description": record.get("description"),
                "source": "curated_monuments",
                "island": record_island,
            },
        })
    return result


def _load_curated_pueblos(island: str | None) -> list[dict[str, Any]]:
    """Use curated Explore stories as a small, reliable pueblo fallback.

    OSM remains the main source, but scenic settlements already curated by
    Canarias Cerca should never disappear just because Overpass tags vary.
    """
    if not island:
        return []

    source_file = CONTENT_DIR / island / "explore.json"
    if not source_file.exists():
        return []

    try:
        records = json.loads(source_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    settlement_tags = {"village", "town", "city", "fishing-village", "villages"}
    result: list[dict[str, Any]] = []
    for record in records if isinstance(records, list) else []:
        tags = {str(tag).casefold() for tag in (record.get("tags") or [])}
        if not (tags & settlement_tags):
            continue
        latitude = record.get("latitude")
        longitude = record.get("longitude")
        if latitude is None or longitude is None:
            continue
        result.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(longitude), float(latitude)],
            },
            "properties": {
                "id": record.get("id"),
                "name": record.get("name"),
                "category": "village",
                "description": record.get("short_description"),
                "website": record.get("source_url"),
                "source": "curated_explore",
                "island": island,
            },
        })
    return result


def _merge_unique(
    primary: list[dict[str, Any]],
    additions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result = list(primary)
    names = {
        _normalise_name(feature.get("properties", {}).get("name"))
        for feature in primary
    }
    for feature in additions:
        name = _normalise_name(feature.get("properties", {}).get("name"))
        if not name or name in names:
            continue
        names.add(name)
        result.append(feature)
    return result


async def fetch_places(limit: int = 100, island: str | None = None) -> dict[str, Any]:
    normalized_island = normalize_island(island)
    if island is not None and normalized_island is None:
        return {
            "type": "FeatureCollection",
            "features": [],
            "available": False,
            "reason": "invalid_island",
            "filter": {"island": island, "valid": False},
        }

    data = await fetch_overpass_data(normalized_island)
    overpass_available = True

    features: list[dict[str, Any]] = []
    seen: set[tuple[str | None, int | None]] = set()

    for element in data.get("elements", []):
        tags = element.get("tags", {})
        name = tags.get("name:es") or tags.get("name")
        if not name:
            continue

        category = get_category(tags)
        if category == "other":
            continue

        key = (element.get("type"), element.get("id"))
        if key in seen:
            continue
        seen.add(key)

        coordinates = _representative_coordinates(element)
        if coordinates is None:
            continue

        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": list(coordinates)},
            "properties": {
                "osm_id": element.get("id"),
                "osm_type": element.get("type"),
                "name": name,
                "category": category,
                "heritage_type": _heritage_type(tags),
                "description": tags.get("description:es") or tags.get("description"),
                "website": tags.get("website"),
                "wikipedia": tags.get("wikipedia"),
                "wikidata": tags.get("wikidata"),
                "opening_hours": tags.get("opening_hours"),
                "wheelchair": tags.get("wheelchair"),
                "source": "overpass",
            },
        })

    # Curated settlements keep Pueblos useful even when OSM tagging is sparse.
    features = _merge_unique(features, _load_curated_pueblos(normalized_island))

    # The old Monumentos catalogue now lives under Lugares -> Patrimonio.
    features = _merge_unique(features, _load_curated_heritage(normalized_island))

    features = _balanced_limit(features, limit)

    return {
        "type": "FeatureCollection",
        "features": features,
        "available": overpass_available or bool(features),
        "source": "overpass+curated",
        "filter": {"island": normalized_island, "valid": True},
    }
