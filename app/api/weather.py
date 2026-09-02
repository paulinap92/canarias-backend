import asyncio
import json
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from app.services.aemet import fetch_daily_forecast


router = APIRouter(
    prefix="/api/regions/canarias",
    tags=["weather"],
)


DATA_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "cities.json"
)


# Cache pogodowy w pamięci aplikacji.
# Dane dla każdego miasta trzymamy przez 30 minut.
WEATHER_CACHE: dict[str, dict[str, Any]] = {}
CACHE_TTL = 30 * 60


def load_cities() -> list[dict[str, Any]]:
    with DATA_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def parse_weather(
    data: list[dict[str, Any]],
    city: dict[str, Any],
) -> dict[str, Any]:
    forecast = data[0]
    today = forecast["prediccion"]["dia"][0]

    condition = next(
        (
            item
            for item in today["estadoCielo"]
            if item.get("descripcion")
        ),
        {},
    )

    wind = next(
        (
            item
            for item in today["viento"]
            if item.get("direccion")
            and item.get("velocidad", 0) > 0
        ),
        {},
    )

    return {
        "city": city["name"],
        "slug": city["slug"],
        "island": city["island"],
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "updated_at": forecast["elaborado"],
        "date": today["fecha"],
        "temperature_min": today["temperatura"]["minima"],
        "temperature_max": today["temperatura"]["maxima"],
        "humidity_min": today["humedadRelativa"]["minima"],
        "humidity_max": today["humedadRelativa"]["maxima"],
        "uv_max": today["uvMax"],
        "condition": condition.get("descripcion", ""),
        "rain_probability": today["probPrecipitacion"][0]["value"],
        "wind_direction": wind.get("direccion", ""),
        "wind_speed": wind.get("velocidad", 0),
    }


async def get_cached_weather(
    city: dict[str, Any],
) -> dict[str, Any]:
    slug = city["slug"]

    cached = WEATHER_CACHE.get(slug)

    if cached is not None:
        age = time.time() - cached["cached_at"]

        if age < CACHE_TTL:
            return cached["data"]

    data = await fetch_daily_forecast(
        city["aemet_code"]
    )

    weather = parse_weather(
        data,
        city,
    )

    WEATHER_CACHE[slug] = {
        "cached_at": time.time(),
        "data": weather,
    }

    return weather


@router.get("/cities/weather")
async def get_all_cities_weather() -> list[dict[str, Any]]:
    cities = load_cities()

    result = []

    for city in cities:
        weather = await get_cached_weather(city)

        result.append(weather)

        # Nie bombardujemy AEMET requestami.
        # Jeśli dane były w cache, ten sleep jest trochę zbędny,
        # ale na tym etapie zostawiamy rozwiązanie proste.
        await asyncio.sleep(2)

    return result


@router.get("/cities/{city_slug}/weather")
async def get_city_weather(
    city_slug: str,
) -> dict[str, Any]:
    cities = load_cities()

    city = next(
        (
            city
            for city in cities
            if city["slug"] == city_slug
        ),
        None,
    )

    if city is None:
        raise HTTPException(
            status_code=404,
            detail="City not found",
        )

    return await get_cached_weather(city)


# Stary endpoint zostawiamy,
# żeby obecny frontend nadal działał.
@router.get("/islands/tenerife/weather")
async def get_tenerife_weather() -> dict[str, Any]:
    cities = load_cities()

    city = next(
        city
        for city in cities
        if city["slug"] == "santa-cruz-de-tenerife"
    )

    return await get_cached_weather(city)