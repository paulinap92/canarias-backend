from typing import Any

import httpx


MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"


def _find_extremes(
    times: list[str],
    levels: list[float | None],
) -> list[dict[str, Any]]:
    extremes = []

    for index in range(1, len(levels) - 1):
        previous = levels[index - 1]
        current = levels[index]
        following = levels[index + 1]

        if previous is None or current is None or following is None:
            continue

        if current > previous and current > following:
            extremes.append({"type": "high", "time": times[index], "height_m": current})
        elif current < previous and current < following:
            extremes.append({"type": "low", "time": times[index], "height_m": current})

    return extremes


async def fetch_tides(
    latitude: float,
    longitude: float,
    hours: int = 48,
) -> dict[str, Any]:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "sea_level_height_msl",
        "forecast_hours": hours,
        "timezone": "Atlantic/Canary",
        "cell_selection": "sea",
    }

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        response = await client.get(MARINE_URL, params=params)
        response.raise_for_status()

    data = response.json()
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    levels = hourly.get("sea_level_height_msl", [])

    points = [
        {"time": time, "height_m": level}
        for time, level in zip(times, levels, strict=False)
    ]

    return {
        "latitude": latitude,
        "longitude": longitude,
        "unit": "m",
        "reference": "global_mean_sea_level",
        "includes_tides": True,
        "source": "Open-Meteo Marine",
        "points": points,
        "extremes": _find_extremes(times, levels),
        "navigation_warning": "Model data; coastal accuracy is limited. Not for navigation.",
    }
