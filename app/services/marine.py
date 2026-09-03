from typing import Any

import httpx


MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"


async def fetch_marine(
    latitude: float,
    longitude: float,
) -> dict[str, Any]:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ",".join(
            [
                "wave_height",
                "wave_direction",
                "wave_period",
                "swell_wave_height",
                "swell_wave_direction",
                "swell_wave_period",
                "sea_surface_temperature",
                "ocean_current_velocity",
                "ocean_current_direction",
            ]
        ),
        "timezone": "Atlantic/Canary",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            MARINE_URL,
            params=params,
        )

        response.raise_for_status()

        data = response.json()

    current = data["current"]

    return {
        "latitude": latitude,
        "longitude": longitude,
        "updated_at": current["time"],
        "wave_height": current.get("wave_height"),
        "wave_direction": current.get("wave_direction"),
        "wave_period": current.get("wave_period"),
        "swell_height": current.get("swell_wave_height"),
        "swell_direction": current.get("swell_wave_direction"),
        "swell_period": current.get("swell_wave_period"),
        "sea_temperature": current.get("sea_surface_temperature"),
        "current_velocity": current.get("ocean_current_velocity"),
        "current_direction": current.get("ocean_current_direction"),
    }