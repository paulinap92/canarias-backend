from __future__ import annotations

import asyncio
import logging
import os

import httpx


logger = logging.getLogger(__name__)

ISLANDS = [
    "tenerife",
    "gran-canaria",
    "lanzarote",
    "fuerteventura",
    "la-palma",
    "la-gomera",
    "el-hierro",
    "la-graciosa",
]


def _base() -> str:
    explicit = os.getenv("INTERNAL_API_BASE")
    if explicit:
        return explicit.rstrip("/")
    return "http://127.0.0.1:" + os.getenv("PORT", "8000")


async def _get(
    client: httpx.AsyncClient,
    path: str,
) -> None:
    try:
        response = await client.get(f"{_base()}{path}")
        response.raise_for_status()
        logger.info(
            "Cache warmer OK %s cache=%s",
            path,
            response.headers.get("X-Canarias-Cache"),
        )
    except Exception:
        logger.exception("Cache warmer failed: %s", path)


async def _loop(
    paths: list[str],
    interval: int,
    delay: int,
    between: float = 1.0,
) -> None:
    await asyncio.sleep(delay)

    async with httpx.AsyncClient(
        timeout=90.0,
        follow_redirects=True,
    ) as client:
        while True:
            for path in paths:
                await _get(client, path)
                await asyncio.sleep(between)
            await asyncio.sleep(interval)


async def cache_warmer() -> None:
    weather_paths = [
        f"/api/regions/canarias/live/weather?island={island}"
        for island in ISLANDS
    ]
    air_paths = [
        f"/api/regions/canarias/live/air-quality?island={island}"
        for island in ISLANDS
    ]
    tide_paths = [
        f"/api/regions/canarias/live/tides?island={island}&hours=48"
        for island in ISLANDS
    ]

    tasks = [
        asyncio.create_task(
            _loop(
                [
                    "/api/regions/canarias/seismic",
                    "/api/regions/canarias/alerts",
                    "/api/regions/canarias/news?limit=20",
                ],
                600,
                10,
            )
        ),
        asyncio.create_task(
            _loop(weather_paths, 1800, 20, 2.0)
        ),
        asyncio.create_task(
            _loop(air_paths, 3600, 40, 2.0)
        ),
        asyncio.create_task(
            _loop(tide_paths, 3600, 60, 2.0)
        ),
        asyncio.create_task(
            _loop(
                [
                    "/api/regions/canarias/volcanic",
                    "/api/regions/canarias/wildlife?limit=300",
                ],
                21600,
                80,
            )
        ),
        asyncio.create_task(
            _loop(
                [
                    "/api/regions/canarias/places?limit=500",
                    "/api/regions/canarias/beaches?limit=500",
                    "/api/regions/canarias/trails?limit=200",
                ],
                86400,
                100,
            )
        ),
    ]

    try:
        await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            task.cancel()
