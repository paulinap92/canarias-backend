from typing import Any

from app.utils.islands import normalize_island


FERRY_ROUTES: list[dict[str, Any]] = [
    {"id": "tenerife-gran-canaria", "operator": "Fred. Olsen Express", "origin_island": "tenerife", "destination_island": "gran-canaria", "origin_port": "santa-cruz-tenerife", "destination_port": "agaete"},
    {"id": "tenerife-la-gomera", "operator": "Fred. Olsen Express", "origin_island": "tenerife", "destination_island": "la-gomera", "origin_port": "los-cristianos", "destination_port": "san-sebastian-gomera"},
    {"id": "tenerife-la-palma", "operator": "Fred. Olsen Express", "origin_island": "tenerife", "destination_island": "la-palma", "origin_port": "los-cristianos", "destination_port": "santa-cruz-la-palma"},
    {"id": "tenerife-el-hierro", "operator": "Fred. Olsen Express", "origin_island": "tenerife", "destination_island": "el-hierro", "origin_port": "los-cristianos", "destination_port": "la-estaca"},
    {"id": "gran-canaria-fuerteventura", "operator": "Fred. Olsen Express", "origin_island": "gran-canaria", "destination_island": "fuerteventura", "origin_port": "las-palmas", "destination_port": "morro-jable"},
    {"id": "fuerteventura-lanzarote", "operator": "Fred. Olsen Express", "origin_island": "fuerteventura", "destination_island": "lanzarote", "origin_port": "corralejo", "destination_port": "playa-blanca"},
]


def get_ferry_routes(
    island: str | None = None,
) -> dict[str, Any]:
    normalized = normalize_island(island)

    routes = FERRY_ROUTES

    if island is not None:
        if normalized is None:
            routes = []
        else:
            routes = [
                route
                for route in FERRY_ROUTES
                if normalized in {
                    route["origin_island"],
                    route["destination_island"],
                }
            ]

    return {
        "routes": routes,
        "timetable": False,
        "note": (
            "Network only; exact daily departures "
            "will be added from a timetable source later."
        ),
    }
