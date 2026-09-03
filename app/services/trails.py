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

relation
    ["type"="route"]
    ["route"~"^(hiking|foot)$"]
    ({CANARY_BBOX})
    ->.routes;

way(r.routes);

out geom tags;
"""


async def fetch_overpass() -> dict[str, Any]:
    body = "data=" + quote_plus(OVERPASS_QUERY)

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
) -> dict[str, Any]:
    data = await fetch_overpass()

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
    }