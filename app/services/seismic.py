from typing import Any

import httpx
from bs4 import BeautifulSoup


IGN_URL = (
    "https://www.ign.es/web/vlc-ultimo-terremoto/"
    "-/terremotos-canarias/get10dias"
)


def _to_float(value: str) -> float | None:
    value = value.strip().replace(",", ".")

    if not value:
        return None

    try:
        return float(value)
    except ValueError:
        return None


async def fetch_canary_earthquakes() -> dict[str, Any]:
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=20.0,
    ) as client:
        response = await client.get(IGN_URL)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    features = []

    for row in soup.select("tr"):
        cells = [
            cell.get_text(" ", strip=True)
            for cell in row.select("td")
        ]

        if len(cells) < 10:
            continue

        event_id = cells[0]
        date = cells[1]
        time_utc = cells[2]

        latitude = _to_float(cells[3])
        longitude = _to_float(cells[4])
        depth_km = _to_float(cells[5])
        magnitude = _to_float(cells[7])

        magnitude_type = cells[8]
        location = cells[9]

        if latitude is None or longitude is None:
            continue

        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    # GeoJSON zawsze: longitude, latitude
                    "coordinates": [
                        longitude,
                        latitude,
                    ],
                },
                "properties": {
                    "event_id": event_id,
                    "date": date,
                    "time_utc": time_utc,
                    "depth_km": depth_km,
                    "magnitude": magnitude,
                    "magnitude_type": magnitude_type,
                    "location": location,
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "features": features,
    }