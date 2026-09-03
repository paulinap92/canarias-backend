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
[out:json][timeout:30];

(
  nwr["tourism"="attraction"]({CANARY_BBOX});
  nwr["tourism"="museum"]({CANARY_BBOX});
  nwr["tourism"="viewpoint"]({CANARY_BBOX});

  nwr["natural"="beach"]({CANARY_BBOX});

  nwr["historic"="castle"]({CANARY_BBOX});
  nwr["historic"="fort"]({CANARY_BBOX});
  nwr["historic"="archaeological_site"]({CANARY_BBOX});
  nwr["historic"="monument"]({CANARY_BBOX});
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


async def fetch_overpass_data() -> dict[str, Any]:
    body = "data=" + quote_plus(OVERPASS_QUERY)

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Canarias-Cerca/1.0",
    }

    async with httpx.AsyncClient(
        timeout=45.0,
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
) -> dict[str, Any]:
    data = await fetch_overpass_data()

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
    }