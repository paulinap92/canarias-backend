from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx


ROOT = Path(__file__).resolve().parents[2]
WEATHER_POINTS_FILE = ROOT / "data" / "weather_points.json"
AIR_POINTS_FILE = ROOT / "data" / "air_quality_points.json"
COASTAL_POINTS_FILE = ROOT / "data" / "coastal_points.json"

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"


def _load(path: Path, island: str | None) -> list[dict[str, Any]]:
    points = json.loads(path.read_text(encoding="utf-8"))
    if island:
        points = [p for p in points if p["island"] == island]
    return points


def _coords(points: list[dict[str, Any]]) -> tuple[str, str]:
    return (
        ",".join(str(p["latitude"]) for p in points),
        ",".join(str(p["longitude"]) for p in points),
    )


def _many(data: Any) -> list[dict[str, Any]]:
    return data if isinstance(data, list) else [data]


def _wind_label(degrees: float | int | None) -> str:
    if degrees is None:
        return ""
    names = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]
    return names[int((float(degrees) + 22.5) // 45) % 8]


def _aqi_label(value: float | int | None) -> str | None:
    if value is None:
        return None
    value = float(value)
    if value <= 20:
        return "good"
    if value <= 40:
        return "fair"
    if value <= 60:
        return "moderate"
    if value <= 80:
        return "poor"
    if value <= 100:
        return "very_poor"
    return "extremely_poor"


async def fetch_weather_points(island: str | None = None) -> dict[str, Any]:
    points = _load(WEATHER_POINTS_FILE, island)
    if not points:
        return {"source": "Open-Meteo", "source_type": "model", "island": island, "points_count": 0, "points": []}

    lat, lon = _coords(points)
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": "Atlantic/Canary",
        "forecast_days": 1,
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,uv_index_max,sunrise,sunset,daylight_duration",
    }

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers={"User-Agent":"Canarias-Cerca/1.0"}) as client:
        response = await client.get(WEATHER_URL, params=params)
        response.raise_for_status()
        raw = _many(response.json())

    result = []
    for point, item in zip(points, raw, strict=False):
        current = item.get("current", {})
        daily = item.get("daily", {})
        first = lambda key: (daily.get(key) or [None])[0]
        result.append({
            **point,
            "temperature": current.get("temperature_2m"),
            "apparent_temperature": current.get("apparent_temperature"),
            "humidity": current.get("relative_humidity_2m"),
            "weather_code": current.get("weather_code"),
            "wind_speed": current.get("wind_speed_10m"),
            "wind_direction_degrees": current.get("wind_direction_10m"),
            "wind_direction": _wind_label(current.get("wind_direction_10m")),
            "temperature_min": first("temperature_2m_min"),
            "temperature_max": first("temperature_2m_max"),
            "rain_probability": first("precipitation_probability_max"),
            "uv_max": first("uv_index_max"),
            "sunrise": first("sunrise"),
            "sunset": first("sunset"),
            "daylight_duration_seconds": first("daylight_duration"),
            "updated_at": current.get("time"),
        })

    return {
        "source": "Open-Meteo",
        "source_type": "model",
        "island": island,
        "points_count": len(result),
        "points": result,
    }


async def fetch_air_quality_points(island: str | None = None) -> dict[str, Any]:
    points = _load(AIR_POINTS_FILE, island)
    if not points:
        return {"source":"Open-Meteo / CAMS","source_type":"model","island":island,"points_count":0,"points":[]}

    lat, lon = _coords(points)
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": "Atlantic/Canary",
        "domains": "auto",
        "current": "pm10,pm2_5,dust,european_aqi,nitrogen_dioxide,ozone",
    }

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers={"User-Agent":"Canarias-Cerca/1.0"}) as client:
        response = await client.get(AIR_URL, params=params)
        response.raise_for_status()
        raw = _many(response.json())

    result = []
    for point, item in zip(points, raw, strict=False):
        current = item.get("current", {})
        aqi = current.get("european_aqi")
        result.append({
            **point,
            "pm10": current.get("pm10"),
            "pm25": current.get("pm2_5"),
            "dust": current.get("dust"),
            "european_aqi": aqi,
            "aqi_level": _aqi_label(aqi),
            "no2": current.get("nitrogen_dioxide"),
            "o3": current.get("ozone"),
            "updated_at": current.get("time"),
        })

    return {
        "source": "Open-Meteo / CAMS",
        "source_type": "model",
        "model_resolution_note": "Modeled air-quality data; not an observed Gobierno monitoring-station measurement.",
        "island": island,
        "points_count": len(result),
        "points": result,
    }


def _extrema(times: list[str], heights: list[float | None]) -> list[dict[str, Any]]:
    pairs = [(t,h) for t,h in zip(times, heights, strict=False) if h is not None]
    turns = []
    for i in range(1, len(pairs)-1):
        p = pairs[i-1][1]
        t, h = pairs[i]
        n = pairs[i+1][1]
        if h >= p and h > n:
            turns.append({"type":"high","time":t,"height_m":round(float(h),3)})
        elif h <= p and h < n:
            turns.append({"type":"low","time":t,"height_m":round(float(h),3)})
    return turns


async def fetch_tide_points(island: str | None = None, hours: int = 48) -> dict[str, Any]:
    points = _load(COASTAL_POINTS_FILE, island)
    if not points:
        return {"source":"Open-Meteo Marine","source_type":"model","island":island,"hours":hours,"points_count":0,"points":[]}

    lat, lon = _coords(points)
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": "Atlantic/Canary",
        "forecast_hours": hours,
        "cell_selection": "sea",
        "hourly": "sea_level_height_msl",
    }

    async with httpx.AsyncClient(timeout=35.0, follow_redirects=True, headers={"User-Agent":"Canarias-Cerca/1.0"}) as client:
        response = await client.get(MARINE_URL, params=params)
        response.raise_for_status()
        raw = _many(response.json())

    result = []
    for point, item in zip(points, raw, strict=False):
        hourly = item.get("hourly", {})
        turns = _extrema(hourly.get("time", []), hourly.get("sea_level_height_msl", []))
        result.append({
            **point,
            "turns": turns[:8],
            "next_high": next((x for x in turns if x["type"]=="high"), None),
            "next_low": next((x for x in turns if x["type"]=="low"), None),
        })

    return {
        "source": "Open-Meteo Marine",
        "source_type": "model",
        "island": island,
        "hours": hours,
        "navigation_warning": "Modeled sea-level height including tides. Coastal accuracy is limited; not suitable for coastal navigation.",
        "points_count": len(result),
        "points": result,
    }
