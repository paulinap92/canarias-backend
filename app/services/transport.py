from __future__ import annotations

import csv
import io
import time
import zipfile
from pathlib import Path
from typing import Any

import httpx

from app.data_sources.store import DATA_ROOT
from app.utils.islands import filter_records_by_island


TITSA_GTFS_URL = (
    "https://datos.tenerife.es/ckan/dataset/"
    "36c2e26f-0d18-4b5a-b214-1636168e0765/resource/"
    "9f291323-8b78-453a-9008-4f0e3bfb3ce3/download/"
    "fichero-zip-de-google-transit.zip"
)

GTFS_TTL_SECONDS = 24 * 60 * 60


AIRPORTS: list[dict[str, Any]] = [
    {"name": "Tenerife Norte-Ciudad de La Laguna", "iata": "TFN", "island": "tenerife", "latitude": 28.4827, "longitude": -16.3415},
    {"name": "Tenerife Sur", "iata": "TFS", "island": "tenerife", "latitude": 28.0445, "longitude": -16.5725},
    {"name": "Gran Canaria", "iata": "LPA", "island": "gran-canaria", "latitude": 27.9319, "longitude": -15.3866},
    {"name": "César Manrique-Lanzarote", "iata": "ACE", "island": "lanzarote", "latitude": 28.9455, "longitude": -13.6052},
    {"name": "Fuerteventura", "iata": "FUE", "island": "fuerteventura", "latitude": 28.4527, "longitude": -13.8638},
    {"name": "La Palma", "iata": "SPC", "island": "la-palma", "latitude": 28.6265, "longitude": -17.7556},
    {"name": "La Gomera", "iata": "GMZ", "island": "la-gomera", "latitude": 28.0296, "longitude": -17.2146},
    {"name": "El Hierro", "iata": "VDE", "island": "el-hierro", "latitude": 27.8148, "longitude": -17.8871},
]


def get_airports(
    island: str | None = None,
) -> list[dict[str, Any]]:
    return filter_records_by_island(
        AIRPORTS,
        island,
    )


def _transport_dir() -> Path:
    path = DATA_ROOT / "transport"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _gtfs_file() -> Path:
    return _transport_dir() / "titsa_gtfs.zip"


async def _ensure_gtfs() -> Path:
    path = _gtfs_file()

    if (
        path.exists()
        and time.time() - path.stat().st_mtime
        < GTFS_TTL_SECONDS
    ):
        return path

    async with httpx.AsyncClient(
        timeout=90.0,
        follow_redirects=True,
        headers={"User-Agent": "Canarias-Cerca/1.0"},
    ) as client:
        response = await client.get(TITSA_GTFS_URL)
        response.raise_for_status()

    temp = path.with_suffix(".tmp")
    temp.write_bytes(response.content)

    with zipfile.ZipFile(temp) as archive:
        if not {
            "stops.txt",
            "routes.txt",
        }.issubset(set(archive.namelist())):
            temp.unlink(missing_ok=True)
            raise RuntimeError("Invalid TITSA GTFS")

    temp.replace(path)
    return path


def _read_csv(
    archive: zipfile.ZipFile,
    filename: str,
) -> list[dict[str, str]]:
    return list(
        csv.DictReader(
            io.StringIO(
                archive.read(filename).decode(
                    "utf-8-sig",
                    errors="replace",
                )
            )
        )
    )


async def fetch_titsa_stops(
    limit: int = 500,
) -> dict[str, Any]:
    path = await _ensure_gtfs()

    with zipfile.ZipFile(path) as archive:
        rows = _read_csv(
            archive,
            "stops.txt",
        )

    features = []

    for row in rows:
        try:
            latitude = float(row["stop_lat"])
            longitude = float(row["stop_lon"])
        except (KeyError, ValueError, TypeError):
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
                    "stop_id": row.get("stop_id"),
                    "name": row.get("stop_name"),
                    "code": row.get("stop_code"),
                    "island": "tenerife",
                },
            }
        )

        if len(features) >= limit:
            break

    return {
        "type": "FeatureCollection",
        "features": features,
    }


async def fetch_titsa_routes(
    limit: int = 250,
) -> list[dict[str, Any]]:
    path = await _ensure_gtfs()

    with zipfile.ZipFile(path) as archive:
        rows = _read_csv(
            archive,
            "routes.txt",
        )

    return [
        {
            "route_id": row.get("route_id"),
            "short_name": row.get("route_short_name"),
            "long_name": row.get("route_long_name"),
            "type": row.get("route_type"),
            "island": "tenerife",
        }
        for row in rows[:limit]
    ]


def get_transport_overview(island: str) -> dict[str, Any]:
    """Static/persisted transport foundation for an island.

    This intentionally does not pretend to be a live timetable. It exposes the
    transport network we can already serve safely before background jobs/SQL.
    """
    from app.services.ferries import get_ferry_routes
    from app.services.ports import get_ports
    from app.utils.islands import normalize_island

    normalized = normalize_island(island)
    if normalized is None:
        return {
            "island": island,
            "available": False,
            "airports": [],
            "ports": [],
            "ferry_routes": [],
            "local_transit": {"available": False},
        }

    ports_fc = get_ports(normalized)
    ferries = get_ferry_routes(normalized)
    return {
        "island": normalized,
        "available": True,
        "airports": get_airports(normalized),
        "ports": ports_fc.get("features", []),
        "ferry_routes": ferries.get("routes", []),
        "local_transit": {
            "available": normalized == "tenerife",
            "provider": "TITSA" if normalized == "tenerife" else None,
            "persisted_gtfs": normalized == "tenerife",
            "note": (
                "Stops and routes are available from the persisted TITSA GTFS snapshot."
                if normalized == "tenerife"
                else "Local bus GTFS is not integrated for this island yet."
            ),
        },
        "live_timetable": False,
        "note": "Static transport network foundation; live departures are intentionally deferred.",
    }
