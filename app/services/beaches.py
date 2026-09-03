from typing import Any
from urllib.parse import quote_plus

import httpx


OVERPASS_URLS = [
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

CANARY_BBOX = "27.5,-18.3,29.5,-13.2"

OVERPASS_QUERY = f"""
[out:json][timeout:35];

nwr["natural"="beach"]({CANARY_BBOX});

out center tags;
"""


async def _fetch_overpass() -> dict[str, Any]:
    body = "data=" + quote_plus(OVERPASS_QUERY)
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


async def fetch_beaches(limit: int = 200) -> dict[str, Any]:
    data = await _fetch_overpass()
    features = []

    for element in data.get("elements", []):
        tags = element.get("tags", {})
        name = tags.get("name") or tags.get("name:es")

        if not name:
            continue

        latitude = element.get("lat")
        longitude = element.get("lon")

        if latitude is None or longitude is None:
            center = element.get("center", {})
            latitude = center.get("lat")
            longitude = center.get("lon")

        if latitude is None or longitude is None:
            continue

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

    return {"type": "FeatureCollection", "features": features}
