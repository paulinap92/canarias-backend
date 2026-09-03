from __future__ import annotations

from typing import Any, Iterable


# west, south, east, north
ISLAND_BBOXES: dict[str, tuple[float, float, float, float]] = {
    "el-hierro": (-18.20, 27.55, -17.80, 27.90),
    "la-palma": (-18.05, 28.40, -17.65, 28.90),
    "la-gomera": (-17.40, 27.95, -17.00, 28.25),
    "tenerife": (-16.95, 27.95, -16.05, 28.65),
    "gran-canaria": (-15.90, 27.70, -15.25, 28.25),
    "fuerteventura": (-14.55, 27.95, -13.70, 28.80),
    "lanzarote": (-13.95, 28.80, -13.35, 29.30),
    "la-graciosa": (-13.60, 29.18, -13.45, 29.32),
}

VALID_ISLANDS = tuple(ISLAND_BBOXES.keys())


def normalize_island(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = (
        value.strip()
        .lower()
        .replace("_", "-")
        .replace(" ", "-")
    )

    aliases = {
        "grancanaria": "gran-canaria",
        "lapalma": "la-palma",
        "lagomera": "la-gomera",
        "elhierro": "el-hierro",
        "lagraciosa": "la-graciosa",
    }

    normalized = aliases.get(cleaned, cleaned)

    if normalized not in ISLAND_BBOXES:
        return None

    return normalized


def _iter_coords(
    geometry: dict[str, Any],
) -> Iterable[tuple[float, float]]:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")

    if coordinates is None:
        return

    if geometry_type == "Point":
        if len(coordinates) >= 2:
            yield float(coordinates[0]), float(coordinates[1])

    elif geometry_type == "LineString":
        for point in coordinates:
            if len(point) >= 2:
                yield float(point[0]), float(point[1])

    elif geometry_type == "MultiLineString":
        for line in coordinates:
            for point in line:
                if len(point) >= 2:
                    yield float(point[0]), float(point[1])


def geometry_center(
    geometry: dict[str, Any],
) -> tuple[float, float] | None:
    points = list(_iter_coords(geometry))

    if not points:
        return None

    longitude = sum(x for x, _ in points) / len(points)
    latitude = sum(y for _, y in points) / len(points)

    return longitude, latitude


def point_is_on_island(
    longitude: float,
    latitude: float,
    island: str,
) -> bool:
    west, south, east, north = ISLAND_BBOXES[island]

    return (
        west <= longitude <= east
        and south <= latitude <= north
    )


def filter_feature_collection_by_island(
    data: dict[str, Any],
    island: str | None,
) -> dict[str, Any]:
    if island is None:
        return data

    normalized = normalize_island(island)

    if normalized is None:
        return {
            "type": "FeatureCollection",
            "features": [],
            "filter": {
                "island": island,
                "valid": False,
            },
        }

    features = []

    for feature in data.get("features", []):
        center = geometry_center(
            feature.get("geometry") or {}
        )

        if center is None:
            continue

        longitude, latitude = center

        if point_is_on_island(
            longitude,
            latitude,
            normalized,
        ):
            features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features,
        "filter": {
            "island": normalized,
            "valid": True,
        },
    }


def filter_records_by_island(
    records: list[dict[str, Any]],
    island: str | None,
    *,
    include_regional: bool = False,
) -> list[dict[str, Any]]:
    if island is None:
        return records

    normalized = normalize_island(island)

    if normalized is None:
        return []

    result = []

    for record in records:
        record_island = normalize_island(
            record.get("island")
        )

        if record_island == normalized:
            result.append(record)
        elif include_regional and record.get("island") is None:
            result.append(record)

    return result
