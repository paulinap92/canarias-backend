from __future__ import annotations

import asyncio
import logging
import os

import httpx


logger = logging.getLogger(__name__)


CITY_SLUGS = [
    "santa-cruz-de-tenerife",
    "puerto-de-la-cruz",
    "las-palmas-de-gran-canaria",
    "arrecife",
    "puerto-del-rosario",
    "san-sebastian-de-la-gomera",
    "santa-cruz-de-la-palma",
    "valverde",
]


def _base() -> str:
    explicit = os.getenv("INTERNAL_API_BASE")

    if explicit:
        return explicit.rstrip("/")

    return (
        "http://127.0.0.1:"
        + os.getenv("PORT", "8000")
    )


async def _loop(
    paths: list[str],
    interval: int,
    delay: int,
) -> None:
    await asyncio.sleep(delay)

    async with httpx.AsyncClient(
        timeout=90.0,
        follow_redirects=True,
    ) as client:
        while True:
            for path in paths:
                try:
                    response = await client.get(
                        f"{_base()}{path}"
                    )
                    response.raise_for_status()
                except Exception:
                    logger.exception(
                        "Cache warmer failed: %s",
                        path,
                    )

            await asyncio.sleep(interval)


async def cache_warmer() -> None:
    tasks = [
        asyncio.create_task(
            _loop(
                [
                    "/api/regions/canarias/seismic",
                    "/api/regions/canarias/alerts?limit=20",
                    "/api/regions/canarias/news?limit=20",
                ],
                600,
                10,
            )
        ),
        asyncio.create_task(
            _loop(
                [
                    f"/api/regions/canarias/cities/{slug}/weather"
                    for slug in CITY_SLUGS
                ],
                1800,
                20,
            )
        ),
        asyncio.create_task(
            _loop(
                [
                    "/api/regions/canarias/islands/tenerife/air-quality",
                ],
                900,
                30,
            )
        ),
        asyncio.create_task(
            _loop(
                [
                    "/api/regions/canarias/volcanic",
                    "/api/regions/canarias/wildlife?limit=300",
                ],
                21600,
                40,
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
                50,
            )
        ),
    ]

    try:
        await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            task.cancel()
