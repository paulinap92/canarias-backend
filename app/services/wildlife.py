from typing import Any

import httpx


GBIF_URL = "https://api.gbif.org/v1/occurrence/search"

# Przybliżony obszar Wysp Kanaryjskich
CANARY_GEOMETRY = (
    "POLYGON(("
    "-18.5 27.0,"
    "-13.0 27.0,"
    "-13.0 29.5,"
    "-18.5 29.5,"
    "-18.5 27.0"
    "))"
)


async def fetch_wildlife(
    limit: int = 50,
) -> dict[str, Any]:
    params = {
        "geometry": CANARY_GEOMETRY,
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
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "features": features,
    }