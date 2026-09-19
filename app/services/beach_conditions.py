from __future__ import annotations

import asyncio
from typing import Any

import httpx


WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
MAX_LIVE_BEACHES = 24


def _many(data: Any) -> list[dict[str, Any]]:
    return data if isinstance(data, list) else [data]


def _wind_label(degrees: float | int | None) -> str:
    if degrees is None:
        return ""
    names = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]
    return names[int((float(degrees) + 22.5) // 45) % 8]


def _extrema(times: list[str], heights: list[float | None]) -> list[dict[str, Any]]:
    pairs = [(time, height) for time, height in zip(times, heights, strict=False) if height is not None]
    turns: list[dict[str, Any]] = []
    for index in range(1, len(pairs) - 1):
        previous = pairs[index - 1][1]
        time, height = pairs[index]
        following = pairs[index + 1][1]
        if height >= previous and height > following:
            turns.append({"type": "high", "time": time, "height_m": round(float(height), 3)})
        elif height <= previous and height < following:
            turns.append({"type": "low", "time": time, "height_m": round(float(height), 3)})
    return turns


def _priority(feature: dict[str, Any]) -> tuple[int, int, int, str]:
    properties = feature.get("properties") or {}
    try:
        priority = int(properties.get("priority") or 9999)
    except (TypeError, ValueError):
        priority = 9999
    return (
        0 if properties.get("featured") is True else 1,
        priority,
        0 if properties.get("cc_curated") else 1,
        str(properties.get("name") or "").casefold(),
    )


def _published_beach_points(payload: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    features = [
        feature
        for feature in payload.get("features", [])
        if isinstance(feature, dict)
        and (feature.get("geometry") or {}).get("type") == "Point"
        and (feature.get("properties") or {}).get("name")
    ]
    features.sort(key=_priority)

    points: list[dict[str, Any]] = []
    for feature in features[:limit]:
        properties = feature.get("properties") or {}
        coordinates = (feature.get("geometry") or {}).get("coordinates") or []
        if len(coordinates) < 2:
            continue
        longitude = float(coordinates[0])
        latitude = float(coordinates[1])
        beach_id = properties.get("id") or properties.get("osm_id")
        if beach_id is None:
            continue
        points.append(
            {
                "beach_id": str(beach_id),
                "name": properties.get("name"),
                "latitude": latitude,
                "longitude": longitude,
                "featured": properties.get("featured") is True,
                "priority": properties.get("priority"),
                "surface": properties.get("surface"),
                "access": properties.get("access"),
                "wheelchair": properties.get("wheelchair"),
                "lifeguard": properties.get("lifeguard") or properties.get("supervised"),
                "description": properties.get("description") or properties.get("short_description"),
            }
        )
    return points


async def _fetch_weather(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latitudes = ",".join(str(point["latitude"]) for point in points)
    longitudes = ",".join(str(point["longitude"]) for point in points)
    params = {
        "latitude": latitudes,
        "longitude": longitudes,
        "timezone": "Atlantic/Canary",
        "forecast_days": 1,
        "current": ",".join(
            [
                "temperature_2m",
                "apparent_temperature",
                "relative_humidity_2m",
                "cloud_cover",
                "weather_code",
                "wind_speed_10m",
                "wind_direction_10m",
                "wind_gusts_10m",
            ]
        ),
        "daily": "uv_index_max,sunrise,sunset,precipitation_probability_max",
    }
    async with httpx.AsyncClient(
        timeout=35.0,
        follow_redirects=True,
        headers={"User-Agent": "Canarias-Cerca/1.0"},
    ) as client:
        response = await client.get(WEATHER_URL, params=params)
        response.raise_for_status()
        return _many(response.json())


async def _fetch_marine(points: list[dict[str, Any]], hours: int) -> list[dict[str, Any]]:
    latitudes = ",".join(str(point["latitude"]) for point in points)
    longitudes = ",".join(str(point["longitude"]) for point in points)
    params = {
        "latitude": latitudes,
        "longitude": longitudes,
        "timezone": "Atlantic/Canary",
        "cell_selection": "sea",
        "forecast_hours": hours,
        "current": ",".join(
            [
                "wave_height",
                "wave_direction",
                "wave_period",
                "swell_wave_height",
                "swell_wave_direction",
                "swell_wave_period",
                "sea_surface_temperature",
            ]
        ),
        "hourly": "sea_level_height_msl",
    }
    async with httpx.AsyncClient(
        timeout=40.0,
        follow_redirects=True,
        headers={"User-Agent": "Canarias-Cerca/1.0"},
    ) as client:
        response = await client.get(MARINE_URL, params=params)
        response.raise_for_status()
        return _many(response.json())


async def fetch_beach_conditions(
    beaches: dict[str, Any],
    *,
    island: str | None,
    limit: int = MAX_LIVE_BEACHES,
    hours: int = 48,
) -> dict[str, Any]:
    points = _published_beach_points(beaches, max(1, min(limit, MAX_LIVE_BEACHES)))
    if not points:
        return {
            "source": "Canarias Cerca + Open-Meteo",
            "source_type": "model",
            "island": island,
            "points_count": 0,
            "points": [],
        }

    weather_raw, marine_raw = await asyncio.gather(
        _fetch_weather(points),
        _fetch_marine(points, hours),
    )

    result: list[dict[str, Any]] = []
    for index, point in enumerate(points):
        weather = weather_raw[index] if index < len(weather_raw) else {}
        marine = marine_raw[index] if index < len(marine_raw) else {}
        current_weather = weather.get("current") or {}
        daily = weather.get("daily") or {}
        current_marine = marine.get("current") or {}
        hourly = marine.get("hourly") or {}
        turns = _extrema(
            hourly.get("time") or [],
            hourly.get("sea_level_height_msl") or [],
        )
        first = lambda key: (daily.get(key) or [None])[0]

        result.append(
            {
                **point,
                "temperature": current_weather.get("temperature_2m"),
                "apparent_temperature": current_weather.get("apparent_temperature"),
                "humidity": current_weather.get("relative_humidity_2m"),
                "cloud_cover": current_weather.get("cloud_cover"),
                "weather_code": current_weather.get("weather_code"),
                "wind_speed": current_weather.get("wind_speed_10m"),
                "wind_gusts": current_weather.get("wind_gusts_10m"),
                "wind_direction_degrees": current_weather.get("wind_direction_10m"),
                "wind_direction": _wind_label(current_weather.get("wind_direction_10m")),
                "uv_max": first("uv_index_max"),
                "rain_probability": first("precipitation_probability_max"),
                "sunrise": first("sunrise"),
                "sunset": first("sunset"),
                "wave_height": current_marine.get("wave_height"),
                "wave_direction": current_marine.get("wave_direction"),
                "wave_period": current_marine.get("wave_period"),
                "swell_height": current_marine.get("swell_wave_height"),
                "swell_direction": current_marine.get("swell_wave_direction"),
                "swell_period": current_marine.get("swell_wave_period"),
                "sea_temperature": current_marine.get("sea_surface_temperature"),
                "next_high": next((turn for turn in turns if turn["type"] == "high"), None),
                "next_low": next((turn for turn in turns if turn["type"] == "low"), None),
                "tide_turns": turns[:8],
                "updated_at": current_weather.get("time") or current_marine.get("time"),
            }
        )

    return {
        "source": "Canarias Cerca beaches + Open-Meteo + Open-Meteo Marine",
        "source_type": "model",
        "island": island,
        "hours": hours,
        "points_count": len(result),
        "points": result,
        "coverage_note": "Live v1 covers up to 24 published beaches, prioritising featured and editorial beaches.",
        "navigation_warning": "Marine and tide values are model data and are not suitable for navigation or safety decisions.",
    }
