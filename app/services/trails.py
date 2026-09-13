from __future__ import annotations

from math import asin, cos, radians, sin, sqrt
from typing import Any
from urllib.parse import quote_plus

import httpx

from app.utils.islands import normalize_island, overpass_bbox


OVERPASS_URLS = [
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]


def _build_query(island: str | None) -> str:
    bbox = overpass_bbox(island)
    # One relation = one route. The previous implementation requested every
    # member way separately, producing dozens of fragments and a much heavier
    # Overpass response. `out geom` keeps member geometry inside the relation.
    return f"""
[out:json][timeout:25];
relation
    ["type"="route"]
    ["route"~"^(hiking|foot)$"]
    ({bbox});
out geom;
"""


async def fetch_overpass(island: str | None = None) -> dict[str, Any]:
    body = "data=" + quote_plus(_build_query(island))
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
                if "json" not in response.headers.get("content-type", "").lower():
                    continue
                return response.json()
            except (httpx.HTTPError, ValueError) as error:
                last_error = error

    raise RuntimeError(f"All Overpass servers failed: {last_error}")


def _relation_lines(relation: dict[str, Any]) -> list[list[list[float]]]:
    lines: list[list[list[float]]] = []
    for member in relation.get("members") or []:
        geometry = member.get("geometry") or []
        coordinates = [
            [float(point["lon"]), float(point["lat"])]
            for point in geometry
            if point.get("lon") is not None and point.get("lat") is not None
        ]
        if len(coordinates) >= 2:
            lines.append(coordinates)
    return lines


def _distance_km(lines: list[list[list[float]]]) -> float:
    total = 0.0
    earth_radius_km = 6371.0088
    for line in lines:
        for first, second in zip(line, line[1:]):
            lon1, lat1 = first
            lon2, lat2 = second
            lat1_r = radians(lat1)
            lat2_r = radians(lat2)
            dlat = lat2_r - lat1_r
            dlon = radians(lon2 - lon1)
            a = sin(dlat / 2) ** 2 + cos(lat1_r) * cos(lat2_r) * sin(dlon / 2) ** 2
            total += 2 * earth_radius_km * asin(sqrt(a))
    return total


def _display_distance(tags: dict[str, Any], lines: list[list[list[float]]]) -> str | None:
    explicit = str(tags.get("distance") or "").strip()
    if explicit:
        return explicit
    calculated = _distance_km(lines)
    if calculated <= 0:
        return None
    return f"{calculated:.1f} km"


def _difficulty(tags: dict[str, Any]) -> str | None:
    sac_scale = str(tags.get("sac_scale") or "").strip().casefold()
    if not sac_scale:
        return None
    if sac_scale == "hiking":
        return "fácil"
    if sac_scale in {"mountain_hiking", "demanding_mountain_hiking"}:
        return "media" if sac_scale == "mountain_hiking" else "difícil"
    if sac_scale in {
        "alpine_hiking",
        "demanding_alpine_hiking",
        "difficult_alpine_hiking",
    }:
        return "difícil"
    return None


def _duration(tags: dict[str, Any]) -> str | None:
    value = str(tags.get("duration") or tags.get("duration:forward") or "").strip()
    return value or None


def _route_feature(relation: dict[str, Any]) -> dict[str, Any] | None:
    lines = _relation_lines(relation)
    if not lines:
        return None

    tags = relation.get("tags") or {}
    name = tags.get("name:es") or tags.get("name") or tags.get("ref")
    if not name:
        return None

    route_id = f"relation-{relation.get('id')}"
    geometry: dict[str, Any]
    if len(lines) == 1:
        geometry = {"type": "LineString", "coordinates": lines[0]}
    else:
        geometry = {"type": "MultiLineString", "coordinates": lines}

    calculated_distance_km = _distance_km(lines)
    roundtrip = str(tags.get("roundtrip") or "").strip().casefold()

    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": {
            "route_id": route_id,
            "osm_id": relation.get("id"),
            "name": name,
            "ref": tags.get("ref"),
            "route": tags.get("route"),
            "network": tags.get("network"),
            "distance": _display_distance(tags, lines),
            "distance_km": round(calculated_distance_km, 1) if calculated_distance_km > 0 else None,
            "duration": _duration(tags),
            "difficulty": _difficulty(tags),
            "roundtrip": tags.get("roundtrip"),
            "circular": True if roundtrip == "yes" else False if roundtrip == "no" else None,
            "operator": tags.get("operator"),
            "description": tags.get("description:es") or tags.get("description"),
            "website": tags.get("website"),
            "source": "overpass_route_relation",
        },
    }


async def fetch_trails(limit: int = 100, island: str | None = None) -> dict[str, Any]:
    normalized = normalize_island(island)
    if island is not None and normalized is None:
        return {
            "type": "FeatureCollection",
            "features": [],
            "available": False,
            "reason": "invalid_island",
        }

    data = await fetch_overpass(normalized)

    features: list[dict[str, Any]] = []
    seen_names: set[str] = set()

    for relation in data.get("elements", []):
        feature = _route_feature(relation)
        if feature is None:
            continue

        name_key = " ".join(
            str(feature.get("properties", {}).get("name") or "").casefold().split()
        )
        if name_key in seen_names:
            continue
        seen_names.add(name_key)
        features.append(feature)

        if len(features) >= limit:
            break

    return {
        "type": "FeatureCollection",
        "features": features,
        "available": True,
        "source": "overpass_route_relations",
    }
