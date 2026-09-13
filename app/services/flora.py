from __future__ import annotations

from typing import Any

import httpx

from app.utils.islands import ISLAND_BBOXES, normalize_island


GBIF_URL = "https://api.gbif.org/v1/occurrence/search"
CANARY_GEOMETRY = "POLYGON((-18.5 27.0,-13.0 27.0,-13.0 29.5,-18.5 29.5,-18.5 27.0))"
PLANTAE_KEY = 6


def _geometry_for_island(island: str | None) -> str:
    if island is None:
        return CANARY_GEOMETRY
    normalized = normalize_island(island)
    if normalized is None:
        return CANARY_GEOMETRY
    west, south, east, north = ISLAND_BBOXES[normalized]
    return (
        f"POLYGON(({west} {south},{east} {south},{east} {north},"
        f"{west} {north},{west} {south}))"
    )


async def fetch_flora(limit: int = 80, island: str | None = None) -> dict[str, Any]:
    normalized = normalize_island(island)
    if island is not None and normalized is None:
        return {"type": "FeatureCollection", "features": []}

    params = {
        "geometry": _geometry_for_island(normalized),
        "hasCoordinate": "true",
        "occurrenceStatus": "PRESENT",
        "kingdomKey": PLANTAE_KEY,
        "limit": limit,
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(GBIF_URL, params=params)
        response.raise_for_status()
        data = response.json()

    features: list[dict[str, Any]] = []
    seen_species: set[str] = set()
    for item in data.get("results", []):
        latitude = item.get("decimalLatitude")
        longitude = item.get("decimalLongitude")
        if latitude is None or longitude is None:
            continue

        scientific_name = item.get("scientificName") or item.get("species")
        species_key = str(scientific_name or item.get("key") or "").casefold()
        if not species_key or species_key in seen_species:
            continue
        seen_species.add(species_key)

        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [longitude, latitude]},
            "properties": {
                "gbif_id": item.get("key"),
                "scientific_name": scientific_name,
                "species": item.get("species"),
                "genus": item.get("genus"),
                "family": item.get("family"),
                "kingdom": item.get("kingdom"),
                "event_date": item.get("eventDate"),
                "basis_of_record": item.get("basisOfRecord"),
                "source": "GBIF",
            },
        })

    return {"type": "FeatureCollection", "features": features}
