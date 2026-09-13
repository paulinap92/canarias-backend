from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus

import httpx

from app.services.places import _representative_coordinates
from app.utils.islands import normalize_island, overpass_bbox


OVERPASS_URLS = [
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]


def _build_query(island: str | None) -> str:
    bbox = overpass_bbox(island)
    return f"""
[out:json][timeout:35];
nwr["natural"="beach"]({bbox});
out center geom tags;
"""


async def _fetch_overpass(island: str | None = None) -> dict[str, Any]:
    body = "data=" + quote_plus(_build_query(island))
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Canarias-Cerca/1.0",
    }
    last_error: Exception | None = None

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


async def fetch_beaches(limit: int = 200, island: str | None = None) -> dict[str, Any]:
    normalized = normalize_island(island)
    if island is not None and normalized is None:
        return {"type": "FeatureCollection", "features": []}

    data = await _fetch_overpass(normalized)
    features = []

    for element in data.get("elements", []):
        tags = element.get("tags", {})
        name = tags.get("name:es") or tags.get("name")
        if not name:
            continue

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
                "surface": tags.get("surface"),
                "access": tags.get("access"),
                "wheelchair": tags.get("wheelchair"),
                "lifeguard": tags.get("lifeguard"),
                "supervised": tags.get("supervised"),
                "nudism": tags.get("nudism"),
                "description": tags.get("description:es") or tags.get("description"),
                "website": tags.get("website"),
                "wikidata": tags.get("wikidata"),
                "wikipedia": tags.get("wikipedia"),
                "operator": tags.get("operator"),
                "fee": tags.get("fee"),
                "dog": tags.get("dog"),
                "toilets": tags.get("toilets"),
                "shower": tags.get("shower"),
            },
        })

    # Stable ordering avoids arbitrary Overpass response order becoming product UX.
    features.sort(key=lambda f: str(f.get("properties", {}).get("name") or "").casefold())
    return {"type": "FeatureCollection", "features": features[:limit]}
