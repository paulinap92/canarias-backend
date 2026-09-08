from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus

import httpx

from app.utils.islands import ISLAND_BBOXES, normalize_island


OVERPASS_URLS = [
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

# Overpass uses south,west,north,east.
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
[out:json][timeout:25];

(
  nwr["tourism"="attraction"]({bbox});
  nwr["tourism"="museum"]({bbox});
  nwr["tourism"="viewpoint"]({bbox});

  nwr["natural"="beach"]({bbox});

  nwr["historic"="castle"]({bbox});
  nwr["historic"="fort"]({bbox});
  nwr["historic"="archaeological_site"]({bbox});
  nwr["historic"="monument"]({bbox});
);

out center tags;
"""


def get_category(
    tags: dict[str, Any],
) -> str:
    if tags.get("natural") == "beach":
        return "beach"

    if tags.get("tourism") == "viewpoint":
        return "viewpoint"

    if tags.get("tourism") == "museum":
        return "museum"

    if tags.get("tourism") == "attraction":
        return "attraction"

    historic = tags.get("historic")

    if historic in {
        "castle",
        "fort",
        "archaeological_site",
        "monument",
    }:
        return historic

    return "other"


async def fetch_overpass_data(
    island: str | None = None,
) -> dict[str, Any]:
    query = _build_overpass_query(island)
    body = "data=" + quote_plus(query)

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Canarias-Cerca/1.0",
    }

    async with httpx.AsyncClient(
        timeout=35.0,
        follow_redirects=True,
    ) as client:
        last_error: Exception | None = None

        for url in OVERPASS_URLS:
            try:
                response = await client.post(
                    url,
                    content=body,
                    headers=headers,
                )

                response.raise_for_status()

                content_type = response.headers.get(
                    "content-type",
                    "",
                )

                if "json" not in content_type.lower():
                    print(
                        "OVERPASS NON-JSON:",
                        url,
                        response.status_code,
                        content_type,
                        response.text[:200],
                    )
                    continue

                return response.json()

            except (
                httpx.HTTPError,
                ValueError,
            ) as error:
                last_error = error
                print(
                    "OVERPASS FAILED:",
                    url,
                    error,
                )

        raise RuntimeError(
            f"All Overpass servers failed: {last_error}"
        )


async def fetch_places(
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
            "filter": {
                "island": island,
                "valid": False,
            },
        }

    try:
        data = await fetch_overpass_data(
            normalized_island,
        )
    except RuntimeError as error:
        print(
            "PLACES OVERPASS UNAVAILABLE:",
            normalized_island or "canarias",
            error,
        )
        return {
            "type": "FeatureCollection",
            "features": [],
            "available": False,
            "reason": "overpass_unavailable",
            "filter": {
                "island": normalized_island,
                "valid": True,
            },
        }

    features = []

    for element in data.get("elements", []):
        tags = element.get("tags", {})

        name = tags.get("name")

        if not name:
            continue

        latitude = element.get("lat")
        longitude = element.get("lon")

        if latitude is None or longitude is None:
            center = element.get(
                "center",
                {},
            )

            latitude = center.get("lat")
            longitude = center.get("lon")

        if latitude is None or longitude is None:
            continue

        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        longitude,
                        latitude,
                    ],
                },
                "properties": {
                    "osm_id": element.get("id"),
                    "osm_type": element.get("type"),
                    "name": name,
                    "category": get_category(tags),
                    "website": tags.get("website"),
                    "wikipedia": tags.get("wikipedia"),
                    "wikidata": tags.get("wikidata"),
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
