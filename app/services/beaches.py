from typing import Any
from urllib.parse import quote_plus

import httpx

from app.utils.islands import ISLAND_BBOXES, normalize_island


OVERPASS_URLS = [
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

CANARY_BBOX = "27.5,-18.3,29.5,-13.2"


def _bbox_for_island(island: str | None) -> str:
    if island is None:
        return CANARY_BBOX

    normalized = normalize_island(island)
    if normalized is None:
        return CANARY_BBOX

    west, south, east, north = ISLAND_BBOXES[normalized]
    return f"{south},{west},{north},{east}"


def _build_overpass_query(island: str | None) -> str:
    bbox = _bbox_for_island(island)

    return f"""
[out:json][timeout:35];

nwr["natural"="beach"]({bbox});

out geom tags;
"""


def _representative_coordinates(
    element: dict[str, Any],
) -> tuple[float, float] | None:
    latitude = element.get("lat")
    longitude = element.get("lon")

    if latitude is not None and longitude is not None:
        return float(latitude), float(longitude)

    geometry = element.get("geometry") or []
    points = [
        (float(point["lat"]), float(point["lon"]))
        for point in geometry
        if point.get("lat") is not None and point.get("lon") is not None
    ]

    if not points:
        center = element.get("center") or {}
        latitude = center.get("lat")
        longitude = center.get("lon")
        if latitude is None or longitude is None:
            return None
        return float(latitude), float(longitude)

    mean_latitude = sum(lat for lat, _ in points) / len(points)
    mean_longitude = sum(lon for _, lon in points) / len(points)

    return min(
        points,
        key=lambda point: (
            (point[0] - mean_latitude) ** 2
            + (point[1] - mean_longitude) ** 2
        ),
    )


async def _fetch_overpass(
    island: str | None = None,
) -> dict[str, Any]:
    query = _build_overpass_query(island)
    body = "data=" + quote_plus(query)
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Canarias-Cerca/1.0",
    }

    last_error = None

    async with httpx.AsyncClient(timeout=50.0, follow_redirects=True) as client:
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


async def fetch_beaches(
    limit: int = 200,
    island: str | None = None,
) -> dict[str, Any]:
    normalized_island = normalize_island(island)

    if island is not None and normalized_island is None:
        return {
            "type": "FeatureCollection",
            "features": [],
            "available": False,
            "reason": "invalid_island",
        }

    data = await _fetch_overpass(normalized_island)
    features = []

    for element in data.get("elements", []):
        tags = element.get("tags", {})
        name = tags.get("name") or tags.get("name:es")

        if not name:
            continue

        coordinates = _representative_coordinates(element)
        if coordinates is None:
            continue

        latitude, longitude = coordinates

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [longitude, latitude],
            },
            "properties": {
                "osm_id": element.get("id"),
                "osm_type": element.get("type"),
                "name": name,
                "surface": tags.get("surface"),
                "access": tags.get("access"),
                "wheelchair": tags.get("wheelchair"),
                "lifeguard": tags.get("lifeguard"),
                "supervised": tags.get("supervised"),
                "nudism": tags.get("nudism"),
                "website": tags.get("website"),
                "wikidata": tags.get("wikidata"),
                "wikipedia": tags.get("wikipedia"),
            },
        })

        if len(features) >= limit:
            break

    return {
        "type": "FeatureCollection",
        "features": features,
        "available": True,
        "source": "overpass",
        "filter": {
            "island": normalized_island,
            "valid": True,
        },
    }
