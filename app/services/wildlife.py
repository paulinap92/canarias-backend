from typing import Any

import httpx

from app.utils.islands import ISLAND_BBOXES, normalize_island


GBIF_URL = "https://api.gbif.org/v1/occurrence/search"

CANARY_GEOMETRY = (
    "POLYGON(("
    "-18.5 27.0,"
    "-13.0 27.0,"
    "-13.0 29.5,"
    "-18.5 29.5,"
    "-18.5 27.0"
    "))"
)


def _geometry_for_island(island: str | None) -> str:
    normalized = normalize_island(island)

    if normalized is None:
        return CANARY_GEOMETRY

    west, south, east, north = ISLAND_BBOXES[normalized]

    return (
        "POLYGON(("
        f"{west} {south},"
        f"{east} {south},"
        f"{east} {north},"
        f"{west} {north},"
        f"{west} {south}"
        "))"
    )


async def fetch_wildlife(
    limit: int = 50,
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

    params = {
        "geometry": _geometry_for_island(normalized_island),
        "hasCoordinate": "true",
        "occurrenceStatus": "PRESENT",
        "limit": limit,
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            GBIF_URL,
            params=params,
        )
        response.raise_for_status()

        data = response.json()

    features = []

    for item in data.get("results", []):
        latitude = item.get("decimalLatitude")
        longitude = item.get("decimalLongitude")

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
                    "gbif_id": item.get("key"),
                    "scientific_name": item.get("scientificName"),
                    "species": item.get("species"),
                    "kingdom": item.get("kingdom"),
                    "class": item.get("class"),
                    "event_date": item.get("eventDate"),
                    "basis_of_record": item.get("basisOfRecord"),
                    "coordinate_uncertainty_m": item.get(
                        "coordinateUncertaintyInMeters"
                    ),
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "features": features,
        "available": True,
        "source": "gbif",
        "filter": {
            "island": normalized_island,
            "valid": True,
        },
    }
