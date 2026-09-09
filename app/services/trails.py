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

relation
    ["type"="route"]
    ["route"~"^(hiking|foot)$"]
    ({bbox})
    ->.routes;

way(r.routes);

out geom tags;
"""


async def fetch_overpass(
    island: str | None = None,
) -> dict[str, Any]:
    body = "data=" + quote_plus(_build_overpass_query(island))

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Canarias-Cerca/1.0",
    }

    async with httpx.AsyncClient(
        timeout=50.0,
        follow_redirects=True,
    ) as client:
        last_error = None

        for url in OVERPASS_URLS:
            try:
                response = await client.post(
                    url,
                    content=body,
                    headers=headers,
                )

                response.raise_for_status()

                if "json" not in response.headers.get(
                    "content-type",
                    "",
                ).lower():
                    continue

                return response.json()

            except httpx.HTTPError as error:
                last_error = error

        raise RuntimeError(
            f"All Overpass servers failed: {last_error}"
        )


async def fetch_trails(
    limit: int = 100,
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

    data = await fetch_overpass(normalized_island)

    features = []

    for way in data.get("elements", []):
        geometry = way.get("geometry")

        if not geometry:
            continue

        coordinates = [
            [
                point["lon"],
                point["lat"],
            ]
            for point in geometry
        ]

        if len(coordinates) < 2:
            continue

        tags = way.get("tags", {})

        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": coordinates,
                },
                "properties": {
                    "osm_id": way.get("id"),
                    "name": tags.get("name"),
                    "ref": tags.get("ref"),
                    "highway": tags.get("highway"),
                    "surface": tags.get("surface"),
                    "sac_scale": tags.get("sac_scale"),
                    "trail_visibility": tags.get(
                        "trail_visibility"
                    ),
                },
            }
        )

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
